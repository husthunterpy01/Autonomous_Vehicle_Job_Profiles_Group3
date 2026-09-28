import type { Metadata } from "next";
import SkillTrendChart from "./skill-trend-chart";

export const metadata: Metadata = {
  title: "Market Trends | AV Job Finder",
  description:
    "See how demand for each skill in autonomous vehicle jobs changes month by month.",
};

export default function TrendsPage() {
  return (
    <main className="bg-background">
      <section className="mx-auto max-w-[1200px] px-6 pt-12">
        <p className="text-sm font-semibold text-primary">Market insights</p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Top Skills in Demand Over Time
        </h1>

        <p className="mt-3 max-w-2xl text-ink-secondary">
          How many autonomous vehicle job postings ask for each of the most
          requested skills, month by month.
        </p>
      </section>

      <section className="mx-auto max-w-[1200px] px-6 py-10">
        <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-6">
          <SkillTrendChart />
          <p className="mt-4 text-xs text-ink-muted">
            Each month uses its last scrape of the month. Counts are job
            postings that list the skill.
          </p>
        </div>
      </section>
    </main>
  );
}
