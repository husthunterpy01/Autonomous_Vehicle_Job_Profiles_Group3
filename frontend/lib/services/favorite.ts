import { apiFetch } from "./api";
import type { JobListItem } from "./job";

/* Auth is cookie-based (see lib/services/auth.ts), so every request here
   needs credentials: "include" to send the httpOnly JWT cookie. */

export function getFavorites(): Promise<JobListItem[]> {
  return apiFetch<JobListItem[]>("/api/v1/favorites", {
    credentials: "include",
  });
}

export function addFavorite(jobId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/favorites/${jobId}`, {
    method: "POST",
    credentials: "include",
  });
}

export function removeFavorite(jobId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/favorites/${jobId}`, {
    method: "DELETE",
    credentials: "include",
  });
}
