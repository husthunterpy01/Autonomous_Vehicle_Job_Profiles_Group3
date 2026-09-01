import type { ReactNode } from "react";
import {
  AV_CATEGORIES,
  AV_COMPANIES,
  ALL_JOBS,
  MOCK_JOBS,
  getTopSkills,
} from "@/lib/mock-data";

/* ------------------------------------------------------------------ */
/* Floating decorative badges                                          */
/* ------------------------------------------------------------------ */

const HEX_CLIP =
  "[clip-path:polygon(25%_0%,75%_0%,100%_50%,75%_100%,25%_100%,0%_50%)]";

function Badge({
  className,
  bg,
  delay = "0s",
  children,
}: {
  className: string;
  bg: string;
  delay?: string;
  children: ReactNode;
}) {
  return (
    <div
      style={{ animationDelay: delay }}
      className={`absolute flex h-14 w-14 motion-safe:animate-[float_5s_ease-in-out_infinite] items-center justify-center ${HEX_CLIP} text-white shadow-lg transition-transform duration-300 hover:scale-110 ${bg} ${className}`}
    >
      {children}
    </div>
  );
}

/** A sparse, low-opacity hexagon outline used to texture the panel
 *  background — a handful scattered around rather than a dense tiled
 *  honeycomb, matching the reference's look. */
function HexOutline({ size, className }: { size: number; className: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={`absolute text-white/10 ${className}`}
      aria-hidden="true"
    >
      <polygon
        points="25,2 75,2 98,50 75,98 25,98 2,50"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      />
    </svg>
  );
}

const iconProps = {
  className: "h-6 w-6",
  fill: "none",
  viewBox: "0 0 24 24",
  strokeWidth: 1.8,
  stroke: "currentColor",
  "aria-hidden": true,
} as const;

function BriefcaseIcon() {
  return (
    <svg {...iconProps}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 8.25h16.5a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H3.75a1.5 1.5 0 0 1-1.5-1.5v-9a1.5 1.5 0 0 1 1.5-1.5zM8.25 8.25V6a1.5 1.5 0 0 1 1.5-1.5h4.5A1.5 1.5 0 0 1 15.75 6v2.25M2.25 13.5h19.5"
      />
    </svg>
  );
}

function PeopleIcon() {
  return (
    <svg {...iconProps}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 19.5v-1.5a4.5 4.5 0 0 0-4.5-4.5h-3A4.5 4.5 0 0 0 3 18v1.5M17.25 19.5v-1.5a4.5 4.5 0 0 0-3-4.24M13.5 4.32a3 3 0 0 1 0 5.36M9 10.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
      />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg {...iconProps}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.75 3.75h10.5a1.5 1.5 0 0 1 1.5 1.5v15l-6.75-4.5-6.75 4.5v-15a1.5 1.5 0 0 1 1.5-1.5z"
      />
    </svg>
  );
}

function TrendingUpIcon() {
  return (
    <svg {...iconProps}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.25 18 9 11.25l4.5 4.5 7.5-7.5M15.75 8.25h5.25v5.25"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Mini category trend chart, built from real AV_CATEGORIES data       */
/* ------------------------------------------------------------------ */

function CategoryChart() {
  const width = 320;
  const height = 110;
  const padding = 10;
  const maxJobs = Math.max(...AV_CATEGORIES.map((c) => c.jobs));
  const step = (width - padding * 2) / (AV_CATEGORIES.length - 1);

  const points = AV_CATEGORIES.map((c, i) => {
    const x = padding + i * step;
    const y = height - padding - (c.jobs / maxJobs) * (height - padding * 2);
    return { x, y, category: c };
  });

  const peak = points.reduce((a, b) =>
    b.category.jobs > a.category.jobs ? b : a,
  );
  const pointsAttr = points.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        aria-hidden="true"
      >
        <polyline
          points={pointsAttr}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((p) => (
          <circle
            key={p.category.name}
            cx={p.x}
            cy={p.y}
            r={p === peak ? 4 : 2.5}
            fill={p === peak ? "var(--color-primary)" : "var(--color-surface)"}
            stroke="var(--color-primary)"
            strokeWidth={1.5}
          />
        ))}
      </svg>

      {/* Tooltip callout on the peak category */}
      <div
        className="absolute -translate-x-1/2 -translate-y-full rounded-lg border border-line bg-surface px-3 py-1.5 text-xs shadow-md"
        style={{
          left: `${(peak.x / width) * 100}%`,
          top: `${(peak.y / height) * 100}%`,
        }}
      >
        <p className="font-semibold text-ink">{peak.category.name}</p>
        <p className="text-ink-secondary">{peak.category.jobs} jobs</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Dashboard preview card                                              */
/* ------------------------------------------------------------------ */

const SIDEBAR_ITEMS = ["Home", "Find Jobs", "Companies", "Saved Jobs"];

function DashboardPreview() {
  const topSkills = getTopSkills(3);
  const maxSkillJobs = topSkills[0]?.jobs ?? 1;
  const recentJobs = MOCK_JOBS.slice(0, 3);

  return (
    <div className="flex -rotate-2 overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl transition-transform duration-500 ease-out hover:rotate-0 hover:scale-[1.02]">
      {/* Sidebar */}
      <div className="hidden w-36 shrink-0 flex-col gap-1 border-r border-line bg-section p-4 sm:flex">
        <div className="mb-3 flex items-center gap-2 font-bold text-ink">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
            AV
          </span>
          <span className="text-sm">Job Finder</span>
        </div>
        {SIDEBAR_ITEMS.map((item, i) => (
          <div
            key={item}
            className={`cursor-default rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
              i === 0
                ? "bg-primary-light text-primary"
                : "text-ink-secondary hover:bg-surface hover:text-ink"
            }`}
          >
            {item}
          </div>
        ))}
      </div>

      {/* Main content */}
      <div className="flex-1 p-5">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-ink">Dashboard</p>
          <div className="flex items-center gap-2 rounded-lg border border-line px-2.5 py-1 text-xs text-ink-muted">
            Search jobs...
          </div>
        </div>

        {/* Stat tiles — real numbers from mock-data */}
        <div className="mt-4 grid grid-cols-3 gap-2">
          <div className="rounded-lg border border-line px-3 py-2">
            <p className="text-lg font-bold text-ink">{AV_COMPANIES.length}</p>
            <p className="text-[11px] text-ink-secondary">Companies</p>
          </div>
          <div className="rounded-lg border border-line px-3 py-2">
            <p className="text-lg font-bold text-ink">{ALL_JOBS.length}</p>
            <p className="text-[11px] text-ink-secondary">Open Roles</p>
          </div>
          <div className="rounded-lg border border-line px-3 py-2">
            <p className="text-lg font-bold text-ink">{AV_CATEGORIES.length}</p>
            <p className="text-[11px] text-ink-secondary">Categories</p>
          </div>
        </div>

        {/* Chart */}
        <div className="mt-4">
          <p className="mb-16 text-xs font-medium text-ink-secondary">
            Jobs by Category
          </p>
          <CategoryChart />
        </div>

        {/* Recently posted + top skills */}
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-medium text-ink-secondary">
              Recently Posted
            </p>
            <ul className="space-y-1.5">
              {recentJobs.map((job) => (
                <li key={job.id} className="truncate text-xs text-ink">
                  {job.title}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-ink-secondary">
              Top Skills
            </p>
            <ul className="space-y-1.5">
              {topSkills.map((skill) => (
                <li key={skill.name}>
                  <div className="mb-0.5 flex justify-between text-xs text-ink">
                    <span className="truncate">{skill.name}</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-line">
                    <div
                      className="h-1.5 rounded-full bg-primary"
                      style={{
                        width: `${(skill.jobs / maxSkillJobs) * 100}%`,
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Demo user chip — matches the mock login account, not a real person */}
        <div className="mt-4 flex items-center gap-2 border-t border-line pt-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-light text-xs font-bold text-primary">
            D
          </span>
          <div>
            <p className="text-xs font-medium text-ink">Demo User</p>
            <p className="text-[11px] text-ink-muted">demo@avjobfinder.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Panel                                                                */
/* ------------------------------------------------------------------ */

export default function LoginShowcase() {
  return (
    <div className="relative hidden overflow-hidden bg-primary p-12 lg:flex lg:flex-col lg:justify-center">
      {/* Scattered hexagon outline texture — sparse, not a tiled honeycomb */}
      <HexOutline size={180} className="-left-10 -top-10" />
      <HexOutline size={120} className="right-16 top-10" />
      <HexOutline size={140} className="-right-16 bottom-24" />
      <HexOutline size={100} className="bottom-10 left-20" />
      <HexOutline size={90} className="right-1/3 top-1/2" />

      <Badge className="left-10 top-16" bg="bg-emerald-500" delay="0s">
        <BriefcaseIcon />
      </Badge>
      <Badge
        className="right-10 top-24"
        bg="bg-white/15 backdrop-blur-sm"
        delay="0.6s"
      >
        <PeopleIcon />
      </Badge>
      <Badge className="bottom-40 left-6" bg="bg-amber-400" delay="1.2s">
        <BookmarkIcon />
      </Badge>
      <Badge className="bottom-24 right-8" bg="bg-sky-500" delay="1.8s">
        <TrendingUpIcon />
      </Badge>

      <div className="relative z-10 mx-auto w-full max-w-md">
        <DashboardPreview />

        <blockquote className="mt-8 text-white/90">
          <p className="text-lg font-medium">
            &ldquo;Built by AV engineering students to make job hunting in this
            industry easier.&rdquo;
          </p>
          <p className="mt-2 text-sm text-white/70">
            &mdash; The AV Job Finder Team
          </p>
        </blockquote>
      </div>
    </div>
  );
}
