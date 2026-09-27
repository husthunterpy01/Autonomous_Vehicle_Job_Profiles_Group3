import assert from "node:assert/strict";
import { test } from "node:test";
import {
  CHART,
  layoutSkillTrend,
  MAX_SERIES,
  nearestMonthIndex,
  niceStep,
  SERIES_COLORS,
} from "./skill-trend-chart.ts";
import type { SkillTrends } from "./services/trend.ts";

const AUG = 202608;
const SEP = 202609;

function month(key: number, label: string) {
  return {
    month_key: key,
    label,
    snapshot_at: "2026-09-01T00:00:00Z",
    jobs_with_skills: 100,
  };
}

function skill(name: string, counts: [number, number][]) {
  return {
    name,
    normalized_name: name.toLowerCase(),
    skill_type: "domain_concept",
    points: counts.map(([key, jobCount], i) => ({
      month_key: key,
      rank: i + 1,
      job_count: jobCount,
    })),
  };
}

const DATA: SkillTrends = {
  months: [month(AUG, "Aug 2026"), month(SEP, "Sep 2026")],
  skills: [
    skill("Python", [
      [AUG, 664],
      [SEP, 806],
    ]),
    // No August point: no job listed it that month.
    skill("ROS 2", [[SEP, 81]]),
  ],
};

const plotTop = CHART.top;
const plotBottom = CHART.height - CHART.bottom;

test("tick steps are round and whole", () => {
  assert.equal(niceStep(806), 250);
  assert.equal(niceStep(463), 200);
  assert.equal(niceStep(81), 25);
  assert.equal(niceStep(7), 2);
  assert.equal(niceStep(0), 1);
});

test("the y axis runs from 0 to a round maximum above the highest count", () => {
  const layout = layoutSkillTrend(DATA);
  assert.deepEqual(
    layout.yTicks.map((t) => t.value),
    [0, 250, 500, 750, 1000],
  );
  assert.equal(layout.yTicks[0].y, plotBottom);
  assert.equal(layout.yTicks.at(-1)!.y, plotTop);
});

test("months spread across the plot and a missing month counts as 0", () => {
  const layout = layoutSkillTrend(DATA);
  assert.deepEqual(
    layout.months.map((m) => m.x),
    [CHART.left, CHART.width - CHART.right],
  );
  const ros = layout.series[1];
  assert.deepEqual(
    ros.points.map((p) => [p.monthLabel, p.jobCount]),
    [
      ["Aug 2026", 0],
      ["Sep 2026", 81],
    ],
  );
  assert.equal(ros.points[0].y, plotBottom);
  assert.match(ros.path, /^M\S+ \S+ L\S+ \S+$/);
});

test("hiding a skill rescales the axis but keeps every color", () => {
  const layout = layoutSkillTrend(DATA, new Set(["python|domain_concept"]));
  assert.equal(layout.series[0].hidden, true);
  assert.deepEqual(
    layout.yTicks.map((t) => t.value),
    [0, 25, 50, 75, 100],
  );
  assert.deepEqual(
    layout.series.map((s) => s.color),
    [SERIES_COLORS[0], SERIES_COLORS[1]],
  );
});

test("shows at most eight skills, one color each", () => {
  const many: SkillTrends = {
    months: DATA.months,
    skills: Array.from({ length: 10 }, (_, i) =>
      skill(`Skill ${i}`, [[SEP, 100 - i]]),
    ),
  };
  const layout = layoutSkillTrend(many);
  assert.equal(layout.series.length, MAX_SERIES);
  assert.equal(new Set(layout.series.map((s) => s.color)).size, MAX_SERIES);
});

test("a single month sits in the middle and the nearest month is found", () => {
  const single = layoutSkillTrend({ ...DATA, months: [DATA.months[1]] });
  assert.equal(
    single.months[0].x,
    (CHART.left + CHART.width - CHART.right) / 2,
  );

  const layout = layoutSkillTrend(DATA);
  assert.equal(nearestMonthIndex(layout, CHART.left + 10), 0);
  assert.equal(nearestMonthIndex(layout, CHART.width), 1);
});
