import Link from "next/link";
import type { Company } from "@/lib/mock-data";
import CompanyLogo from "./CompanyLogo";

/* Company summary shown on Job Detail — richer than CompanyCard (adds
   about/size), used only in that one context. */
export default function CompanySummaryCard({ company }: { company: Company }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <CompanyLogo text={company.name.charAt(0)} />
        <div className="min-w-0">
          <h3 className="font-semibold text-ink">{company.name}</h3>
          <p className="text-sm text-ink-secondary">
            {company.type} · {company.country}
          </p>
        </div>
      </div>

      {company.about && (
        <p className="mt-3 text-sm text-ink-secondary">{company.about}</p>
      )}

      <dl className="mt-4 space-y-2 text-sm">
        {company.size && (
          <div className="flex justify-between">
            <dt className="text-ink-muted">Company size</dt>
            <dd className="font-medium text-ink">{company.size}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <dt className="text-ink-muted">Open positions</dt>
          <dd className="font-medium text-ink">{company.openPositions}</dd>
        </div>
      </dl>

      <Link
        href="/companies"
        className="mt-4 block rounded-lg border border-primary px-4 py-2 text-center text-sm font-medium text-primary transition-colors hover:bg-primary-light"
      >
        View company profile
      </Link>
    </div>
  );
}
