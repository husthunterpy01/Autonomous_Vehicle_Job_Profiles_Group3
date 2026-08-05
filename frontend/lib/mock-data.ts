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

export const AV_COMPANIES: string[] = [
  "42dot",
  "ADASTEC",
  "Aurora",
  "AutoBrains",
  "Baidu Apollo",
  "Applied Intuition",
  "AImotive",
  "Avride",
  "Bot.Auto",
  "Bosch",
  "DeepRoute",
  "DiDi",
  "May Mobility",
  "Gatik",
  "Inceptio.ai",
  "Horizon Robotics",
  "Huawei",
  "Kodiak",
  "Einride",
  "Latitude AI",
  "GM",
  "Mobileye",
  "Motional",
  "Momenta",
  "Nuro",
  "NVIDIA",
  "Pony.ai",
  "Plus AI",
  "QCraft",
  "Stack AV",
  "Tensor / AutoX",
  "Torc Robotics",
  "Tier IV",
  "Waabi",
  "Waymo",
  "Wayve",
  "WeRide",
  "Woven by Toyota",
  "Vay",
  "XPeng",
  "Zoox",
];
