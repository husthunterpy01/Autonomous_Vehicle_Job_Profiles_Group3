import Link from "next/link";
import CategoryGridPanel from "@/components/CategoryGridPanel";
import TopSkillsPanel from "@/components/TopSkillsPanel";
import {
  FeaturedJobsGrid,
  LatestJobsGrid,
  LatestOpportunitiesList,
  TopCategoryHighlight,
  TopCompaniesGrid,
} from "./home-sections";

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
              <LatestOpportunitiesList />
              <TopCategoryHighlight />
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

        <CategoryGridPanel />
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

        <LatestJobsGrid />
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
          subtitle="The newest roles from employers that publish their salary range."
          linkHref="/search"
          linkLabel="View all jobs"
        />

        <FeaturedJobsGrid />
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
          subtitle="The AV companies with the most open roles right now."
          linkHref="/companies"
          linkLabel="View all companies"
        />

        <TopCompaniesGrid />
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
