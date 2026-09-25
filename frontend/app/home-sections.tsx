"use client";

import { useEffect, useState } from "react";
import type { CategoryStat } from "@/lib/category-filter";
import { DEFAULT_JOB_SORT } from "@/lib/job-sort";
import { getCompaniesWithJobCounts } from "@/lib/services/company";
import { getCategoryStatsRaw } from "@/lib/services/home";
import { getJobs } from "@/lib/services/job";
import {
  busiestCategory,
  FeaturedJobsView,
  LatestJobsView,
  LatestOpportunitiesView,
  TopCategoryView,
  TopCompaniesView,
  topHiringCompanies,
  type CompanyListState,
  type JobListState,
} from "./home-sections-view";

export const LATEST_PREVIEW_COUNT = 4;
export const LATEST_COUNT = 6;
export const FEATURED_COUNT = 3;
export const TOP_COMPANY_COUNT = 8;

/* Newest jobs first (the API's default sort), optionally limited to jobs
   whose employer published a salary range. */
function useJobList(pageSize: number, salaryDisclosed?: boolean): JobListState {
  const [state, setState] = useState<JobListState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getJobs(
      {
        sort: DEFAULT_JOB_SORT,
        page_size: pageSize,
        salary_disclosed: salaryDisclosed,
      },
      controller.signal,
    )
      .then((page) =>
        setState({ status: "success", jobs: page.items, total: page.total }),
      )
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => controller.abort();
  }, [pageSize, salaryDisclosed]);

  return state;
}

export function LatestOpportunitiesList() {
  return <LatestOpportunitiesView state={useJobList(LATEST_PREVIEW_COUNT)} />;
}

export function LatestJobsGrid() {
  return <LatestJobsView state={useJobList(LATEST_COUNT)} />;
}

export function FeaturedJobsGrid() {
  return <FeaturedJobsView state={useJobList(FEATURED_COUNT, true)} />;
}

export function TopCompaniesGrid() {
  const [state, setState] = useState<CompanyListState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    // The API caps page_size at 100, well above the ~42 tracked companies.
    getCompaniesWithJobCounts(1, 100)
      .then((page) => {
        if (cancelled) return;
        setState({
          status: "success",
          companies: topHiringCompanies(page.items, TOP_COMPANY_COUNT),
        });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <TopCompaniesView state={state} />;
}

export function TopCategoryHighlight() {
  const [category, setCategory] = useState<CategoryStat | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCategoryStatsRaw()
      .then((stats) => {
        if (!cancelled) setCategory(busiestCategory(stats));
      })
      // A decorative highlight: on failure it simply stays hidden.
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return <TopCategoryView category={category} />;
}
