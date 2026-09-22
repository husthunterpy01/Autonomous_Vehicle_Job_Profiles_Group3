/* Sorting state for the job list, shared by the table header and the API
   call so both always agree on what is being sorted. Mirrors the `sort` and
   `direction` parameters of GET /api/v1/jobs. */

export type JobSortField = "posted_date" | "title" | "company";
export type SortDirection = "asc" | "desc";

export type JobSort = {
  field: JobSortField;
  direction: SortDirection;
};

/** Same as the API's own default. It is still sent with every request, but
 *  left out of the URL so a plain /search link stays unchanged. */
export const DEFAULT_JOB_SORT: JobSort = {
  field: "posted_date",
  direction: "desc",
};

/* Clicking a date column should start at newest first; a name column at A-Z. */
const FIRST_DIRECTION: Record<JobSortField, SortDirection> = {
  posted_date: "desc",
  title: "asc",
  company: "asc",
};

const SORT_FIELDS = Object.keys(FIRST_DIRECTION) as JobSortField[];

/** Clicking the sorted column flips it; clicking another one starts fresh. */
export function nextJobSort(current: JobSort, field: JobSortField): JobSort {
  if (current.field !== field) {
    return { field, direction: FIRST_DIRECTION[field] };
  }
  return {
    field,
    direction: current.direction === "asc" ? "desc" : "asc",
  };
}

/** Reads the sort out of the URL, falling back to the default for anything
 *  unrecognized so a hand-edited link cannot break the page. */
export function parseJobSort(
  field: string | null,
  direction: string | null,
): JobSort {
  if (!SORT_FIELDS.includes(field as JobSortField)) return DEFAULT_JOB_SORT;
  return {
    field: field as JobSortField,
    direction:
      direction === "asc" || direction === "desc"
        ? direction
        : FIRST_DIRECTION[field as JobSortField],
  };
}

export function isDefaultJobSort(sort: JobSort): boolean {
  return (
    sort.field === DEFAULT_JOB_SORT.field &&
    sort.direction === DEFAULT_JOB_SORT.direction
  );
}
