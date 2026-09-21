/* Builds the Find Jobs category dropdown from the home category-stats
   response, so the option list stays a pure function that can be tested
   without a network call. */

import type { DropdownOption } from "@/components/ui/Dropdown";

export type CategoryStat = {
  category_id: string;
  sub_type: string;
  main_type: string | null;
  job_count: number;
};

/** Value used by the "no filter" option; empty so it never looks like an id. */
export const ALL_CATEGORIES = "";

export function categoryOptions(stats: CategoryStat[]): DropdownOption[] {
  const sorted = [...stats].sort(
    (a, b) => b.job_count - a.job_count || a.sub_type.localeCompare(b.sub_type),
  );
  return [
    { value: ALL_CATEGORIES, label: "All categories" },
    ...sorted.map((stat) => ({
      value: stat.category_id,
      label: `${stat.sub_type} (${stat.job_count})`,
    })),
  ];
}

/** Keeps a category from the URL only when the backend still returns it, so
 *  a stale or hand-edited link falls back to showing everything instead of
 *  an empty result list the user cannot explain. */
export function resolveCategory(
  requested: string | null,
  options: DropdownOption[],
): string {
  if (!requested) return ALL_CATEGORIES;
  return options.some((option) => option.value === requested)
    ? requested
    : ALL_CATEGORIES;
}
