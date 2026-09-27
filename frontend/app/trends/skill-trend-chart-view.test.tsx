import assert from "node:assert/strict";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { SkillTrends } from "../../lib/services/trend";
import { SERIES_COLORS } from "../../lib/skill-trend-chart";
import { SkillTrendChartView } from "./skill-trend-chart-view";

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

afterEach(cleanup);

function renderChart() {
  return render(
    <SkillTrendChartView state={{ status: "success", data: DATA }} />,
  );
}

describe("SkillTrendChartView", () => {
  it("shows loading, error and empty notices", () => {
    const html = (state: Parameters<typeof SkillTrendChartView>[0]["state"]) =>
      renderToStaticMarkup(<SkillTrendChartView state={state} />);
    assert.match(html({ status: "loading" }), /Loading skill trends/);
    assert.match(
      html({ status: "error" }),
      /Couldn&#x27;t load skill trends right now/,
    );
    assert.match(
      html({ status: "success", data: { months: [], skills: [] } }),
      /No skill trends yet/,
    );
  });

  it("draws one colored line per skill with a job-count axis and a legend", () => {
    const { container, getByRole } = renderChart();
    const strokes = [...container.querySelectorAll("path")].map((p) =>
      p.getAttribute("stroke"),
    );
    assert.deepEqual(strokes, [SERIES_COLORS[0], SERIES_COLORS[1]]);
    const ticks = [...container.querySelectorAll("text")].map(
      (t) => t.textContent,
    );
    assert.deepEqual(ticks.slice(0, 5), ["0", "250", "500", "750", "1,000"]);
    assert.ok(ticks.includes("Aug 2026") && ticks.includes("Sep 2026"));
    assert.equal(
      getByRole("button", { name: "Python" }).getAttribute("aria-pressed"),
      "true",
    );
  });

  it("hovering a month lists every skill's job count, highest first", () => {
    const { container, getByRole, queryByRole } = renderChart();
    const target = container.querySelector("rect[tabindex='0']")!;
    const svg = container.querySelector("svg")!;
    svg.getBoundingClientRect = () =>
      ({ left: 0, width: 760, top: 0, height: 320 }) as DOMRect;

    fireEvent.pointerMove(target, { clientX: 60 });
    const tooltip = getByRole("status");
    assert.match(tooltip.textContent!, /Aug 2026/);
    assert.match(tooltip.textContent!, /664Python.*0ROS 2/);

    fireEvent.pointerLeave(target);
    assert.equal(queryByRole("status"), null);
  });

  it("arrow keys move between months from the keyboard", () => {
    const { container, getByRole } = renderChart();
    const target = container.querySelector("rect[tabindex='0']")!;
    fireEvent.focus(target);
    assert.match(getByRole("status").textContent!, /Sep 2026.*806Python/);
    fireEvent.keyDown(target, { key: "ArrowLeft" });
    assert.match(getByRole("status").textContent!, /Aug 2026/);
  });

  it("the legend hides a skill but never the last one", () => {
    const { container, getByRole } = renderChart();
    fireEvent.click(getByRole("button", { name: "Python" }));
    assert.equal(
      getByRole("button", { name: "Python" }).getAttribute("aria-pressed"),
      "false",
    );
    assert.equal(container.querySelectorAll("path").length, 1);

    fireEvent.click(getByRole("button", { name: "ROS 2" }));
    assert.equal(container.querySelectorAll("path").length, 1);
  });

  it("zooms between 100% and 200%", () => {
    const { getByRole, getByText } = renderChart();
    const zoomOut = getByRole("button", { name: "Zoom out" });
    const zoomIn = getByRole("button", { name: "Zoom in" });
    assert.equal((zoomOut as HTMLButtonElement).disabled, true);
    for (let i = 0; i < 4; i += 1) fireEvent.click(zoomIn);
    getByText("200%");
    assert.equal((zoomIn as HTMLButtonElement).disabled, true);
  });

  it("lists the same numbers in a table, with 0 for a missing month", () => {
    const { container } = renderChart();
    const cells = [...container.querySelectorAll("tbody tr")].map((row) =>
      [...row.querySelectorAll("th, td")].map((cell) => cell.textContent),
    );
    assert.deepEqual(cells, [
      ["Python", "664 jobs", "806 jobs"],
      ["ROS 2", "0 jobs", "81 jobs"],
    ]);
  });
});
