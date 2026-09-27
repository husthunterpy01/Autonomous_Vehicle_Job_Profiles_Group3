"use client";

import {
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import {
  layoutSkillTrend,
  nearestMonthIndex,
  type SkillTrendLayout,
  type TrendSeries,
} from "@/lib/skill-trend-chart";
import type { SkillTrends } from "@/lib/services/trend";

export type SkillTrendsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "success"; data: SkillTrends };

export const MIN_ZOOM = 1;
export const MAX_ZOOM = 2;
const ZOOM_STEP = 0.25;
const MIN_RENDERED_WIDTH = 640;
const GRID = "#eef0f4";
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

/* A short stroke of the series color: the key in the legend and tooltip. */
function LineKey({ color }: { color: string }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-0.5 w-4 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  );
}

function Legend({
  series,
  onToggle,
}: {
  series: TrendSeries[];
  onToggle: (key: string) => void;
}) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Skills">
      {series.map((s) => (
        <li key={s.key}>
          <button
            type="button"
            aria-pressed={!s.hidden}
            onClick={() => onToggle(s.key)}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm transition-colors ${
              s.hidden
                ? "border-line text-ink-muted"
                : "border-line bg-surface text-ink hover:border-primary"
            }`}
          >
            <LineKey color={s.hidden ? "#cbd5e1" : s.color} />
            {s.name}
          </button>
        </li>
      ))}
    </ul>
  );
}

function ZoomControls({
  zoom,
  onZoom,
}: {
  zoom: number;
  onZoom: (change: (zoom: number) => number) => void;
}) {
  const button =
    "rounded-md border border-line px-2.5 py-1 text-sm text-ink-secondary transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="flex items-center gap-2" aria-label="Chart zoom">
      <button
        type="button"
        className={button}
        aria-label="Zoom out"
        onClick={() => onZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP))}
        disabled={zoom <= MIN_ZOOM}
      >
        −
      </button>
      <span className="w-12 text-center text-sm text-ink-secondary">
        {Math.round(zoom * 100)}%
      </span>
      <button
        type="button"
        className={button}
        aria-label="Zoom in"
        onClick={() => onZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP))}
        disabled={zoom >= MAX_ZOOM}
      >
        +
      </button>
    </div>
  );
}

/* One readout for the hovered month, listing every shown skill: the value
   leads, the name follows, highest first. */
function Tooltip({
  layout,
  monthIndex,
}: {
  layout: SkillTrendLayout;
  monthIndex: number;
}) {
  const month = layout.months[monthIndex];
  const rows = layout.series
    .filter((s) => !s.hidden)
    .map((s) => ({ s, count: s.points[monthIndex].jobCount }))
    .sort((a, b) => b.count - a.count);
  const leftPercent = (month.x / layout.width) * 100;
  const alignRight = leftPercent > 60;
  return (
    <div
      role="status"
      className="pointer-events-none absolute top-2 z-10 min-w-[180px] rounded-lg border border-line bg-surface p-3 text-sm shadow-md"
      style={
        alignRight
          ? { right: `${100 - leftPercent + 2}%` }
          : { left: `${leftPercent + 2}%` }
      }
    >
      <p className="mb-1.5 text-xs font-medium text-ink-muted">{month.label}</p>
      <ul className="space-y-1">
        {rows.map(({ s, count }) => (
          <li key={s.key} className="flex items-center gap-2">
            <LineKey color={s.color} />
            <span className="font-semibold text-ink">
              {count.toLocaleString("en-US")}
            </span>
            <span className="text-ink-secondary">{s.name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkillTable({ layout }: { layout: SkillTrendLayout }) {
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
              {layout.months.map((m) => (
                <th key={m.key} className="py-2 pr-4 font-medium">
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {layout.series.map((s) => (
              <tr key={s.key} className="border-b border-line last:border-0">
                <th scope="row" className="py-2 pr-4 font-medium text-ink">
                  {s.name}
                </th>
                {s.points.map((p) => (
                  <td key={p.monthKey} className="py-2 pr-4 text-ink-secondary">
                    {jobsLabel(p.jobCount)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function TrendChart({ data }: { data: SkillTrends }) {
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const [zoom, setZoom] = useState(MIN_ZOOM);
  const [activeMonth, setActiveMonth] = useState<number | null>(null);
  const layout = layoutSkillTrend(data, hidden);
  const visible = layout.series.filter((s) => !s.hidden);
  const lastMonth = layout.months.length - 1;

  const toggle = (key: string) =>
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      // Keep at least one skill on the chart.
      else if (layout.series.length - next.size > 1) next.add(key);
      return next;
    });

  const onPointerMove = (event: PointerEvent<SVGRectElement>) => {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) return;
    const box = svg.getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * layout.width;
    setActiveMonth(nearestMonthIndex(layout, x));
  };

  const onKeyDown = (event: KeyboardEvent<SVGRectElement>) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      const step = event.key === "ArrowLeft" ? -1 : 1;
      setActiveMonth((current) =>
        Math.min(lastMonth, Math.max(0, (current ?? lastMonth) + step)),
      );
    } else if (event.key === "Escape") {
      setActiveMonth(null);
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <Legend series={layout.series} onToggle={toggle} />
        <ZoomControls zoom={zoom} onZoom={setZoom} />
      </div>
      <div className="overflow-x-auto overscroll-x-contain">
        <div
          className="relative"
          style={{
            width: `${zoom * 100}%`,
            minWidth: `${MIN_RENDERED_WIDTH * zoom}px`,
          }}
        >
          <svg
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            className="block w-full"
            role="group"
            aria-label={`Job postings per month for ${visible.map((s) => s.name).join(", ")}`}
          >
            {layout.yTicks.map((tick) => (
              <g key={tick.value}>
                <line
                  x1={layout.plotLeft}
                  x2={layout.plotRight}
                  y1={tick.y}
                  y2={tick.y}
                  stroke={GRID}
                  strokeWidth={1}
                />
                <text
                  x={layout.plotLeft - 10}
                  y={tick.y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className="fill-ink-muted text-xs"
                >
                  {tick.value.toLocaleString("en-US")}
                </text>
              </g>
            ))}
            {layout.months.map((m) => (
              <text
                key={m.key}
                x={m.x}
                y={layout.height - 12}
                textAnchor="middle"
                className="fill-ink-secondary text-xs"
              >
                {m.label}
              </text>
            ))}
            {activeMonth !== null && (
              <line
                x1={layout.months[activeMonth].x}
                x2={layout.months[activeMonth].x}
                y1={layout.plotTop}
                y2={layout.plotBottom}
                stroke="#94a3b8"
                strokeWidth={1}
              />
            )}
            {visible.map((s) => (
              <g key={s.key}>
                <path
                  d={s.path}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {s.points.map((p, index) => (
                  <circle
                    key={p.monthKey}
                    cx={p.x}
                    cy={p.y}
                    r={index === activeMonth ? 5 : 4}
                    fill={s.color}
                    stroke={SURFACE}
                    strokeWidth={2}
                  />
                ))}
              </g>
            ))}
            {/* The whole plot is the hover target, so any x picks the nearest
                month; arrow keys do the same from the keyboard. */}
            <rect
              x={0}
              y={0}
              width={layout.width}
              height={layout.plotBottom + 8}
              fill="transparent"
              tabIndex={0}
              role="group"
              aria-label="Hover, or focus and use the left and right arrow keys, to read each month's job counts"
              className="cursor-crosshair outline-none"
              onPointerMove={onPointerMove}
              onPointerLeave={() => setActiveMonth(null)}
              onFocus={() => setActiveMonth((current) => current ?? lastMonth)}
              onBlur={() => setActiveMonth(null)}
              onKeyDown={onKeyDown}
            />
          </svg>
          {activeMonth !== null && (
            <Tooltip layout={layout} monthIndex={activeMonth} />
          )}
        </div>
      </div>
      <SkillTable layout={layout} />
    </div>
  );
}

export function SkillTrendChartView({ state }: { state: SkillTrendsState }) {
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
  return <TrendChart data={state.data} />;
}
