import { Suspense } from "react";
import JobDetailClient from "./[id]/job-detail-client";

export default function JobsPage() {
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
      <JobDetailClient />
    </Suspense>
  );
}
