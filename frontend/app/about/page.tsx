import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About | AV Job Finder",
  description:
    "What AV Job Finder is, where its job data comes from, and who built it.",
};

const REPO_URL =
  "https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[800px] px-6 py-16">
      <h1 className="text-3xl font-bold text-ink">About AV Job Finder</h1>
      <p className="mt-4 text-ink-secondary">
        AV Job Finder collects job postings from autonomous vehicle companies in
        one place, so students and early-career engineers can see which roles
        and skills the industry is hiring for.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-ink">
        Where the data comes from
      </h2>
      <p className="mt-3 text-ink-secondary">
        Postings are collected from public job boards and company career pages
        (for example Greenhouse, Lever, Workday and company websites). Each
        posting is cleaned, labelled with a role category and its skills, and
        links back to the original page. Some details, such as location and
        seniority, are read from the posting text and can be incomplete. Check
        the original posting before you apply.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-ink">Who built it</h2>
      <p className="mt-3 text-ink-secondary">
        A student project by Group 3 for the CITS5206 capstone unit. The source
        code is on{" "}
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline"
        >
          GitHub
        </a>
        . To report a problem or ask a question, open an issue there.
      </p>

      <div className="mt-10 flex gap-3">
        <Link
          href="/search"
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        >
          Browse Jobs
        </Link>
        <Link
          href="/trends"
          className="rounded-lg border border-primary bg-surface px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary-light"
        >
          Market Trends
        </Link>
      </div>
    </div>
  );
}
