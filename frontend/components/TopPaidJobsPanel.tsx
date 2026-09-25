"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTopPaidJobs, type TopPaidJob } from "@/lib/services/home";
import { jobDetailHref } from "@/lib/services/job";
import CompanyLogo from "./ui/CompanyLogo";
import Salary from "./ui/Salary";

/* Ranked by estimated_annual_usd (period-annualized, currency-converted -
   see SalaryStatsService), but every card still displays pay exactly as
   posted via the same Salary component used everywhere else - only the
   sort order is computed, never the shown figure. */
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
            <Salary
              min={job.salary_min}
              max={job.salary_max}
              average={job.salary_average}
              currency={job.salary_currency}
              period={job.salary_period}
              source={job.salary_source}
            />
          </div>
        </Link>
      ))}
    </div>
  );
}
