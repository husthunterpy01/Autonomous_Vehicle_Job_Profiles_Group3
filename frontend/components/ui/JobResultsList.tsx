import type { ReactNode } from "react";
import CompanyLogo from "./CompanyLogo";
import Tag from "./Tag";
import { EMPLOYMENT_TYPE_LABELS, type JobListItem } from "@/lib/services/job";

/* Shared Table/Cards rendering for any screen that lists real jobs (Find
   Jobs, My Favorites) — kept in one place so both stay visually and
   behaviorally identical. `renderAction` lets each screen slot in its own
   per-job button (add to favorites, remove from favorites, ...) without
   this file needing to know what that action does. */

export function locationLabel(job: JobListItem): string {
  return job.locations.length > 0
    ? job.locations.join(", ")
    : "Location not specified";
}

export function typeLabel(job: JobListItem): string | null {
  return job.employment_type != null
    ? (EMPLOYMENT_TYPE_LABELS[job.employment_type] ?? "Other")
    : null;
}

export function postedLabel(job: JobListItem): string {
  if (!job.posted_date) return "Date unknown";
  return new Date(job.posted_date).toLocaleDateString(undefined, {
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
  return (
    // Not a Link: job detail pages are still mock-only (static export
    // requires every dynamic route known at build time), so a real job id
    // would 404/crash. Re-enable once /jobs/[id] is wired to the real API.
    <div className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5">
      <CompanyLogo text={job.company_name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{job.title}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {job.company_name} · {locationLabel(job)}
        </p>
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
}: {
  jobs: JobListItem[];
  renderAction?: (job: JobListItem) => ReactNode;
  actionColumnLabel?: string;
}) {
  const columns = ["Role", "Company", "Location", "Type", "Posted"];
  if (renderAction) columns.push(actionColumnLabel);

  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[800px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-section/60">
            {columns.map((label, index) => (
              <th
                key={label || `col-${index}`}
                scope="col"
                className="px-4 py-4 text-sm font-semibold text-ink-secondary first:pl-5 last:pr-5"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.job_id}
              className="border-b border-line last:border-b-0 hover:bg-section/40"
            >
              <td className="px-4 py-4 pl-5 align-middle font-semibold text-ink">
                {job.title}
              </td>
              <td className="px-4 py-4 text-sm text-ink-secondary">
                {job.company_name}
              </td>
              <td className="px-4 py-4 text-sm text-ink">
                {locationLabel(job)}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary">
                {typeLabel(job) ?? "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-ink-secondary">
                {postedLabel(job)}
              </td>
              {renderAction && (
                <td className="whitespace-nowrap px-4 py-4 pr-5 align-middle">
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
