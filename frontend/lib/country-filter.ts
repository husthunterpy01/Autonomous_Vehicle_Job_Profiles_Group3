/** The empty value represents an unrestricted country search. */
export const ALL_COUNTRIES = "";

/** Countries represented by the authoritative scraper company list. */
export const COUNTRY_OPTIONS = [
  { value: ALL_COUNTRIES, label: "All Countries" },
  { value: "Canada", label: "Canada" },
  { value: "China", label: "China" },
  { value: "Germany", label: "Germany" },
  { value: "Hungary", label: "Hungary" },
  { value: "Israel", label: "Israel" },
  { value: "Japan", label: "Japan" },
  { value: "Russia", label: "Russia" },
  { value: "South Korea", label: "South Korea" },
  { value: "Sweden", label: "Sweden" },
  { value: "Turkey", label: "Turkey" },
  { value: "United Kingdom", label: "United Kingdom" },
  { value: "United States", label: "United States" },
] as const;

/**
 * Keeps a country from the URL only when it is one of the supported options.
 * Missing, empty, or hand-edited values fall back to an unrestricted search.
 */
export function resolveCountry(requested: string | null): string {
  if (!requested) return ALL_COUNTRIES;
  return COUNTRY_OPTIONS.some((option) => option.value === requested)
    ? requested
    : ALL_COUNTRIES;
}
