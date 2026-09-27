"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatSalary } from "@/lib/salary";
import { getTopPaidJobs, type TopPaidJob } from "@/lib/services/home";
import { jobDetailHref } from "@/lib/services/job";
import CompanyLogo from "./ui/CompanyLogo";

/* Rounds to the nearest thousand for a compact "US$210k" figure - this
   comparison line is deliberately less precise than the exact posted salary
   shown underneath it, since its job is a fast side-by-side scan, not a
   quoted number. */
function compactUsd(amount: number): string {
  return `US$${Math.round(amount / 1000)}k`;
}

/* The annualized/converted comparison range, e.g. "US$210k – 275k" (min
   carries the currency prefix, max doesn't, to read as one range) or a
   single "US$180k" when there's no disclosed span (a levels.fyi average
   only - see SalaryStatsService). Prefixed with "≈" whenever this isn't
   already the literal posted figure (period != yearly and/or currency !=
   USD) - matches the same "~" convention the Salary component already uses
   for estimates, so an approximation always reads as one. */
function comparisonRange(job: TopPaidJob): string {
  const isExact =
    job.salary_currency === "USD" && job.salary_period === "yearly";
  const prefix = isExact ? "" : "≈";
  if (job.estimated_annual_usd_min === job.estimated_annual_usd_max) {
    return `${prefix}${compactUsd(job.estimated_annual_usd_max)}`;
  }
  const min = compactUsd(job.estimated_annual_usd_min).replace("US$", "");
  return `${prefix}US$${min} – ${Math.round(job.estimated_annual_usd_max / 1000)}k`;
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

/* A round upper bound for the shared scale, e.g. 275_000 -> 300_000 - always
   rounds up to the next $100k so a bar never clips at the right edge, and
   ticks land on clean numbers ($0/$100k/$200k/...) instead of whatever the
   highest job's exact figure happens to be. */
function niceScaleMax(highest: number): number {
  return Math.max(100_000, Math.ceil(highest / 100_000) * 100_000);
}

/* Ticks every $100k from 0 up to the scale max, e.g. [0, 100000, 200000,
   300000] - shown once above the list of bars (right-aligned and the same
   width as SalarySpanBar's track, so the ticks land above the bars they
   describe) rather than each row drawing its own axis. */
function ScaleAxis({ scaleMax }: { scaleMax: number }) {
  const step = 100_000;
  const tickCount = scaleMax / step + 1;
  const ticks = Array.from({ length: tickCount }, (_, i) => i * step);
  return (
    <div className="mb-2 flex justify-end">
      <div className="flex w-40 justify-between text-xs text-ink-muted sm:w-56">
        {ticks.map((tick) => (
          <span key={tick}>${tick / 1000}k</span>
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

  const scaleMax = niceScaleMax(
    Math.max(...jobs.map((job) => job.estimated_annual_usd_max)),
  );

  return (
    <div>
      <div className="mb-3">
        <PayViewToggle view={view} onChange={setView} />
      </div>
      {view === "chart" && <ScaleAxis scaleMax={scaleMax} />}
      <div className="flex flex-col gap-3">
        {jobs.map((job, index) => (
          <Link
            key={job.job_id}
            href={jobDetailHref(job.job_id)}
            className="flex items-center gap-4 rounded-xl border border-line bg-surface p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md sm:p-5"
          >
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
            {view === "chart" ? (
              <SalarySpanBar job={job} scaleMax={scaleMax} />
            ) : (
              <div className="shrink-0 text-right">
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
