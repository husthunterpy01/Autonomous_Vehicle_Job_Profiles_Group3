import assert from "node:assert/strict";
import { test } from "node:test";
import {
  CHART,
  layoutSkillTrend as layoutAt,
  MAX_SERIES,
  nearestMonthIndex,
  niceStep,
  scrollAfterZoom,
  SERIES_COLORS,
  zoomedStep,
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

const WIDTH = 640;
const plotTop = CHART.padTop;
const plotBottom = CHART.height - CHART.padBottom;

// The plot at 100% unless a zoom is given.
function layoutSkillTrend(data: SkillTrends, zoom = 1, width = WIDTH) {
  return layoutAt(data, {
    width: width * zoom,
    height: CHART.height * zoom,
    zoom,
  });
}

test("tick steps are round and whole", () => {
  assert.equal(niceStep(806), 250);
  assert.equal(niceStep(463), 200);
  assert.equal(niceStep(81), 25);
  assert.equal(niceStep(7), 2);
  assert.equal(niceStep(0), 1);
});

test("zoomed in, ticks get closer in value but never wider", () => {
  assert.equal(zoomedStep(250, 1), 250);
  assert.equal(zoomedStep(250, 2), 200);
  assert.equal(zoomedStep(250, 4), 100);
  assert.equal(zoomedStep(2, 4), 1);
});

test("zooming stretches the plot but keeps the same count range", () => {
  const zoomed = layoutSkillTrend(DATA, 2);
  assert.equal(zoomed.width, WIDTH * 2);
  assert.equal(zoomed.height, CHART.height * 2);
  assert.deepEqual(
    zoomed.yTicks.map((t) => t.value),
    [0, 200, 400, 600, 800, 1000],
  );
  assert.equal(zoomed.yTicks.at(-1)!.y, plotTop);
  assert.equal(zoomed.yTicks[0].y, CHART.height * 2 - CHART.padBottom);
});

test("zooming keeps the top and right edges of the view in place", () => {
  // From 100% (nothing to scroll) to 200%: the latest month and the
  // highest counts, i.e. the top right corner.
  const same = { before: 600, after: 600 };
  assert.deepEqual(scrollAfterZoom({ left: 0, top: 0 }, same, 2), {
    left: 600,
    top: 0,
  });
  assert.deepEqual(scrollAfterZoom({ left: 600, top: 100 }, same, 1.5), {
    left: 1200,
    top: 150,
  });
  // A scrollbar appearing narrows the view: still flush with the right edge.
  assert.deepEqual(
    scrollAfterZoom({ left: 0, top: 0 }, { before: 600, after: 585 }, 2),
    { left: 615, top: 0 },
  );
  // Zooming out never scrolls past the start.
  assert.deepEqual(scrollAfterZoom({ left: 100, top: 50 }, same, 0.5), {
    left: 0,
    top: 25,
  });
});

test("crowded month labels are thinned, always keeping the latest month", () => {
  const year: SkillTrends = {
    months: Array.from({ length: 12 }, (_, i) =>
      month(202601 + i, `M${i + 1}`),
    ),
    skills: [skill("Python", [[202612, 10]])],
  };
  const labelled = (layout: ReturnType<typeof layoutSkillTrend>) =>
    layout.months.filter((m) => m.showLabel).map((m) => m.label);

  // 12 months in a narrow plot: about 34px apart, so every other label.
  assert.deepEqual(labelled(layoutSkillTrend(year, 1, 450)), [
    "M2",
    "M4",
    "M6",
    "M8",
    "M10",
    "M12",
  ]);
  // Zoomed in, they fit again.
  assert.equal(labelled(layoutSkillTrend(year, 2, 450)).length, 12);
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
    [CHART.padX, WIDTH - CHART.padX],
  );
  assert.ok(layout.months.every((m) => m.showLabel));
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

test("colors follow the API order", () => {
  const layout = layoutSkillTrend(DATA);
  assert.deepEqual(
    layout.series.map((s) => [s.name, s.color]),
    [
      ["Python", SERIES_COLORS[0]],
      ["ROS 2", SERIES_COLORS[1]],
    ],
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
  assert.equal(single.months[0].x, WIDTH / 2);

  const layout = layoutSkillTrend(DATA);
  assert.equal(nearestMonthIndex(layout, CHART.padX + 10), 0);
  assert.equal(nearestMonthIndex(layout, WIDTH), 1);
});
