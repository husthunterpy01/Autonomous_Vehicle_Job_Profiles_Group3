import type { TopPaidJob } from "@/lib/services/home";

/* Compact USD figure for fast scanning - "US$210k" below a million,
   "US$2.6M" at or above it, so an outlier salary reads as "$2.6M" instead
   of an unwieldy "$2600k" (FE-21: formatting must stay consistent
   regardless of magnitude). Shared by TopPaidJobsPanel's comparison range
   text and its chart axis ticks, so both use identical formatting. */
export function formatCompactUsd(amount: number): string {
  if (amount >= 1_000_000) {
    const millions = Math.round((amount / 1_000_000) * 10) / 10;
    return `US$${millions}M`;
  }
  return `US$${Math.round(amount / 1000)}k`;
}

/* The annualized/converted comparison range, e.g. "US$210k – US$275k" or a
   single "US$180k" when there's no disclosed span (a levels.fyi average
   only - see SalaryStatsService). Each side is formatted independently
   (rather than a bare number on the max side) so a range that crosses the
   k/M boundary, e.g. "US$850k – US$1.2M", still reads correctly. Prefixed
   with "≈" whenever this isn't already the literal posted figure (period
   != yearly and/or currency != USD) - matches the same "~" convention the
   Salary component already uses for estimates, so an approximation always
   reads as one. */
export function comparisonRange(job: TopPaidJob): string {
  const isExact =
    job.salary_currency === "USD" && job.salary_period === "yearly";
  const prefix = isExact ? "" : "≈";
  if (job.estimated_annual_usd_min === job.estimated_annual_usd_max) {
    return `${prefix}${formatCompactUsd(job.estimated_annual_usd_max)}`;
  }
  return `${prefix}${formatCompactUsd(job.estimated_annual_usd_min)} – ${formatCompactUsd(job.estimated_annual_usd_max)}`;
}

/* Rounds a raw step (highest / target tick count) up to a "nice" 1/2/5 x
   10^n number, e.g. 74_000 -> 100_000, 1_400_000 -> 2_000_000 - the
   standard approach for chart axes, so ticks always land on clean numbers
   no matter the scale. */
export function niceStep(roughStep: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const normalized = roughStep / magnitude;
  const niceNormalized =
    normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return niceNormalized * magnitude;
}

const TARGET_TICKS = 4;

/* Picks a step size that keeps a chart axis to a small, fixed number of
   ticks regardless of how large the highest value is (FE-21: a fixed
   $100k step previously produced 30+ overlapping ticks once an outlier
   salary pushed the scale past $3M), then rounds the max up to a whole
   number of that step so a bar never clips at the right edge. */
export function computeScale(highest: number): { max: number; step: number } {
  const step = niceStep(Math.max(highest, 1) / TARGET_TICKS);
  const max = Math.ceil(Math.max(highest, step) / step) * step;
  return { max, step };
}
