import type { ReactNode } from "react";
import Link from "next/link";
import CompanyLogo from "@/components/ui/CompanyLogo";
import {
  JobColumn,
  JobRow,
  locationLabel,
} from "@/components/ui/JobResultsList";
import Salary from "@/components/ui/Salary";
import { jobDetailHref, jobSalary, type JobListItem } from "@/lib/services/job";

/* Presentational parts of the homepage job sections. Data loading lives in
   home-jobs.tsx, so these render from a plain state and can be tested
   without a network call. */

export type JobListState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "success"; jobs: JobListItem[]; total: number };

function Notice({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface p-12 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && (
        <p className="mt-2 text-sm text-ink-secondary">{children}</p>
      )}
    </div>
  );
}

function StatusNotice({ status }: { status: "loading" | "error" }) {
  return status === "loading" ? (
    <Notice title="Loading jobs…" />
  ) : (
    <Notice title="Couldn't load jobs right now">
      Please try again in a moment.
    </Notice>
  );
}

/* Compact rows for the hero card: the newest jobs, with the real total. */
export function LatestOpportunitiesView({ state }: { state: JobListState }) {
  return (
    <>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-ink">Latest opportunities</p>
        {state.status === "success" && state.total > 0 && (
          <span className="rounded-md bg-primary-light px-2 py-1 text-xs font-medium text-primary">
            {state.total.toLocaleString("en-US")} jobs
          </span>
        )}
      </div>

      {state.status !== "success" ? (
        <p className="mt-4 text-sm text-ink-muted">
          {state.status === "loading"
            ? "Loading jobs…"
            : "Couldn't load jobs right now."}
        </p>
      ) : state.jobs.length === 0 ? (
        <p className="mt-4 text-sm text-ink-muted">No jobs yet.</p>
      ) : (
        state.jobs.map((job) => {
          const location = locationLabel(job);
          return (
            <Link
              key={job.job_id}
              href={jobDetailHref(job.job_id)}
              className="mt-4 flex items-center gap-3 rounded-xl border border-line bg-surface p-3 transition-colors hover:border-primary"
            >
              <CompanyLogo text={job.company_name.charAt(0)} size="h-9 w-9" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">
                  {job.title}
                </p>
                <p className="truncate text-xs text-ink-muted">
                  {job.company_name}
                  {location ? ` · ${location}` : ""}
                </p>
              </div>
              <Salary {...jobSalary(job)} />
            </Link>
          );
        })
      )}
    </>
  );
}

export function LatestJobsView({ state }: { state: JobListState }) {
  if (state.status !== "success") return <StatusNotice status={state.status} />;
  if (state.jobs.length === 0) return <Notice title="No jobs yet" />;
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      {state.jobs.map((job) => (
        <JobRow key={job.job_id} job={job} />
      ))}
    </div>
  );
}

/* Featured = the newest jobs whose employer published a salary range. */
export function FeaturedJobsView({ state }: { state: JobListState }) {
  if (state.status !== "success") return <StatusNotice status={state.status} />;
  if (state.jobs.length === 0) {
    return (
      <Notice title="No published salary ranges yet">
        Featured jobs are roles where the employer publishes pay.{" "}
        <Link
          href="/search"
          className="font-semibold text-primary hover:text-primary-hover"
        >
          Browse all jobs
        </Link>
      </Notice>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
      {state.jobs.map((job) => (
        <JobColumn key={job.job_id} job={job} />
      ))}
    </div>
  );
}
