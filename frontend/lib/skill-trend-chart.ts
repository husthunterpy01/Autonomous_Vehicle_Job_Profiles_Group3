/* Layout for the Market Trends skill demand chart: job postings per skill
   per month, one colored line per skill. Pure geometry, so it can be
   tested without rendering. */
import type { SkillTrends } from "./services/trend";

/* Categorical slots in fixed order (validated for adjacent-pair and CVD
   separation on the white card). Eight is the ceiling: a ninth hue would
   be indistinguishable from one of these, so the chart shows eight skills.
   Colors follow the skill's position in the API's order, never the
   current highlight. */
export const SERIES_COLORS = [
  "#2a78d6",
  "#eb6834",
  "#1baf7a",
  "#eda100",
  "#e87ba4",
  "#008300",
  "#4a3aa7",
  "#e34948",
] as const;

export const MAX_SERIES = SERIES_COLORS.length;

export const CHART = {
  width: 760,
  height: 440,
  top: 16,
  right: 40,
  // Room for the month labels and the "Month" axis title.
  bottom: 62,
  // Room for the count labels and the rotated "Job postings" title.
  left: 78,
} as const;

export type TrendPoint = {
  monthKey: number;
  monthLabel: string;
  x: number;
  y: number;
  jobCount: number;
};

export type TrendSeries = {
  key: string;
  name: string;
  skillType: string;
  color: string;
  points: TrendPoint[];
  /** Job count in the latest month shown. */
  latestCount: number;
  path: string;
};

export type SkillTrendLayout = {
  width: number;
  height: number;
  plotTop: number;
  plotBottom: number;
  plotLeft: number;
  plotRight: number;
  months: { key: number; label: string; x: number }[];
  yTicks: { value: number; y: number }[];
  series: TrendSeries[];
};

export function seriesKey(skill: {
  normalized_name: string;
  skill_type: string;
}): string {
  return `${skill.normalized_name}|${skill.skill_type}`;
}

/** A round tick step for about four intervals up to value: the smallest
 *  1 / 2 / 2.5 / 5 × 10^n at or above value / 4 (2.5 only from 25 up, so
 *  every tick is a whole number of jobs). */
export function niceStep(value: number): number {
  const raw = Math.max(value / 4, 1);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const multipliers = magnitude >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10];
  return multipliers.find((m) => m * magnitude >= raw)! * magnitude;
}

export function layoutSkillTrend(data: SkillTrends): SkillTrendLayout {
  const plotLeft = CHART.left;
  const plotRight = CHART.width - CHART.right;
  const plotTop = CHART.top;
  const plotBottom = CHART.height - CHART.bottom;
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

  const skills = data.skills.slice(0, MAX_SERIES);
  // A month without a point means no job listed the skill: count it as 0
  // so every line spans the same months.
  const counts = skills.map((skill) =>
    data.months.map(
      (month) =>
        skill.points.find((p) => p.month_key === month.month_key)?.job_count ??
        0,
    ),
  );
  const highest = Math.max(0, ...counts.flat());
  const step = niceStep(highest);
  const yMax = Math.max(step, Math.ceil(highest / step) * step);
  const y = (value: number) =>
    plotBottom - (value / yMax) * (plotBottom - plotTop);

  const series = skills.map((skill, i) => {
    const points = months.map((month, m) => ({
      monthKey: month.key,
      monthLabel: month.label,
      x: month.x,
      y: y(counts[i][m]),
      jobCount: counts[i][m],
    }));
    return {
      key: seriesKey(skill),
      name: skill.name,
      skillType: skill.skill_type,
      color: SERIES_COLORS[i],
      points,
      latestCount: counts[i][counts[i].length - 1] ?? 0,
      path: points
        .map((p, index) => `${index === 0 ? "M" : "L"}${p.x} ${p.y}`)
        .join(" "),
    };
  });

  return {
    width: CHART.width,
    height: CHART.height,
    plotTop,
    plotBottom,
    plotLeft,
    plotRight,
    months,
    yTicks: Array.from({ length: Math.round(yMax / step) + 1 }, (_, i) => ({
      value: i * step,
      y: y(i * step),
    })),
    series,
  };
}

/** Index of the month closest to an x position in chart coordinates. */
export function nearestMonthIndex(
  layout: Pick<SkillTrendLayout, "months">,
  x: number,
): number {
  let best = 0;
  layout.months.forEach((month, index) => {
    if (Math.abs(month.x - x) < Math.abs(layout.months[best].x - x)) {
      best = index;
    }
  });
  return best;
}
