import { Suspense } from "react";
import { AV_COMPANIES } from "@/lib/mock-data";
import CompanyDetailClient from "./company-detail-client";

/* Pre-render every mock company for static export (GitHub Pages). Live
   companies use /companies/profile?id=<uuid> (see
   app/companies/profile/page.tsx) so unknown ids still resolve. */
export function generateStaticParams() {
  return AV_COMPANIES.map((company) => ({ id: company.id }));
}

export default async function CompanyDetailPage({
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
            <p className="font-semibold text-ink">Loading company…</p>
          </div>
        </div>
      }
    >
      <CompanyDetailClient id={id} />
    </Suspense>
  );
}
