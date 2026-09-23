import { apiFetch, type PageResponse } from "./api";

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

export function getCompaniesWithJobCounts(
  page = 1,
  pageSize = 100,
): Promise<PageResponse<CompanyWithJobCount>> {
  return apiFetch<PageResponse<CompanyWithJobCount>>(
    `/api/v1/companies/with-job-counts?page=${page}&page_size=${pageSize}`,
  );
}

/** Matches backend CompanyResponse (GET /api/v1/companies/{company_id}). */
export type CompanyDetail = {
  company_id: string;
  name: string;
  website_url: string | null;
  career_page_url: string | null;
  company_type: string | null;
  datasource_status: string | null;
  description: string | null;
};

export function getCompany(companyId: string): Promise<CompanyDetail> {
  return apiFetch<CompanyDetail>(`/api/v1/companies/${companyId}`);
}

const COMPANY_UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True for backend company ids; mock landing-page slugs fail this check. */
export function isCompanyUuid(id: string): boolean {
  return COMPANY_UUID.test(id);
}

export function companyDetailHref(companyId: string): string {
  /* Query string so the static export always has a real /companies/profile.html
     file. /companies/<uuid> does not exist at build time (see
     app/companies/[id]/page.tsx's generateStaticParams, which only covers
     the mock ids) and would 404 on GitHub Pages. */
  return `/companies/profile?id=${encodeURIComponent(companyId)}`;
}

export function companyTypeLabel(
  companyType: string | null | undefined,
): string | null {
  if (!companyType) return null;
  return COMPANY_TYPE_LABELS[companyType] ?? companyType.replaceAll("_", " ");
}
