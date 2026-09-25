import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { JobListItem } from "../lib/services/job";
import {
  FeaturedJobsView,
  LatestJobsView,
  LatestOpportunitiesView,
} from "./home-jobs-view";

function job(overrides: Partial<JobListItem>): JobListItem {
  return {
    job_id: "11111111-1111-1111-1111-111111111111",
    title: "Staff Lidar Systems Engineer",
    company_id: "22222222-2222-2222-2222-222222222222",
    company_name: "Aurora",
    locations: ["Mountain View, CA"],
    skills: [],
    employment_type: 1,
    raw_description: "",
    source_url: null,
    posted_date: "2026-09-03T00:00:00Z",
    salary_min: 181000,
    salary_max: 262000,
    salary_average: null,
    salary_currency: "USD",
    salary_period: "yearly",
    salary_source: "regex",
    category: null,
    ...overrides,
  } as JobListItem;
}

const published = job({});
const estimated = job({
  job_id: "33333333-3333-3333-3333-333333333333",
  title: "Senior Perception Engineer",
  company_name: "NVIDIA",
  salary_min: null,
  salary_max: null,
  salary_average: 251250,
  salary_source: "levels_fyi_average",
});

describe("LatestOpportunitiesView", () => {
  it("shows the real total and links each job to its detail page", () => {
    const html = renderToStaticMarkup(
      <LatestOpportunitiesView
        state={{ status: "success", jobs: [published, estimated], total: 1819 }}
      />,
    );
    assert.match(html, /1,819 jobs/);
    assert.match(
      html,
      /href="\/jobs\?id=11111111-1111-1111-1111-111111111111"/,
    );
    assert.match(html, /Aurora · Mountain View, CA/);
    assert.match(html, /US\$181,000/);
    assert.match(html, /~US\$251,250/);
  });

  it("says so instead of showing a count while loading or on error", () => {
    const loading = renderToStaticMarkup(
      <LatestOpportunitiesView state={{ status: "loading" }} />,
    );
    assert.match(loading, /Loading jobs/);
    assert.doesNotMatch(loading, /\d+ jobs/);

    const failed = renderToStaticMarkup(
      <LatestOpportunitiesView state={{ status: "error" }} />,
    );
    assert.match(failed, /Couldn(&#x27;|')t load jobs/);
  });
});

describe("LatestJobsView", () => {
  it("renders one row per job", () => {
    const html = renderToStaticMarkup(
      <LatestJobsView
        state={{ status: "success", jobs: [published, estimated], total: 2 }}
      />,
    );
    assert.match(html, /Staff Lidar Systems Engineer/);
    assert.match(html, /Senior Perception Engineer/);
  });

  it("shows an empty state when there are no jobs", () => {
    const html = renderToStaticMarkup(
      <LatestJobsView state={{ status: "success", jobs: [], total: 0 }} />,
    );
    assert.match(html, /No jobs yet/);
  });
});

describe("FeaturedJobsView", () => {
  it("renders the jobs it is given as column cards", () => {
    const html = renderToStaticMarkup(
      <FeaturedJobsView
        state={{ status: "success", jobs: [published], total: 1 }}
      />,
    );
    assert.match(html, /Staff Lidar Systems Engineer/);
    assert.match(html, /US\$181,000/);
  });

  it("explains an empty result instead of looking broken", () => {
    const html = renderToStaticMarkup(
      <FeaturedJobsView state={{ status: "success", jobs: [], total: 0 }} />,
    );
    assert.match(html, /No published salary ranges yet/);
    assert.match(html, /href="\/search"/);
  });

  it("shows the error state when loading fails", () => {
    const html = renderToStaticMarkup(
      <FeaturedJobsView state={{ status: "error" }} />,
    );
    assert.match(html, /Couldn(&#x27;|')t load jobs right now/);
  });
});
