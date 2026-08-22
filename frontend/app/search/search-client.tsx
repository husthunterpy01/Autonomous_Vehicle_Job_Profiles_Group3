"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AV_CATEGORIES, MOCK_JOBS, type Job } from "@/lib/mock-data";
import type { DropdownOption } from "@/components/ui/Dropdown";
import JobCardRow from "@/components/ui/JobCardRow";
import JobTable, {
  type JobSortDirection,
  type JobSortKey,
  type JobSortRule,
} from "@/components/ui/JobTable";
import PageHeader from "@/components/ui/PageHeader";
import Pagination from "@/components/ui/Pagination";
import SearchBar from "@/components/ui/SearchBar";
import ViewToggle, { type ViewMode } from "@/components/ui/ViewToggle";

const CATEGORY_OPTIONS: DropdownOption[] = [
  { value: "All", label: "All Categories" },
  ...AV_CATEGORIES.map((c) => ({ value: c.name, label: c.name })),
];

const DEFAULT_PER_PAGE = 6;

function compareJobs(a: Job, b: Job, key: JobSortKey): number {
  if (key === "salary") {
    return a.salaryMin - b.salaryMin;
  }

  const values: Record<Exclude<JobSortKey, "salary">, string> = {
    role: a.title,
    company: a.company,
    location: a.country,
    status: a.status,
    type: a.type,
    category: a.category,
  };
  const otherValues: Record<Exclude<JobSortKey, "salary">, string> = {
    role: b.title,
    company: b.company,
    location: b.country,
    status: b.status,
    type: b.type,
    category: b.category,
  };

  return values[key].localeCompare(otherValues[key], undefined, {
    sensitivity: "base",
  });
}

export default function SearchClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [keyword, setKeyword] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState(() => {
    const value = searchParams.get("category");
    return value && AV_CATEGORIES.some((c) => c.name === value) ? value : "All";
  });
  const [view, setView] = useState<ViewMode>("table");
  const [sorts, setSorts] = useState<JobSortRule[]>([]);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);
  const [perPageInput, setPerPageInput] = useState(String(DEFAULT_PER_PAGE));

  const hasFilters = keyword.trim() !== "" || category !== "All";

  const syncUrl = (kw: string, cat: string) => {
    const params = new URLSearchParams();
    if (kw.trim()) params.set("q", kw.trim());
    if (cat !== "All") params.set("category", cat);
    const qs = params.toString();
    router.replace(qs ? `/search?${qs}` : "/search");
  };

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return MOCK_JOBS.filter((job) => {
      const matchesCategory = category === "All" || job.category === category;
      const matchesKeyword =
        kw === "" ||
        job.title.toLowerCase().includes(kw) ||
        job.company.toLowerCase().includes(kw) ||
        job.country.toLowerCase().includes(kw) ||
        job.category.toLowerCase().includes(kw) ||
        job.type.toLowerCase().includes(kw);
      return matchesCategory && matchesKeyword;
    });
  }, [keyword, category]);

  const sorted = useMemo(() => {
    if (sorts.length === 0) return filtered;

    return [...filtered].sort((a, b) => {
      for (const sort of sorts) {
        const comparison = compareJobs(a, b, sort.key);
        if (comparison !== 0) {
          return sort.direction === "asc" ? comparison : -comparison;
        }
      }
      return 0;
    });
  }, [filtered, sorts]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / perPage));
  const safePage = Math.min(page, pageCount);
  const pageItems = sorted.slice(
    (safePage - 1) * perPage,
    safePage * perPage,
  );

  const handleKeyword = (value: string) => {
    setKeyword(value);
    setPage(1);
  };

  const handleCategory = (value: string) => {
    setCategory(value);
    setPage(1);
  };

  const handleSort = (key: JobSortKey, additive: boolean) => {
    setSorts((current) => {
      const existingIndex = current.findIndex((sort) => sort.key === key);

      if (!additive) {
        const existing = current[existingIndex];
        const direction: JobSortDirection =
          existingIndex === 0 && existing?.direction === "asc" ? "desc" : "asc";
        return [{ key, direction }];
      }

      if (existingIndex >= 0) {
        return current.map((sort, index) =>
          index === existingIndex
            ? {
                ...sort,
                direction: sort.direction === "asc" ? "desc" : "asc",
              }
            : sort,
        );
      }

      return [...current, { key, direction: "asc" }];
    });
    setPage(1);
  };

  const handlePerPageInput = (raw: string) => {
    setPerPageInput(raw);
    const next = Number(raw);
    if (Number.isInteger(next) && next >= 1) {
      setPerPage(next);
      setPage(1);
    }
  };

  const normalizePerPage = () => {
    const next = Number(perPageInput);
    if (!Number.isInteger(next) || next < 1) {
      setPerPageInput(String(perPage));
      return;
    }
    setPerPage(next);
    setPerPageInput(String(next));
    setPage(1);
  };

  const resetFilters = () => {
    setKeyword("");
    setCategory("All");
    setPage(1);
    router.replace("/search");
  };

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <PageHeader
        title="Find your next job"
        subtitle="Search and filter autonomous vehicle job openings."
      />

      <div>
        <SearchBar
          className="mt-0"
          keyword={keyword}
          onKeywordChange={handleKeyword}
          placeholder="Job title, skill or keyword"
          dropdownValue={category}
          onDropdownChange={handleCategory}
          dropdownOptions={CATEGORY_OPTIONS}
          dropdownClassName="lg:w-56"
          onSubmit={(e) => {
            e.preventDefault();
            syncUrl(keyword, category);
          }}
        />
        <div className="mt-4 flex justify-end">
          <ViewToggle view={view} onChange={setView} />
        </div>
      </div>

      <div className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink-secondary">
            <span className="font-semibold text-ink">{sorted.length}</span>{" "}
            {sorted.length === 1 ? "job" : "jobs"} found
            {category !== "All" ? ` in ${category}` : ""}
            {keyword.trim() !== "" ? ` for "${keyword.trim()}"` : ""}
          </p>
          {view === "table" && (
            <p className="w-full text-sm leading-6 text-ink-secondary">
              Click a column to sort. Hold{" "}
              <span className="rounded-md bg-primary-light px-1.5 py-0.5 font-semibold text-primary">
                Shift
              </span>{" "}
              while clicking to add a secondary sort.
            </p>
          )}
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

        {sorted.length > 0 && (
          <>
            <div className="mt-4">
              {view === "table" ? (
                <JobTable
                  jobs={pageItems}
                  sorts={sorts}
                  onSort={handleSort}
                />
              ) : (
                <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                  {pageItems.map((job) => (
                    <JobCardRow key={job.id} job={job} />
                  ))}
                </div>
              )}
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  value={perPageInput}
                  onChange={(e) => handlePerPageInput(e.target.value)}
                  onBlur={normalizePerPage}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") normalizePerPage();
                  }}
                  aria-label="Results per page"
                  className="w-24 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <span className="text-xs text-ink-muted">per page</span>
              </div>
              <Pagination
                page={safePage}
                pageCount={pageCount}
                onPageChange={setPage}
                alwaysVisible
              />
            </div>
          </>
        )}

        {sorted.length === 0 && (
          <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
            <p className="font-semibold text-ink">No jobs found</p>
            <p className="mt-2 text-sm text-ink-secondary">
              Try a different keyword or category.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
