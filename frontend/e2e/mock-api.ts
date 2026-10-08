import type { Page, Route } from "@playwright/test";

export const JOB_ID = "11111111-2222-4333-8444-555555555555";

const CORS = { "access-control-allow-origin": "*" };

type Job = ReturnType<typeof makeJob>;

function makeJob(n: number) {
  const us = n <= 15;
  return {
    job_id: `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`,
    title: `${n % 2 ? "Perception" : "Planning"} Engineer ${n}`,
    company_id: "c0000000-0000-4000-8000-000000000001",
    company_name: us ? "Acme Autonomy" : "Beispiel Mobility",
    locations: [us ? "Mountain View, CA" : "Munich"],
    country: us ? "United States" : "Germany",
    skills: ["Python", "C++"],
    employment_type: 1,
    raw_description: null,
    source_url: null,
    posted_date: "2026-09-01T00:00:00Z",
    salary_min: 150000,
    salary_max: 200000,
    salary_average: null,
    salary_currency: "USD",
    salary_period: "yearly",
    salary_source: "api",
  };
}

export const JOBS: Job[] = Array.from({ length: 23 }, (_, i) => makeJob(i + 1));

export const JOB_DETAIL = {
  ...makeJob(1),
  job_id: JOB_ID,
  title: "Senior Perception Engineer",
  raw_description: "Build the perception stack for our autonomous trucks.",
  category: null,
  department: "Autonomy",
  seniority_level: 3,
  requirements: "Five years of C++ experience.",
  source_platform: "greenhouse",
  source_job_id: "42",
};

export const TRENDS = {
  months: [
    {
      month_key: 202607,
      label: "Jul 2026",
      snapshot_at: "2026-07-31T00:00:00Z",
      jobs_with_skills: 100,
    },
    {
      month_key: 202608,
      label: "Aug 2026",
      snapshot_at: "2026-08-31T00:00:00Z",
      jobs_with_skills: 120,
    },
    {
      month_key: 202609,
      label: "Sep 2026",
      snapshot_at: "2026-09-30T00:00:00Z",
      jobs_with_skills: 140,
    },
  ],
  skills: [
    ["Python", "python", [40, 50, 60]],
    ["C++", "c++", [35, 38, 45]],
    ["ROS", "ros", [20, 25, 30]],
  ].map(([name, normalized_name, counts]) => ({
    name,
    normalized_name,
    skill_type: "programming_language",
    points: (counts as number[]).map((job_count, i) => ({
      month_key: 202607 + i,
      rank: 0,
      job_count,
    })),
  })),
};

export type ApiOptions = {
  jobsStatus?: number;
  trends?: unknown;
  trendsStatus?: number;
  detail?: unknown;
};

/** Answers every /api/v1 call from the page, so no backend is needed.
 *  `listRequests` records the query of each job search. */
export async function mockApi(page: Page, options: ApiOptions = {}) {
  const listRequests: URLSearchParams[] = [];

  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({
      status,
      headers: { ...CORS, "content-type": "application/json" },
      body: JSON.stringify(body),
    });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path === "/api/v1/jobs/countries") {
      return json(route, [
        { country: "United States", job_count: 15 },
        { country: "Germany", job_count: 8 },
      ]);
    }
    if (path === "/api/v1/home/category-stats") {
      return json(route, [
        {
          category_id: "a0000000-0000-4000-8000-000000000001",
          sub_type: "Perception",
          main_type: "Perception & Sensing",
          job_count: 12,
        },
      ]);
    }
    if (path === "/api/v1/jobs") {
      listRequests.push(url.searchParams);
      if (options.jobsStatus && options.jobsStatus >= 400) {
        return json(route, { detail: "Server error" }, options.jobsStatus);
      }
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      const country = url.searchParams.get("country");
      const matching = JOBS.filter(
        (job) =>
          (!q || job.title.toLowerCase().includes(q)) &&
          (!country || job.country === country),
      );
      const size = Number(url.searchParams.get("page_size") ?? 10);
      const current = Number(url.searchParams.get("page") ?? 1);
      return json(route, {
        items: matching.slice((current - 1) * size, current * size),
        total: matching.length,
        page: current,
        page_size: size,
        total_pages: Math.max(1, Math.ceil(matching.length / size)),
      });
    }
    if (/^\/api\/v1\/jobs\/[0-9a-f-]{36}$/.test(path)) {
      return options.detail === null
        ? json(route, { detail: "Job not found" }, 404)
        : json(route, options.detail ?? JOB_DETAIL);
    }
    if (path === "/api/v1/trends/skills") {
      return json(route, options.trends ?? TRENDS, options.trendsStatus ?? 200);
    }
    return json(route, { detail: "Not mocked" }, 404);
  });

  return { listRequests };
}
