import type { ReactNode } from "react";
import type { JobSort, JobSortField } from "@/lib/job-sort";
import { formatPayPeriod } from "@/lib/salary";
import {
  EMPLOYMENT_TYPE_LABELS,
  jobSalary,
  type JobListItem,
} from "@/lib/services/job";
import CompanyLogo from "./CompanyLogo";
import Salary from "./Salary";
import Tag from "./Tag";

/* Shared Table/Cards rendering for any screen that lists real jobs (Find
   Jobs, My Favorites) — kept in one place so both stay visually and
   behaviorally identical. `renderAction`/`action` let each screen slot in
   its own per-job button (add to favorites, remove from favorites, ...)
   without this file needing to know what that action does. */

/* Each column carries its own sort field, so renaming a header can never
   quietly make it unsortable. Salary and Pay Period have none on purpose:
   their values mix pay periods, currencies and levels.fyi estimates, so
   ordering them against each other would be meaningless. */
type JobColumn = { label: string; sortField?: JobSortField };

const JOB_TABLE_COLUMNS: JobColumn[] = [
  { label: "Role", sortField: "title" },
  { label: "Company", sortField: "company" },
  { label: "Location" },
  { label: "Salary" },
  { label: "Pay Period" },
  { label: "Type" },
  { label: "Posted", sortField: "posted_date" },
];

function SortableHeader({
  label,
  field,
  sort,
  onSortChange,
}: {
  label: string;
  field: JobSortField;
  sort: JobSort;
  onSortChange: (field: JobSortField) => void;
}) {
  const active = sort.field === field;
  return (
    <button
      type="button"
      onClick={() => onSortChange(field)}
      className="inline-flex items-center gap-1 font-semibold text-ink-secondary hover:text-ink"
    >
      {label}
      <span
        aria-hidden="true"
        className={active ? "text-primary" : "text-ink-muted"}
      >
        {active && sort.direction === "asc" ? "▲" : "▼"}
      </span>
    </button>
  );
}

/** Joined locations, or null when the posting lists none. */
export function locationLabel(job: JobListItem): string | null {
  return job.locations.length > 0 ? job.locations.join(", ") : null;
}

export function typeLabel(job: JobListItem): string | null {
  return job.employment_type != null
    ? (EMPLOYMENT_TYPE_LABELS[job.employment_type] ?? "Other")
    : null;
}

export function postedLabel(job: JobListItem): string {
  if (!job.posted_date) return "Date unknown";
  // Fixed locale so dates read the same for every visitor ("Sep 6, 2026")
  // instead of following the browser language, matching the job detail page.
  return new Date(job.posted_date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function FavoriteHeartButton({
  filled,
  onClick,
  disabled,
}: {
  filled: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={filled}
      aria-label={filled ? "Remove from favorites" : "Add to favorites"}
      title={filled ? "Remove from favorites" : "Add to favorites"}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors disabled:cursor-default disabled:opacity-50 ${
        filled
          ? "text-primary hover:text-primary-hover"
          : "text-ink-muted hover:text-primary"
      }`}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-5 w-5"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={1.8}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 20.25c-.318 0-.635-.088-.912-.263C7.71 17.72 3 14.24 3 9.75 3 7.09 5.09 5 7.75 5c1.44 0 2.79.65 3.68 1.76a.75.75 0 0 0 1.14 0C13.46 5.65 14.81 5 16.25 5 18.91 5 21 7.09 21 9.75c0 4.49-4.71 7.97-8.088 10.237-.277.175-.594.263-.912.263Z"
        />
      </svg>
    </button>
  );
}

export function RemoveFavoriteButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label="Remove from favorites"
      title="Remove from favorites"
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink-muted transition-colors hover:text-warning disabled:cursor-default disabled:opacity-50"
    >
      <svg
        viewBox="0 0 24 24"
        className="h-5 w-5"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6 18 18 6M6 6l12 12"
        />
      </svg>
    </button>
  );
}

export function JobRow({
  job,
  action,
}: {
  job: JobListItem;
  action?: ReactNode;
}) {
  const type = typeLabel(job);
  const location = locationLabel(job);
  return (
    // Not a Link: job detail pages are still mock-only (static export
    // requires every dynamic route known at build time), so a real job id
    // would 404/crash. Re-enable once /jobs/[id] is wired to the real API.
    <div className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5">
      <CompanyLogo text={job.company_name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{job.title}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {job.company_name}
          {location ? ` · ${location}` : ""}
        </p>
        <Salary className="mt-1" {...jobSalary(job)} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {type && <Tag label={type} />}
          <span className="text-xs text-ink-muted">
            Posted {postedLabel(job)}
          </span>
        </div>
      </div>
      {action}
    </div>
  );
}

export function JobsTable({
  jobs,
  renderAction,
  actionColumnLabel = "",
  sort,
  onSortChange,
}: {
  jobs: JobListItem[];
  renderAction?: (job: JobListItem) => ReactNode;
  actionColumnLabel?: string;
  /* Both together make the headers sortable; screens without server-side
     sorting (My Favorites) simply leave them out. */
  sort?: JobSort;
  onSortChange?: (field: JobSortField) => void;
}) {
  const columns: JobColumn[] = renderAction
    ? [...JOB_TABLE_COLUMNS, { label: actionColumnLabel }]
    : JOB_TABLE_COLUMNS;

  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[900px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-section/60">
            {columns.map(({ label, sortField }, index) => {
              const active = Boolean(
                sort && sortField && onSortChange && sort.field === sortField,
              );
              return (
                <th
                  key={label || `col-${index}`}
                  scope="col"
                  aria-sort={
                    active && sort
                      ? sort.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : undefined
                  }
                  className="px-4 py-4 text-sm font-semibold text-ink-secondary first:pl-5 last:pr-5"
                >
                  {sortField && sort && onSortChange ? (
                    <SortableHeader
                      label={label}
                      field={sortField}
                      sort={sort}
                      onSortChange={onSortChange}
                    />
                  ) : (
                    label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.job_id}
              className="border-b border-line last:border-b-0 hover:bg-section/40"
            >
              <td className="px-4 py-4 pl-5 align-middle font-semibold text-ink last:pr-5">
                {job.title}
              </td>
              <td className="px-4 py-4 text-sm text-ink-secondary last:pr-5">
                {job.company_name}
              </td>
              <td className="px-4 py-4 text-sm text-ink last:pr-5">
                {locationLabel(job) ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-4 last:pr-5">
                <Salary fallback="—" showPeriod={false} {...jobSalary(job)} />
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary last:pr-5">
                {formatPayPeriod(jobSalary(job)) ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary last:pr-5">
                {typeLabel(job) ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary last:pr-5">
                {postedLabel(job)}
              </td>
              {renderAction && (
                <td className="whitespace-nowrap px-4 py-4 align-middle last:pr-5">
                  {renderAction(job)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
