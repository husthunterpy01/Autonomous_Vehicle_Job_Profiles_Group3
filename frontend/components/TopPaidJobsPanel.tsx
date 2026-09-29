"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatSalary } from "@/lib/salary";
import {
  comparisonRange,
  computeScale,
  formatCompactUsd,
} from "@/lib/salary-scale";
import { getTopPaidJobs, type TopPaidJob } from "@/lib/services/home";
import { jobDetailHref } from "@/lib/services/job";
import CompanyLogo from "./ui/CompanyLogo";

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

// Shared by ScaleAxis and SalarySpanBar so the ticks land exactly above the
// bars they describe - both the track and the range-label column need to be
// the same size in both places, or the two drift apart (see SalarySpanBar).
const _TRACK_WIDTH = "w-40 sm:w-56";
const _LABEL_WIDTH = "min-w-[8.5rem] sm:min-w-[10.5rem]";

/* Ticks from 0 to the scale max in steps of `step`, e.g. [0, 100000,
   200000, 300000] - shown once above the list of bars, rather than each row
   drawing its own axis. Left-aligned to match where the bars sit once the
   card stacks vertically on mobile (FE-21); the bars move to the right-hand
   side of the row from sm: up, so the axis does too.

   The ticks track is the same fixed width as SalarySpanBar's track, but that
   alone isn't enough to land ticks above bars: each row is a [track][range
   label] pair right-aligned as a whole (see SalarySpanBar), so the track's
   own position depends on how wide that row's label is. The trailing spacer
   below reserves the same width as the label column, unlabeled and empty,
   so the ticks track sits exactly where every row's track sits rather than
   where the row's right edge (label included) sits.

   The row cards have their own inner padding (p-4/sm:p-5) that insets their
   content from the card edge - the axis sits outside any card, so without
   matching px-4/sm:px-5 here it right-aligns to the card's outer edge
   instead of its padded content edge, landing a card-padding's-width to the
   right of the actual bars beneath it. */
function ScaleAxis({ scaleMax, step }: { scaleMax: number; step: number }) {
  const ticks = Array.from({ length: scaleMax / step + 1 }, (_, i) => i * step);
  return (
    <div className="mb-2 flex justify-start px-4 sm:justify-end sm:px-5">
      <div className="flex items-center gap-3">
        <div
          className={`flex justify-between text-xs text-ink-muted ${_TRACK_WIDTH}`}
        >
          {ticks.map((tick) => (
            <span key={tick}>{formatCompactUsd(tick).replace("US$", "$")}</span>
          ))}
        </div>
        <div aria-hidden="true" className={`shrink-0 ${_LABEL_WIDTH}`} />
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
   disappearing.

   Martin's follow-up review: the shared axis above only ticks round numbers,
   so a row's actual range had no label anywhere near it - reading exact
   figures off the bar alone meant interpolating between distant gridlines,
   and got worse the narrower a bar was. comparisonRange() is now printed
   next to every bar rather than left to the axis to imply. The label column
   is a fixed min-width (_LABEL_WIDTH, shared with ScaleAxis's spacer) rather
   than sized to its own text - each row is right-aligned as a [track][label]
   pair (the card's justify-between), so if the label were left to size
   itself, a longer or shorter range string would shift that row's track
   left or right by the difference, throwing off both the shared axis above
   and comparisons between rows' bars. A fixed column keeps every track at
   the same x regardless of that row's own number of digits. Because the
   range is real visible text now (not just implied by the bar's position),
   it doubles as the bar's accessible name and no separate sr-only
   description is needed. */
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
    <div className="flex shrink-0 items-center gap-3">
      <div
        aria-hidden="true"
        className={`relative h-2 shrink-0 rounded-full bg-line ${_TRACK_WIDTH}`}
      >
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
      <span
        className={`shrink-0 whitespace-nowrap text-right text-sm font-bold text-primary ${_LABEL_WIDTH}`}
      >
        {comparisonRange(job)}
      </span>
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
   two-state text choice rather than an icon-labeled table/cards switch.
   FE-21 (AC7): each button is already keyboard-focusable and its visible
   text is its accessible name, but the pair reads as two unrelated buttons
   without a group label explaining what they're switching between -
   role="group" + aria-label ties them together for assistive tech the same
   way the visible pill border does for sighted users. */
function PayViewToggle({
  view,
  onChange,
}: {
  view: PayView;
  onChange: (view: PayView) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Salary display format"
      className="inline-flex rounded-lg border border-line bg-surface p-0.5"
    >
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
   same way the rest of the app does via lib/salary's formatSalary().

   A levels.fyi-estimate row's title/company come from whichever one job at
   that company happened to rank first (SalaryStatsService picks one to
   represent the company-wide figure) - the number isn't really that job's
   own salary, so the "Company estimate" label under it says so explicitly
   rather than letting it read as a normal, job-specific listing (Weishan,
   PR #147 follow-up). */
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
                {job.salary_source === "levels_fyi_average" && (
                  <p className="mt-0.5 text-xs text-ink-muted">
                    Company estimate
                  </p>
                )}
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
