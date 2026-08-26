"use client";

import { useState } from "react";
import Link from "next/link";
import { getTopSkills, getCompaniesForSkill } from "@/lib/mock-data";
import CompanyLogo from "./ui/CompanyLogo";

const TOP_N_OPTIONS = [5, 10, 20] as const;
type TopN = (typeof TOP_N_OPTIONS)[number];

export default function TopSkillsPanel() {
  const [topN, setTopN] = useState<TopN>(10);
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);

  const skills = getTopSkills(topN);
  const max = skills[0]?.jobs ?? 1;

  return (
    <div className="rounded-2xl border border-line bg-section p-6 shadow-sm sm:p-8">
      <div className="mb-6 inline-flex rounded-xl border border-line bg-surface p-1 shadow-sm">
        {TOP_N_OPTIONS.map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={topN === n}
            onClick={() => {
              setTopN(n);
              setExpandedSkill(null);
            }}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              topN === n
                ? "bg-primary-light text-primary shadow-sm"
                : "text-ink-secondary hover:bg-section hover:text-ink"
            }`}
          >
            Top {n}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-x-10 gap-y-2 sm:grid-cols-2">
        {skills.map((skill) => {
          const isExpanded = expandedSkill === skill.name;
          const companies = isExpanded ? getCompaniesForSkill(skill.name) : [];

          return (
            <div key={skill.name} className="py-3">
              <button
                type="button"
                aria-expanded={isExpanded}
                onClick={() => setExpandedSkill(isExpanded ? null : skill.name)}
                className="w-full text-left"
              >
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="font-semibold text-ink">{skill.name}</span>
                  <span className="text-sm text-ink-muted">
                    {skill.jobs} {skill.jobs === 1 ? "job" : "jobs"}
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-line">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${(skill.jobs / max) * 100}%` }}
                  />
                </div>
              </button>

              {isExpanded && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {companies.map((company) => (
                    <Link
                      key={company.id}
                      href={`/companies/${company.id}`}
                      className="flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm transition-colors hover:border-primary hover:text-primary"
                    >
                      <CompanyLogo
                        text={company.name.charAt(0)}
                        size="h-5 w-5"
                      />
                      {company.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
