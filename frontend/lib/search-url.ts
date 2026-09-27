/* Find Jobs keeps its state in the URL (?q=, ?category=, ?sort=, ?direction=,
   ?page=, ?per_page=), so a filtered list or a specific page (e.g. ?page=50)
   can be reloaded, shared, or jumped to directly. These are pure functions so
   they can be tested without a router. */

import { isDefaultJobSort, type JobSort } from "./job-sort.ts";

export const DEFAULT_PER_PAGE = 6;
/** The API rejects page_size above 100. */
export const MAX_PER_PAGE = 100;

/** A positive whole number from the URL, or the fallback for anything else
 *  (missing, "abc", "0", "-3", "2.5"), optionally capped at max. */
export function parsePositiveInt(
  raw: string | null,
  fallback: number,
  max?: number,
): number {
  if (raw === null || !/^\d+$/.test(raw.trim())) return fallback;
  const value = Number(raw.trim());
  if (!Number.isSafeInteger(value) || value < 1) return fallback;
  return max !== undefined ? Math.min(value, max) : value;
}

export type SearchState = {
  q: string;
  category: string;
  sort: JobSort;
  page: number;
  perPage: number;
};

/** Query string for the state. Defaults are left out, so a plain /search link
 *  stays unchanged and only non-default choices appear in the URL. */
export function searchQueryString(state: SearchState): string {
  const params = new URLSearchParams();
  if (state.q.trim()) params.set("q", state.q.trim());
  if (state.category) params.set("category", state.category);
  if (!isDefaultJobSort(state.sort)) {
    params.set("sort", state.sort.field);
    params.set("direction", state.sort.direction);
  }
  if (state.page > 1) params.set("page", String(state.page));
  if (state.perPage !== DEFAULT_PER_PAGE) {
    params.set("per_page", String(state.perPage));
  }
  return params.toString();
}
