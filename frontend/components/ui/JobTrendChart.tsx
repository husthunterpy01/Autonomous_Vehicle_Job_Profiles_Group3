"use client";

import { useState } from "react";
import { JOB_TREND_DATA, type JobTrendPoint } from "@/lib/mock-data";

const CHART_WIDTH = 720;
const CHART_HEIGHT = 260;
const MIN_RENDERED_WIDTH = 620;

const PADDING_LEFT = 54;
const PADDING_RIGHT = 24;
const PADDING_TOP = 24;
const PADDING_BOTTOM = 44;

const GRID_RATIOS = [0, 0.25, 0.5, 0.75, 1];

const TOOLTIP_WIDTH = 110;
const TOOLTIP_HEIGHT = 44;

const RANGE_OPTIONS = [
  { label: "3M", months: 3 },
  { label: "6M", months: 6 },
] as const;

const MIN_ZOOM = 0.75;
const MAX_ZOOM = 1.75;
const ZOOM_STEP = 0.25;
const DEFAULT_ZOOM = 1;

type JobTrendChartProps = {
  data?: readonly JobTrendPoint[];
};

type ChartPoint = JobTrendPoint & {
  x: number;
  y: number;
};

type GridLine = {
  ratio: number;
  y: number;
  label: number;
};

type ChartModel = {
  first: JobTrendPoint;
  latest: JobTrendPoint;
  change: number;
  points: ChartPoint[];
  polylinePoints: string;
  gridLines: GridLine[];
};

/* ------------------------------------------------------------------ */
/* Chart data preparation                                              */
/* ------------------------------------------------------------------ */

function buildChartModel(data: readonly JobTrendPoint[]): ChartModel {
  const values = data.map((point) => point.jobCount);

  const first = data[0];
  const latest = data[data.length - 1];

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  const valueRange = Math.max(maxValue - minValue, 20);
  const axisPadding = Math.max(10, Math.ceil(valueRange * 0.2));

  const yMin = Math.max(0, Math.floor((minValue - axisPadding) / 10) * 10);

  const yMax = Math.ceil((maxValue + axisPadding) / 10) * 10;

  const plotWidth = CHART_WIDTH - PADDING_LEFT - PADDING_RIGHT;
  const plotHeight = CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM;

  const points = data.map((point, index) => {
    const x = PADDING_LEFT + (index / Math.max(data.length - 1, 1)) * plotWidth;

    const y =
      PADDING_TOP +
      plotHeight -
      ((point.jobCount - yMin) / (yMax - yMin)) * plotHeight;

    return {
      ...point,
      x,
      y,
    };
  });

  const gridLines = GRID_RATIOS.map((ratio) => ({
    ratio,
    y: PADDING_TOP + plotHeight - ratio * plotHeight,
    label: Math.round(yMin + (yMax - yMin) * ratio),
  }));

  const polylinePoints = points.map(({ x, y }) => `${x},${y}`).join(" ");

  const change =
    first.jobCount === 0
      ? 0
      : ((latest.jobCount - first.jobCount) / first.jobCount) * 100;

  return {
    first,
    latest,
    change,
    points,
    polylinePoints,
    gridLines,
  };
}

/* ------------------------------------------------------------------ */
/* Subcomponents                                                       */
/* ------------------------------------------------------------------ */

function EmptyTrendState() {
  return (
    <section className="bg-surface py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-sm md:p-8">
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            Job Market <span className="text-primary">Trend</span>
          </h2>

          <p className="mt-3 text-sm text-ink-secondary">
            Insufficient dated data is available to show a reliable job-volume
            trend yet.
          </p>
        </div>
      </div>
    </section>
  );
}

function TrendHeader({
  first,
  latest,
  change,
  periodCount,
}: {
  first: JobTrendPoint;
  latest: JobTrendPoint;
  change: number;
  periodCount: number;
}) {
  const changeLabel = `${change >= 0 ? "+" : ""}${change.toFixed(1)}%`;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            Job Market <span className="text-primary">Trend</span>
          </h2>

          <span className="rounded-full bg-primary-light px-2.5 py-1 text-xs font-semibold text-primary">
            Prototype data
          </span>
        </div>

        <p className="mt-2 text-sm text-ink-secondary">
          Total AV job volume across {periodCount} monthly prototype snapshots,{" "}
          {first.period}–{latest.period}.
        </p>
      </div>

      <div className="sm:text-right">
        <p className="text-3xl font-bold text-ink">{latest.jobCount}</p>

        <p className="text-sm text-ink-secondary">
          jobs in {latest.period}{" "}
          <span className="ml-2 font-semibold text-primary">
            {changeLabel} over selected range
          </span>
        </p>
      </div>
    </div>
  );
}

function ChartControls({
  selectedMonths,
  zoom,
  onRangeChange,
  onZoomIn,
  onZoomOut,
}: {
  selectedMonths: number;
  zoom: number;
  onRangeChange: (months: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}) {
  return (
    <div className="mt-6 flex flex-wrap items-end justify-between gap-4 border-t border-line pt-5">
      <fieldset>
        <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Time range
        </legend>

        <div className="inline-flex rounded-lg border border-line bg-background p-1">
          {RANGE_OPTIONS.map((option) => {
            const selected = selectedMonths === option.months;

            return (
              <button
                key={option.months}
                type="button"
                aria-label={"Show the latest " + option.months + " months"}
                aria-pressed={selected}
                onClick={() => onRangeChange(option.months)}
                className={[
                  "rounded-md px-3 py-1.5 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                  selected
                    ? "bg-primary text-white"
                    : "text-ink-secondary hover:bg-surface hover:text-ink",
                ].join(" ")}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Chart zoom
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            aria-label="Zoom out on job trend chart"
            onClick={onZoomOut}
            disabled={zoom <= MIN_ZOOM}
            className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-semibold text-ink-secondary transition-colors hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-40"
          >
            − Zoom Out
          </button>

          <output
            aria-live="polite"
            aria-label="Current chart zoom"
            className="min-w-12 text-center text-sm font-medium text-ink-muted"
          >
            {Math.round(zoom * 100)}%
          </output>

          <button
            type="button"
            aria-label="Zoom in on job trend chart"
            onClick={onZoomIn}
            disabled={zoom >= MAX_ZOOM}
            className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-semibold text-ink-secondary transition-colors hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-40"
          >
            + Zoom In
          </button>
        </div>
      </div>
    </div>
  );
}

function ChartGrid({ gridLines }: { gridLines: GridLine[] }) {
  const gridElements = gridLines.map(({ ratio, y, label }) => (
    <g key={ratio}>
      <line
        x1={PADDING_LEFT}
        x2={CHART_WIDTH - PADDING_RIGHT}
        y1={y}
        y2={y}
        className="stroke-line"
        strokeWidth="1"
      />

      <text
        x={PADDING_LEFT - 12}
        y={y + 4}
        textAnchor="end"
        className="fill-ink-muted text-[11px]"
      >
        {label}
      </text>
    </g>
  ));

  return <>{gridElements}</>;
}

function TrendPoint({ point }: { point: ChartPoint }) {
  const tooltipX = Math.min(
    Math.max(point.x - TOOLTIP_WIDTH / 2, 4),
    CHART_WIDTH - TOOLTIP_WIDTH - 4,
  );

  const tooltipY = Math.max(point.y - TOOLTIP_HEIGHT - 14, 4);

  return (
    <g
      tabIndex={0}
      aria-label={`${point.period}: ${point.jobCount} jobs`}
      className="group cursor-pointer outline-none"
    >
      <circle
        cx={point.x}
        cy={point.y}
        r="5"
        className="fill-white stroke-primary transition-all group-hover:fill-primary group-focus:fill-primary"
        strokeWidth="3"
      />

      <text
        x={point.x}
        y={CHART_HEIGHT - 14}
        textAnchor="middle"
        className="fill-ink-secondary text-xs"
      >
        {point.period}
      </text>

      <g
        className="pointer-events-none opacity-0 transition-opacity group-hover:opacity-100 group-focus:opacity-100"
        aria-hidden="true"
      >
        <rect
          x={tooltipX}
          y={tooltipY}
          width={TOOLTIP_WIDTH}
          height={TOOLTIP_HEIGHT}
          rx="8"
          className="fill-ink"
        />

        <text
          x={tooltipX + TOOLTIP_WIDTH / 2}
          y={tooltipY + 17}
          textAnchor="middle"
          className="fill-white text-[11px] font-semibold"
        >
          {point.period}
        </text>

        <text
          x={tooltipX + TOOLTIP_WIDTH / 2}
          y={tooltipY + 33}
          textAnchor="middle"
          className="fill-white text-[11px]"
        >
          {point.jobCount} jobs
        </text>
      </g>
    </g>
  );
}

function TrendPlot({
  points,
  polylinePoints,
  gridLines,
  startPeriod,
  endPeriod,
  change,
  zoom,
}: {
  points: ChartPoint[];
  polylinePoints: string;
  gridLines: GridLine[];
  startPeriod: string;
  endPeriod: string;
  change: number;
  zoom: number;
}) {
  const pointElements = points.map((point) => (
    <TrendPoint key={point.period} point={point} />
  ));
  const changeLabel = (change >= 0 ? "+" : "") + change.toFixed(1) + "%";

  return (
    <div className="mt-5 max-w-full overflow-x-auto overscroll-x-contain">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-labelledby="job-trend-title job-trend-description"
        className="block h-auto max-w-none text-primary"
        style={{
          width: zoom * 100 + "%",
          minWidth: MIN_RENDERED_WIDTH * zoom + "px",
        }}
      >
        <title id="job-trend-title">Autonomous vehicle job volume trend</title>

        <desc id="job-trend-description">
          Interactive prototype line chart showing {points.length} monthly
          snapshots from {startPeriod} through {endPeriod}, with a {changeLabel}{" "}
          change over the selected range. Hover or focus on a data point to see
          its job count.
        </desc>

        <ChartGrid gridLines={gridLines} />

        <polyline
          points={polylinePoints}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {pointElements}
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function JobTrendChart({
  data = JOB_TREND_DATA,
}: JobTrendChartProps) {
  const [selectedMonths, setSelectedMonths] = useState<number>(
    RANGE_OPTIONS[RANGE_OPTIONS.length - 1].months,
  );
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

  if (data.length < 2) {
    return <EmptyTrendState />;
  }

  const visibleData = data.slice(-Math.min(selectedMonths, data.length));
  const { first, latest, change, points, polylinePoints, gridLines } =
    buildChartModel(visibleData);

  const zoomIn = () => {
    setZoom((currentZoom) => Math.min(MAX_ZOOM, currentZoom + ZOOM_STEP));
  };

  const zoomOut = () => {
    setZoom((currentZoom) => Math.max(MIN_ZOOM, currentZoom - ZOOM_STEP));
  };

  return (
    <section className="bg-surface py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="min-w-0 rounded-2xl border border-line bg-surface p-6 shadow-sm md:p-8">
          <TrendHeader
            first={first}
            latest={latest}
            change={change}
            periodCount={visibleData.length}
          />

          <ChartControls
            selectedMonths={selectedMonths}
            zoom={zoom}
            onRangeChange={setSelectedMonths}
            onZoomIn={zoomIn}
            onZoomOut={zoomOut}
          />

          <TrendPlot
            points={points}
            polylinePoints={polylinePoints}
            gridLines={gridLines}
            startPeriod={first.period}
            endPeriod={latest.period}
            change={change}
            zoom={zoom}
          />

          <p className="mt-3 text-xs text-ink-muted">
            Prototype values are shown until aggregated scraper history is
            available.
          </p>
        </div>
      </div>
    </section>
  );
}
