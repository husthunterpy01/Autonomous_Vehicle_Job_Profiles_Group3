import type { Metadata } from "next";
import { Suspense } from "react";
import CompanyDetailClient from "../[id]/company-detail-client";

export const metadata: Metadata = { title: "Company profile | AV Job Finder" };

export default function CompanyProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-[1200px] px-6 py-10">
          <div
            aria-busy="true"
            className="rounded-xl border border-dashed border-line bg-surface p-12 text-center"
          >
            <p className="font-semibold text-ink">Loading company…</p>
          </div>
        </div>
      }
    >
      <CompanyDetailClient />
    </Suspense>
  );
}
