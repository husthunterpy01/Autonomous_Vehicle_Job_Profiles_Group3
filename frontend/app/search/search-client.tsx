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
import { addFavoriteJob, removeFavoriteJob } from "@/lib/services/favorite";
import {
  ALL_CATEGORIES,
  categoryOptions,
  resolveCategory,
} from "@/lib/category-filter";
import {
  DEFAULT_JOB_SORT,
  isDefaultJobSort,
  nextJobSort,
  parseJobSort,
  type JobSortField,
} from "@/lib/job-sort";
import {
  DEFAULT_PER_PAGE,
  MAX_PER_PAGE,
  parsePositiveInt,
  searchQueryString,
} from "@/lib/search-url";
import { getCategoryStatsRaw } from "@/lib/services/home";
import { getJobs, type JobListItem } from "@/lib/services/job";

/* Debounce keyword input before hitting the API — unlike the Companies list
   (fetched once, filtered client-side), jobs are paginated server-side, so
   every keystroke would otherwise be a new request. */
const SEARCH_DEBOUNCE_MS = 400;

export default function SearchClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [keyword, setKeyword] = useState(searchParams.get("q") ?? "");
  // The keyword as last submitted - only that one goes into the URL, so the
  // address bar doesn't change on every keystroke.
  const [urlKeyword, setUrlKeyword] = useState(searchParams.get("q") ?? "");
  const [sort, setSort] = useState(() =>
    parseJobSort(searchParams.get("sort"), searchParams.get("direction")),
  );
  const [categoryOptionList, setCategoryOptionList] = useState(() =>
    categoryOptions([]),
  );
  const [category, setCategory] = useState(
    searchParams.get("category") ?? ALL_CATEGORIES,
  );
  const [view, setView] = useState<ViewMode>("table");
  // ?page=50 opens page 50 directly; ?per_page= is kept too.
  const [page, setPage] = useState(() =>
    parsePositiveInt(searchParams.get("page"), 1),
  );
  const [perPage, setPerPage] = useState(() =>
    parsePositiveInt(
      searchParams.get("per_page"),
      DEFAULT_PER_PAGE,
      MAX_PER_PAGE,
    ),
  );
  const [perPageInput, setPerPageInput] = useState(() => String(perPage));

  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [listBusy, setListBusy] = useState(false);
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
        await removeFavoriteJob(jobId);
        setSavedIds((prev) => {
          const next = new Set(prev);
          next.delete(jobId);
          return next;
        });
      } else {
        await addFavoriteJob(jobId);
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
    getCategoryStatsRaw()
      .then((stats) => {
        if (cancelled) return;
        const options = categoryOptions(stats);
        setCategoryOptionList(options);
        // Drop a category from the URL that the backend no longer returns,
        // which would otherwise filter the list down to nothing.
        setCategory((current) => resolveCategory(current, options));
      })
      // The dropdown just stays on "All categories" if this fails; the job
      // list itself does not depend on it.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const handle = setTimeout(
      () => {
        setListBusy(true);
        const query = {
          q: keyword.trim() || undefined,
          category_id: category || undefined,
          sort,
          page_size: perPage,
        };
        getJobs({ ...query, page }, controller.signal)
          .then(async (response) => {
            // A page past the end (e.g. ?page=999 from a hand-edited or old
            // link) jumps to the last page instead of showing an empty list.
            // The API reports total 0 for an out-of-range page, so page 1 is
            // asked once for the real page count.
            if (page > 1 && response.items.length === 0) {
              const first = await getJobs(
                { ...query, page: 1 },
                controller.signal,
              );
              setPage(Math.max(1, first.total_pages));
              return;
            }
            setJobs(response.items);
            setTotal(response.total);
            setTotalPages(Math.max(1, response.total_pages));
            setStatus("success");
          })
          .catch((error: unknown) => {
            if (error instanceof Error && error.name === "AbortError") {
              return;
            }
            setErrorMessage(
              error instanceof ApiError
                ? error.message
                : "Something went wrong loading jobs. Please try again.",
            );
            setStatus("error");
          })
          .finally(() => {
            if (!controller.signal.aborted) setListBusy(false);
          });
      },
      keyword ? SEARCH_DEBOUNCE_MS : 0,
    );

    return () => {
      controller.abort();
      clearTimeout(handle);
    };
  }, [keyword, category, sort, page, perPage, reloadToken]);

  const hasFilters =
    keyword.trim() !== "" ||
    category !== ALL_CATEGORIES ||
    !isDefaultJobSort(sort);

  // One place keeps the URL in step with the list (keyword as submitted,
  // category, sort, page and per page), so a page can be shared or jumped to
  // by editing ?page= directly. Defaults stay out of the URL.
  useEffect(() => {
    const qs = searchQueryString({
      q: urlKeyword,
      category,
      sort,
      page,
      perPage,
    });
    router.replace(qs ? `/search?${qs}` : "/search");
  }, [urlKeyword, category, sort, page, perPage, router]);

  const handleCategoryChange = (value: string) => {
    setCategory(value);
    setPage(1);
  };

  const handleSortChange = (field: JobSortField) => {
    const updated = nextJobSort(sort, field);
    setSort(updated);
    // A re-sorted list starts from the first page, otherwise page 3 of the
    // old order silently becomes page 3 of the new one.
    setPage(1);
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
    setUrlKeyword("");
    setCategory(ALL_CATEGORIES);
    setSort(DEFAULT_JOB_SORT);
    setPage(1);
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
        dropdownId="category-filter"
        dropdownAriaLabel="Category"
        dropdownValue={category}
        onDropdownChange={handleCategoryChange}
        dropdownOptions={categoryOptionList}
        dropdownClassName="sm:w-64"
        onSubmit={(e) => {
          e.preventDefault();
          setUrlKeyword(keyword);
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
                {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
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
              <div
                className={`mt-4 ${listBusy ? "pointer-events-none opacity-60" : ""}`}
                aria-busy={listBusy}
              >
                {view === "table" ? (
                  <JobsTable
                    key={`page-${page}-${jobs[0]?.job_id ?? "empty"}`}
                    jobs={jobs}
                    renderAction={renderFavoriteAction}
                    actionColumnLabel="Favorite"
                    sort={sort}
                    onSortChange={handleSortChange}
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
