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
};

export function getJobs(params: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<PageResponse<JobListItem>> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.page_size ?? 10));
  return apiFetch<PageResponse<JobListItem>>(`/api/v1/jobs?${search.toString()}`);
}
