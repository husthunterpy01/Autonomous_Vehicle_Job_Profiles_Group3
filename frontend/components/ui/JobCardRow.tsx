import Link from "next/link";
import type { Job } from "@/lib/mock-data";
import CompanyLogo from "./CompanyLogo";
import StatusBadge from "./StatusBadge";
import Salary from "./Salary";
import Tag from "./Tag";

/* Row layout — used for Latest Jobs (Home) and Search results. */
export default function JobCardRow({ job }: { job: Job }) {
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
