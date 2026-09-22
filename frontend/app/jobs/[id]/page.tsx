import { Suspense } from "react";
import { ALL_JOBS } from "@/lib/mock-data";
import JobDetailClient from "./job-detail-client";

/* Pre-render mock landing-page slugs for GitHub Pages. Live postings use
   /jobs?id=<uuid> (see app/jobs/page.tsx) so unknown ids still resolve. */
export function generateStaticParams() {
  return ALL_JOBS.map((job) => ({ id: job.id }));
}

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-[1200px] px-6 py-10">
          <div
            aria-busy="true"
            className="rounded-xl border border-dashed border-line bg-surface p-12 text-center"
          >
            <p className="font-semibold text-ink">Loading job…</p>
          </div>
        </div>
      }
    >
      <JobDetailClient id={id} />
    </Suspense>
  );
}
