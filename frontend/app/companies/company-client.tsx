"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AV_COMPANIES, type CompanyType } from "@/lib/mock-data";
import { CompanyLogo } from "@/components/job-ui";

const COMPANY_TYPES: ("All" | CompanyType)[] = [
  "All",
  "AV Startup",
  "OEM",
  "Tier 1 Supplier",
  "Tech Giant",
];

export default function CompanyClient({
  initialKeyword,
  initialType,
}: {
  initialKeyword: string;
  initialType: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [type, setType] = useState<"All" | CompanyType>(
    COMPANY_TYPES.includes(initialType as CompanyType) ? (initialType as "All" | CompanyType) : "All",
  );
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const hasFilters = keyword.trim() !== "" || type !== "All";

  const syncUrl = (kw: string, t: string) => {
    const params = new URLSearchParams();
    if (kw.trim()) params.set("q", kw.trim());
    if (t !== "All") params.set("type", t);
    const qs = params.toString();
    router.replace(qs ? `/companies?${qs}` : "/companies");
  };

  const results = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return AV_COMPANIES.filter((company) => {
      const matchesType = type === "All" || company.type === type;
      const matchesKeyword =
        kw === "" || company.name.toLowerCase().includes(kw);
      return matchesType && matchesKeyword;
    });
  }, [keyword, type]);

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
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Search companies..."
          className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
        />

        {/* Company type dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen((open) => !open)}
            className="flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary lg:w-56"
          >
            {type === "All" ? "All Company Types" : type}
            <svg
              className={`h-4 w-4 text-ink-muted transition-transform ${dropdownOpen ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
            </svg>
          </button>

          {dropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setDropdownOpen(false)}
              />
              <div className="absolute left-0 right-0 z-20 mt-2 rounded-xl border border-line bg-surface p-2 shadow-lg">
                {COMPANY_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      setType(t);
                      setDropdownOpen(false);
                    }}
                    className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                      type === t
                        ? "bg-primary-light font-medium text-primary"
                        : "text-ink-secondary hover:bg-section hover:text-ink"
                    }`}
                  >
                    {t === "All" ? "All Company Types" : t}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </form>

      {/* Results */}
      <div className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink-secondary">
            <span className="font-semibold text-ink">{results.length}</span>{" "}
            {results.length === 1 ? "company" : "companies"} found
            {type !== "All" ? ` · ${type}` : ""}
          </p>
          {hasFilters && (
            <button
              type="button"
              onClick={() => {
                setKeyword("");
                setType("All");
                router.replace("/companies");
              }}
              className="text-sm font-medium text-primary hover:text-primary-hover"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {results.map((company) => (
            <Link
              key={company.name}
              href="/companies"
              className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
            >
              <CompanyLogo text={company.name.charAt(0)} />
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-ink">{company.name}</h3>
                <p className="mt-1 text-sm text-ink-secondary">
                  {company.type} · {company.country}
                </p>
                <p className="mt-2 text-sm text-ink-muted">
                  {company.openPositions} open positions
                </p>
              </div>
            </Link>
          ))}
        </div>

        {results.length === 0 && (
          <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
            <p className="font-semibold text-ink">No companies found</p>
            <p className="mt-2 text-sm text-ink-secondary">
              Try a different name or company type.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
