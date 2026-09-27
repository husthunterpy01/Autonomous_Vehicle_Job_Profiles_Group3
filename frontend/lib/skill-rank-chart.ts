/* Layout for the Market Trends skill rank (bump) chart: pure geometry, so
   it can be tested without rendering. Ranks run top to bottom; a rank
   below the chart's top N (a skill that climbed into it later) sits in one
   "below" lane under the last rank. */
import type { SkillTrends } from "./services/trend";

export const CHART = {
  width: 760,
  rowHeight: 34,
  top: 28,
  bottom: 36,
  left: 44,
  right: 190,
} as const;

export type LaidOutPoint = {
  monthKey: number;
  monthLabel: string;
  x: number;
  y: number;
  rank: number;
  jobCount: number;
  /** Rank is below the chart's top N (drawn in the "below" lane). */
  below: boolean;
};

export type LaidOutSkill = {
  key: string;
  name: string;
  skillType: string;
  latestRank: number;
  points: LaidOutPoint[];
  /** SVG path; a month with no point breaks the line. */
  path: string;
  labelY: number;
};

export type SkillRankLayout = {
  width: number;
  height: number;
  topN: number;
  months: { key: number; label: string; x: number }[];
  rankTicks: { label: string; y: number }[];
  /** y of the "below top N" lane, or null when no point needs it. */
  belowLaneY: number | null;
  skills: LaidOutSkill[];
};

export function rankY(rank: number, topN: number): number {
  const lane = Math.min(rank, topN + 1);
  return CHART.top + (lane - 1) * CHART.rowHeight;
}

export function layoutSkillRanks(data: SkillTrends): SkillRankLayout {
  const topN = data.skills.length;
  const plotLeft = CHART.left;
  const plotRight = CHART.width - CHART.right;
  const count = data.months.length;
  const months = data.months.map((month, index) => ({
    key: month.month_key,
    label: month.label,
    // One month sits in the middle; more spread evenly across the plot.
    x:
      count === 1
        ? (plotLeft + plotRight) / 2
        : plotLeft + (index * (plotRight - plotLeft)) / (count - 1),
  }));
  const monthIndex = new Map(months.map((month, index) => [month.key, index]));

  let usesBelowLane = false;
  const skills = data.skills.map((skill, index) => {
    const points = skill.points
      .filter((point) => monthIndex.has(point.month_key))
      .sort((a, b) => a.month_key - b.month_key)
      .map((point) => {
        const month = months[monthIndex.get(point.month_key)!];
        const below = point.rank > topN;
        usesBelowLane ||= below;
        return {
          monthKey: point.month_key,
          monthLabel: month.label,
          x: month.x,
          y: rankY(point.rank, topN),
          rank: point.rank,
          jobCount: point.job_count,
          below,
        };
      });
    const path = points
      .map((point, i) => {
        const previous = points[i - 1];
        const joined =
          previous !== undefined &&
          monthIndex.get(point.monthKey)! -
            monthIndex.get(previous.monthKey)! ===
            1;
        return `${joined ? "L" : "M"}${point.x} ${point.y}`;
      })
      .join(" ");
    return {
      key: `${skill.normalized_name}|${skill.skill_type}`,
      name: skill.name,
      skillType: skill.skill_type,
      // The API lists skills in the latest month's rank order.
      latestRank: index + 1,
      points,
      path,
      labelY: rankY(index + 1, topN),
    };
  });

  const lanes = topN + (usesBelowLane ? 1 : 0);
  return {
    width: CHART.width,
    height: CHART.top + Math.max(lanes - 1, 0) * CHART.rowHeight + CHART.bottom,
    topN,
    months,
    rankTicks: Array.from({ length: topN }, (_, i) => ({
      label: `#${i + 1}`,
      y: rankY(i + 1, topN),
    })),
    belowLaneY: usesBelowLane ? rankY(topN + 1, topN) : null,
    skills,
  };
}
