import { apiFetch, ApiError } from "./api";
import type { JobListItem } from "./job";

/* Matches backend/app/schemas/favorite.py (BE-11, Harshil's backend —
   see PR #101). Split into separate job/company resources, each with
   its own created_at, unlike the single shared table this page
   originally shipped with. */

export type FavoriteJob = {
  job_id: string;
  created_at: string;
  job: JobListItem;
};

export type FavoriteCompanyDetail = {
  company_id: string;
  name: string;
  website_url: string | null;
  career_page_url: string | null;
  company_type: string | null;
  datasource_status: string | null;
};

export type FavoriteCompany = {
  company_id: string;
  created_at: string;
  company: FavoriteCompanyDetail;
};

/* This backend is strict REST, not idempotent: adding an
   already-favorited item returns 409, removing one that isn't
   favorited returns 404. Both are treated here as "already in the
   state the user wanted" so callers don't need special-case handling
   for what's really a no-op. */
async function ignoring(status: number, action: () => Promise<void>) {
  try {
    await action();
  } catch (error) {
    if (error instanceof ApiError && error.status === status) return;
    throw error;
  }
}

export function getFavoriteJobs(): Promise<FavoriteJob[]> {
  return apiFetch<FavoriteJob[]>("/api/v1/favorites/jobs", {
    credentials: "include",
  });
}

export function addFavoriteJob(jobId: string): Promise<void> {
  return ignoring(409, () =>
    apiFetch(`/api/v1/favorites/jobs/${jobId}`, {
      method: "POST",
      credentials: "include",
    }),
  );
}

export function removeFavoriteJob(jobId: string): Promise<void> {
  return ignoring(404, () =>
    apiFetch(`/api/v1/favorites/jobs/${jobId}`, {
      method: "DELETE",
      credentials: "include",
    }),
  );
}

export function getFavoriteCompanies(): Promise<FavoriteCompany[]> {
  return apiFetch<FavoriteCompany[]>("/api/v1/favorites/companies", {
    credentials: "include",
  });
}

export function addFavoriteCompany(companyId: string): Promise<void> {
  return ignoring(409, () =>
    apiFetch(`/api/v1/favorites/companies/${companyId}`, {
      method: "POST",
      credentials: "include",
    }),
  );
}

export function removeFavoriteCompany(companyId: string): Promise<void> {
  return ignoring(404, () =>
    apiFetch(`/api/v1/favorites/companies/${companyId}`, {
      method: "DELETE",
      credentials: "include",
    }),
  );
}
