import Link from "next/link";
import {
  AV_CATEGORIES,
  AV_COMPANIES,
  FEATURED_JOBS,
  MOCK_JOBS,
} from "@/lib/mock-data";
import CompanyLogo from "@/components/ui/CompanyLogo";
import JobCardColumn from "@/components/ui/JobCardColumn";
import JobCardRow from "@/components/ui/JobCardRow";
import Salary from "@/components/ui/Salary";
import TopSkillsPanel from "@/components/TopSkillsPanel";

/* ------------------------------------------------------------------ */
/* Small building blocks                                               */
/* ------------------------------------------------------------------ */

function SectionHeader({
  title,
  highlight,
  subtitle,
  linkHref,
  linkLabel,
}: {
  title: string;
  highlight: string;
  subtitle: string;
  linkHref: string;
  linkLabel: string;
}) {
  return (
    <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-ink">
          {title} <span className="text-primary">{highlight}</span>
        </h2>
        <p className="mt-2 text-ink-secondary">{subtitle}</p>
      </div>
      <Link
        href={linkHref}
        className="text-sm font-semibold text-primary hover:text-primary-hover"
      >
        {linkLabel}
      </Link>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page sections                                                       */
/* ------------------------------------------------------------------ */

function Hero() {
  return (
    <section className="border-b border-line bg-background">
      <div className="mx-auto grid max-w-[1200px] items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:py-20">
        {/* Left */}
        <div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
            Find Your Next <span className="text-primary">Dream Job</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-secondary">
            Explore autonomous vehicle job opportunities from leading AV
            companies and find the role that fits your skills and goals.
          </p>

          {/* Search bar */}
          <form className="mt-8 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 shadow-sm sm:flex-row sm:items-center">
            <input
              type="text"
              name="q"
              placeholder="Job title, skill or keyword"
              className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
            />
            <div className="hidden h-8 w-px bg-line sm:block" />
            <input
              type="text"
              placeholder="Country"
              className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
            >
              Search Jobs
            </button>
          </form>

          {/* Popular searches */}
          <p className="mt-4 text-sm text-ink-muted">
            Popular searches:{" "}
            <span className="font-medium text-ink-secondary">
              Perception · Planning · Control · Localization
            </span>
          </p>
        </div>

        {/* Right: dashboard preview illustration */}
        <div className="hidden lg:block">
          <div className="relative mx-auto max-w-md">
            <div className="relative rounded-2xl border border-line bg-surface p-6 shadow-lg">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-ink">
                  Latest opportunities
                </p>
                <span className="rounded-md bg-primary-light px-2 py-1 text-xs font-medium text-primary">
                  {MOCK_JOBS.length} jobs
                </span>
              </div>

              {MOCK_JOBS.slice(0, 4).map((job) => (
                <div
                  key={job.id}
                  className="mt-4 flex items-center gap-3 rounded-xl border border-line bg-surface p-3"
                >
                  <CompanyLogo text={job.company.charAt(0)} size="h-9 w-9" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {job.title}
                    </p>
                    <p className="truncate text-xs text-ink-muted">
                      {job.company} · {job.country}
                    </p>
                  </div>
                  <Salary job={job} />
                </div>
              ))}

              <div className="mt-5 flex items-center justify-between rounded-xl bg-primary-light px-4 py-3">
                <div>
                  <p className="text-xs font-medium text-primary">Trending</p>
                  <p className="text-sm font-semibold text-ink">
                    Perception Engineer
                  </p>
                </div>
                <span className="text-sm font-bold text-primary">+32%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function JobCategories() {
  return (
    <section className="bg-surface py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          title="Explore Jobs by"
          highlight="Category"
          subtitle="AV roles across the full autonomous driving tech stack."
          linkHref="/search"
          linkLabel="View all categories"
        />

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {AV_CATEGORIES.map((category) => (
            <Link
              key={category.name}
              href="/search"
              className="rounded-[10px] border border-line bg-surface p-6 text-center shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-primary hover:shadow-md"
            >
              <h3 className="font-semibold text-ink">{category.name}</h3>
              <p className="mt-1 text-sm text-ink-secondary">
                {category.jobs} jobs available
              </p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function TopSkills() {
  return (
    <section className="bg-surface py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          title="Top Skills in"
          highlight="Demand"
          subtitle="Most requested skills across current AV job postings."
          linkHref="/search"
          linkLabel="View all jobs"
        />

        <TopSkillsPanel />
      </div>
    </section>
  );
}

function LatestJobs() {
  return (
    <section className="bg-section py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          title="Latest"
          highlight="Jobs Open"
          subtitle="Recently added opportunities from AV companies hiring now."
          linkHref="/search"
          linkLabel="View all jobs"
        />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {MOCK_JOBS.map((job) => (
            <JobCardRow key={job.id} job={job} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturedJobs() {
  return (
    <section className="bg-surface py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          title="Featured"
          highlight="Jobs"
          subtitle="Hand-picked opportunities from our top partners."
          linkHref="/search"
          linkLabel="View all jobs"
        />

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {FEATURED_JOBS.map((job) => (
            <JobCardColumn key={job.id} job={job} />
          ))}
        </div>
      </div>
    </section>
  );
}

function TopCompanies() {
  return (
    <section className="bg-section py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          title="AV"
          highlight="Companies Hiring"
          subtitle="Open roles at the AV companies tracked by this platform."
          linkHref="/companies"
          linkLabel="View all companies"
        />

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {AV_COMPANIES.slice(0, 8).map((company) => (
            <Link
              key={company.id}
              href={`/companies/${company.id}`}
              className="flex items-center gap-3 rounded-xl border border-line bg-surface p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
            >
              <CompanyLogo text={company.name.charAt(0)} size="h-9 w-9" />
              <span className="truncate font-semibold text-ink">
                {company.name}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaSection() {
  return (
    <section className="bg-surface px-6 py-20">
      <div className="mx-auto max-w-[1200px]">
        <div className="rounded-2xl bg-primary-light px-8 py-12 text-center md:px-16">
          <h2 className="text-3xl font-bold tracking-tight text-ink">
            Ready to find your next opportunity?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-ink-secondary">
            Browse open AV roles and see which skills are in demand.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/search"
              className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
            >
              Browse Jobs
            </Link>
            <Link
              href="/companies"
              className="rounded-lg border border-primary bg-surface px-6 py-3 text-sm font-medium text-primary transition-colors hover:bg-primary-light"
            >
              View Companies
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  return (
    <>
      <Hero />
      <JobCategories />
      <TopSkills />
      <LatestJobs />
      <FeaturedJobs />
      <TopCompanies />
      <CtaSection />
    </>
  );
}
