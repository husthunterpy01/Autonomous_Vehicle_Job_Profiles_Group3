import { JOB_TREND_DATA, type JobTrendPoint } from "@/lib/mock-data";

const CHART_WIDTH = 720;
const CHART_HEIGHT = 260;
const PADDING_LEFT = 54;
const PADDING_RIGHT = 24;
const PADDING_TOP = 24;
const PADDING_BOTTOM = 44;

type JobTrendChartProps = {
  data?: JobTrendPoint[];
};

export default function JobTrendChart({
  data = JOB_TREND_DATA,
}: JobTrendChartProps) {
  if (data.length < 2) {
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

  const values = data.map((point) => point.jobCount);
  const latest = data[data.length - 1];
  const previous = data[data.length - 2];
  
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = Math.max(maxValue - minValue, 20);
  const axisPadding = Math.max(10, Math.ceil(valueRange * 0.2));
  
  const yMin = Math.max(
    0,
    Math.floor((minValue - axisPadding) / 10) * 10,
  );
  const yMax = Math.ceil((maxValue + axisPadding) / 10) * 10;
  
  const plotWidth = CHART_WIDTH - PADDING_LEFT - PADDING_RIGHT;
  const plotHeight = CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM;

  const points = data.map((point, index) => {
    const x = PADDING_LEFT + (index / Math.max(data.length - 1, 1)) * plotWidth;
    const y =
      PADDING_TOP +
      plotHeight -
      ((point.jobCount - yMin) / (yMax - yMin)) * plotHeight;
  
    return { ...point, x, y };
  });

  const polylinePoints = points.map(({ x, y }) => `${x},${y}`).join(" ");
  const change =
    ((latest.jobCount - previous.jobCount) / previous.jobCount) * 100;

  return (
    <section className="bg-surface py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-sm md:p-8">
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
                Total AV job volume across the most recent six monthly periods.
              </p>
            </div>

            <div className="sm:text-right">
              <p className="text-3xl font-bold text-ink">{latest.jobCount}</p>
              <p className="text-sm text-ink-secondary">
                jobs in {latest.period}
                <span className="ml-2 font-semibold text-primary">
                  {change >= 0 ? "+" : ""}
                  {change.toFixed(1)}%
                </span>
              </p>
            </div>
          </div>

          <div className="mt-8 overflow-x-auto">
            <svg
              viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
              role="img"
              aria-labelledby="job-trend-title job-trend-description"
              className="h-auto w-full min-w-[620px] text-primary"
            >
              <title id="job-trend-title">
                Autonomous vehicle job volume trend
              </title>
              <desc id="job-trend-description">
                Prototype line chart showing total AV job counts for March
                through August.
              </desc>

              {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                const y = PADDING_TOP + plotHeight - ratio * plotHeight;
                const label = Math.round(yMin + (yMax - yMin) * ratio);

                return (
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
                );
              })}

              <polyline
                points={polylinePoints}
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {points.map((point) => (
                <g key={point.period}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r="5"
                    fill="white"
                    stroke="currentColor"
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
                </g>
              ))}
            </svg>
          </div>

          <p className="mt-3 text-xs text-ink-muted">
            This Sprint 2 chart uses prototype data and is ready to be wired to
            the scraper/aggregation API when that endpoint becomes available.
          </p>
        </div>
      </div>
    </section>
  );
}
