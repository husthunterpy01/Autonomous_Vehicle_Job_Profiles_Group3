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

/* Sizes in CSS pixels. The plot is drawn at its real size, so zooming makes
   the plot larger inside a fixed frame while text and dots keep their size. */
export const CHART = {
  // Height of the plot frame; at 100% the whole plot fits in it.
  height: 340,
  // Keeps the first and last month's dots and labels inside the plot.
  padX: 36,
  padTop: 14,
  padBottom: 8,
  // Room one month label needs; closer months only label every few.
  labelWidth: 64,
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
  path: string;
};

export type SkillTrendLayout = {
  width: number;
  height: number;
  plotTop: number;
  plotBottom: number;
  months: { key: number; label: string; x: number; showLabel: boolean }[];
  yTicks: { value: number; y: number }[];
  series: TrendSeries[];
};

export function seriesKey(skill: {
  normalized_name: string;
  skill_type: string;
}): string {
  return `${skill.normalized_name}|${skill.skill_type}`;
}

/** The smallest 1 / 2 / 2.5 / 5 × 10^n at or above raw (2.5 only from 25
 *  up, so every tick is a whole number of jobs). */
function roundStepAtLeast(raw: number): number {
  const value = Math.max(raw, 1);
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const multipliers = magnitude >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10];
  return multipliers.find((m) => m * magnitude >= value)! * magnitude;
}

/** A round tick step for about four intervals up to value. */
export function niceStep(value: number): number {
  return roundStepAtLeast(value / 4);
}

/** Zoomed in, ticks get closer in value so they stay about as far apart on
 *  screen: 250 at 100% becomes 200 at 150–200% and 100 at 300–400%. */
export function zoomedStep(step: number, zoom: number): number {
  return Math.min(step, roundStepAtLeast(step / zoom));
}

export function layoutSkillTrend(
  data: SkillTrends,
  size: { width: number; height: number; zoom: number },
): SkillTrendLayout {
  const plotLeft = CHART.padX;
  const plotRight = size.width - CHART.padX;
  const plotTop = CHART.padTop;
  const plotBottom = size.height - CHART.padBottom;
  const count = data.months.length;
  const spacing = count > 1 ? (plotRight - plotLeft) / (count - 1) : Infinity;
  // Months too close to label them all get every few labels, counting back
  // from the latest month so it is always labelled.
  const every = Math.max(1, Math.ceil(CHART.labelWidth / spacing));

  const months = data.months.map((month, index) => ({
    key: month.month_key,
    label: month.label,
    // One month sits in the middle; more spread evenly across the plot.
    x: count === 1 ? size.width / 2 : plotLeft + index * spacing,
    showLabel: (count - 1 - index) % every === 0,
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
  // The range is fixed by the data; zoom only changes the tick spacing.
  const baseStep = niceStep(highest);
  const yMax = Math.max(baseStep, Math.ceil(highest / baseStep) * baseStep);
  const step = zoomedStep(baseStep, size.zoom);
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
      path: points
        .map((p, index) => `${index === 0 ? "M" : "L"}${p.x} ${p.y}`)
        .join(" "),
    };
  });

  return {
    width: size.width,
    height: size.height,
    plotTop,
    plotBottom,
    months,
    yTicks: Array.from({ length: Math.floor(yMax / step) + 1 }, (_, i) => ({
      value: i * step,
      y: y(i * step),
    })),
    series,
  };
}

/** Scroll position after zooming by ratio: the top edge and the right edge
 *  of the view stay put, so zooming in from 100% lands on the latest month
 *  and the highest counts, and further zooms keep that corner in view. The
 *  view can be narrower afterwards (a scrollbar appears once zoomed in). */
export function scrollAfterZoom(
  scroll: { left: number; top: number },
  viewWidth: { before: number; after: number },
  ratio: number,
): { left: number; top: number } {
  return {
    left: Math.max(
      0,
      (scroll.left + viewWidth.before) * ratio - viewWidth.after,
    ),
    top: Math.max(0, scroll.top * ratio),
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
