import Link from "next/link";
import type { Job } from "@/lib/mock-data";

/* Shared job-listing UI primitives, used by Home, Search and (later)
   Company pages. Keep one implementation so all pages stay consistent. */

export function CompanyLogo({
  text,
  size = "h-10 w-10",
}: {
  text: string;
  size?: string;
}) {
  return (
    <span
      className={`flex ${size} shrink-0 items-center justify-center rounded-lg bg-ink/10 font-bold text-ink`}
    >
      {text}
    </span>
  );
}

export function Tag({ label }: { label: string }) {
  return (
    <span className="rounded-md bg-section px-2.5 py-1 text-xs font-medium text-ink-secondary">
      {label}
    </span>
  );
}

export function StatusBadge({ status }: { status: Job["status"] }) {
  const open = status === "Open";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium ${
        open ? "bg-success/10 text-success" : "bg-section text-ink-muted"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${open ? "bg-success" : "bg-ink-muted"}`}
      />
      {status}
    </span>
  );
}

export function Salary({ job }: { job: Job }) {
  return (
    <p className="text-sm font-semibold text-primary">
      ${job.salaryMin}k – ${job.salaryMax}k
    </p>
  );
}

/* Row layout — used for Latest Jobs (Home) and Search results. */
export function JobCardRow({ job }: { job: Job }) {
  return (
    <Link
      href="/search"
      className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
    >
      <CompanyLogo text={job.company.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{job.title}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {job.company} · {job.country}
        </p>
        <Salary job={job} />
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge status={job.status} />
          <Tag label={job.type} />
          <Tag label={job.category} />
        </div>
      </div>
    </Link>
  );
}

/* Column layout — used for Featured Jobs (Home). */
export function JobCardColumn({ job }: { job: Job }) {
  return (
    <Link
      href="/search"
      className="flex flex-col rounded-xl border border-line bg-surface p-6 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-primary hover:shadow-md"
    >
      <CompanyLogo text={job.company.charAt(0)} />
      <h3 className="mt-5 font-semibold text-ink">{job.title}</h3>
      <p className="mt-1 text-sm text-ink-secondary">
        {job.company} · {job.country}
      </p>
      <Salary job={job} />
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge status={job.status} />
        <Tag label={job.type} />
        <Tag label={job.category} />
      </div>
    </Link>
  );
}
