import Link from "next/link";
import CompanyLogo from "./CompanyLogo";

/* Company summary shown on Job Detail — richer than CompanyCard (adds
   about/size), used only in that one context. Optional fields are omitted
   when the backend does not send them. */
export type CompanySummaryInfo = {
  id: string;
  name: string;
  type?: string | null;
  country?: string | null;
  about?: string | null;
  size?: string | null;
  openPositions?: number | null;
  careersUrl?: string | null;
  /** In-app profile route; omit for live API companies (that page is mock). */
  profileHref?: string | null;
};

export default function CompanySummaryCard({
  company,
}: {
  company: CompanySummaryInfo;
}) {
  const typeLine = [company.type, company.country].filter(Boolean).join(" · ");
  const ctaHref = company.profileHref ?? company.careersUrl ?? null;
  const ctaLabel = company.profileHref
    ? "View company profile"
    : "View careers page";
  const ctaIsExternal = !company.profileHref && Boolean(company.careersUrl);

  return (
    <div className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <CompanyLogo text={company.name.charAt(0)} />
        <div className="min-w-0">
          <h3 className="font-semibold text-ink">{company.name}</h3>
          {typeLine && <p className="text-sm text-ink-secondary">{typeLine}</p>}
        </div>
      </div>

      {company.about && (
        <p className="mt-3 text-sm text-ink-secondary">{company.about}</p>
      )}

      {(company.size || company.openPositions != null) && (
        <dl className="mt-4 space-y-2 text-sm">
          {company.size && (
            <div className="flex justify-between">
              <dt className="text-ink-muted">Company size</dt>
              <dd className="font-medium text-ink">{company.size}</dd>
            </div>
          )}
          {company.openPositions != null && (
            <div className="flex justify-between">
              <dt className="text-ink-muted">Open positions</dt>
              <dd className="font-medium text-ink">{company.openPositions}</dd>
            </div>
          )}
        </dl>
      )}

      {ctaHref &&
        (ctaIsExternal ? (
          <a
            href={ctaHref}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 block rounded-lg border border-primary px-4 py-2 text-center text-sm font-medium text-primary transition-colors hover:bg-primary-light"
          >
            {ctaLabel} ↗
          </a>
        ) : (
          <Link
            href={ctaHref}
            className="mt-4 block rounded-lg border border-primary px-4 py-2 text-center text-sm font-medium text-primary transition-colors hover:bg-primary-light"
          >
            {ctaLabel}
          </Link>
        ))}
    </div>
  );
}
