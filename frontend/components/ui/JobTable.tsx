import Link from "next/link";
import type { Job } from "@/lib/mock-data";
import CategoryTag from "./CategoryTag";
import StatusBadge from "./StatusBadge";
import Tag from "./Tag";
import { formatSalary } from "./Salary";

export type JobSortKey =
  "role" | "company" | "location" | "salary" | "status" | "type" | "category";

export type JobSortDirection = "asc" | "desc";

export type JobSortRule = {
  key: JobSortKey;
  direction: JobSortDirection;
};

type JobTableProps = {
  jobs: Job[];
  sorts: JobSortRule[];
  onSort: (key: JobSortKey, additive: boolean) => void;
};

const COLUMNS: { key: JobSortKey; label: string }[] = [
  { key: "role", label: "Role" },
  { key: "company", label: "Company" },
  { key: "location", label: "Location" },
  { key: "salary", label: "Salary" },
  { key: "status", label: "Status" },
  { key: "type", label: "Type" },
  { key: "category", label: "Category" },
];

function SortIndicator({ direction }: { direction?: JobSortDirection }) {
  return (
    <svg
      aria-hidden="true"
      className={`h-4 w-4 ${direction ? "text-primary" : "text-ink-muted"}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      {direction === "asc" ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="m5 15 7-7 7 7" />
      ) : direction === "desc" ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
      ) : (
        <>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m5 10 7-6 7 6"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m5 14 7 6 7-6"
          />
        </>
      )}
    </svg>
  );
}

function JobTableRow({ job }: { job: Job }) {
  return (
    <tr className="border-b border-line last:border-b-0 hover:bg-section/40">
      <td className="px-4 py-4 pl-5 align-middle">
        <Link
          href={`/jobs/${job.id}`}
          className="font-semibold text-ink hover:text-primary"
        >
          {job.title}
        </Link>
      </td>
      <td className="px-4 py-4 text-sm text-ink-secondary">{job.company}</td>
      <td className="px-4 py-4 text-sm text-ink">{job.country}</td>
      <td className="whitespace-nowrap px-4 py-4 text-sm font-semibold text-primary">
        {formatSalary(job)}
      </td>
      <td className="px-4 py-4">
        <StatusBadge status={job.status} />
      </td>
      <td className="whitespace-nowrap px-4 py-4 text-center align-middle text-sm text-ink-secondary">
        <Tag label={job.type} />
      </td>
      <td className="px-4 py-4 pr-5">
        <CategoryTag category={job.category} />
      </td>
    </tr>
  );
}

export default function JobTable({ jobs, sorts, onSort }: JobTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[900px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-section/60">
            {COLUMNS.map((column) => {
              const sortIndex = sorts.findIndex(
                (sort) => sort.key === column.key,
              );
              const activeSort = sorts[sortIndex];
              const isActive = activeSort !== undefined;
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={
                    isActive
                      ? activeSort.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                  className="px-4 py-4 first:pl-5 last:pr-5"
                >
                  <button
                    type="button"
                    aria-label={`Sort by ${column.label}. Hold Shift while clicking to add a secondary sort.`}
                    onClick={(event) => onSort(column.key, event.shiftKey)}
                    className={`inline-flex items-center gap-1.5 text-sm font-semibold transition-colors hover:text-primary ${
                      isActive ? "text-primary" : "text-ink-secondary"
                    }`}
                  >
                    {column.label}
                    <SortIndicator direction={activeSort?.direction} />
                    {isActive && sorts.length > 1 && (
                      <span className="text-xs font-semibold text-ink-muted">
                        {sortIndex + 1}
                      </span>
                    )}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <JobTableRow key={job.id} job={job} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
