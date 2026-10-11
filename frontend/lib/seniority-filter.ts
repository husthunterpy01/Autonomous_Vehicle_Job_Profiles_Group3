/* Builds the Find Jobs seniority dropdown from GET /api/v1/jobs/seniority-levels,
   so it lists only the levels that have jobs, lowest first. Pure functions, so
   they can be tested without a network call. */

export type SeniorityCount = {
  seniority_level: number;
  job_count: number;
};

export type SeniorityOption = {
  value: string;
  label: string;
};

/** The empty value represents an unrestricted seniority search. */
export const ALL_SENIORITIES = "";

// Jobs whose title states no level are stored as mid-level, so say so.
const MID_LEVEL = 2;

/** "All levels", then each level that has jobs with its count. */
export function seniorityOptions(
  counts: SeniorityCount[],
  labels: Record<number, string>,
): SeniorityOption[] {
  const sorted = [...counts].sort(
    (a, b) => a.seniority_level - b.seniority_level,
  );
  return [
    { value: ALL_SENIORITIES, label: "All levels" },
    ...sorted.map(({ seniority_level, job_count }) => {
      const name = labels[seniority_level] ?? "Other";
      const text =
        seniority_level === MID_LEVEL ? `${name} or not stated` : name;
      return {
        value: String(seniority_level),
        label: `${text} (${job_count})`,
      };
    }),
  ];
}

/** Keeps a level from the URL only while it still has jobs, so a stale or
 *  hand-edited link falls back to showing everything. */
export function resolveSeniority(
  requested: string | null,
  options: SeniorityOption[],
): string {
  if (!requested) return ALL_SENIORITIES;
  return options.some((option) => option.value === requested)
    ? requested
    : ALL_SENIORITIES;
}
