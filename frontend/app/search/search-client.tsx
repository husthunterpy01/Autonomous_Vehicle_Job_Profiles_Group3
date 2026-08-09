"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AV_CATEGORIES, MOCK_JOBS } from "@/lib/mock-data";
import type { DropdownOption } from "@/components/ui/Dropdown";
import JobCardRow from "@/components/ui/JobCardRow";
import PageHeader from "@/components/ui/PageHeader";
import SearchBar from "@/components/ui/SearchBar";

const CATEGORY_OPTIONS: DropdownOption[] = [
  { value: "All", label: "All Categories" },
  ...AV_CATEGORIES.map((c) => ({ value: c.name, label: c.name })),
];

export default function SearchClient({
  initialKeyword = "",
  initialCategory = "All",
}: {
  initialKeyword?: string;
  initialCategory?: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [category, setCategory] = useState(
    AV_CATEGORIES.some((c) => c.name === initialCategory)
      ? initialCategory
      : "All",
  );

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
      <PageHeader
        title="Find your next job"
        subtitle="Search and filter autonomous vehicle job openings."
      />

      <SearchBar
        keyword={keyword}
        onKeywordChange={setKeyword}
        placeholder="Job title, skill or keyword"
        dropdownValue={category}
        onDropdownChange={setCategory}
        dropdownOptions={CATEGORY_OPTIONS}
        dropdownClassName="lg:w-56"
        onSubmit={(e) => {
          e.preventDefault();
          syncUrl(keyword, category);
        }}
      />

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
            <JobCardRow key={job.id} job={job} />
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
