"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatSalary } from "@/lib/salary";
import { getTopPaidJobs, type TopPaidJob } from "@/lib/services/home";
import { jobDetailHref } from "@/lib/services/job";
import CompanyLogo from "./ui/CompanyLogo";

/* Compact USD figure for fast scanning - "US$210k" below a million,
   "US$2.6M" at or above it, so an outlier salary reads as "$2.6M" instead
   of an unwieldy "$2600k" (FE-21: formatting must stay consistent
   regardless of magnitude). Shared by the comparison range text below and
   the chart's axis ticks, so both use identical formatting. */
function formatCompactUsd(amount: number): string {
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
function comparisonRange(job: TopPaidJob): string {
  const isExact =
    job.salary_currency === "USD" && job.salary_period === "yearly";
  const prefix = isExact ? "" : "≈";
  if (job.estimated_annual_usd_min === job.estimated_annual_usd_max) {
    return `${prefix}${formatCompactUsd(job.estimated_annual_usd_max)}`;
  }
  return `${prefix}${formatCompactUsd(job.estimated_annual_usd_min)} – ${formatCompactUsd(job.estimated_annual_usd_max)}`;
}

/* The literal posted figure, small and muted underneath the comparison
   range above - deliberately not the shared Salary component, which always
   renders its amount in bold primary color; here that emphasis belongs to
   the comparison range instead. */
function PostedSalary({ job }: { job: TopPaidJob }) {
  const display = formatSalary({
    min: job.salary_min,
    max: job.salary_max,
    average: job.salary_average,
    currency: job.salary_currency,
    period: job.salary_period,
    source: job.salary_source,
  });
  if (!display) return null;
  return (
    <p className="mt-0.5 text-xs text-ink-muted">
      {display.amount}
      {display.period && <span className="ml-1">{display.period}</span>}
    </p>
  );
}

/* Rounds a raw step (highest / target tick count) up to a "nice" 1/2/5 x
   10^n number, e.g. 74_000 -> 100_000, 1_400_000 -> 2_000_000 - the
   standard approach for chart axes, so ticks always land on clean numbers
   no matter the scale. */
function niceStep(roughStep: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const normalized = roughStep / magnitude;
  const niceNormalized =
    normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return niceNormalized * magnitude;
}

const TARGET_TICKS = 4;

/* Picks a step size that keeps the axis to a small, fixed number of ticks
   regardless of how large the highest value is (FE-21: a fixed $100k step
   previously produced 30+ overlapping ticks once an outlier salary pushed
   the scale past $3M), then rounds the max up to a whole number of that
   step so a bar never clips at the right edge. */
function computeScale(highest: number): { max: number; step: number } {
  const step = niceStep(Math.max(highest, 1) / TARGET_TICKS);
  const max = Math.ceil(Math.max(highest, step) / step) * step;
  return { max, step };
}

/* Ticks from 0 to the scale max in steps of `step`, e.g. [0, 100000,
   200000, 300000] - shown once above the list of bars, the same width as
   SalarySpanBar's track so the ticks land above the bars they describe,
   rather than each row drawing its own axis. Left-aligned to match where
   the bars sit once the card stacks vertically on mobile (FE-21); the bars
   move to the right-hand side of the row from sm: up, so the axis does too. */
function ScaleAxis({ scaleMax, step }: { scaleMax: number; step: number }) {
  const ticks = Array.from({ length: scaleMax / step + 1 }, (_, i) => i * step);
  return (
    <div className="mb-2 flex justify-start sm:justify-end">
      <div className="flex w-40 justify-between text-xs text-ink-muted sm:w-56">
        {ticks.map((tick) => (
          <span key={tick}>{formatCompactUsd(tick).replace("US$", "$")}</span>
        ))}
      </div>
    </div>
  );
}

/* The horizontal span itself: a fixed-width track (not stretched across the
   card) with a filled bar from estimated_annual_usd_min to
   estimated_annual_usd_max - Martin's review request for a faster way to
   compare ranges across jobs than reading numbers. Deliberately compact and
   left-aligned within its own slot rather than spanning the row, so a
   narrow range doesn't read as if it's using the whole card's width. A job
   with no disclosed range (min == max, a levels.fyi average only) renders
   as a dot rather than a zero-width bar, so it stays visible instead of
   disappearing. */
function SalarySpanBar({
  job,
  scaleMax,
}: {
  job: TopPaidJob;
  scaleMax: number;
}) {
  const left = (job.estimated_annual_usd_min / scaleMax) * 100;
  const right = (job.estimated_annual_usd_max / scaleMax) * 100;
  const isPoint = job.estimated_annual_usd_min === job.estimated_annual_usd_max;
  return (
    <div className="relative h-2 w-40 shrink-0 rounded-full bg-line sm:w-56">
      {isPoint ? (
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-surface bg-primary"
          style={{ left: `calc(${left}% - 6px)` }}
        />
      ) : (
        <div
          className="absolute h-2 rounded-full bg-primary"
          style={{ left: `${left}%`, width: `${right - left}%` }}
        />
      )}
    </div>
  );
}

type PayView = "list" | "chart";

const PAY_VIEW_LABELS: Record<PayView, string> = {
  list: "List View",
  chart: "Chart View",
};

/* Two-button pill matching the app's ViewToggle pattern (components/ui/
   ViewToggle.tsx), but smaller and local to this panel since it's a
   two-state text choice rather than an icon-labeled table/cards switch. */
function PayViewToggle({
  view,
  onChange,
}: {
  view: PayView;
  onChange: (view: PayView) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-surface p-0.5">
      {(["list", "chart"] as const).map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={view === option}
          onClick={() => onChange(option)}
          className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
            view === option
              ? "bg-primary-light text-primary"
              : "text-ink-secondary hover:text-ink"
          }`}
        >
          {PAY_VIEW_LABELS[option]}
        </button>
      ))}
    </div>
  );
}

/* Ranked by estimated_annual_usd_max (period-annualized, currency-converted
   - see SalaryStatsService). Each card shows that comparable figure as the
   prominent line (marked "≈" whenever it's an approximation, not the exact
   posted figure) plus the literal posted salary underneath, formatted the
   same way the rest of the app does via lib/salary's formatSalary(). */
export default function TopPaidJobsPanel() {
  const [jobs, setJobs] = useState<TopPaidJob[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [view, setView] = useState<PayView>("list");

  useEffect(() => {
    let cancelled = false;
    getTopPaidJobs(5)
      .then((result) => {
        if (cancelled) return;
        setJobs(result);
        setStatus("success");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return (
      <div className="rounded-2xl border border-line bg-section p-6 shadow-sm sm:p-8">
        <p className="text-sm text-ink-secondary">Loading top paid jobs…</p>
      </div>
    );
  }

  if (status === "error" || jobs.length === 0) {
    return (
      <div className="rounded-2xl border border-line bg-section p-6 shadow-sm sm:p-8">
        <p className="text-sm text-ink-secondary">
          {status === "error"
            ? "Couldn't load top paid jobs right now."
            : "No salary data available yet."}
        </p>
      </div>
    );
  }

  const { max: scaleMax, step: scaleStep } = computeScale(
    Math.max(...jobs.map((job) => job.estimated_annual_usd_max)),
  );

  return (
    <div>
      <div className="mb-3">
        <PayViewToggle view={view} onChange={setView} />
      </div>
      {view === "chart" && <ScaleAxis scaleMax={scaleMax} step={scaleStep} />}
      <div className="flex flex-col gap-3">
        {jobs.map((job, index) => (
          <Link
            key={job.job_id}
            href={jobDetailHref(job.job_id)}
            className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:p-5"
          >
            <div className="flex min-w-0 items-center gap-4 sm:max-w-sm">
              <span className="w-6 shrink-0 text-center text-lg font-extrabold text-ink-muted">
                {index + 1}
              </span>
              <CompanyLogo text={job.company_name.charAt(0)} />
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-semibold text-ink">{job.title}</h3>
                <p className="mt-1 truncate text-sm text-ink-secondary">
                  {job.company_name}
                </p>
              </div>
            </div>
            {view === "chart" ? (
              <SalarySpanBar job={job} scaleMax={scaleMax} />
            ) : (
              <div className="sm:shrink-0 sm:text-right">
                <p className="text-base font-bold text-primary">
                  {comparisonRange(job)}
                </p>
                <PostedSalary job={job} />
              </div>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
