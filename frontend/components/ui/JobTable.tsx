import Link from "next/link";
import type { Job } from "@/lib/mock-data";
import CategoryTag from "./CategoryTag";
import StatusBadge from "./StatusBadge";
import Tag from "./Tag";
import { formatSalary } from "./Salary";

export type JobSortKey =
  | "role"
  | "company"
  | "location"
  | "salary"
  | "status"
  | "type"
  | "category";

type JobTableProps = {
  jobs: Job[];
  sortBy: JobSortKey | null;
  sortDir: "asc" | "desc";
  onSort: (key: JobSortKey) => void;
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

function SortIndicator({ direction }: { direction: "asc" | "desc" }) {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4 text-primary"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      {direction === "asc" ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="m5 15 7-7 7 7" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
      )}
    </svg>
  );
}

export default function JobTable({
  jobs,
  sortBy,
  sortDir,
  onSort,
}: JobTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[900px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-section/60">
            {COLUMNS.map((column) => {
              const isActive = sortBy === column.key;
              return (
                <th key={column.key} scope="col" className="px-4 py-4 first:pl-5 last:pr-5">
                  <button
                    type="button"
                    aria-label={`Sort by ${column.label}`}
                    aria-sort={isActive ? sortDir : "none"}
                    onClick={() => onSort(column.key)}
                    className={`inline-flex items-center gap-1.5 text-sm font-semibold transition-colors hover:text-primary ${
                      isActive ? "text-primary" : "text-ink-secondary"
                    }`}
                  >
                    {column.label}
                    {isActive && <SortIndicator direction={sortDir} />}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              className="border-b border-line last:border-b-0 hover:bg-section/40"
            >
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
              <td className="px-4 py-4 text-sm text-ink-secondary">
                <Tag label={job.type} />
              </td>
              <td className="px-4 py-4 pr-5">
                <CategoryTag category={job.category} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
