"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import DetailHeaderCard from "@/components/ui/DetailHeaderCard";
import JobCardRow from "@/components/ui/JobCardRow";
import { JobRow } from "@/components/ui/JobResultsList";
import Pagination from "@/components/ui/Pagination";
import { ApiError } from "@/lib/services/api";
import {
  companyTypeLabel,
  getCompany,
  isCompanyUuid,
  type CompanyDetail,
} from "@/lib/services/company";
import { getJobs, type JobListItem } from "@/lib/services/job";
import {
  getCompanyById,
  getJobsByCompanyId,
  type Company,
  type Job,
} from "@/lib/mock-data";

type Status = "loading" | "ready" | "notfound" | "error";

/* Matches the backend's default page size (see GET /jobs). Some companies
   already have 100+ open postings (NVIDIA, Waymo), so the job list needs
   real pagination rather than a single capped fetch. */
const JOBS_PAGE_SIZE = 10;

function companyIdFromPath(pathname: string, fallback: string): string {
  const fromPath = pathname.match(/\/companies\/([^/]+)\/?$/)?.[1];
  if (fromPath && fromPath !== "profile") return decodeURIComponent(fromPath);
  return fallback === "profile" ? "" : fallback;
}

export default function CompanyDetailClient({ id = "" }: { id?: string }) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const companyId =
    searchParams.get("id")?.trim() || companyIdFromPath(pathname, id);

  const [status, setStatus] = useState<Status>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [mockCompany, setMockCompany] = useState<Company | null>(null);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [mockJobs, setMockJobs] = useState<Job[]>([]);
  const [jobCount, setJobCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [reloadToken, setReloadToken] = useState(0);

  // Tracks the last companyId this effect ran for, so a brand-new company
  // always fetches page 1 of its jobs even if `page` still holds a stale
  // value left over from paging through a previous company's list.
  const prevCompanyIdRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const isNewCompany = prevCompanyIdRef.current !== companyId;
    prevCompanyIdRef.current = companyId;
    const pageToFetch = isNewCompany ? 1 : page;

    async function load() {
      if (!companyId) {
        setStatus("notfound");
        return;
      }

      setStatus("loading");
      setErrorMessage(null);

      if (isCompanyUuid(companyId)) {
        try {
          const [detail, jobsPage] = await Promise.all([
            getCompany(companyId),
            getJobs({
              company_id: companyId,
              page: pageToFetch,
              page_size: JOBS_PAGE_SIZE,
            }),
          ]);
          if (cancelled) return;
          setCompany(detail);
          setJobs(jobsPage.items);
          setJobCount(jobsPage.total);
          setPageCount(Math.max(1, jobsPage.total_pages));
          if (isNewCompany) setPage(1);
          setStatus("ready");
        } catch (error) {
          if (cancelled) return;
          if (error instanceof ApiError && error.status === 404) {
            setStatus("notfound");
            return;
          }
          setErrorMessage(
            error instanceof ApiError
              ? error.message
              : "Couldn't load this company.",
          );
          setStatus("error");
        }
        return;
      }

      const mock = getCompanyById(companyId);
      if (!mock) {
        setStatus("notfound");
        return;
      }
      setMockCompany(mock);
      setMockJobs(getJobsByCompanyId(mock.id));
      setStatus("ready");
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [companyId, page, reloadToken]);

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <div
          aria-busy="true"
          className="rounded-xl border border-dashed border-line bg-surface p-12 text-center"
        >
          <p className="font-semibold text-ink">Loading company…</p>
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
          <p className="font-semibold text-warning">
            Couldn&apos;t load company
          </p>
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

  if (status === "notfound" || (!company && !mockCompany)) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <Link
          href="/companies"
          className="text-sm font-medium text-primary hover:text-primary-hover"
        >
          ← Back to companies
        </Link>
        <div className="mt-8 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
          <p className="font-semibold text-ink">Company not found</p>
          <p className="mt-2 text-sm text-ink-secondary">
            This company profile may have been removed, or the link is out of
            date.
          </p>
        </div>
      </div>
    );
  }

  if (mockCompany) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-10">
        <Link
          href="/companies"
          className="text-sm font-medium text-primary hover:text-primary-hover"
        >
          ← Back to companies
        </Link>

        <DetailHeaderCard
          logoText={mockCompany.name.charAt(0)}
          title={mockCompany.name}
          subtitle={`${mockCompany.type} · ${mockCompany.country}`}
          action={
            mockCompany.careersUrl
              ? { href: mockCompany.careersUrl, label: "View careers page" }
              : undefined
          }
          description={mockCompany.about}
          footer={
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {mockCompany.size && (
                <div>
                  <dt className="text-xs text-ink-muted">Company size</dt>
                  <dd className="mt-1 text-sm font-semibold text-ink">
                    {mockCompany.size}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-ink-muted">Location</dt>
                <dd className="mt-1 text-sm font-semibold text-ink">
                  {mockCompany.country}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Open positions</dt>
                <dd className="mt-1 text-sm font-semibold text-ink">
                  {mockCompany.openPositions}
                </dd>
              </div>
            </dl>
          }
        />

        <section className="mt-10">
          <h2 className="text-lg font-bold text-ink">Open Positions</h2>
          <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-2">
            {mockJobs.map((job) => (
              <JobCardRow key={job.id} job={job} />
            ))}
          </div>

          {mockJobs.length === 0 && (
            <div className="mt-4 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
              <p className="font-semibold text-ink">No jobs found</p>
              <p className="mt-2 text-sm text-ink-secondary">
                {mockCompany.name} doesn&apos;t have any open positions listed
                right now.
              </p>
            </div>
          )}
        </section>
      </div>
    );
  }

  const detail = company as CompanyDetail;
  const type = companyTypeLabel(detail.company_type);
  const careersUrl = detail.career_page_url ?? detail.website_url;

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <Link
        href="/companies"
        className="text-sm font-medium text-primary hover:text-primary-hover"
      >
        ← Back to companies
      </Link>

      <DetailHeaderCard
        logoText={detail.name.charAt(0)}
        title={detail.name}
        subtitle={type ?? "Company"}
        action={
          careersUrl
            ? { href: careersUrl, label: "View careers page" }
            : undefined
        }
        description={detail.description}
        footer={
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs text-ink-muted">Open positions</dt>
              <dd className="mt-1 text-sm font-semibold text-ink">
                {jobCount}
              </dd>
            </div>
          </dl>
        }
      />

      <section className="mt-10">
        <h2 className="text-lg font-bold text-ink">Open Positions</h2>
        <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {jobs.map((job) => (
            <JobRow key={job.job_id} job={job} />
          ))}
        </div>

        {jobs.length === 0 && (
          <div className="mt-4 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
            <p className="font-semibold text-ink">No jobs found</p>
            <p className="mt-2 text-sm text-ink-secondary">
              {detail.name} doesn&apos;t have any open positions listed right
              now.
            </p>
          </div>
        )}

        {jobs.length > 0 && (
          <div className="mt-8">
            <Pagination
              page={page}
              pageCount={pageCount}
              onPageChange={setPage}
            />
          </div>
        )}
      </section>
    </div>
  );
}
