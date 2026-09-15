/* Salary display helpers (FE-14).
   The backend returns posted pay as a min/max pair (a single figure arrives
   as min === max) and a company-wide levels.fyi estimate as `average` only,
   each with a currency, a pay period and a source. Nothing is inferred
   here: when neither a usable pair nor an average is present, the salary
   line is simply not shown. */

export type SalaryPeriod = "yearly" | "monthly" | "weekly" | "daily" | "hourly";
export type SalarySource = "api" | "regex" | "levels_fyi_average";

export type SalaryInput = {
  min?: number | null;
  max?: number | null;
  /** Estimate with no posted range; only used when min/max are absent. */
  average?: number | null;
  /** ISO 4217 code such as "USD". Leave unset when the source is unknown. */
  currency?: string | null;
  /** One of SalaryPeriod; anything else is shown without a period. */
  period?: string | null;
  /** One of SalarySource; only used to mark estimates with "~". */
  source?: string | null;
};

export type SalaryDisplay = {
  /** "US$189,000 – US$303,000", "US$180,923", or "~US$180,923" for an
   *  estimate. */
  amount: string;
  /** "/ year", "/ hour", …, or null when the period is unknown. */
  period: string | null;
  /** True when the figure is an estimate rather than posted pay. */
  estimated: boolean;
};

const LOCALE = "en-US";

const PERIOD_LABELS: Record<SalaryPeriod, string> = {
  yearly: "year",
  monthly: "month",
  weekly: "week",
  daily: "day",
  hourly: "hour",
};

const PERIOD_NAMES: Record<SalaryPeriod, string> = {
  yearly: "Yearly",
  monthly: "Monthly",
  weekly: "Weekly",
  daily: "Daily",
  hourly: "Hourly",
};

const ESTIMATED_SOURCES: ReadonlySet<string> = new Set<SalarySource>([
  "levels_fyi_average",
]);

function isAmount(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

function knownPeriod(period: string | null | undefined): SalaryPeriod | null {
  const normalized = period?.trim().toLowerCase();
  return normalized && normalized in PERIOD_LABELS
    ? (normalized as SalaryPeriod)
    : null;
}

function periodLabel(period: string | null | undefined): string | null {
  const known = knownPeriod(period);
  return known ? PERIOD_LABELS[known] : null;
}

/** The figures to display: the posted pair when both bounds are valid,
 *  otherwise the average as a single figure, otherwise null. */
export function resolveSalaryRange(
  input: SalaryInput,
): { min: number; max: number } | null {
  if (isAmount(input.min) && isAmount(input.max)) {
    return input.min <= input.max
      ? { min: input.min, max: input.max }
      : { min: input.max, max: input.min };
  }
  if (isAmount(input.average)) {
    return { min: input.average, max: input.average };
  }
  return null;
}

/* en-US renders USD as a bare "$", which Australian users read as AUD.
   Spell US dollars out so every dollar currency is unambiguous (AUD is
   already "A$", CAD "CA$"). */
const EXPLICIT_SYMBOLS: Record<string, string> = { USD: "US$" };

/** "US$185,000", "A$160,000", "€90,000", "EUR 90,000" for unknown symbols,
 *  "185,000" when no currency is known. Decimals only for non-whole amounts. */
export function formatSalaryAmount(
  amount: number,
  currency?: string | null,
): string {
  const digits = Number.isInteger(amount) ? 0 : 2;
  const fractionOptions = {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  };
  const plain = amount.toLocaleString(LOCALE, fractionOptions);
  const code = currency?.trim().toUpperCase();
  if (!code) return plain;
  try {
    const parts = new Intl.NumberFormat(LOCALE, {
      style: "currency",
      currency: code,
      ...fractionOptions,
    }).formatToParts(amount);
    const symbol = EXPLICIT_SYMBOLS[code];
    return parts
      .map((part) => (symbol && part.type === "currency" ? symbol : part.value))
      .join("");
  } catch {
    // Malformed currency code: keep the figure readable rather than failing.
    return `${code} ${plain}`;
  }
}

/** Display parts for a salary, or null when there is nothing to show. */
export function formatSalary(input: SalaryInput): SalaryDisplay | null {
  const range = resolveSalaryRange(input);
  if (!range) return null;
  const source = input.source?.trim().toLowerCase() ?? "";
  const estimated = ESTIMATED_SOURCES.has(source);
  const low = formatSalaryAmount(range.min, input.currency);
  const high = formatSalaryAmount(range.max, input.currency);
  const figure = range.min === range.max ? low : `${low} – ${high}`;
  const period = periodLabel(input.period);
  return {
    amount: estimated ? `~${figure}` : figure,
    period: period ? `/ ${period}` : null,
    estimated,
  };
}

/** Pay period for its own table column ("Yearly", "Hourly", …), or null
 *  when the job shows no salary or the period is unknown. */
export function formatPayPeriod(input: SalaryInput): string | null {
  if (!resolveSalaryRange(input)) return null;
  const known = knownPeriod(input.period);
  return known ? PERIOD_NAMES[known] : null;
}

/** One-line text form, e.g. "US$189,000 – US$303,000 / year", or null. */
export function salaryLabel(input: SalaryInput): string | null {
  const display = formatSalary(input);
  if (!display) return null;
  return display.period
    ? `${display.amount} ${display.period}`
    : display.amount;
}
