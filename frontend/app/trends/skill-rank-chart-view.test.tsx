import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { SkillTrends } from "../../lib/services/trend";
import { SkillRankChartView } from "./skill-rank-chart-view";

const DATA: SkillTrends = {
  months: [
    {
      month_key: 202608,
      label: "Aug 2026",
      snapshot_at: "2026-08-31T14:17:29Z",
      jobs_with_skills: 1074,
    },
    {
      month_key: 202609,
      label: "Sep 2026",
      snapshot_at: "2026-09-12T05:46:21Z",
      jobs_with_skills: 1198,
    },
  ],
  skills: [
    {
      name: "Python",
      normalized_name: "python",
      skill_type: "programming_language",
      points: [
        { month_key: 202608, rank: 1, job_count: 664 },
        { month_key: 202609, rank: 1, job_count: 806 },
      ],
    },
    {
      name: "ROS 2",
      normalized_name: "ros 2",
      skill_type: "framework",
      points: [{ month_key: 202609, rank: 2, job_count: 81 }],
    },
  ],
};

function render(state: Parameters<typeof SkillRankChartView>[0]["state"]) {
  return renderToStaticMarkup(<SkillRankChartView state={state} />);
}

describe("SkillRankChartView", () => {
  it("shows loading, error and empty notices", () => {
    assert.match(render({ status: "loading" }), /Loading skill trends/);
    assert.match(
      render({ status: "error" }),
      /Couldn&#x27;t load skill trends right now/,
    );
    assert.match(
      render({ status: "success", data: { months: [], skills: [] } }),
      /No skill trends yet/,
    );
  });

  it("draws a labelled line per skill with every month as axis labels", () => {
    const html = render({ status: "success", data: DATA });
    assert.match(html, />Python<\/text>/);
    assert.match(html, />ROS 2<\/text>/);
    assert.match(html, />Aug 2026<\/text>/);
    assert.match(html, />Sep 2026<\/text>/);
    assert.match(html, />#1<\/text>/);
    // Keyboard and screen-reader access to each skill's numbers.
    assert.match(
      html,
      /aria-label="Python: Aug 2026 #1 \(664 jobs\), Sep 2026 #1 \(806 jobs\)"/,
    );
    assert.equal(html.match(/tabindex="0"/g)?.length, 2);
  });

  it("lists the same numbers in a table, with a dash for a missing month", () => {
    const html = render({ status: "success", data: DATA });
    assert.match(html, /Show as table/);
    assert.match(html, /<td[^>]*>#1 · 806 jobs<\/td>/);
    assert.match(
      html,
      /<th scope="row"[^>]*>ROS 2<\/th><td[^>]*>—<\/td><td[^>]*>#2 · 81 jobs<\/td>/,
    );
  });
});
