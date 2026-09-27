import assert from "node:assert/strict";
import { test } from "node:test";
import { CHART, layoutSkillRanks, rankY } from "./skill-rank-chart.ts";
import type { SkillTrends } from "./services/trend.ts";

const AUG = 202608;
const SEP = 202609;
const OCT = 202610;

function month(key: number, label: string) {
  return {
    month_key: key,
    label,
    snapshot_at: "2026-09-01T00:00:00Z",
    jobs_with_skills: 100,
  };
}

function skill(name: string, points: [number, number][]) {
  return {
    name,
    normalized_name: name.toLowerCase(),
    skill_type: "domain_concept",
    points: points.map(([key, rank]) => ({
      month_key: key,
      rank,
      job_count: 10,
    })),
  };
}

const DATA: SkillTrends = {
  months: [
    month(AUG, "Aug 2026"),
    month(SEP, "Sep 2026"),
    month(OCT, "Oct 2026"),
  ],
  skills: [
    skill("Python", [
      [AUG, 1],
      [SEP, 1],
      [OCT, 1],
    ]),
    // Below the top 2 in August, missing in September, back in October.
    skill("ROS 2", [
      [AUG, 5],
      [OCT, 2],
    ]),
  ],
};

test("months spread evenly across the plot, oldest first", () => {
  const layout = layoutSkillRanks(DATA);
  assert.deepEqual(
    layout.months.map((m) => [m.label, m.x]),
    [
      ["Aug 2026", CHART.left],
      ["Sep 2026", (CHART.left + CHART.width - CHART.right) / 2],
      ["Oct 2026", CHART.width - CHART.right],
    ],
  );
});

test("a single month sits in the middle", () => {
  const layout = layoutSkillRanks({ ...DATA, months: [DATA.months[2]] });
  assert.equal(
    layout.months[0].x,
    (CHART.left + CHART.width - CHART.right) / 2,
  );
  assert.equal(layout.skills[1].points.length, 1);
});

test("ranks run top to bottom and ranks past the top N share one lane", () => {
  assert.equal(rankY(1, 10), CHART.top);
  assert.equal(rankY(2, 10), CHART.top + CHART.rowHeight);
  assert.equal(rankY(11, 10), rankY(40, 10));

  const layout = layoutSkillRanks(DATA);
  const ros = layout.skills[1];
  assert.equal(layout.topN, 2);
  assert.deepEqual(
    ros.points.map((p) => [p.rank, p.below, p.y]),
    [
      [5, true, rankY(3, 2)],
      [2, false, rankY(2, 2)],
    ],
  );
  assert.equal(layout.belowLaneY, rankY(3, 2));
  assert.equal(layout.height, CHART.top + 2 * CHART.rowHeight + CHART.bottom);
});

test("a month without a point breaks the line", () => {
  const layout = layoutSkillRanks(DATA);
  assert.equal(layout.skills[0].path.match(/L/g)?.length, 2);
  assert.match(layout.skills[1].path, /^M\S+ \S+ M\S+ \S+$/);
});

test("labels follow the latest rank and no below lane when every rank fits", () => {
  const layout = layoutSkillRanks({
    months: DATA.months,
    skills: [
      skill("C++", [[OCT, 1]]),
      skill("Python", [
        [AUG, 1],
        [OCT, 2],
      ]),
    ],
  });
  assert.deepEqual(
    layout.skills.map((s) => [s.name, s.latestRank, s.labelY]),
    [
      ["C++", 1, rankY(1, 2)],
      ["Python", 2, rankY(2, 2)],
    ],
  );
  assert.equal(layout.belowLaneY, null);
  assert.deepEqual(
    layout.rankTicks.map((t) => t.label),
    ["#1", "#2"],
  );
  assert.equal(layout.skills[0].key, "c++|domain_concept");
});
