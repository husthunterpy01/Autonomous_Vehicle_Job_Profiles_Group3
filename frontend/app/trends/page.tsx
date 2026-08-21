import type { Metadata } from "next";
import JobTrendChart from "@/components/ui/JobTrendChart";

export const metadata: Metadata = {
  title: "Market Trends | AV Job Finder",
  description: "Explore autonomous vehicle job market trends over time.",
};

export default function TrendsPage() {
  return (
    <main className="bg-background">
      <section className="mx-auto max-w-[1200px] px-6 pt-12">
        <p className="text-sm font-semibold text-primary">Market insights</p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Autonomous Vehicle Job Trends
        </h1>

        <p className="mt-3 max-w-2xl text-ink-secondary">
          Explore how autonomous vehicle job demand changes over time and
          inspect the number of available roles for each period.
        </p>
      </section>

      <JobTrendChart />
    </main>
  );
}
