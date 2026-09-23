"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import CompanySummaryCard, {
  type CompanySummaryInfo,
} from "@/components/ui/CompanySummaryCard";
import DetailHeaderCard from "@/components/ui/DetailHeaderCard";
import { JobRow } from "@/components/ui/JobResultsList";
import Salary from "@/components/ui/Salary";
import StatusBadge from "@/components/ui/StatusBadge";
import Tag from "@/components/ui/Tag";
import { ApiError } from "@/lib/services/api";
import { companyTypeLabel, getCompany } from "@/lib/services/company";
import {
  descriptionSections,
  employmentTypeLabel,
  getJob,
  getJobs,
  isJobUuid,
  jobCategoryLabels,
  jobSalary,
  requirementLines,
  seniorityLabel,
  type DescriptionBlock,
  type JobDetail,
  type JobListItem,
} from "@/lib/services/job";
import {
  getCompanyById,
  getJobById,
  getSimilarJobs,
  mockJobSalary,
  type Job,
} from "@/lib/mock-data";

type Status = "loading" | "ready" | "notfound" | "error";

function CheckIcon() {
  return (
    <svg
      className="mt-0.5 h-4 w-4 shrink-0 text-primary"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m4.5 12.75 6 6 9-13.5"
      />
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

function jobIdFromPath(pathname: string, fallback: string): string {
  const fromPath = pathname.match(/\/jobs\/([^/]+)\/?$/)?.[1];
  if (fromPath && fromPath !== "_") return decodeURIComponent(fromPath);
  return fallback === "_" ? "" : fallback;
}

const MOCK_EMPLOYMENT_TYPE: Record<Job["type"], number> = {
  "Full-time": 1,
  "Part-time": 2,
  Contract: 3,
  Internship: 5,
};

function mockToListItem(job: Job): JobListItem {
  const salary = mockJobSalary(job);
  return {
    job_id: job.id,
    title: job.title,
    company_id: job.companyId,
    company_name: job.company,
    locations: [job.country],
    skills: job.skills,
    employment_type: MOCK_EMPLOYMENT_TYPE[job.type] ?? null,
    raw_description: job.description,
    source_url: job.sourceUrl,
    posted_date: job.postedDate,
    salary_min: salary.min,
    salary_max: salary.max,
    salary_currency: salary.currency,
    salary_period: salary.period,
    salary_source: salary.source,
  };
}

function DescriptionBlocks({ blocks }: { blocks: DescriptionBlock[] }) {
  return (
    <div className="mt-4 space-y-4 text-[15px] leading-7 text-ink-secondary">
      {blocks.map((block, i) => {
        if (block.type === "heading") {
          return (
            <h3
              key={`h-${i}`}
              className="pt-2 text-sm font-semibold tracking-wide text-ink"
            >
              {block.text}
            </h3>
          );
        }
        if (block.type === "list") {
          return (
            <ul key={`l-${i}`} className="space-y-2.5">
              {block.items.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2.5 text-[15px] leading-6"
                >
                  <CheckIcon />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={`p-${i}`} className="text-pretty">
            {block.text}
          </p>
        );
      })}
    </div>
  );
}

function DescriptionSection({ description }: { description: string }) {
  const sections = descriptionSections(description);
  const hasContent = sections.some((section) => section.blocks.length > 0);
  if (!hasContent) {
    return (
      <section>
        <h2 className="text-lg font-bold text-ink">Description</h2>
        <p className="mt-3 text-sm text-ink-muted">No description provided.</p>
      </section>
    );
  }
  return (
    <div className="space-y-8">
      {sections.map((section) =>
        section.blocks.length === 0 ? null : (
          <section key={section.title}>
            <h2 className="text-lg font-bold text-ink">{section.title}</h2>
            <DescriptionBlocks blocks={section.blocks} />
          </section>
        ),
      )}
    </div>
  );
}

function RequirementsSection({ requirements }: { requirements: string[] }) {
  if (requirements.length === 0) return null;
  return (
    <section>
      <h2 className="text-lg font-bold text-ink">Requirements</h2>
      <ul className="mt-3 space-y-2.5">
        {requirements.map((req) => (
          <li
            key={req}
            className="flex items-start gap-2.5 text-sm text-ink-secondary"
          >
            <CheckIcon />
            {req}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SkillsSection({ skills }: { skills: string[] }) {
  if (skills.length === 0) return null;
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

function RoleSidebar({
  postedDate,
  type,
  salary,
  department,
  seniority,
  company,
}: {
  postedDate: string | null;
  type: string | null;
  salary: ReturnType<typeof jobSalary>;
  department: string | null;
  seniority: string | null;
  company: CompanySummaryInfo | null;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
        <h2 className="font-bold text-ink">About this role</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-ink-muted">Job Posted On</dt>
            <dd className="font-medium text-ink">
              {postedDate ? formatDate(postedDate) : "Date unknown"}
            </dd>
          </div>
          {type && (
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Job Type</dt>
              <dd className="font-medium text-ink">{type}</dd>
            </div>
          )}
          {seniority && (
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Seniority</dt>
              <dd className="font-medium text-ink">{seniority}</dd>
            </div>
          )}
          {department && (
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Department</dt>
              <dd className="text-right font-medium text-ink">{department}</dd>
            </div>
          )}
          <div className="flex items-center justify-between gap-4">
            <dt className="text-ink-muted">Salary</dt>
            <dd>
              <Salary {...salary} />
            </dd>
          </div>
        </dl>
      </div>

      {company && <CompanySummaryCard company={company} />}
    </div>
  );
}

function SimilarJobsSection({ jobs }: { jobs: JobListItem[] }) {
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
          <JobRow key={job.job_id} job={job} />
        ))}
      </div>
    </section>
  );
}

export default function JobDetailClient({ id = "" }: { id?: string }) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const jobId = searchParams.get("id")?.trim() || jobIdFromPath(pathname, id);

  const [status, setStatus] = useState<Status>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [company, setCompany] = useState<CompanySummaryInfo | null>(null);
  const [similarJobs, setSimilarJobs] = useState<JobListItem[]>([]);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      await Promise.resolve();
      if (cancelled) return;
      if (!jobId) {
        setStatus("notfound");
        return;
      }

      setStatus("loading");
      setErrorMessage(null);

      if (isJobUuid(jobId)) {
        try {
          const detail = await getJob(jobId);
          if (cancelled) return;
          setJob(detail);
          setCompany({
            id: detail.company_id,
            name: detail.company_name,
          });
          setStatus("ready");

          const categoryId = detail.category?.sub_types[0]?.category_id;
          const [companyResult, similarResult] = await Promise.allSettled([
            getCompany(detail.company_id),
            categoryId
              ? getJobs({ category_id: categoryId, page_size: 4 })
              : Promise.resolve({ items: [] as JobListItem[] }),
          ]);
          if (cancelled) return;

          if (companyResult.status === "fulfilled") {
            const c = companyResult.value;
            const type = companyTypeLabel(c.company_type);
            setCompany({
              id: c.company_id,
              name: c.name,
              type,
              about: c.description,
              careersUrl: c.career_page_url ?? c.website_url,
            });
          }

          const similar =
            similarResult.status === "fulfilled"
              ? similarResult.value.items.filter(
                  (item) => item.job_id !== detail.job_id,
                )
              : [];
          setSimilarJobs(similar.slice(0, 3));
          return;
        } catch (error) {
          if (cancelled) return;
          if (error instanceof ApiError && error.status === 404) {
            setStatus("notfound");
            return;
          }
          setErrorMessage(
            error instanceof ApiError
              ? error.message
              : "Couldn't load this job.",
          );
          setStatus("error");
          return;
        }
      }

      const mock = getJobById(jobId);
      if (!mock) {
        setStatus("notfound");
        return;
      }
      const salary = mockJobSalary(mock);
      setJob({
        job_id: mock.id,
        title: mock.title,
        company_id: mock.companyId,
        company_name: mock.company,
        locations: [mock.country],
        skills: mock.skills,
        employment_type: MOCK_EMPLOYMENT_TYPE[mock.type] ?? null,
        raw_description: mock.description,
        source_url: mock.sourceUrl,
        posted_date: mock.postedDate,
        salary_min: salary.min,
        salary_max: salary.max,
        salary_currency: salary.currency,
        salary_period: salary.period,
        salary_source: salary.source,
        category: {
          main_type: mock.category,
          taxonomy_version: 1,
          sub_types: [],
        },
        department: null,
        seniority_level: null,
        requirements: mock.requirements.join("\n"),
        source_platform: null,
        source_job_id: null,
      });
      const mockCompany = getCompanyById(mock.companyId);
      setCompany(
        mockCompany
          ? {
              id: mockCompany.id,
              name: mockCompany.name,
              type: mockCompany.type,
              country: mockCompany.country,
              about: mockCompany.about,
              size: mockCompany.size,
              openPositions: mockCompany.openPositions,
              careersUrl: mockCompany.careersUrl,
              profileHref: `/companies/${mockCompany.id}`,
            }
          : { id: mock.companyId, name: mock.company, country: mock.country },
      );
      setSimilarJobs(getSimilarJobs(mock).map(mockToListItem));
      setStatus("ready");
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [jobId, reloadToken]);

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <div
          aria-busy="true"
          className="rounded-xl border border-dashed border-line bg-surface p-12 text-center"
        >
          <p className="font-semibold text-ink">Loading job…</p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <div
          role="alert"
          className="rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
        >
          <p className="font-semibold text-warning">Couldn&apos;t load job</p>
          <p className="mt-2 text-sm text-ink-secondary">{errorMessage}</p>
          <button
            type="button"
            onClick={() => setReloadToken((n) => n + 1)}
            className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (status === "notfound" || !job) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <Link
          href="/search"
          className="text-sm font-medium text-primary hover:text-primary-hover"
        >
          ← Back to jobs
        </Link>
        <div className="mt-8 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
          <p className="font-semibold text-ink">Job not found</p>
          <p className="mt-2 text-sm text-ink-secondary">
            This posting may have been removed, or the link is out of date.
          </p>
        </div>
      </div>
    );
  }

  const location = job.locations.length > 0 ? job.locations.join(", ") : null;
  const type = employmentTypeLabel(job.employment_type);
  const subtitle = [job.company_name, location, type]
    .filter(Boolean)
    .join(" · ");
  const categories = jobCategoryLabels(job.category);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <Link
        href="/search"
        className="text-sm font-medium text-primary hover:text-primary-hover"
      >
        ← Back to jobs
      </Link>

      <DetailHeaderCard
        logoText={job.company_name.charAt(0)}
        title={job.title}
        subtitle={subtitle}
        action={
          job.source_url
            ? { href: job.source_url, label: "View original posting" }
            : undefined
        }
        meta={
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="Open" />
            {categories.map((label) => (
              <Tag key={label} label={label} />
            ))}
          </div>
        }
      />

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          <DescriptionSection description={job.raw_description} />
          <RequirementsSection
            requirements={requirementLines(job.requirements)}
          />
          <SkillsSection skills={job.skills} />
        </div>

        <RoleSidebar
          postedDate={job.posted_date}
          type={type}
          salary={jobSalary(job)}
          department={job.department}
          seniority={seniorityLabel(job.seniority_level)}
          company={company}
        />
      </div>

      <SimilarJobsSection jobs={similarJobs} />
    </div>
  );
}
