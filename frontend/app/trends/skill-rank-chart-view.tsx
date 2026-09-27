"use client";

import { useState, type ReactNode } from "react";
import {
  CHART,
  layoutSkillRanks,
  type LaidOutSkill,
} from "@/lib/skill-rank-chart";
import type { SkillTrends } from "@/lib/services/trend";

export type SkillTrendsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "success"; data: SkillTrends };

// Emphasis form: every line is recessive gray and the hovered/focused skill
// takes the primary hue, so ten lines never need ten colors. Skill names
// are direct labels in ink, never in a series color.
const LINE_GRAY = "#94a3b8";
const GRID = "#eef0f4";
const PRIMARY = "#4f46e5";
const SURFACE = "#ffffff";

function Notice({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface p-12 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && (
        <p className="mt-2 text-sm text-ink-secondary">{children}</p>
      )}
    </div>
  );
}

function jobsLabel(count: number): string {
  return `${count.toLocaleString("en-US")} ${count === 1 ? "job" : "jobs"}`;
}

function describeSkill(skill: LaidOutSkill): string {
  const months = skill.points
    .map((p) => `${p.monthLabel} #${p.rank} (${jobsLabel(p.jobCount)})`)
    .join(", ");
  return `${skill.name}: ${months}`;
}

/* The readout above the chart: values lead, the month follows. It is the
   hover/focus detail; the same numbers are in the table below. */
function Readout({ skill }: { skill: LaidOutSkill | undefined }) {
  if (!skill) {
    return (
      <p className="text-sm text-ink-muted">
        Hover or tab to a skill to see its rank each month.
      </p>
    );
  }
  return (
    <p className="text-sm text-ink-secondary">
      <span className="font-semibold text-ink">{skill.name}</span>
      {skill.points.map((p) => (
        <span key={p.monthKey} className="ml-3 whitespace-nowrap">
          <span className="font-semibold text-ink">#{p.rank}</span>{" "}
          {p.monthLabel} · {jobsLabel(p.jobCount)}
        </span>
      ))}
    </p>
  );
}

function SkillTable({ data }: { data: SkillTrends }) {
  return (
    <details className="mt-4">
      <summary className="cursor-pointer text-sm font-medium text-primary">
        Show as table
      </summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-ink-secondary">
              <th className="py-2 pr-4 font-medium">Skill</th>
              {data.months.map((m) => (
                <th key={m.month_key} className="py-2 pr-4 font-medium">
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.skills.map((s) => (
              <tr
                key={`${s.normalized_name}|${s.skill_type}`}
                className="border-b border-line last:border-0"
              >
                <th scope="row" className="py-2 pr-4 font-medium text-ink">
                  {s.name}
                </th>
                {data.months.map((m) => {
                  const point = s.points.find(
                    (p) => p.month_key === m.month_key,
                  );
                  return (
                    <td
                      key={m.month_key}
                      className="py-2 pr-4 text-ink-secondary"
                    >
                      {point
                        ? `#${point.rank} · ${jobsLabel(point.job_count)}`
                        : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function RankChart({ data }: { data: SkillTrends }) {
  const [active, setActive] = useState<string | null>(null);
  const layout = layoutSkillRanks(data);
  const plotRight = CHART.width - CHART.right;
  const activeSkill = layout.skills.find((s) => s.key === active);
  // The active line is drawn last so it sits on top of the gray ones.
  const ordered = [
    ...layout.skills.filter((s) => s.key !== active),
    ...layout.skills.filter((s) => s.key === active),
  ];

  return (
    <div>
      <div className="mb-3 min-h-[1.5rem]">
        <Readout skill={activeSkill} />
      </div>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          className="w-full min-w-[640px]"
          role="group"
          aria-label={`Top ${layout.topN} skills by number of AV job postings, ranked each month`}
        >
          {/* Vertical month guides only: a horizontal grid would sit exactly
              under a skill whose rank doesn't change and read as data. */}
          {layout.months.map((m) => (
            <line
              key={m.key}
              x1={m.x}
              x2={m.x}
              y1={CHART.top - 12}
              y2={layout.height - CHART.bottom + 12}
              stroke={GRID}
              strokeWidth={1}
            />
          ))}
          {layout.rankTicks.map((tick) => (
            <text
              key={tick.label}
              x={CHART.left - 14}
              y={tick.y}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-ink-muted text-xs"
            >
              {tick.label}
            </text>
          ))}
          {layout.belowLaneY !== null && (
            <text
              x={CHART.left - 14}
              y={layout.belowLaneY}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-ink-muted text-[10px]"
            >
              {`>#${layout.topN}`}
            </text>
          )}
          {layout.months.map((m) => (
            <text
              key={m.key}
              x={m.x}
              y={layout.height - 10}
              textAnchor="middle"
              className="fill-ink-secondary text-xs"
            >
              {m.label}
            </text>
          ))}

          {ordered.map((skill) => {
            const isActive = skill.key === active;
            const dimmed = active !== null && !isActive;
            const color = isActive ? PRIMARY : LINE_GRAY;
            return (
              <g
                key={skill.key}
                tabIndex={0}
                role="img"
                aria-label={describeSkill(skill)}
                className="cursor-pointer outline-none"
                opacity={dimmed ? 0.35 : 1}
                onPointerEnter={() => setActive(skill.key)}
                onPointerLeave={() => setActive(null)}
                onFocus={() => setActive(skill.key)}
                onBlur={() => setActive(null)}
              >
                {/* Wide transparent stroke: the hit target is bigger than the 2px line. */}
                <path
                  d={skill.path}
                  fill="none"
                  stroke="transparent"
                  strokeWidth={16}
                />
                <path
                  d={skill.path}
                  fill="none"
                  stroke={color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {skill.points.map((p) => (
                  <circle
                    key={p.monthKey}
                    cx={p.x}
                    cy={p.y}
                    r={4}
                    fill={color}
                    stroke={SURFACE}
                    strokeWidth={2}
                  />
                ))}
                <text
                  x={plotRight + 16}
                  y={skill.labelY}
                  dominantBaseline="middle"
                  className={`text-xs ${isActive ? "fill-ink font-semibold" : "fill-ink-secondary"}`}
                >
                  {skill.name}
                </text>
                {/* Hit area over the label as well. */}
                <rect
                  x={plotRight + 8}
                  y={skill.labelY - CHART.rowHeight / 2}
                  width={CHART.right - 8}
                  height={CHART.rowHeight}
                  fill="transparent"
                />
              </g>
            );
          })}
        </svg>
      </div>
      <SkillTable data={data} />
    </div>
  );
}

export function SkillRankChartView({ state }: { state: SkillTrendsState }) {
  if (state.status === "loading")
    return <Notice title="Loading skill trends…" />;
  if (state.status === "error") {
    return (
      <Notice title="Couldn't load skill trends right now">
        Please try again in a moment.
      </Notice>
    );
  }
  if (state.data.months.length === 0 || state.data.skills.length === 0) {
    return (
      <Notice title="No skill trends yet">
        Trends appear once the first month of scrapes has been processed.
      </Notice>
    );
  }
  return <RankChart data={state.data} />;
}
