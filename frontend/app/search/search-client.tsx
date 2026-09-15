"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import Pagination from "@/components/ui/Pagination";
import SearchBar from "@/components/ui/SearchBar";
import ViewToggle, { type ViewMode } from "@/components/ui/ViewToggle";
import {
  FavoriteHeartButton,
  JobRow,
  JobsTable,
} from "@/components/ui/JobResultsList";
import { ApiError } from "@/lib/services/api";
import { addFavorite, removeFavorite } from "@/lib/services/favorite";
import { getJobs, type JobListItem } from "@/lib/services/job";

const DEFAULT_PER_PAGE = 6;
/* Debounce keyword input before hitting the API — unlike the Companies list
   (fetched once, filtered client-side), jobs are paginated server-side, so
   every keystroke would otherwise be a new request. */
const SEARCH_DEBOUNCE_MS = 400;

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

  // Tracks which jobs were favorited/unfavorited in this session so the
  // heart can fill in — we don't know the user's existing favorites up
  // front (no bulk "is this favorited" endpoint), so this resets on reload.
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [savingId, setSavingId] = useState<string | null>(null);

  const handleToggleFavorite = async (jobId: string) => {
    const alreadySaved = savedIds.has(jobId);
    setSavingId(jobId);
    try {
      if (alreadySaved) {
        await removeFavorite(jobId);
        setSavedIds((prev) => {
          const next = new Set(prev);
          next.delete(jobId);
          return next;
        });
      } else {
        await addFavorite(jobId);
        setSavedIds((prev) => new Set(prev).add(jobId));
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.push("/login");
      }
    } finally {
      setSavingId(null);
    }
  };

  const renderFavoriteAction = (job: JobListItem) => (
    <FavoriteHeartButton
      filled={savedIds.has(job.job_id)}
      disabled={savingId === job.job_id}
      onClick={() => handleToggleFavorite(job.job_id)}
    />
  );

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
                  <JobsTable
                    jobs={jobs}
                    renderAction={renderFavoriteAction}
                    actionColumnLabel="Favorite"
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    {jobs.map((job) => (
                      <JobRow
                        key={job.job_id}
                        job={job}
                        action={renderFavoriteAction(job)}
                      />
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
