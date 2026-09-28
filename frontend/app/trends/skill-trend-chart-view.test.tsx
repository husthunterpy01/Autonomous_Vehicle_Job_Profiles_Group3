import assert from "node:assert/strict";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { SkillTrends } from "../../lib/services/trend";
import { CHART, SERIES_COLORS } from "../../lib/skill-trend-chart";
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

  it("draws one colored line per skill with named axes", () => {
    const { container } = renderChart();
    const strokes = [...container.querySelectorAll("path")].map((p) =>
      p.getAttribute("stroke"),
    );
    assert.deepEqual(strokes, [SERIES_COLORS[0], SERIES_COLORS[1]]);
    const texts = [...container.querySelectorAll("text")].map(
      (t) => t.textContent,
    );
    assert.deepEqual(texts.slice(0, 5), ["0", "250", "500", "750", "1,000"]);
    for (const label of ["Job postings", "Month", "Aug 2026", "Sep 2026"]) {
      assert.ok(texts.includes(label), label);
    }
  });

  it("the legend lists each skill and its type, without counts", () => {
    const { getByRole } = renderChart();
    const python = getByRole("button", { name: /Python/ });
    assert.equal(python.textContent, "PythonLanguage");
    assert.equal(python.getAttribute("aria-pressed"), "false");
    assert.equal(
      getByRole("button", { name: /ROS 2/ }).textContent,
      "ROS 2Framework",
    );
  });

  it("clicking a skill highlights it and dims the others", () => {
    const { container, getByRole } = renderChart();
    const line = (name: string) =>
      container.querySelector(`g[data-skill="${name}"]`)!;
    fireEvent.click(getByRole("button", { name: /ROS 2/ }));

    assert.equal(
      getByRole("button", { name: /ROS 2/ }).getAttribute("aria-pressed"),
      "true",
    );
    assert.equal(line("ROS 2").getAttribute("opacity"), "1");
    assert.equal(line("Python").getAttribute("opacity"), "0.2");
    // Drawn last, so it sits on top of the others.
    assert.equal(
      container
        .querySelector("g[data-skill]:last-of-type")
        ?.getAttribute("data-skill"),
      "ROS 2",
    );

    fireEvent.click(getByRole("button", { name: /ROS 2/ }));
    assert.equal(line("Python").getAttribute("opacity"), "1");
  });

  it("hovering a month lists every skill's job count, highest first", () => {
    const { container, getByRole, getByTestId, queryByRole } = renderChart();
    const target = container.querySelector("rect[tabindex='0']")!;
    getByTestId("chart-plot").getBoundingClientRect = () =>
      ({ left: 0, width: 640, top: 0, height: CHART.height }) as DOMRect;

    fireEvent.pointerMove(target, { clientX: 80 });
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

  it("zooms with the buttons from 100% to 400%, and resets", () => {
    const { getByRole, getByText } = renderChart();
    const zoomOut = getByRole("button", { name: "Zoom out" });
    const zoomIn = getByRole("button", { name: "Zoom in" });
    const reset = getByRole("button", { name: "Reset zoom" });
    assert.equal((zoomOut as HTMLButtonElement).disabled, true);
    assert.equal((reset as HTMLButtonElement).disabled, true);
    for (const level of ["150%", "200%", "300%", "400%"]) {
      fireEvent.click(zoomIn);
      getByText(level);
    }
    assert.equal((zoomIn as HTMLButtonElement).disabled, true);
    fireEvent.click(zoomOut);
    getByText("300%");
    fireEvent.click(reset);
    getByText("100%");
  });

  it("zooming grows the plot inside a frame that keeps its size", () => {
    const { container, getByRole, getByTestId } = renderChart();
    const plot = getByTestId("chart-plot");
    const frame = getByTestId("chart-scroll").parentElement!;
    const frameHeight = frame.style.height;
    const scroll = getByTestId("chart-scroll");
    assert.match(scroll.className, /overflow-hidden/);

    fireEvent.click(getByRole("button", { name: "Zoom in" }));
    fireEvent.click(getByRole("button", { name: "Zoom in" }));

    assert.equal(frame.style.height, frameHeight);
    assert.equal(plot.getAttribute("height"), String(CHART.height * 2));
    assert.match(scroll.className, /overflow-auto/);
    // The count axis sits outside the scrolling plot, with closer ticks.
    const axis = container.querySelector("svg")!;
    assert.notEqual(axis, plot);
    assert.deepEqual(
      [...axis.querySelectorAll("text")].map((t) => t.textContent),
      ["0", "200", "400", "600", "800", "1,000", "Job postings"],
    );
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
