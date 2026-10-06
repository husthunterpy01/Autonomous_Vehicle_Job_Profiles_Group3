/* The job search page's salary range filter (FE-22). Both bounds are
   whole-dollar annual USD figures, matching what the backend's
   salary_min/salary_max query params actually compare against (BE-22's
   annualized, currency-converted figure) - a job seeker types "60000"
   meaning "around this much a year," not a currency- or period-specific
   number. */

import { formatSalaryAmount } from "./salary.ts";

/** Strips everything but digits as the user types, so a negative sign,
 *  decimal point, or letter can never enter the field - "Only non-negative
 *  numbers are accepted" (AC3) enforced at input time rather than after the
 *  fact. Empty input stays empty (no bound), not "0". */
export function sanitizeSalaryDigits(raw: string): string {
  return raw.replace(/[^\d]/g, "");
}

/** The field's raw text to the bound it represents - null for "no bound",
 *  distinct from 0. */
export function parseSalaryField(raw: string): number | null {
  const digits = sanitizeSalaryDigits(raw);
  if (!digits) return null;
  const value = Number(digits);
  return Number.isSafeInteger(value) ? value : null;
}

/** "Min must not be greater than max" (AC3) - the one case the UI must
 *  catch and refuse to submit, rather than letting the backend's own 400
 *  (BE-22) be the first the user hears of it. Null when both bounds are
 *  valid (including when one or both are unset). */
export function salaryRangeError(
  min: number | null,
  max: number | null,
): string | null {
  if (min !== null && max !== null && min > max) {
    return "Minimum salary must not be greater than the maximum.";
  }
  return null;
}

/** "Salary: $60,000 - $100,000", "Salary: $60,000+", "Salary: Up to
 *  $100,000" for the removable filter chip (AC5) - null when neither bound
 *  is set, so callers can skip rendering the chip entirely. Reuses
 *  formatSalaryAmount so this matches every other dollar figure in the app
 *  (thousands separators, "US$" prefix) rather than a one-off format. */
export function salaryFilterLabel(
  min: number | null,
  max: number | null,
): string | null {
  if (min === null && max === null) return null;
  const low = min !== null ? formatSalaryAmount(min, "USD") : null;
  const high = max !== null ? formatSalaryAmount(max, "USD") : null;
  if (low && high) return `Salary: ${low} - ${high}`;
  if (low) return `Salary: ${low}+`;
  return `Salary: Up to ${high}`;
}
