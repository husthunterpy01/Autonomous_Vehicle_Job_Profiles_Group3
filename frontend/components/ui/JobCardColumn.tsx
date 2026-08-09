import Link from "next/link";
import type { Job } from "@/lib/mock-data";
import CompanyLogo from "./CompanyLogo";
import StatusBadge from "./StatusBadge";
import Salary from "./Salary";
import Tag from "./Tag";

/* Column layout — used for Featured Jobs (Home). */
export default function JobCardColumn({ job }: { job: Job }) {
  return (
    <Link
      href={`/jobs/${job.id}`}
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
