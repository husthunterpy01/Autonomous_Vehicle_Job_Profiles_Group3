"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Dropdown from "@/components/ui/Dropdown";
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
  ALL_COUNTRIES,
  countryOptions,
  resolveCountry,
} from "@/lib/country-filter";
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
  parseSalaryBound,
  searchQueryString,
} from "@/lib/search-url";
import {
  parseSalaryField,
  salaryFilterLabel,
  salaryRangeError,
  sanitizeSalaryDigits,
} from "@/lib/salary-filter";
import { getCategoryStatsRaw } from "@/lib/services/home";
import { getJobCountries, getJobs, type JobListItem } from "@/lib/services/job";

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
  const [countryOptionList, setCountryOptionList] = useState(() =>
    countryOptions([]),
  );
  const [country, setCountry] = useState(
    searchParams.get("country") ?? ALL_COUNTRIES,
  );
  // null means "no bound". Committed (affects the request/URL) separately
  // from the draft the filter row edits - same reasoning as
  // draftCategory/draftCountry below, so Apply/Clear treats salary exactly
  // like every other filter instead of being the one live-as-you-type
  // exception.
  const [salaryMin, setSalaryMin] = useState(() =>
    parseSalaryBound(searchParams.get("salary_min")),
  );
  const [salaryMax, setSalaryMax] = useState(() =>
    parseSalaryBound(searchParams.get("salary_max")),
  );
  // What the filter row shows; the list only uses it once Apply is pressed.
  const [draftCategory, setDraftCategory] = useState(category);
  const [draftCountry, setDraftCountry] = useState(country);
  const [draftSalaryMin, setDraftSalaryMin] = useState(salaryMin);
  const [draftSalaryMax, setDraftSalaryMax] = useState(salaryMax);
  // Validated on the draft so Apply itself is blocked while min > max,
  // rather than letting an invalid pair reach committed state and then
  // skipping the request after the fact.
  const draftSalaryError = salaryRangeError(draftSalaryMin, draftSalaryMax);
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
        setDraftCategory((current) => resolveCategory(current, options));
      })
      // The dropdown just stays on "All categories" if this fails; the job
      // list itself does not depend on it.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Same for countries: the list follows where the jobs are.
  useEffect(() => {
    let cancelled = false;
    getJobCountries()
      .then((counts) => {
        if (cancelled) return;
        const options = countryOptions(counts);
        setCountryOptionList(options);
        setCountry((current) => resolveCountry(current, options));
        setDraftCountry((current) => resolveCountry(current, options));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    // Committed salary can only be invalid from a hand-edited or shared URL
    // (Apply itself is disabled while the draft is invalid - see
    // draftSalaryError) - skip the request rather than send a pair the
    // backend would 400 on anyway.
    if (salaryRangeError(salaryMin, salaryMax)) return;
    const controller = new AbortController();
    const handle = setTimeout(
      () => {
        setListBusy(true);
        const query = {
          q: keyword.trim() || undefined,
          category_id: category || undefined,
          country: country || undefined,
          salary_min: salaryMin ?? undefined,
          salary_max: salaryMax ?? undefined,
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
      // Debounced only for keyword, the one field still live-as-you-type;
      // category/country/salary now all change via Apply - a deliberate
      // click, not a keystroke - so they fire immediately like before.
      keyword ? SEARCH_DEBOUNCE_MS : 0,
    );

    return () => {
      controller.abort();
      clearTimeout(handle);
    };
  }, [
    keyword,
    category,
    country,
    salaryMin,
    salaryMax,
    sort,
    page,
    perPage,
    reloadToken,
  ]);

  const hasFilters =
    keyword.trim() !== "" ||
    category !== ALL_CATEGORIES ||
    country !== ALL_COUNTRIES ||
    salaryMin !== null ||
    salaryMax !== null ||
    !isDefaultJobSort(sort);

  // One place keeps the URL in step with the list (keyword as submitted,
  // category, country, salary bounds, sort, page and per page), so a page
  // can be shared or jumped to by editing ?page= directly. Defaults stay
  // out of the URL.
  useEffect(() => {
    const qs = searchQueryString({
      q: urlKeyword,
      category,
      country,
      salaryMin,
      salaryMax,
      sort,
      page,
      perPage,
    });
    router.replace(qs ? `/search?${qs}` : "/search");
  }, [
    urlKeyword,
    category,
    country,
    salaryMin,
    salaryMax,
    sort,
    page,
    perPage,
    router,
  ]);

  const draftChanged =
    draftCategory !== category ||
    draftCountry !== country ||
    draftSalaryMin !== salaryMin ||
    draftSalaryMax !== salaryMax;
  const filterRowSet =
    draftChanged ||
    category !== ALL_CATEGORIES ||
    country !== ALL_COUNTRIES ||
    salaryMin !== null ||
    salaryMax !== null;

  const applyFilters = () => {
    if (draftSalaryError) return;
    setCategory(draftCategory);
    setCountry(draftCountry);
    setSalaryMin(draftSalaryMin);
    setSalaryMax(draftSalaryMax);
    setPage(1);
  };

  const clearFilterRow = () => {
    setDraftCategory(ALL_CATEGORIES);
    setDraftCountry(ALL_COUNTRIES);
    setDraftSalaryMin(null);
    setDraftSalaryMax(null);
    setCategory(ALL_CATEGORIES);
    setCountry(ALL_COUNTRIES);
    setSalaryMin(null);
    setSalaryMax(null);
    setPage(1);
  };

  const handleDraftSalaryMinChange = (raw: string) => {
    setDraftSalaryMin(parseSalaryField(sanitizeSalaryDigits(raw)));
  };

  const handleDraftSalaryMaxChange = (raw: string) => {
    setDraftSalaryMax(parseSalaryField(sanitizeSalaryDigits(raw)));
  };

  // The chip removes only the applied salary filter (category/country are
  // untouched), so it clears both committed and draft state together -
  // otherwise a stale draft would silently reappear next time Apply is hit.
  const clearSalaryFilter = () => {
    setDraftSalaryMin(null);
    setDraftSalaryMax(null);
    setSalaryMin(null);
    setSalaryMax(null);
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
    setCountry(ALL_COUNTRIES);
    setDraftCategory(ALL_CATEGORIES);
    setDraftCountry(ALL_COUNTRIES);
    setSalaryMin(null);
    setSalaryMax(null);
    setDraftSalaryMin(null);
    setDraftSalaryMax(null);
    setSort(DEFAULT_JOB_SORT);
    setPage(1);
  };

  const salaryChipLabel = salaryFilterLabel(salaryMin, salaryMax);

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
          setUrlKeyword(keyword);
        }}
      />

      {/* The search bar is only for the keyword; the filters sit in one row
          and take effect together on Apply. */}
      <div
        role="group"
        aria-label="Filters"
        className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end"
      >
        <Dropdown
          id="category-filter"
          aria-label="Category"
          value={draftCategory}
          onChange={setDraftCategory}
          options={categoryOptionList}
          className="sm:w-64"
        />
        <select
          id="country-filter"
          aria-label="Country"
          value={draftCountry}
          onChange={(event) => setDraftCountry(event.target.value)}
          className="w-full rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink outline-none transition-colors hover:border-primary focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20 sm:w-56"
        >
          {countryOptionList.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <div>
            <label
              htmlFor="salary-min-filter"
              className="block text-sm text-ink-secondary"
            >
              Min salary (USD/yr)
            </label>
            <div className="mt-1 flex items-center rounded-lg border border-line bg-surface px-3 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <span aria-hidden="true" className="text-sm text-ink-muted">
                $
              </span>
              <input
                id="salary-min-filter"
                type="text"
                inputMode="numeric"
                maxLength={9}
                value={draftSalaryMin !== null ? String(draftSalaryMin) : ""}
                onChange={(e) => handleDraftSalaryMinChange(e.target.value)}
                placeholder="No minimum"
                aria-invalid={draftSalaryError ? true : undefined}
                aria-describedby={
                  draftSalaryError ? "salary-filter-error" : undefined
                }
                className="w-24 border-0 bg-transparent py-2.5 pl-1 text-sm font-medium text-ink outline-none"
              />
            </div>
          </div>
          <span aria-hidden="true" className="pb-2.5 text-ink-muted">
            –
          </span>
          <div>
            <label
              htmlFor="salary-max-filter"
              className="block text-sm text-ink-secondary"
            >
              Max salary (USD/yr)
            </label>
            <div className="mt-1 flex items-center rounded-lg border border-line bg-surface px-3 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <span aria-hidden="true" className="text-sm text-ink-muted">
                $
              </span>
              <input
                id="salary-max-filter"
                type="text"
                inputMode="numeric"
                maxLength={9}
                value={draftSalaryMax !== null ? String(draftSalaryMax) : ""}
                onChange={(e) => handleDraftSalaryMaxChange(e.target.value)}
                placeholder="No maximum"
                aria-invalid={draftSalaryError ? true : undefined}
                aria-describedby={
                  draftSalaryError ? "salary-filter-error" : undefined
                }
                className="w-24 border-0 bg-transparent py-2.5 pl-1 text-sm font-medium text-ink outline-none"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 sm:ml-auto">
          <button
            type="button"
            onClick={applyFilters}
            disabled={!draftChanged || Boolean(draftSalaryError)}
            className="flex-1 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
          >
            Apply
          </button>
          <button
            type="button"
            onClick={clearFilterRow}
            disabled={!filterRowSet}
            className="flex-1 rounded-lg border border-line bg-surface px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
          >
            Clear
          </button>
        </div>
      </div>

      {salaryChipLabel && (
        <div className="mt-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-light px-3 py-1.5 text-sm font-medium text-primary">
            {salaryChipLabel}
            <button
              type="button"
              onClick={clearSalaryFilter}
              aria-label="Remove salary filter"
              className="leading-none text-primary/70 hover:text-primary"
            >
              ×
            </button>
          </span>
        </div>
      )}

      {draftSalaryError && (
        <p
          id="salary-filter-error"
          role="alert"
          className="mt-2 text-sm text-warning"
        >
          {draftSalaryError}
        </p>
      )}

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
              <p className="font-semibold text-ink">
                {salaryChipLabel
                  ? "No jobs match your salary range"
                  : "No jobs found"}
              </p>
              <p className="mt-2 text-sm text-ink-secondary">
                {salaryChipLabel
                  ? "Try widening the range, or clear it to see every job."
                  : "Try a different keyword."}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
