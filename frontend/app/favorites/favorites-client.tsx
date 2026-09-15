"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import PageHeader from "@/components/ui/PageHeader";
import ViewToggle, { type ViewMode } from "@/components/ui/ViewToggle";
import {
  JobRow,
  JobsTable,
  RemoveFavoriteButton,
} from "@/components/ui/JobResultsList";
import { ApiError } from "@/lib/services/api";
import { getFavorites, removeFavorite } from "@/lib/services/favorite";
import type { JobListItem } from "@/lib/services/job";

export default function FavoritesClient() {
  const router = useRouter();
  const [view, setView] = useState<ViewMode>("table");
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [pendingRemoval, setPendingRemoval] = useState<JobListItem | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    getFavorites()
      .then((items) => {
        if (cancelled) return;
        setJobs(items);
        setStatus("success");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
          return;
        }
        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "Something went wrong loading your favorites. Please try again.",
        );
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken, router]);

  const confirmRemove = async () => {
    const job = pendingRemoval;
    if (!job) return;
    setPendingRemoval(null);
    setRemovingId(job.job_id);
    try {
      await removeFavorite(job.job_id);
      setJobs((prev) => prev.filter((j) => j.job_id !== job.job_id));
    } catch {
      // Leave the row in place so the user can just try the button again.
    } finally {
      setRemovingId(null);
    }
  };

  const renderRemoveAction = (job: JobListItem) => (
    <RemoveFavoriteButton
      disabled={removingId === job.job_id}
      onClick={() => setPendingRemoval(job)}
    />
  );

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <PageHeader
        title="My Favorites"
        subtitle="Job postings you've saved for later."
      />

      {status === "loading" && (
        <div
          aria-busy="true"
          className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center"
        >
          <p className="font-semibold text-ink">Loading your favorites…</p>
        </div>
      )}

      {status === "error" && (
        <div
          role="alert"
          className="mt-10 rounded-xl border border-dashed border-line bg-warning/10 p-12 text-center"
        >
          <p className="font-semibold text-warning">
            Couldn&apos;t load your favorites
          </p>
          <p className="mt-2 text-sm text-ink-secondary">{errorMessage}</p>
          <button
            type="button"
            onClick={() => {
              setStatus("loading");
              setErrorMessage(null);
              setReloadToken((n) => n + 1);
            }}
            className="mt-4 text-sm font-medium text-primary hover:text-primary-hover"
          >
            Try again
          </button>
        </div>
      )}

      {status === "success" && jobs.length > 0 && (
        <>
          <div className="mt-4 flex flex-col gap-4 lg:mt-8 lg:grid lg:grid-cols-[minmax(0,1fr)_14rem] lg:items-center lg:gap-x-6 lg:pr-3">
            <p className="text-sm text-ink-secondary">
              <span className="font-semibold text-ink">{jobs.length}</span>{" "}
              {jobs.length === 1 ? "job" : "jobs"} saved
            </p>
            <div className="lg:justify-self-end">
              <ViewToggle view={view} onChange={setView} />
            </div>
          </div>

          <div className="mt-4">
            {view === "table" ? (
              <JobsTable
                jobs={jobs}
                renderAction={renderRemoveAction}
                actionColumnLabel="Remove"
              />
            ) : (
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {jobs.map((job) => (
                  <JobRow
                    key={job.job_id}
                    job={job}
                    action={renderRemoveAction(job)}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {status === "success" && jobs.length === 0 && (
        <div className="mt-10 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
          <p className="font-semibold text-ink">No favorites yet</p>
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

      <ConfirmDialog
        open={pendingRemoval !== null}
        title="Remove from favorites?"
        description={
          pendingRemoval
            ? `Are you sure you want to remove "${pendingRemoval.title}" from your favorites list?`
            : undefined
        }
        confirmLabel="Yes"
        cancelLabel="No"
        onConfirm={confirmRemove}
        onCancel={() => setPendingRemoval(null)}
      />
    </div>
  );
}
