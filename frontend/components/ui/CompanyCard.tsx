import Link from "next/link";
import type { Company } from "@/lib/mock-data";
import CompanyLogo from "./CompanyLogo";

export default function CompanyCard({ company }: { company: Company }) {
  return (
    <Link
      href={`/companies/${company.id}`}
      className="flex items-start gap-4 rounded-xl border border-line bg-surface p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
    >
      <CompanyLogo text={company.name.charAt(0)} />
      <div className="min-w-0 flex-1">
        <h3 className="font-semibold text-ink">{company.name}</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          {company.type} · {company.country}
        </p>
        <p className="mt-2 text-sm text-ink-muted">
          {company.openPositions} open positions
        </p>
      </div>
    </Link>
  );
}
