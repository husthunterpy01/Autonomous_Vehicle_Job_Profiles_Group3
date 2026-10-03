/* Builds the country dropdowns (homepage and Find Jobs) from GET
   /api/v1/jobs/countries, so the list follows where the jobs actually are
   (BE-21) and stays a pure function that can be tested without a network
   call. The filter itself is exact: a job matches when any of its locations
   is in the chosen country. */

export type CountryCount = {
  country: string;
  job_count: number;
};

export type CountryOption = {
  value: string;
  label: string;
};

/** The empty value represents an unrestricted country search. */
export const ALL_COUNTRIES = "";

/** "All Countries", then the countries with the most jobs first. */
export function countryOptions(counts: CountryCount[]): CountryOption[] {
  const sorted = [...counts].sort(
    (a, b) => b.job_count - a.job_count || a.country.localeCompare(b.country),
  );
  return [
    { value: ALL_COUNTRIES, label: "All Countries" },
    ...sorted.map((count) => ({
      value: count.country,
      label: `${count.country} (${count.job_count})`,
    })),
  ];
}

/** Keeps a country from the URL only when it still has jobs, so a stale or
 *  hand-edited link falls back to showing everything instead of an empty
 *  list the user cannot explain. */
export function resolveCountry(
  requested: string | null,
  options: CountryOption[],
): string {
  if (!requested) return ALL_COUNTRIES;
  return options.some((option) => option.value === requested)
    ? requested
    : ALL_COUNTRIES;
}
