import { apiFetch } from "./api";

/* Matches backend/app/models/company.py's `company_type` column values —
   free-text in the DB, not a real enum, so keep this list in sync with
   backend/app/sql/seed_companies.sql until the backend adds a proper enum. */
export const COMPANY_TYPE_LABELS: Record<string, string> = {
  AV_Startup: "AV Startup",
  OEM: "OEM",
  OEM_Tech: "OEM / Tech",
  Supplier: "Supplier",
  AV_Chip: "AV Chip",
  AV_Tools: "AV Tools",
};

export type CompanyWithJobCount = {
  company_id: string;
  name: string;
  company_type: string;
  location: string | null;
  number_of_jobs: number;
};

export type PageResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export function getCompaniesWithJobCounts(
  page = 1,
  pageSize = 100,
): Promise<PageResponse<CompanyWithJobCount>> {
  return apiFetch<PageResponse<CompanyWithJobCount>>(
    `/api/v1/companies/with-job-counts?page=${page}&page_size=${pageSize}`,
  );
}
