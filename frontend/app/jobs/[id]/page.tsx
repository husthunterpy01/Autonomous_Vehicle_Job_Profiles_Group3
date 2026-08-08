import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getCompanyById,
  getJobById,
  getSimilarJobs,
  type Company,
  type Job,
} from "@/lib/mock-data";
import CompanySummaryCard from "@/components/ui/CompanySummaryCard";
import DetailHeaderCard from "@/components/ui/DetailHeaderCard";
import JobCardRow from "@/components/ui/JobCardRow";
import Salary from "@/components/ui/Salary";
import StatusBadge from "@/components/ui/StatusBadge";
import Tag from "@/components/ui/Tag";

function CheckIcon() {
  return (
    <svg
      className="mt-0.5 h-4 w-4 shrink-0 text-primary"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/* Page sections                                                       */
/* ------------------------------------------------------------------ */

function DescriptionSection({ description }: { description: string }) {
  return (
    <section>
      <h2 className="text-lg font-bold text-ink">Description</h2>
      <div className="mt-3 space-y-4 text-sm leading-relaxed text-ink-secondary">
        {description.split("\n\n").map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
      </div>
    </section>
  );
}

function RequirementsSection({ requirements }: { requirements: string[] }) {
  return (
    <section>
      <h2 className="text-lg font-bold text-ink">Requirements</h2>
      <ul className="mt-3 space-y-2.5">
        {requirements.map((req) => (
          <li key={req} className="flex items-start gap-2.5 text-sm text-ink-secondary">
            <CheckIcon />
            {req}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SkillsSection({ skills }: { skills: string[] }) {
  return (
    <section>
      <h2 className="text-lg font-bold text-ink">Skills</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {skills.map((skill) => (
          <Tag key={skill} label={skill} />
        ))}
      </div>
    </section>
  );
}

function RoleSidebar({ job, company }: { job: Job; company: Company | undefined }) {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
        <h2 className="font-bold text-ink">About this role</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink-muted">Job Posted On</dt>
            <dd className="font-medium text-ink">{formatDate(job.postedDate)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-muted">Job Type</dt>
            <dd className="font-medium text-ink">{job.type}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-ink-muted">Salary</dt>
            <dd>
              <Salary job={job} />
            </dd>
          </div>
        </dl>
      </div>

      {company && <CompanySummaryCard company={company} />}
    </div>
  );
}

/** Optional — returns null if there's nothing similar to show. */
function SimilarJobsSection({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0) return null;

  return (
    <section className="mt-12">
      <div className="flex items-end justify-between gap-4">
        <h2 className="text-xl font-bold text-ink">Similar Jobs</h2>
        <Link
          href="/search"
          className="text-sm font-semibold text-primary hover:text-primary-hover"
        >
          Show all jobs
        </Link>
      </div>
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {jobs.map((job) => (
          <JobCardRow key={job.id} job={job} />
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const job = getJobById(id);
  if (!job) notFound();

  const company = getCompanyById(job.companyId);
  const similarJobs = getSimilarJobs(job);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <Link
        href="/search"
        className="text-sm font-medium text-primary hover:text-primary-hover"
      >
        ← Back to jobs
      </Link>

      <DetailHeaderCard
        logoText={job.company.charAt(0)}
        title={job.title}
        subtitle={`${job.company} · ${job.country} · ${job.type}`}
        action={{ href: job.sourceUrl, label: "View original posting" }}
        meta={
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={job.status} />
            <Tag label={job.category} />
          </div>
        }
      />

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          <DescriptionSection description={job.description} />
          <RequirementsSection requirements={job.requirements} />
          <SkillsSection skills={job.skills} />
        </div>

        <RoleSidebar job={job} company={company} />
      </div>

      <SimilarJobsSection jobs={similarJobs} />
    </div>
  );
}