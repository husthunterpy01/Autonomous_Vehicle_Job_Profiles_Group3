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
