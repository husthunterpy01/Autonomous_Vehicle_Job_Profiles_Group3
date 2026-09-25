"use client";

import { useEffect, useState } from "react";
import { DEFAULT_JOB_SORT } from "@/lib/job-sort";
import { getJobs } from "@/lib/services/job";
import {
  FeaturedJobsView,
  LatestJobsView,
  LatestOpportunitiesView,
  type JobListState,
} from "./home-jobs-view";

export const LATEST_PREVIEW_COUNT = 4;
export const LATEST_COUNT = 6;
export const FEATURED_COUNT = 3;

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
