"use client";

import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
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
export const MAX_ZOOM = 3;
const ZOOM_STEP = 0.25;
// How fast the mouse wheel zooms: one notch (deltaY 100) is about 16%.
const WHEEL_ZOOM_SPEED = 0.0015;
const MIN_RENDERED_WIDTH = 560;
const GRID = "#eef0f4";
const SURFACE = "#ffffff";

const SKILL_TYPE_LABELS: Record<string, string> = {
  programming_language: "Language",
  framework: "Framework",
  tool: "Tool",
  domain_concept: "Domain concept",
  certification: "Certification",
};

export function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(zoom * 100) / 100));
}

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
  latestLabel,
  highlighted,
  onSelect,
}: {
  series: TrendSeries[];
  latestLabel: string;
  highlighted: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <aside className="border-t border-line p-4 lg:w-72 lg:shrink-0 lg:border-t-0 lg:border-l">
      <div className="flex items-baseline justify-between text-xs font-semibold tracking-wide text-ink-muted uppercase">
        <span>Skills</span>
        <span className="normal-case">{latestLabel}</span>
      </div>
      <ul className="mt-3 space-y-1.5" aria-label="Skills">
        {series.map((s) => {
          const active = s.key === highlighted;
          const dimmed = highlighted !== null && !active;
          return (
            <li key={s.key}>
              <button
                type="button"
                aria-pressed={active}
                onClick={() => onSelect(s.key)}
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-1.5 text-left transition-colors ${
                  active
                    ? "border-primary bg-primary-light"
                    : "border-line bg-section hover:border-primary"
                } ${dimmed ? "opacity-60" : ""}`}
              >
                <LineKey color={s.color} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-ink">
                    {s.name}
                  </span>
                  <span className="block text-xs text-ink-muted">
                    {SKILL_TYPE_LABELS[s.skillType] ?? s.skillType}
                  </span>
                </span>
                <span className="text-sm font-bold text-ink">
                  {s.latestCount.toLocaleString("en-US")}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
        Click a skill to highlight it in the chart. Counts are job postings in{" "}
        {latestLabel}.
      </p>
    </aside>
  );
}

function ZoomControls({
  zoom,
  onZoom,
  onReset,
}: {
  zoom: number;
  onZoom: (change: (zoom: number) => number) => void;
  onReset: () => void;
}) {
  const button =
    "rounded-md border border-line px-2.5 py-1 text-sm text-ink-secondary transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="flex items-center gap-2">
      <div
        className="flex items-center gap-1 rounded-lg border border-line p-1"
        aria-label="Chart zoom"
      >
        <button
          type="button"
          className={button}
          aria-label="Zoom out"
          onClick={() => onZoom((z) => clampZoom(z - ZOOM_STEP))}
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
          onClick={() => onZoom((z) => clampZoom(z + ZOOM_STEP))}
          disabled={zoom >= MAX_ZOOM}
        >
          +
        </button>
      </div>
      <button
        type="button"
        className={button}
        aria-label="Reset zoom"
        onClick={onReset}
        disabled={zoom === MIN_ZOOM}
      >
        ↺
      </button>
    </div>
  );
}

/* One readout for the hovered month, listing every skill: the value leads,
   the name follows, highest first. */
function Tooltip({
  layout,
  monthIndex,
  highlighted,
}: {
  layout: SkillTrendLayout;
  monthIndex: number;
  highlighted: string | null;
}) {
  const month = layout.months[monthIndex];
  const rows = layout.series
    .map((s) => ({ s, count: s.points[monthIndex].jobCount }))
    .sort((a, b) => b.count - a.count);
  const leftPercent = (month.x / layout.width) * 100;
  const alignRight = leftPercent > 60;
  return (
    <div
      role="status"
      className="pointer-events-none absolute top-2 z-10 min-w-[190px] rounded-lg border border-line bg-surface p-3 text-sm shadow-md"
      style={
        alignRight
          ? { right: `${100 - leftPercent + 2}%` }
          : { left: `${leftPercent + 2}%` }
      }
    >
      <p className="mb-1.5 text-xs font-medium text-ink-muted">{month.label}</p>
      <ul className="space-y-1">
        {rows.map(({ s, count }) => (
          <li
            key={s.key}
            className={`flex items-center gap-2 rounded px-1 ${
              s.key === highlighted ? "bg-primary-light" : ""
            }`}
          >
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
  // The geometry only depends on the data: zooming, hovering and
  // highlighting re-render without recomputing it.
  const layout = useMemo(() => layoutSkillTrend(data), [data]);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [zoom, setZoom] = useState(MIN_ZOOM);
  const [activeMonth, setActiveMonth] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef(zoom);
  // Where to keep the content under the cursor after a zoom.
  const anchorRef = useRef<{
    contentX: number;
    offsetX: number;
    ratio: number;
  } | null>(null);
  const dragRef = useRef<{ x: number; scrollLeft: number } | null>(null);
  const lastMonth = layout.months.length - 1;

  const zoomAround = (next: number, offsetX: number) => {
    const el = scrollRef.current;
    const current = zoomRef.current;
    if (!el || next === current) return;
    anchorRef.current = {
      contentX: el.scrollLeft + offsetX,
      offsetX,
      ratio: next / current,
    };
    zoomRef.current = next;
    setZoom(next);
  };

  const zoomBy = (change: (zoom: number) => number) => {
    const el = scrollRef.current;
    zoomAround(change(zoomRef.current), el ? el.clientWidth / 2 : 0);
  };

  useLayoutEffect(() => {
    const el = scrollRef.current;
    const anchor = anchorRef.current;
    if (!el || !anchor) return;
    el.scrollLeft = anchor.contentX * anchor.ratio - anchor.offsetX;
    anchorRef.current = null;
  }, [zoom]);

  // Wheel zoom needs a non-passive listener to stop the page scrolling. At
  // the zoom limits the wheel scrolls the page as usual.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (event: WheelEvent) => {
      if (event.deltaY === 0) return;
      const next = clampZoom(
        zoomRef.current * Math.exp(-event.deltaY * WHEEL_ZOOM_SPEED),
      );
      if (next === zoomRef.current) return;
      event.preventDefault();
      zoomAround(next, event.clientX - el.getBoundingClientRect().left);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
    // Registered once: zoomAround only reads refs, so it never goes stale.
  }, []);

  const onPanStart = (event: PointerEvent<HTMLDivElement>) => {
    const el = scrollRef.current;
    if (!el || event.button !== 0 || el.scrollWidth <= el.clientWidth) return;
    dragRef.current = { x: event.clientX, scrollLeft: el.scrollLeft };
    el.setPointerCapture?.(event.pointerId);
    setDragging(true);
  };
  const onPanMove = (event: PointerEvent<HTMLDivElement>) => {
    const el = scrollRef.current;
    if (!el || !dragRef.current) return;
    el.scrollLeft =
      dragRef.current.scrollLeft - (event.clientX - dragRef.current.x);
  };
  const onPanEnd = () => {
    dragRef.current = null;
    setDragging(false);
  };

  const onHover = (event: PointerEvent<SVGRectElement>) => {
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

  // The highlighted skill is drawn last, on top of the others.
  const ordered = [
    ...layout.series.filter((s) => s.key !== highlighted),
    ...layout.series.filter((s) => s.key === highlighted),
  ];
  const plotMiddleY = (layout.plotTop + layout.plotBottom) / 2;
  const plotMiddleX = (layout.plotLeft + layout.plotRight) / 2;

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <ZoomControls
          zoom={zoom}
          onZoom={zoomBy}
          onReset={() => zoomAround(MIN_ZOOM, 0)}
        />
      </div>
      <div className="overflow-hidden rounded-xl border border-line">
        <div className="flex flex-col lg:flex-row">
          <div className="min-w-0 flex-1 p-4">
            <div
              ref={scrollRef}
              data-testid="chart-scroll"
              className={`overflow-x-auto overscroll-x-contain ${
                zoom > MIN_ZOOM
                  ? dragging
                    ? "cursor-grabbing"
                    : "cursor-grab"
                  : ""
              }`}
              onPointerDown={onPanStart}
              onPointerMove={onPanMove}
              onPointerUp={onPanEnd}
              onPointerCancel={onPanEnd}
            >
              <div
                className="relative"
                style={{
                  width: `${zoom * 100}%`,
                  minWidth: `${MIN_RENDERED_WIDTH * zoom}px`,
                }}
              >
                <svg
                  viewBox={`0 0 ${layout.width} ${layout.height}`}
                  className="block w-full select-none"
                  role="group"
                  aria-label={`Job postings per month for ${layout.series.map((s) => s.name).join(", ")}`}
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
                  <text
                    x={16}
                    y={plotMiddleY}
                    textAnchor="middle"
                    transform={`rotate(-90 16 ${plotMiddleY})`}
                    className="fill-ink-secondary text-xs font-medium"
                  >
                    Job postings
                  </text>
                  {layout.months.map((m) => (
                    <text
                      key={m.key}
                      x={m.x}
                      y={layout.plotBottom + 22}
                      textAnchor="middle"
                      className="fill-ink-secondary text-xs"
                    >
                      {m.label}
                    </text>
                  ))}
                  <text
                    x={plotMiddleX}
                    y={layout.height - 8}
                    textAnchor="middle"
                    className="fill-ink-secondary text-xs font-medium"
                  >
                    Month
                  </text>
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
                  {ordered.map((s) => {
                    const active = s.key === highlighted;
                    const dimmed = highlighted !== null && !active;
                    return (
                      <g
                        key={s.key}
                        data-skill={s.name}
                        opacity={dimmed ? 0.2 : 1}
                      >
                        <path
                          d={s.path}
                          fill="none"
                          stroke={s.color}
                          strokeWidth={active ? 3 : 2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        {s.points.map((p, index) => (
                          <circle
                            key={p.monthKey}
                            cx={p.x}
                            cy={p.y}
                            r={index === activeMonth || active ? 5 : 4}
                            fill={s.color}
                            stroke={SURFACE}
                            strokeWidth={2}
                          />
                        ))}
                      </g>
                    );
                  })}
                  {/* The whole plot is the hover target, so any x picks the
                      nearest month; arrow keys do the same from the keyboard. */}
                  <rect
                    x={0}
                    y={0}
                    width={layout.width}
                    height={layout.plotBottom + 8}
                    fill="transparent"
                    tabIndex={0}
                    role="group"
                    aria-label="Hover, or focus and use the left and right arrow keys, to read each month's job counts"
                    className="outline-none"
                    onPointerMove={onHover}
                    onPointerLeave={() => setActiveMonth(null)}
                    onFocus={() =>
                      setActiveMonth((current) => current ?? lastMonth)
                    }
                    onBlur={() => setActiveMonth(null)}
                    onKeyDown={onKeyDown}
                  />
                </svg>
                {activeMonth !== null && !dragging && (
                  <Tooltip
                    layout={layout}
                    monthIndex={activeMonth}
                    highlighted={highlighted}
                  />
                )}
              </div>
            </div>
            <p className="mt-2 text-xs text-ink-muted">
              Scroll to zoom · Drag to pan when zoomed in
            </p>
          </div>
          <Legend
            series={layout.series}
            latestLabel={layout.months[lastMonth].label}
            highlighted={highlighted}
            onSelect={(key) =>
              setHighlighted((current) => (current === key ? null : key))
            }
          />
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
