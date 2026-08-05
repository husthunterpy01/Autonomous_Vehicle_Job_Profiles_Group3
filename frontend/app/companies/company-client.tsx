"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AV_COMPANIES, type CompanyType } from "@/lib/mock-data";
import Dropdown, { type DropdownOption } from "@/components/ui/Dropdown";
import CompanyCard from "@/components/ui/CompanyCard";

const PAGE_SIZE = 12;

const COMPANY_TYPE_OPTIONS: DropdownOption[] = [
  { value: "All", label: "All Company Types" },
  { value: "AV Startup", label: "AV Startup" },
  { value: "OEM", label: "OEM" },
  { value: "Tier 1 Supplier", label: "Tier 1 Supplier" },
  { value: "Tech Giant", label: "Tech Giant" },
];

export default function CompanyClient({
  initialKeyword = "",
  initialType = "All",
}: {
  initialKeyword?: string;
  initialType?: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [type, setType] = useState<"All" | CompanyType>(
    COMPANY_TYPE_OPTIONS.some((o) => o.value === initialType)
      ? (initialType as "All" | CompanyType)
      : "All",
  );
  const [page, setPage] = useState(1);

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
    return AV_COMPANIES.filter((company) => {
      const matchesType = type === "All" || company.type === type;
      const matchesKeyword =
        kw === "" || company.name.toLowerCase().includes(kw);
      return matchesType && matchesKeyword;
    });
  }, [keyword, type]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageItems = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE,
  );

  const handleKeyword = (value: string) => {
    setKeyword(value);
    setPage(1);
  };

  const handleType = (value: string) => {
    setType(value as "All" | CompanyType);
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
      <h1 className="text-3xl font-bold tracking-tight text-ink">
        Explore Companies
      </h1>
      <p className="mt-2 text-ink-secondary">
        Browse the autonomous vehicle companies tracked by this platform.
      </p>

      {/* Search + filter */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          syncUrl(keyword, type);
        }}
        className="mt-8 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 shadow-sm lg:flex-row lg:items-center"
      >
        <input
          type="text"
          value={keyword}
          onChange={(e) => handleKeyword(e.target.value)}
          placeholder="Search companies..."
          className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
        />
        <Dropdown
          value={type}
          onChange={handleType}
          options={COMPANY_TYPE_OPTIONS}
          className="lg:w-56"
        />
      </form>

      {/* Results */}
      <div className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink-secondary">
            <span className="font-semibold text-ink">{filtered.length}</span>{" "}
            {filtered.length === 1 ? "company" : "companies"} found
            {type !== "All" ? ` · ${type}` : ""}
          </p>
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

        <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {pageItems.map((company) => (
            <CompanyCard key={company.name} company={company} />
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

        {/* Pagination */}
        {filtered.length > PAGE_SIZE && (
          <div className="mt-10 flex items-center justify-center gap-4">
            <button
              type="button"
              disabled={safePage === 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:border-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            <span className="text-sm text-ink-secondary">
              Page {safePage} of {pageCount}
            </span>
            <button
              type="button"
              disabled={safePage === pageCount}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:border-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
