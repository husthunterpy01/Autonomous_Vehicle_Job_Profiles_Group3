"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AV_CATEGORIES, MOCK_JOBS } from "@/lib/mock-data";
import { JobCardRow } from "@/components/job-ui";

export default function SearchClient({
  initialKeyword,
  initialCategory,
}: {
  initialKeyword: string;
  initialCategory: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [category, setCategory] = useState(
    AV_CATEGORIES.some((c) => c.name === initialCategory)
      ? initialCategory
      : "All",
  );
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const hasFilters = keyword.trim() !== "" || category !== "All";

  const syncUrl = (kw: string, cat: string) => {
    const params = new URLSearchParams();
    if (kw.trim()) params.set("q", kw.trim());
    if (cat !== "All") params.set("category", cat);
    const qs = params.toString();
    router.replace(qs ? `/search?${qs}` : "/search");
  };

  const results = useMemo(() => {
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

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <h1 className="text-3xl font-bold tracking-tight text-ink">
        Find your next job
      </h1>
      <p className="mt-2 text-ink-secondary">
        Search and filter autonomous vehicle job openings.
      </p>

      {/* Search area */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          syncUrl(keyword, category);
        }}
        className="mt-8 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 shadow-sm lg:flex-row lg:items-center"
      >
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Job title, skill or keyword"
          className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
        />

        {/* Category dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen((open) => !open)}
            className="flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary lg:w-56"
          >
            {category === "All" ? "All Categories" : category}
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
              {/* click-away backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setDropdownOpen(false)}
              />
              <div className="absolute left-0 right-0 z-20 mt-2 max-h-72 overflow-y-auto rounded-xl border border-line bg-surface p-2 shadow-lg">
                <button
                  type="button"
                  onClick={() => {
                    setCategory("All");
                    setDropdownOpen(false);
                  }}
                  className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    category === "All"
                      ? "bg-primary-light font-medium text-primary"
                      : "text-ink-secondary hover:bg-section hover:text-ink"
                  }`}
                >
                  All Categories
                </button>
                {AV_CATEGORIES.map((c) => (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => {
                      setCategory(c.name);
                      setDropdownOpen(false);
                    }}
                    className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                      category === c.name
                        ? "bg-primary-light font-medium text-primary"
                        : "text-ink-secondary hover:bg-section hover:text-ink"
                    }`}
                  >
                    {c.name}
                    <span className="ml-2 text-xs text-ink-muted">
                      {c.jobs}
                    </span>
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
            {results.length === 1 ? "job" : "jobs"} found
            {category !== "All" ? ` in ${category}` : ""}
            {keyword.trim() !== "" ? ` for "${keyword.trim()}"` : ""}
          </p>
          {hasFilters && (
            <button
              type="button"
              onClick={() => {
                setKeyword("");
                setCategory("All");
                router.replace("/search");
              }}
              className="text-sm font-medium text-primary hover:text-primary-hover"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {results.map((job) => (
            <JobCardRow key={job.title} job={job} />
          ))}
        </div>

        {results.length === 0 && (
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
