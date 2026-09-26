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
  const isExact = job.salary_currency === "USD" && job.salary_period === "yearly";
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

  return (
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
          <div className="shrink-0 text-right">
            <p className="text-base font-bold text-primary">
              {comparisonRange(job)}
            </p>
            <PostedSalary job={job} />
          </div>
        </Link>
      ))}
    </div>
  );
}
