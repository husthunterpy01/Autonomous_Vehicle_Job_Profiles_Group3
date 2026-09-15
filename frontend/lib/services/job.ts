import type { SalaryInput } from "@/lib/salary";
import { apiFetch, type PageResponse } from "./api";

/* Matches backend/app/enums/employment_type.py's EmploymentType IntEnum. */
export const EMPLOYMENT_TYPE_LABELS: Record<number, string> = {
  1: "Full-time",
  2: "Part-time",
  3: "Contract",
  4: "Temporary",
  5: "Internship",
  6: "Other",
};

export type JobListItem = {
  job_id: string;
  title: string;
  company_id: string;
  company_name: string;
  locations: string[];
  skills: string[];
  employment_type: number | null;
  raw_description: string;
  source_url: string | null;
  posted_date: string | null;
  /** Pay as posted or estimated; a single figure arrives as min === max.
   *  Optional so the page keeps working against a backend that predates
   *  the salary columns. */
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_source?: string | null;
};

/** Salary props for the API shape; see lib/salary.ts for the display rules. */
export function jobSalary(job: JobListItem): SalaryInput {
  return {
    min: job.salary_min ?? null,
    max: job.salary_max ?? null,
    currency: job.salary_currency ?? null,
    period: job.salary_period ?? null,
    source: job.salary_source ?? null,
  };
}

export function getJobs(params: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<PageResponse<JobListItem>> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.page_size ?? 10));
  return apiFetch<PageResponse<JobListItem>>(
    `/api/v1/jobs?${search.toString()}`,
  );
}
