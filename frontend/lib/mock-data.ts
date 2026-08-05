/**
 * Mock data for the landing page.
 *
 * NOTE: This is placeholder data until the scrape pipeline provides real
 * postings. Keep this file as the single source for what the pages render —
 * swap the arrays below for real data later without touching the page code.
 *
 * The company list mirrors the ~42 AV companies provided by the client
 * (see document/investigation/martin_doc_0208.md) and is intentionally not
 * hard-coded into the page: update this array as the list evolves.
 */

/* ------------------------------------------------------------------ */
/* Job categories — AV tech stack taxonomy                             */
/* ------------------------------------------------------------------ */

export type Category = {
  name: string;
  jobs: number;
};

export const AV_CATEGORIES: Category[] = [
  { name: "Perception", jobs: 86 },
  { name: "Localization & Mapping", jobs: 54 },
  { name: "Planning", jobs: 61 },
  { name: "Control", jobs: 42 },
  { name: "System Integration", jobs: 73 },
  { name: "V&V & Safety", jobs: 58 },
  { name: "Simulation", jobs: 39 },
  { name: "Data Infrastructure", jobs: 47 },
];

/* ------------------------------------------------------------------ */
/* Jobs                                                               */
/* ------------------------------------------------------------------ */

export type JobStatus = "Open" | "Closed";

export type Job = {
  title: string;
  company: string;
  /** Company location country, e.g. "USA", "Germany", "China". */
  country: string;
  /** Estimated salary range in thousands USD (may be estimated per brief). */
  salaryMin: number;
  salaryMax: number;
  status: JobStatus;
  type: string;
  category: string;
};

export const MOCK_JOBS: Job[] = [
  {
    title: "Perception Engineer",
    company: "Waymo",
    country: "USA",
    salaryMin: 130,
    salaryMax: 180,
    status: "Open",
    type: "Full-time",
    category: "Perception",
  },
  {
    title: "Localization & Mapping Engineer",
    company: "Zoox",
    country: "USA",
    salaryMin: 120,
    salaryMax: 165,
    status: "Open",
    type: "Full-time",
    category: "Localization & Mapping",
  },
  {
    title: "Motion Planning Engineer",
    company: "Aurora",
    country: "USA",
    salaryMin: 125,
    salaryMax: 175,
    status: "Open",
    type: "Full-time",
    category: "Planning",
  },
  {
    title: "Controls Engineer",
    company: "Tesla",
    country: "USA",
    salaryMin: 110,
    salaryMax: 150,
    status: "Open",
    type: "Full-time",
    category: "Control",
  },
  {
    title: "Sensor Fusion Engineer",
    company: "Motional",
    country: "USA",
    salaryMin: 115,
    salaryMax: 160,
    status: "Open",
    type: "Full-time",
    category: "Perception",
  },
  {
    title: "V&V Test Engineer",
    company: "Bosch",
    country: "Germany",
    salaryMin: 85,
    salaryMax: 120,
    status: "Open",
    type: "Full-time",
    category: "V&V & Safety",
  },
  {
    title: "Simulation Engineer",
    company: "Applied Intuition",
    country: "USA",
    salaryMin: 120,
    salaryMax: 170,
    status: "Open",
    type: "Full-time",
    category: "Simulation",
  },
  {
    title: "Autonomous Driving Engineer",
    company: "Baidu Apollo",
    country: "China",
    salaryMin: 60,
    salaryMax: 90,
    status: "Open",
    type: "Full-time",
    category: "System Integration",
  },
];

export const FEATURED_JOBS: Job[] = [
  {
    title: "Senior Perception Engineer",
    company: "Waymo",
    country: "USA",
    salaryMin: 160,
    salaryMax: 220,
    status: "Open",
    type: "Full-time",
    category: "Perception",
  },
  {
    title: "Staff ML Engineer",
    company: "NVIDIA",
    country: "USA",
    salaryMin: 180,
    salaryMax: 240,
    status: "Open",
    type: "Full-time",
    category: "Perception",
  },
  {
    title: "HD Map Engineer",
    company: "Mobileye",
    country: "Israel",
    salaryMin: 110,
    salaryMax: 150,
    status: "Open",
    type: "Full-time",
    category: "Localization & Mapping",
  },
];

/* ------------------------------------------------------------------ */
/* Companies — client-provided AV company list (~42)                   */
/* ------------------------------------------------------------------ */

export type CompanyType =
  | "AV Startup"
  | "OEM"
  | "Tier 1 Supplier"
  | "Tech Giant";

export type Company = {
  name: string;
  type: CompanyType;
  country: string;
  openPositions: number;
};

/* Type/country/openPositions below are mock values — update as real
   scrape data becomes available. The company names mirror the client's
   list (see document/investigation/martin_doc_0208.md). */
export const AV_COMPANIES: Company[] = [
  { name: "Waymo", type: "AV Startup", country: "USA", openPositions: 35 },
  { name: "Zoox", type: "AV Startup", country: "USA", openPositions: 28 },
  { name: "Aurora", type: "AV Startup", country: "USA", openPositions: 22 },
  { name: "Motional", type: "AV Startup", country: "USA", openPositions: 18 },
  { name: "Pony.ai", type: "AV Startup", country: "China", openPositions: 15 },
  { name: "WeRide", type: "AV Startup", country: "China", openPositions: 12 },
  { name: "Kodiak", type: "AV Startup", country: "USA", openPositions: 9 },
  { name: "Stack AV", type: "AV Startup", country: "USA", openPositions: 8 },
  { name: "Waabi", type: "AV Startup", country: "Canada", openPositions: 14 },
  { name: "May Mobility", type: "AV Startup", country: "USA", openPositions: 7 },
  { name: "Gatik", type: "AV Startup", country: "USA", openPositions: 6 },
  { name: "Einride", type: "AV Startup", country: "Sweden", openPositions: 10 },
  { name: "Plus AI", type: "AV Startup", country: "USA", openPositions: 5 },
  { name: "QCraft", type: "AV Startup", country: "China", openPositions: 6 },
  { name: "AutoBrains", type: "AV Startup", country: "Israel", openPositions: 4 },
  { name: "DeepRoute", type: "AV Startup", country: "China", openPositions: 8 },
  { name: "Tensor / AutoX", type: "AV Startup", country: "China", openPositions: 11 },
  { name: "AImotive", type: "AV Startup", country: "Hungary", openPositions: 3 },
  { name: "Avride", type: "AV Startup", country: "USA", openPositions: 5 },
  { name: "Bot.Auto", type: "AV Startup", country: "USA", openPositions: 2 },
  { name: "42dot", type: "AV Startup", country: "South Korea", openPositions: 9 },
  { name: "Latitude AI", type: "AV Startup", country: "USA", openPositions: 7 },
  { name: "Nuro", type: "AV Startup", country: "USA", openPositions: 6 },
  { name: "Vay", type: "AV Startup", country: "Germany", openPositions: 4 },
  { name: "Wayve", type: "AV Startup", country: "UK", openPositions: 13 },
  { name: "Torc Robotics", type: "AV Startup", country: "USA", openPositions: 10 },
  { name: "Inceptio.ai", type: "AV Startup", country: "China", openPositions: 5 },
  { name: "Momenta", type: "AV Startup", country: "China", openPositions: 8 },
  { name: "ADASTEC", type: "AV Startup", country: "USA", openPositions: 2 },
  { name: "Tier IV", type: "AV Startup", country: "Japan", openPositions: 12 },
  { name: "Applied Intuition", type: "AV Startup", country: "USA", openPositions: 16 },
  { name: "GM", type: "OEM", country: "USA", openPositions: 41 },
  { name: "XPeng", type: "OEM", country: "China", openPositions: 33 },
  { name: "Woven by Toyota", type: "OEM", country: "Japan", openPositions: 19 },
  { name: "Baidu Apollo", type: "Tech Giant", country: "China", openPositions: 27 },
  { name: "Huawei", type: "Tech Giant", country: "China", openPositions: 52 },
  { name: "DiDi", type: "Tech Giant", country: "China", openPositions: 24 },
  { name: "NVIDIA", type: "Tech Giant", country: "USA", openPositions: 48 },
  { name: "Mobileye", type: "Tier 1 Supplier", country: "Israel", openPositions: 21 },
  { name: "Bosch", type: "Tier 1 Supplier", country: "Germany", openPositions: 37 },
  { name: "Horizon Robotics", type: "Tier 1 Supplier", country: "China", openPositions: 13 },
];
