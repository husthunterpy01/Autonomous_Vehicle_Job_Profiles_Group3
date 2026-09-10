"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { DropdownOption } from "@/components/ui/Dropdown";
import CompanyCard, { type CompanyCardData } from "@/components/ui/CompanyCard";
import PageHeader from "@/components/ui/PageHeader";
import Pagination from "@/components/ui/Pagination";
import SearchBar from "@/components/ui/SearchBar";
import { ApiError } from "@/lib/services/api";
import { COMPANY_TYPE_LABELS, getCompaniesWithJobCounts } from "@/lib/services/company";

const COMPANY_TYPE_OPTIONS: DropdownOption[] = [
  { value: "All", label: "All Company Types" },
  ...Object.entries(COMPANY_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

export default function CompanyClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [keyword, setKeyword] = useState(searchParams.get("q") ?? "");
  const [type, setType] = useState(() => {
    const value = searchParams.get("type");
    return COMPANY_TYPE_OPTIONS.some((o) => o.value === value)
      ? (value as string)
      : "All";
  });
  const [pageSize, setPageSize] = useState(12);
  const [pageSizeInput, setPageSizeInput] = useState("12");
  const [page, setPage] = useState(1);

  const [companies, setCompanies] = useState<CompanyCardData[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    // Backend caps page_size at 100, which covers the ~40 companies seeded
    // today. This list will need real server-side pagination once it grows
    // past that (the with-job-counts endpoint already supports page/page_size).
    getCompaniesWithJobCounts(1, 100)
      .then((response) => {
        if (cancelled) return;
        setCompanies(
          response.items.map((item) => ({
            id: item.company_id,
            name: item.name,
            type: item.company_type,
            country: item.location,
            openPositions: item.number_of_jobs,
          })),
        );
        setStatus("success");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "Something went wrong loading companies. Please try again.",
        );
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const hasFilters = keyword.trim() !== "" || type !== "All";

  const syncUrl = (kw: string, t: string) => {
    const params = new URLSearchParams();
    if (kw.trim()) params.set("q", kw.trim());
    if (t !== "All") params.set("type", t);
    const qs = params.toString();
    router.replace(qs ? `/companies?${qs}` : "/companies");
  };

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return companies.filter((company) => {
      const matchesType = type === "All" || company.type === type;
      const matchesKeyword =
        kw === "" || company.name.toLowerCase().includes(kw);
      return matchesType && matchesKeyword;
    });
  }, [companies, keyword, type]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const pageItems = filtered.slice(
    (safePage - 1) * pageSize,
    safePage * pageSize,
  );

  const handleKeyword = (value: string) => {
    setKeyword(value);
    setPage(1);
  };

  const handleType = (value: string) => {
    setType(value);
    setPage(1);
  };

  const handlePageSize = (raw: string) => {
    const n = Math.max(1, Math.floor(Number(raw) || 1));
    setPageSize(n);
    setPageSizeInput(String(n));
    setPage(1);
  };

  const resetFilters = () => {
    setKeyword("");
    setType("All");
    setPage(1);
    router.replace("/companies");
  };

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <PageHeader
        title="Explore Companies"
        subtitle="Browse the autonomous vehicle companies tracked by this platform."
      />

      <SearchBar
        keyword={keyword}
        onKeywordChange={handleKeyword}
        placeholder="Search companies..."
        dropdownValue={type}
        onDropdownChange={handleType}
        dropdownOptions={COMPANY_TYPE_OPTIONS}
        dropdownClassName="lg:w-56"
        onSubmit={(e) => {
          e.preventDefault();
          syncUrl(keyword, type);
        }}
      />

      {status === "loading" && (
        <div
          aria-busy="true"
          className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center"
        >
          <p className="font-semibold text-ink">Loading companies…</p>
        </div>
      )}

      {status === "error" && (
        <div
          role="alert"
          className="mt-10 rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
        >
          <p className="font-semibold text-warning">
            Couldn&apos;t load companies
          </p>
          <p className="mt-2 text-sm text-ink-secondary">{errorMessage}</p>
          <button
            type="button"
            onClick={() => {
              setStatus("loading");
              setErrorMessage(null);
              setReloadToken((n) => n + 1);
            }}
            className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
          >
            Try again
          </button>
        </div>
      )}

      {status === "success" && (
        <div className="mt-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-secondary">
              <span className="font-semibold text-ink">
                {filtered.length}
              </span>{" "}
              {filtered.length === 1 ? "company" : "companies"} found
              {type !== "All" ? ` · ${COMPANY_TYPE_LABELS[type]}` : ""}
            </p>
            <div className="flex items-center gap-3">
              {hasFilters && (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="text-sm font-medium text-primary hover:text-primary-hover"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {pageItems.map((company) => (
              <CompanyCard
                key={company.id}
                company={{
                  ...company,
                  type: COMPANY_TYPE_LABELS[company.type] ?? company.type,
                }}
              />
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
              <p className="font-semibold text-ink">No companies found</p>
              <p className="mt-2 text-sm text-ink-secondary">
                Try a different name or company type.
              </p>
            </div>
          )}

          {/* Bottom bar: page size selector (left) + pagination (right) */}
          {filtered.length > 0 && (
            <div className="mt-10 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  value={pageSizeInput}
                  onChange={(e) => setPageSizeInput(e.target.value)}
                  onBlur={() => handlePageSize(pageSizeInput)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handlePageSize(pageSizeInput);
                  }}
                  className="w-24 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-primary"
                />
                <span className="text-xs text-ink-muted">per page</span>
              </div>
              <Pagination
                page={safePage}
                pageCount={pageCount}
                onPageChange={setPage}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
