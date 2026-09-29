"use client";

import {
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  type RefObject,
} from "react";
import {
  CHART,
  layoutSkillTrend,
  nearestMonthIndex,
  scrollAfterZoom,
  type SkillTrendLayout,
  type TrendSeries,
} from "@/lib/skill-trend-chart";
import type { SkillTrends } from "@/lib/services/trend";

export type SkillTrendsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "success"; data: SkillTrends };

// Zoom scales both axes; the frame around the plot keeps its size.
export const ZOOM_LEVELS = [1, 1.5, 2, 3, 4] as const;
// Room for the count labels and the rotated "Job postings" title.
const Y_AXIS_WIDTH = 72;
// Room for the month labels and the "Month" title.
const X_AXIS_HEIGHT = 48;
// Used until the frame is measured (and in tests, which have no layout).
const FALLBACK_PLOT_WIDTH = 640;
const GRID = "#eef0f4";
const SURFACE = "#ffffff";

const SKILL_TYPE_LABELS: Record<string, string> = {
  programming_language: "Language",
  framework: "Framework",
  tool: "Tool",
  domain_concept: "Domain concept",
  certification: "Certification",
};

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

/* Names only: the job counts live in the month tooltip, so the legend
   stays a key rather than a second data table. */
function Legend({
  series,
  highlighted,
  onSelect,
}: {
  series: TrendSeries[];
  highlighted: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <aside className="border-t border-line p-4 lg:w-72 lg:shrink-0 lg:border-t-0 lg:border-l">
      <p className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
        Skills
      </p>
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
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
        Click a skill to highlight it in the chart. Hover over a month to see
        each skill&apos;s job count.
      </p>
    </aside>
  );
}

function ZoomControls({
  level,
  onLevel,
}: {
  level: number;
  onLevel: (level: number) => void;
}) {
  const button =
    "rounded-md border border-line px-2.5 py-1 text-sm text-ink-secondary transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40";
  const last = ZOOM_LEVELS.length - 1;
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
          onClick={() => onLevel(level - 1)}
          disabled={level === 0}
        >
          −
        </button>
        <span className="w-12 text-center text-sm text-ink-secondary">
          {ZOOM_LEVELS[level] * 100}%
        </span>
        <button
          type="button"
          className={button}
          aria-label="Zoom in"
          onClick={() => onLevel(level + 1)}
          disabled={level === last}
        >
          +
        </button>
      </div>
      <button
        type="button"
        className={button}
        aria-label="Reset zoom"
        onClick={() => onLevel(0)}
        disabled={level === 0}
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
  x,
  viewWidth,
}: {
  layout: SkillTrendLayout;
  monthIndex: number;
  highlighted: string | null;
  /** The month's position in the visible frame, in pixels. */
  x: number;
  viewWidth: number;
}) {
  const month = layout.months[monthIndex];
  const rows = layout.series
    .map((s) => ({ s, count: s.points[monthIndex].jobCount }))
    .sort((a, b) => b.count - a.count);
  // Sits beside the month line, on whichever side has more room.
  const alignRight = x > viewWidth * 0.6;
  return (
    <div
      role="status"
      className="pointer-events-none absolute top-2 z-10 min-w-[190px] rounded-lg border border-line bg-surface p-3 text-sm shadow-md"
      style={
        alignRight
          ? { right: viewWidth - x + 12 }
          : { left: Math.max(x, 0) + 12 }
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

/* Skills down, months across, like the chart. With many months the months
   scroll while the skill column stays pinned, and the table opens on the
   latest month. Plain numbers keep the columns narrow and easy to compare;
   the note under the chart says they are job postings. */
function SkillTable({ layout }: { layout: SkillTrendLayout }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  // The inset shadow draws the divider: a border on a sticky cell would
  // scroll away with the collapsed table borders.
  const pinned =
    "sticky left-0 z-10 bg-surface py-2 pr-4 text-left whitespace-nowrap shadow-[inset_-1px_0_0_var(--color-line)]";
  const count = "py-2 pl-4 text-right whitespace-nowrap tabular-nums";
  return (
    <details
      className="mt-4"
      onToggle={(event) => {
        const el = scrollRef.current;
        if (event.currentTarget.open && el) el.scrollLeft = el.scrollWidth;
      }}
    >
      <summary className="cursor-pointer text-sm font-medium text-primary">
        Show as table
      </summary>
      <div
        ref={scrollRef}
        data-testid="skill-table-scroll"
        className="mt-3 overflow-x-auto"
      >
        <table className="min-w-full text-sm">
          <caption className="sr-only">
            Job postings per skill and month
          </caption>
          <thead>
            <tr className="border-b border-line text-ink-secondary">
              <th scope="col" className={`${pinned} font-medium`}>
                Skill
              </th>
              {layout.months.map((m) => (
                <th key={m.key} scope="col" className={`${count} font-medium`}>
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {layout.series.map((s) => (
              <tr key={s.key} className="border-b border-line last:border-0">
                <th scope="row" className={`${pinned} font-medium text-ink`}>
                  {s.name}
                </th>
                {s.points.map((p) => (
                  <td
                    key={p.monthKey}
                    className={`${count} text-ink-secondary`}
                  >
                    {p.jobCount.toLocaleString("en-US")}
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

/* The plot frame's width at 100%, following the card as it resizes. */
function usePlotWidth(ref: RefObject<HTMLDivElement | null>): number {
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setWidth(Math.floor(el.clientWidth) - Y_AXIS_WIDTH);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return width > 0 ? width : FALLBACK_PLOT_WIDTH;
}

/* Count labels and the axis title, pinned left of the plot. The labels
   follow the plot as it scrolls up and down. */
function YAxis({
  layout,
  scrollTop,
}: {
  layout: SkillTrendLayout;
  scrollTop: number;
}) {
  const middle = CHART.height / 2;
  return (
    <svg width={Y_AXIS_WIDTH} height={CHART.height} className="shrink-0">
      {layout.yTicks.map((tick) => (
        <text
          key={tick.value}
          x={Y_AXIS_WIDTH - 8}
          y={tick.y - scrollTop}
          textAnchor="end"
          dominantBaseline="middle"
          className="fill-ink-muted text-xs"
        >
          {tick.value.toLocaleString("en-US")}
        </text>
      ))}
      <text
        x={14}
        y={middle}
        textAnchor="middle"
        transform={`rotate(-90 14 ${middle})`}
        className="fill-ink-secondary text-xs font-medium"
      >
        Job postings
      </text>
    </svg>
  );
}

/* Month labels and the axis title, pinned below the plot. The labels
   follow the plot as it scrolls left and right. */
function XAxis({
  layout,
  scrollLeft,
}: {
  layout: SkillTrendLayout;
  scrollLeft: number;
}) {
  return (
    <div className="flex">
      <div className="shrink-0" style={{ width: Y_AXIS_WIDTH }} />
      <svg height={X_AXIS_HEIGHT} className="min-w-0 flex-1">
        {layout.months
          .filter((m) => m.showLabel)
          .map((m) => (
            <text
              key={m.key}
              x={m.x - scrollLeft}
              y={16}
              textAnchor="middle"
              className="fill-ink-secondary text-xs"
            >
              {m.label}
            </text>
          ))}
        <text
          x="50%"
          y={X_AXIS_HEIGHT - 6}
          textAnchor="middle"
          className="fill-ink-secondary text-xs font-medium"
        >
          Month
        </text>
      </svg>
    </div>
  );
}

function TrendChart({ data }: { data: SkillTrends }) {
  const frameRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const viewWidth = usePlotWidth(frameRef);
  const [level, setLevel] = useState(0);
  const zoom = ZOOM_LEVELS[level];
  const zoomed = level > 0;
  // Hovering and highlighting re-render without recomputing the geometry.
  const layout = useMemo(
    () =>
      layoutSkillTrend(data, {
        width: viewWidth * zoom,
        height: CHART.height * zoom,
        zoom,
      }),
    [data, viewWidth, zoom],
  );
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [activeMonth, setActiveMonth] = useState<number | null>(null);
  const [scroll, setScroll] = useState({ left: 0, top: 0 });
  const [dragging, setDragging] = useState(false);
  // The view before a zoom, to place the scroll once the plot has resized.
  const pendingZoom = useRef<{
    left: number;
    top: number;
    width: number;
    ratio: number;
  } | null>(null);
  const dragRef = useRef<{
    x: number;
    y: number;
    left: number;
    top: number;
  } | null>(null);
  const lastMonth = layout.months.length - 1;

  const changeLevel = (next: number) => {
    const el = scrollRef.current;
    if (!el || next === level) return;
    pendingZoom.current = {
      left: el.scrollLeft,
      top: el.scrollTop,
      width: el.clientWidth || viewWidth,
      ratio: ZOOM_LEVELS[next] / zoom,
    };
    setLevel(next);
  };

  // Once the resized plot is in the DOM, before the browser paints.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    const before = pendingZoom.current;
    if (!el || !before) return;
    pendingZoom.current = null;
    const target = scrollAfterZoom(
      before,
      { before: before.width, after: el.clientWidth || viewWidth },
      before.ratio,
    );
    el.scrollLeft = target.left;
    el.scrollTop = target.top;
    setScroll({ left: el.scrollLeft, top: el.scrollTop });
  }, [level, viewWidth]);

  // Touch and trackpads scroll natively; a mouse can also drag to pan.
  const onPanStart = (event: PointerEvent<HTMLDivElement>) => {
    const el = scrollRef.current;
    if (!el || !zoomed || event.pointerType !== "mouse" || event.button !== 0)
      return;
    dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      left: el.scrollLeft,
      top: el.scrollTop,
    };
    el.setPointerCapture?.(event.pointerId);
    setDragging(true);
  };
  const onPanMove = (event: PointerEvent<HTMLDivElement>) => {
    const el = scrollRef.current;
    const drag = dragRef.current;
    if (!el || !drag) return;
    el.scrollLeft = drag.left - (event.clientX - drag.x);
    el.scrollTop = drag.top - (event.clientY - drag.y);
  };
  const onPanEnd = () => {
    dragRef.current = null;
    setDragging(false);
  };

  const onHover = (event: PointerEvent<SVGRectElement>) => {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) return;
    const x = event.clientX - svg.getBoundingClientRect().left;
    setActiveMonth(nearestMonthIndex(layout, x));
  };

  // From the keyboard, a month scrolled out of view is brought back.
  const showMonth = (index: number) => {
    setActiveMonth(index);
    const el = scrollRef.current;
    if (!el || !zoomed) return;
    const x = layout.months[index].x;
    if (x < el.scrollLeft || x > el.scrollLeft + el.clientWidth) {
      el.scrollLeft = x - el.clientWidth / 2;
    }
  };

  const onKeyDown = (event: KeyboardEvent<SVGRectElement>) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      const step = event.key === "ArrowLeft" ? -1 : 1;
      showMonth(
        Math.min(lastMonth, Math.max(0, (activeMonth ?? lastMonth) + step)),
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

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <ZoomControls level={level} onLevel={changeLevel} />
      </div>
      <div className="overflow-hidden rounded-xl border border-line">
        <div className="flex flex-col lg:flex-row">
          <div className="min-w-0 flex-1 p-4">
            <div ref={frameRef}>
              <div className="flex">
                <YAxis layout={layout} scrollTop={scroll.top} />
                {/* A fixed frame: zooming grows the plot inside it, and the
                    plot scrolls within it. */}
                <div
                  className="relative min-w-0 flex-1"
                  style={{ height: CHART.height }}
                >
                  <div
                    ref={scrollRef}
                    data-testid="chart-scroll"
                    className={`absolute inset-0 ${
                      zoomed
                        ? `overflow-auto ${dragging ? "cursor-grabbing" : "cursor-grab"}`
                        : "overflow-hidden"
                    }`}
                    onScroll={(event) =>
                      setScroll({
                        left: event.currentTarget.scrollLeft,
                        top: event.currentTarget.scrollTop,
                      })
                    }
                    onPointerDown={onPanStart}
                    onPointerMove={onPanMove}
                    onPointerUp={onPanEnd}
                    onPointerCancel={onPanEnd}
                  >
                    <svg
                      data-testid="chart-plot"
                      width={layout.width}
                      height={layout.height}
                      className="block select-none"
                      role="group"
                      aria-label={`Job postings per month for ${layout.series.map((s) => s.name).join(", ")}`}
                    >
                      {layout.yTicks.map((tick) => (
                        <line
                          key={tick.value}
                          x1={0}
                          x2={layout.width}
                          y1={tick.y}
                          y2={tick.y}
                          stroke={GRID}
                          strokeWidth={1}
                        />
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
                        height={layout.height}
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
                  </div>
                  {activeMonth !== null && !dragging && (
                    <Tooltip
                      layout={layout}
                      monthIndex={activeMonth}
                      highlighted={highlighted}
                      x={layout.months[activeMonth].x - scroll.left}
                      viewWidth={viewWidth}
                    />
                  )}
                </div>
              </div>
              <XAxis layout={layout} scrollLeft={scroll.left} />
            </div>
            <p className="mt-2 text-xs text-ink-muted">
              Zoom with + and −, then scroll or drag inside the chart to see the
              other counts and months.
            </p>
          </div>
          <Legend
            series={layout.series}
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
