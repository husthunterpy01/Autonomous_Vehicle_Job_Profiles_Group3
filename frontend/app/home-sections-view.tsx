import type { ReactNode } from "react";
import Link from "next/link";
import CompanyLogo from "@/components/ui/CompanyLogo";
import {
  JobColumn,
  JobRow,
  locationLabel,
} from "@/components/ui/JobResultsList";
import Salary from "@/components/ui/Salary";
import type { CategoryStat } from "@/lib/category-filter";
import {
  companyDetailHref,
  type CompanyWithJobCount,
} from "@/lib/services/company";
import { jobDetailHref, jobSalary, type JobListItem } from "@/lib/services/job";

/* Presentational parts of the homepage's data-driven sections. Data loading
   lives in home-sections.tsx, so these render from a plain state and can be
   tested without a network call. */

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

/* The companies with the most open jobs, busiest first; companies with no
   open jobs are left out of a "Companies Hiring" section. */
export function topHiringCompanies(
  companies: CompanyWithJobCount[],
  count: number,
): CompanyWithJobCount[] {
  return companies
    .filter((company) => company.number_of_jobs > 0)
    .sort(
      (a, b) =>
        b.number_of_jobs - a.number_of_jobs || a.name.localeCompare(b.name),
    )
    .slice(0, count);
}

export type CompanyListState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "success"; companies: CompanyWithJobCount[] };

export function TopCompaniesView({ state }: { state: CompanyListState }) {
  if (state.status === "loading") return <Notice title="Loading companies…" />;
  if (state.status === "error") {
    return (
      <Notice title="Couldn't load companies right now">
        Please try again in a moment.
      </Notice>
    );
  }
  if (state.companies.length === 0) {
    return <Notice title="No companies are hiring right now" />;
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {state.companies.map((company) => (
        <Link
          key={company.company_id}
          href={companyDetailHref(company.company_id)}
          className="flex items-center gap-3 rounded-xl border border-line bg-surface p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
        >
          <CompanyLogo text={company.name.charAt(0)} size="h-9 w-9" />
          <div className="min-w-0">
            <p className="truncate font-semibold text-ink">{company.name}</p>
            <p className="text-xs text-ink-muted">
              {company.number_of_jobs.toLocaleString("en-US")} open{" "}
              {company.number_of_jobs === 1 ? "position" : "positions"}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}

/* The category with the most jobs right now, or null when there are none. */
export function busiestCategory(stats: CategoryStat[]): CategoryStat | null {
  return stats.reduce<CategoryStat | null>(
    (best, stat) =>
      stat.job_count > 0 && (!best || stat.job_count > best.job_count)
        ? stat
        : best,
    null,
  );
}

/* Hero highlight. We have no hiring-over-time data, so this states a
   current fact (most openings) rather than a trend, and renders nothing
   until there is one to show. */
export function TopCategoryView({
  category,
}: {
  category: CategoryStat | null;
}) {
  if (!category) return null;
  return (
    <div className="mt-5 flex items-center justify-between rounded-xl bg-primary-light px-4 py-3">
      <div>
        <p className="text-xs font-medium text-primary">Most openings</p>
        <p className="text-sm font-semibold text-ink">{category.sub_type}</p>
      </div>
      <span className="text-sm font-bold text-primary">
        {category.job_count.toLocaleString("en-US")} jobs
      </span>
    </div>
  );
}
