import CompanyLogo from "./CompanyLogo";

export type CompanyCardData = {
  id: string;
  name: string;
  type: string;
  country?: string | null;
  openPositions: number;
};

export default function CompanyCard({ company }: { company: CompanyCardData }) {
  return (
    // Not a Link: /companies/[id] is still mock-only (static export requires
    // every dynamic route known at build time), so a real company id would
    // 404/crash. Re-enable once the detail page is wired to the real API.
    <div className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5">
      <CompanyLogo text={company.name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{company.name}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {company.type}
          {company.country ? ` · ${company.country}` : ""}
        </p>
        <p className="mt-2 text-sm text-ink-muted">
          {company.openPositions} open positions
        </p>
      </div>
    </div>
  );
}
