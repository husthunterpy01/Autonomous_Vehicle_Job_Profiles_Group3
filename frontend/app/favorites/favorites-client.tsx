"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import CompanyLogo from "@/components/ui/CompanyLogo";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import PageHeader from "@/components/ui/PageHeader";
import ViewToggle, { type ViewMode } from "@/components/ui/ViewToggle";
import {
  JobRow,
  JobsTable,
  RemoveFavoriteButton,
} from "@/components/ui/JobResultsList";
import { ApiError } from "@/lib/services/api";
import { COMPANY_TYPE_LABELS } from "@/lib/services/company";
import {
  getFavoriteCompanies,
  getFavoriteJobs,
  removeFavoriteCompany,
  removeFavoriteJob,
  type FavoriteCompanyDetail,
} from "@/lib/services/favorite";
import type { JobListItem } from "@/lib/services/job";

type Tab = "jobs" | "companies";
type Status = "loading" | "success" | "error";

function FavoriteCompanyCard({
  company,
  action,
}: {
  company: FavoriteCompanyDetail;
  action?: ReactNode;
}) {
  const type = company.company_type
    ? (COMPANY_TYPE_LABELS[company.company_type] ?? company.company_type)
    : null;
  return (
    <div className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5">
      <CompanyLogo text={company.name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{company.name}</h3>
        {type && <p className="mt-1 text-sm text-ink-secondary">{type}</p>}
        {company.career_page_url && (
          <a
            href={company.career_page_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-sm text-primary hover:text-primary-hover"
          >
            View careers page
          </a>
        )}
      </div>
      {action}
    </div>
  );
}

export default function FavoritesClient() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("jobs");
  const [view, setView] = useState<ViewMode>("table");
  const [reloadToken, setReloadToken] = useState(0);

  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [jobsStatus, setJobsStatus] = useState<Status>("loading");
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [removingJobId, setRemovingJobId] = useState<string | null>(null);
  const [pendingJobRemoval, setPendingJobRemoval] =
    useState<JobListItem | null>(null);

  const [companies, setCompanies] = useState<FavoriteCompanyDetail[]>([]);
  const [companiesStatus, setCompaniesStatus] = useState<Status>("loading");
  const [companiesError, setCompaniesError] = useState<string | null>(null);
  const [removingCompanyId, setRemovingCompanyId] = useState<string | null>(
    null,
  );
  const [pendingCompanyRemoval, setPendingCompanyRemoval] =
    useState<FavoriteCompanyDetail | null>(null);

  useEffect(() => {
    let cancelled = false;

    getFavoriteJobs()
      .then((favorites) => {
        if (cancelled) return;
        setJobs(favorites.map((favorite) => favorite.job));
        setJobsStatus("success");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
          return;
        }
        setJobsError(
          error instanceof ApiError
            ? error.message
            : "Something went wrong loading your favorite jobs. Please try again.",
        );
        setJobsStatus("error");
      });

    getFavoriteCompanies()
      .then((favorites) => {
        if (cancelled) return;
        setCompanies(favorites.map((favorite) => favorite.company));
        setCompaniesStatus("success");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
          return;
        }
        setCompaniesError(
          error instanceof ApiError
            ? error.message
            : "Something went wrong loading your favorite companies. Please try again.",
        );
        setCompaniesStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken, router]);

  const confirmRemoveJob = async () => {
    const job = pendingJobRemoval;
    if (!job) return;
    setPendingJobRemoval(null);
    setRemovingJobId(job.job_id);
    try {
      await removeFavoriteJob(job.job_id);
      setJobs((prev) => prev.filter((j) => j.job_id !== job.job_id));
    } catch {
      // Leave the row in place so the user can just try the button again.
    } finally {
      setRemovingJobId(null);
    }
  };

  const confirmRemoveCompany = async () => {
    const company = pendingCompanyRemoval;
    if (!company) return;
    setPendingCompanyRemoval(null);
    setRemovingCompanyId(company.company_id);
    try {
      await removeFavoriteCompany(company.company_id);
      setCompanies((prev) =>
        prev.filter((c) => c.company_id !== company.company_id),
      );
    } catch {
      // Leave the card in place so the user can just try the button again.
    } finally {
      setRemovingCompanyId(null);
    }
  };

  const renderRemoveJobAction = (job: JobListItem) => (
    <RemoveFavoriteButton
      disabled={removingJobId === job.job_id}
      onClick={() => setPendingJobRemoval(job)}
    />
  );

  const renderRemoveCompanyAction = (company: FavoriteCompanyDetail) => (
    <RemoveFavoriteButton
      disabled={removingCompanyId === company.company_id}
      onClick={() => setPendingCompanyRemoval(company)}
    />
  );

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <PageHeader
        title="My Favorites"
        subtitle="Jobs and companies you've saved for later."
      />

      <div className="mt-6 inline-flex rounded-xl border border-line bg-surface p-1 shadow-sm">
        <button
          type="button"
          aria-pressed={tab === "jobs"}
          onClick={() => setTab("jobs")}
          className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            tab === "jobs"
              ? "bg-primary-light text-primary shadow-sm"
              : "text-ink-secondary hover:bg-section hover:text-ink"
          }`}
        >
          Jobs{jobs.length > 0 ? ` (${jobs.length})` : ""}
        </button>
        <button
          type="button"
          aria-pressed={tab === "companies"}
          onClick={() => setTab("companies")}
          className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            tab === "companies"
              ? "bg-primary-light text-primary shadow-sm"
              : "text-ink-secondary hover:bg-section hover:text-ink"
          }`}
        >
          Companies{companies.length > 0 ? ` (${companies.length})` : ""}
        </button>
      </div>

      {tab === "jobs" && (
        <>
          {jobsStatus === "loading" && (
            <div
              aria-busy="true"
              className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center"
            >
              <p className="font-semibold text-ink">
                Loading your favorite jobs…
              </p>
            </div>
          )}

          {jobsStatus === "error" && (
            <div
              role="alert"
              className="mt-10 rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
            >
              <p className="font-semibold text-warning">
                Couldn&apos;t load your favorite jobs
              </p>
              <p className="mt-2 text-sm text-ink-secondary">{jobsError}</p>
              <button
                type="button"
                onClick={() => {
                  setJobsStatus("loading");
                  setJobsError(null);
                  setReloadToken((n) => n + 1);
                }}
                className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
              >
                Try again
              </button>
            </div>
          )}

          {jobsStatus === "success" && jobs.length > 0 && (
            <>
              <div className="mt-6 flex justify-end">
                <ViewToggle view={view} onChange={setView} />
              </div>

              <div className="mt-4">
                {view === "table" ? (
                  <JobsTable
                    jobs={jobs}
                    renderAction={renderRemoveJobAction}
                    actionColumnLabel="Favorite"
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    {jobs.map((job) => (
                      <JobRow
                        key={job.job_id}
                        job={job}
                        action={renderRemoveJobAction(job)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {jobsStatus === "success" && jobs.length === 0 && (
            <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
              <p className="font-semibold text-ink">No favorite jobs yet</p>
              <p className="mt-2 text-sm text-ink-secondary">
                Browse{" "}
                <Link
                  href="/search"
                  className="text-primary hover:text-primary-hover"
                >
                  Find Jobs
                </Link>{" "}
                and save the ones you want to revisit.
              </p>
            </div>
          )}
        </>
      )}

      {tab === "companies" && (
        <>
          {companiesStatus === "loading" && (
            <div
              aria-busy="true"
              className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center"
            >
              <p className="font-semibold text-ink">
                Loading your favorite companies…
              </p>
            </div>
          )}

          {companiesStatus === "error" && (
            <div
              role="alert"
              className="mt-10 rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
            >
              <p className="font-semibold text-warning">
                Couldn&apos;t load your favorite companies
              </p>
              <p className="mt-2 text-sm text-ink-secondary">
                {companiesError}
              </p>
              <button
                type="button"
                onClick={() => {
                  setCompaniesStatus("loading");
                  setCompaniesError(null);
                  setReloadToken((n) => n + 1);
                }}
                className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
              >
                Try again
              </button>
            </div>
          )}

          {companiesStatus === "success" && companies.length > 0 && (
            <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {companies.map((company) => (
                <FavoriteCompanyCard
                  key={company.company_id}
                  company={company}
                  action={renderRemoveCompanyAction(company)}
                />
              ))}
            </div>
          )}

          {companiesStatus === "success" && companies.length === 0 && (
            <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
              <p className="font-semibold text-ink">
                No favorite companies yet
              </p>
              <p className="mt-2 text-sm text-ink-secondary">
                Browse{" "}
                <Link
                  href="/companies"
                  className="text-primary hover:text-primary-hover"
                >
                  Companies
                </Link>{" "}
                and save the ones you want to revisit.
              </p>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={pendingJobRemoval !== null}
        title="Remove from favorites?"
        description={
          pendingJobRemoval
            ? `Are you sure you want to remove "${pendingJobRemoval.title}" from your favorites list?`
            : undefined
        }
        confirmLabel="Yes"
        cancelLabel="No"
        onConfirm={confirmRemoveJob}
        onCancel={() => setPendingJobRemoval(null)}
      />

      <ConfirmDialog
        open={pendingCompanyRemoval !== null}
        title="Remove from favorites?"
        description={
          pendingCompanyRemoval
            ? `Are you sure you want to remove "${pendingCompanyRemoval.name}" from your favorites list?`
            : undefined
        }
        confirmLabel="Yes"
        cancelLabel="No"
        onConfirm={confirmRemoveCompany}
        onCancel={() => setPendingCompanyRemoval(null)}
      />
    </div>
  );
}
