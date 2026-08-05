"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AV_COMPANIES, type CompanyType } from "@/lib/mock-data";
import Dropdown, { type DropdownOption } from "@/components/ui/Dropdown";
import CompanyCard from "@/components/ui/CompanyCard";
import PageHeader from "@/components/ui/PageHeader";
import Pagination from "@/components/ui/Pagination";
import SearchBar from "@/components/ui/SearchBar";

const PAGE_SIZE_OPTIONS: DropdownOption[] = [
  { value: "12", label: "12 per page" },
  { value: "24", label: "24 per page" },
  { value: "48", label: "48 per page" },
];

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
  const [pageSize, setPageSize] = useState(12);
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
    setType(value as "All" | CompanyType);
    setPage(1);
  };

  const handlePageSize = (value: string) => {
    setPageSize(Number(value));
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

      {/* Results */}
      <div className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-ink-secondary">
            <span className="font-semibold text-ink">{filtered.length}</span>{" "}
            {filtered.length === 1 ? "company" : "companies"} found
            {type !== "All" ? ` · ${type}` : ""}
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
            <Dropdown
              value={String(pageSize)}
              onChange={handlePageSize}
              options={PAGE_SIZE_OPTIONS}
              className="w-36"
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {pageItems.map((company) => (
            <CompanyCard key={company.id} company={company} />
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

        <Pagination page={safePage} pageCount={pageCount} onPageChange={setPage} />
      </div>
    </div>
  );
}
