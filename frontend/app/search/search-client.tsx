"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CompanyLogo from "@/components/ui/CompanyLogo";
import PageHeader from "@/components/ui/PageHeader";
import Pagination from "@/components/ui/Pagination";
import SearchBar from "@/components/ui/SearchBar";
import Tag from "@/components/ui/Tag";
import ViewToggle, { type ViewMode } from "@/components/ui/ViewToggle";
import { ApiError } from "@/lib/services/api";
import {
  EMPLOYMENT_TYPE_LABELS,
  getJobs,
  type JobListItem,
} from "@/lib/services/job";

const DEFAULT_PER_PAGE = 6;
/* Debounce keyword input before hitting the API — unlike the Companies list
   (fetched once, filtered client-side), jobs are paginated server-side, so
   every keystroke would otherwise be a new request. */
const SEARCH_DEBOUNCE_MS = 400;

function locationLabel(job: JobListItem): string {
  return job.locations.length > 0
    ? job.locations.join(", ")
    : "Location not specified";
}

function typeLabel(job: JobListItem): string | null {
  return job.employment_type != null
    ? (EMPLOYMENT_TYPE_LABELS[job.employment_type] ?? "Other")
    : null;
}

function postedLabel(job: JobListItem): string {
  if (!job.posted_date) return "Date unknown";
  return new Date(job.posted_date).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function JobRow({ job }: { job: JobListItem }) {
  const type = typeLabel(job);
  return (
    // Not a Link: job detail pages are still mock-only (static export
    // requires every dynamic route known at build time), so a real job id
    // would 404/crash. Re-enable once /jobs/[id] is wired to the real API.
    <div className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5">
      <CompanyLogo text={job.company_name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{job.title}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {job.company_name} · {locationLabel(job)}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {type && <Tag label={type} />}
          <span className="text-xs text-ink-muted">
            Posted {postedLabel(job)}
          </span>
        </div>
      </div>
    </div>
  );
}

function JobsTable({ jobs }: { jobs: JobListItem[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[800px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-section/60">
            {["Role", "Company", "Location", "Type", "Posted"].map((label) => (
              <th
                key={label}
                scope="col"
                className="px-4 py-4 text-sm font-semibold text-ink-secondary first:pl-5 last:pr-5"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.job_id}
              className="border-b border-line last:border-b-0 hover:bg-section/40"
            >
              <td className="px-4 py-4 pl-5 align-middle font-semibold text-ink">
                {job.title}
              </td>
              <td className="px-4 py-4 text-sm text-ink-secondary">
                {job.company_name}
              </td>
              <td className="px-4 py-4 text-sm text-ink">
                {locationLabel(job)}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary">
                {typeLabel(job) ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-4 pr-5 text-sm text-ink-secondary">
                {postedLabel(job)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SearchClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [keyword, setKeyword] = useState(searchParams.get("q") ?? "");
  const [view, setView] = useState<ViewMode>("table");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);
  const [perPageInput, setPerPageInput] = useState(String(DEFAULT_PER_PAGE));

  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const handle = setTimeout(
      () => {
        getJobs({ q: keyword.trim() || undefined, page, page_size: perPage })
          .then((response) => {
            if (cancelled) return;
            setJobs(response.items);
            setTotal(response.total);
            setTotalPages(Math.max(1, response.total_pages));
            setStatus("success");
          })
          .catch((error: unknown) => {
            if (cancelled) return;
            setErrorMessage(
              error instanceof ApiError
                ? error.message
                : "Something went wrong loading jobs. Please try again.",
            );
            setStatus("error");
          });
      },
      keyword ? SEARCH_DEBOUNCE_MS : 0,
    );

    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [keyword, page, perPage, reloadToken]);

  const hasFilters = keyword.trim() !== "";

  const syncUrl = (kw: string) => {
    const params = new URLSearchParams();
    if (kw.trim()) params.set("q", kw.trim());
    const qs = params.toString();
    router.replace(qs ? `/search?${qs}` : "/search");
  };

  const handleKeyword = (value: string) => {
    setKeyword(value);
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
    setPage(1);
    router.replace("/search");
  };

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <PageHeader
        title="Find your next job"
        subtitle="Search autonomous vehicle job openings."
      />

      <SearchBar
        className="mt-0"
        keyword={keyword}
        onKeywordChange={handleKeyword}
        placeholder="Job title, skill or keyword"
        onSubmit={(e) => {
          e.preventDefault();
          syncUrl(keyword);
        }}
      />

      {status === "loading" && (
        <div
          aria-busy="true"
          className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center"
        >
          <p className="font-semibold text-ink">Loading jobs…</p>
        </div>
      )}

      {status === "error" && (
        <div
          role="alert"
          className="mt-10 rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
        >
          <p className="font-semibold text-warning">Couldn&apos;t load jobs</p>
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
        <>
          <div className="mt-4 flex flex-col gap-4 lg:mt-8 lg:grid lg:grid-cols-[minmax(0,1fr)_14rem] lg:items-center lg:gap-x-6 lg:pr-3">
            <div className="order-2 min-w-0 lg:order-1">
              <p className="text-sm text-ink-secondary">
                <span className="font-semibold text-ink">{total}</span>{" "}
                {total === 1 ? "job" : "jobs"} found
                {keyword.trim() !== "" ? ` for "${keyword.trim()}"` : ""}
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
            <div className="order-1 lg:order-2">
              <ViewToggle view={view} onChange={setView} />
            </div>
          </div>

          {jobs.length > 0 && (
            <>
              <div className="mt-4">
                {view === "table" ? (
                  <JobsTable jobs={jobs} />
                ) : (
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    {jobs.map((job) => (
                      <JobRow key={job.job_id} job={job} />
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
                  page={page}
                  pageCount={totalPages}
                  onPageChange={setPage}
                  alwaysVisible
                />
              </div>
            </>
          )}

          {jobs.length === 0 && (
            <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
              <p className="font-semibold text-ink">No jobs found</p>
              <p className="mt-2 text-sm text-ink-secondary">
                Try a different keyword.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
