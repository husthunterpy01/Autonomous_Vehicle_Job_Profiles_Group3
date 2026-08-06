import { notFound } from "next/navigation";
import Link from "next/link";
import { getCompanyById, getJobsByCompanyId } from "@/lib/mock-data";
import CompanyLogo from "@/components/ui/CompanyLogo";
import JobCardRow from "@/components/ui/JobCardRow";
import PageHeader from "@/components/ui/PageHeader";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const company = getCompanyById(id);
  if (!company) notFound();

  const jobs = getJobsByCompanyId(company.id);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <Link
        href="/companies"
        className="text-sm font-medium text-primary hover:text-primary-hover"
      >
        ← Back to companies
      </Link>

      {/* Header */}
      <div className="mt-4 rounded-xl border border-line bg-surface p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <CompanyLogo text={company.name.charAt(0)} size="h-14 w-14" />
          <div>
            <PageHeader
              title={company.name}
              subtitle={`${company.type} · ${company.country}`}
            />
          </div>
        </div>

        <dl className="mt-6 grid grid-cols-1 gap-4 border-t border-line pt-6 sm:grid-cols-3">
          {company.size && (
            <div>
              <dt className="text-xs text-ink-muted">Company size</dt>
              <dd className="mt-1 text-sm font-semibold text-ink">
                {company.size}
              </dd>
            </div>
          )}
          <div>
            <dt className="text-xs text-ink-muted">Location</dt>
            <dd className="mt-1 text-sm font-semibold text-ink">
              {company.country}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">Open positions</dt>
            <dd className="mt-1 text-sm font-semibold text-ink">
              {company.openPositions}
            </dd>
          </div>
        </dl>
      </div>

      {/* About */}
      {company.about && (
        <section className="mt-8">
          <h2 className="text-lg font-bold text-ink">About</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary">
            {company.about}
          </p>
        </section>
      )}

      {/* Open Positions */}
      <section className="mt-10">
        <h2 className="text-lg font-bold text-ink">Open Positions</h2>
        <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {jobs.map((job) => (
            <JobCardRow key={job.id} job={job} />
          ))}
        </div>

        {jobs.length === 0 && (
          <div className="mt-4 rounded-xl border border-dashed border-line bg-surface p-12 text-center">
            <p className="font-semibold text-ink">No jobs found</p>
            <p className="mt-2 text-sm text-ink-secondary">
              {company.name} doesn&apos;t have any open positions listed
              right now.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}