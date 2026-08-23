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

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/* ------------------------------------------------------------------ */
/* Job categories — AV tech stack taxonomy                             */
/* ------------------------------------------------------------------ */

export type Category = {
  name: string;
  jobs: number;
};

export const AV_CATEGORIES: Category[] = [
  { name: "Sensing", jobs: 62 },
  { name: "Localization", jobs: 54 },
  { name: "Perception", jobs: 86 },
  { name: "Planning", jobs: 61 },
  { name: "Control", jobs: 42 },
  { name: "System", jobs: 73 },
  { name: "Vehicle Interface", jobs: 25 },
  { name: "Map", jobs: 38 },
];

export type CategoryName = (typeof AV_CATEGORIES)[number]["name"];

/* ------------------------------------------------------------------ */
/* Companies — client-provided AV company list (~42)                   */
/* ------------------------------------------------------------------ */

export type CompanyType =
  "AV Startup" | "OEM" | "Tier 1 Supplier" | "Tech Giant";

export type Company = {
  id: string;
  name: string;
  type: CompanyType;
  country: string;
  openPositions: number;
  /** One-line company description. Only filled in for companies that
   *  currently have a mock job attached (see Job Detail's company summary) —
   *  optional so the rest of the list doesn't need placeholder text yet. */
  about?: string;
  /** Employee-count bucket, same coverage caveat as `about`. */
  size?: string;
  /** Careers page URL, from the investigation doc's confirmed sources
   *  (document/investigation/martin_doc_0208.md). Left unset for companies
   *  the doc marks as "needs direct inspection" / unconfirmed, rather than
   *  guessing a URL. */
  careersUrl?: string;
};

/* Type/country/openPositions below are mock values — update as real
   scrape data becomes available. The company names mirror the client's
   list (see document/investigation/martin_doc_0208.md). */
export const AV_COMPANIES: Company[] = [
  {
    id: "waymo",
    name: "Waymo",
    type: "AV Startup",
    country: "USA",
    openPositions: 35,
    about:
      "Waymo is Alphabet's autonomous driving technology company, operating a driverless ride-hailing service across multiple US cities.",
    size: "1,001–5,000 employees",
    careersUrl: "https://careers.withwaymo.com/",
  },
  {
    id: "zoox",
    name: "Zoox",
    type: "AV Startup",
    country: "USA",
    openPositions: 28,
    about:
      "Zoox, an Amazon company, is building a purpose-built autonomous robotaxi designed from the ground up for self-driving, without a traditional steering wheel or pedals.",
    size: "1,001–5,000 employees",
    careersUrl: "https://zoox.com/careers",
  },
  {
    id: "aurora",
    name: "Aurora",
    type: "AV Startup",
    country: "USA",
    openPositions: 22,
    about:
      "Aurora Innovation develops self-driving technology for commercial trucking, aiming to bring driverless freight to highways across the US.",
    size: "1,001–5,000 employees",
    careersUrl: "https://aurora.tech/careers",
  },
  {
    id: "motional",
    name: "Motional",
    type: "AV Startup",
    country: "USA",
    openPositions: 18,
    about:
      "Motional is a robotaxi joint venture between Hyundai and Aptiv, developing SAE Level 4 autonomous vehicles for ride-hailing.",
    size: "1,001–5,000 employees",
    careersUrl: "https://boards.greenhouse.io/motional",
  },
  {
    id: "pony-ai",
    name: "Pony.ai",
    type: "AV Startup",
    country: "China",
    openPositions: 15,
    careersUrl: "https://careers.pony.ai/",
  },
  {
    id: "weride",
    name: "WeRide",
    type: "AV Startup",
    country: "China",
    openPositions: 12,
  },
  {
    id: "kodiak",
    name: "Kodiak",
    type: "AV Startup",
    country: "USA",
    openPositions: 9,
    careersUrl: "https://boards.greenhouse.io/kodiak",
  },
  {
    id: "stack-av",
    name: "Stack AV",
    type: "AV Startup",
    country: "USA",
    openPositions: 8,
    careersUrl: "https://boards.greenhouse.io/stackav",
  },
  {
    id: "waabi",
    name: "Waabi",
    type: "AV Startup",
    country: "Canada",
    openPositions: 14,
    careersUrl: "https://jobs.lever.co/waabi",
  },
  {
    id: "may-mobility",
    name: "May Mobility",
    type: "AV Startup",
    country: "USA",
    openPositions: 7,
    careersUrl: "https://boards.greenhouse.io/maymobility",
  },
  {
    id: "gatik",
    name: "Gatik",
    type: "AV Startup",
    country: "USA",
    openPositions: 6,
    careersUrl: "https://archive.gatik.ai/careers/",
  },
  {
    id: "einride",
    name: "Einride",
    type: "AV Startup",
    country: "Sweden",
    openPositions: 10,
  },
  {
    id: "plus-ai",
    name: "Plus AI",
    type: "AV Startup",
    country: "USA",
    openPositions: 5,
    careersUrl: "https://www.plus.ai/",
  },
  {
    id: "qcraft",
    name: "QCraft",
    type: "AV Startup",
    country: "China",
    openPositions: 6,
  },
  {
    id: "autobrains",
    name: "AutoBrains",
    type: "AV Startup",
    country: "Israel",
    openPositions: 4,
    careersUrl: "https://autobrains.ai/life-at-autobrains/",
  },
  {
    id: "deeproute",
    name: "DeepRoute",
    type: "AV Startup",
    country: "China",
    openPositions: 8,
  },
  {
    id: "tensor-autox",
    name: "Tensor / AutoX",
    type: "AV Startup",
    country: "China",
    openPositions: 11,
    careersUrl: "https://www.tensor.auto/careers",
  },
  {
    id: "aimotive",
    name: "AImotive",
    type: "AV Startup",
    country: "Hungary",
    openPositions: 3,
  },
  {
    id: "avride",
    name: "Avride",
    type: "AV Startup",
    country: "USA",
    openPositions: 5,
    careersUrl: "https://boards.greenhouse.io/avride",
  },
  {
    id: "bot-auto",
    name: "Bot.Auto",
    type: "AV Startup",
    country: "USA",
    openPositions: 2,
    careersUrl: "https://boards.greenhouse.io/botauto",
  },
  {
    id: "42dot",
    name: "42dot",
    type: "AV Startup",
    country: "South Korea",
    openPositions: 9,
    careersUrl: "https://www.42dot.ai/ko/careers/open-roles",
  },
  {
    id: "latitude-ai",
    name: "Latitude AI",
    type: "AV Startup",
    country: "USA",
    openPositions: 7,
    careersUrl: "https://boards.greenhouse.io/latitude",
  },
  {
    id: "nuro",
    name: "Nuro",
    type: "AV Startup",
    country: "USA",
    openPositions: 6,
  },
  {
    id: "vay",
    name: "Vay",
    type: "AV Startup",
    country: "Germany",
    openPositions: 4,
    careersUrl: "https://boards.greenhouse.io/vay",
  },
  {
    id: "wayve",
    name: "Wayve",
    type: "AV Startup",
    country: "UK",
    openPositions: 13,
    careersUrl: "https://boards.greenhouse.io/wayve",
  },
  {
    id: "torc-robotics",
    name: "Torc Robotics",
    type: "AV Startup",
    country: "USA",
    openPositions: 10,
    careersUrl: "https://boards.greenhouse.io/torcrobotics",
  },
  {
    id: "inceptio-ai",
    name: "Inceptio.ai",
    type: "AV Startup",
    country: "China",
    openPositions: 5,
  },
  {
    id: "momenta",
    name: "Momenta",
    type: "AV Startup",
    country: "China",
    openPositions: 8,
  },
  {
    id: "adastec",
    name: "ADASTEC",
    type: "AV Startup",
    country: "USA",
    openPositions: 2,
    careersUrl: "https://www.adastec.com/",
  },
  {
    id: "tier-iv",
    name: "Tier IV",
    type: "AV Startup",
    country: "Japan",
    openPositions: 12,
  },
  {
    id: "applied-intuition",
    name: "Applied Intuition",
    type: "AV Startup",
    country: "USA",
    openPositions: 16,
    about:
      "Applied Intuition builds simulation and toolchain software used by automakers and AV companies to develop and test autonomous vehicles.",
    size: "201–1,000 employees",
    careersUrl: "https://jobs.ashbyhq.com/applied",
  },
  {
    id: "gm",
    name: "GM",
    type: "OEM",
    country: "USA",
    openPositions: 41,
    about:
      "General Motors is a major American automaker developing autonomous driving and EV technology across its vehicle lineup.",
    size: "10,001+ employees",
    careersUrl: "https://search-careers.gm.com/en/",
  },
  {
    id: "xpeng",
    name: "XPeng",
    type: "OEM",
    country: "China",
    openPositions: 33,
    careersUrl: "https://www.xpeng.com/au/join-us",
  },
  {
    id: "woven-by-toyota",
    name: "Woven by Toyota",
    type: "OEM",
    country: "Japan",
    openPositions: 19,
    careersUrl: "https://woven.toyota/en/careers",
  },
  {
    id: "baidu-apollo",
    name: "Baidu Apollo",
    type: "Tech Giant",
    country: "China",
    openPositions: 27,
    about:
      "Baidu Apollo is Baidu's autonomous driving platform, one of the world's largest open-source self-driving ecosystems and a leading robotaxi operator in China.",
    size: "10,001+ employees",
    // No careersUrl: the investigation doc marks this as "no stable public
    // URL confirmed" — left unset rather than guessing, unlike the job-level
    // sourceUrl which needed some fallback value.
  },
  {
    id: "huawei",
    name: "Huawei",
    type: "Tech Giant",
    country: "China",
    openPositions: 52,
    careersUrl: "https://career.huawei.com/",
  },
  {
    id: "didi",
    name: "DiDi",
    type: "Tech Giant",
    country: "China",
    openPositions: 24,
    careersUrl: "https://boards.greenhouse.io/didi",
  },
  {
    id: "nvidia",
    name: "NVIDIA",
    type: "Tech Giant",
    country: "USA",
    openPositions: 48,
    about:
      "NVIDIA provides the GPU computing platforms and software stack used across much of the autonomous vehicle industry for AI training and in-vehicle inference.",
    size: "10,001+ employees",
    careersUrl: "https://www.nvidia.com/en-au/about-nvidia/careers/",
  },
  {
    id: "mobileye",
    name: "Mobileye",
    type: "Tier 1 Supplier",
    country: "Israel",
    openPositions: 21,
    about:
      "Mobileye, an Intel company, develops camera-based ADAS and autonomous driving technology used by automakers worldwide.",
    size: "1,001–5,000 employees",
    careersUrl: "https://www.mobileye.com/about/",
  },
  {
    id: "bosch",
    name: "Bosch",
    type: "Tier 1 Supplier",
    country: "Germany",
    openPositions: 37,
    about:
      "Bosch is a global engineering and technology company supplying automotive components and driver-assistance/autonomous systems to major automakers.",
    size: "10,001+ employees",
    careersUrl: "https://jobs.smartrecruiters.com/BoschGroup",
  },
  {
    id: "horizon-robotics",
    name: "Horizon Robotics",
    type: "Tier 1 Supplier",
    country: "China",
    openPositions: 13,
  },
];

export function getCompanyById(id: string): Company | undefined {
  return AV_COMPANIES.find((c) => c.id === id);
}

/* ------------------------------------------------------------------ */
/* Jobs                                                               */
/* ------------------------------------------------------------------ */

export type JobStatus = "Open" | "Closed";
export type JobType = "Full-time" | "Part-time" | "Contract" | "Internship";

export type Job = {
  id: string;
  title: string;
  /** Display name — kept alongside companyId rather than derived, so
   *  existing card components don't need a lookup just to show a name. */
  company: string;
  companyId: string;
  /** Company location country, e.g. "USA", "Germany", "China". */
  country: string;
  /** Estimated salary range in thousands USD (may be estimated per brief). */
  salaryMin: number;
  salaryMax: number;
  status: JobStatus;
  type: JobType;
  category: CategoryName;
  /** ISO date string, e.g. "2026-07-18". */
  postedDate: string;
  description: string;
  requirements: string[];
  skills: string[];
  /** Link to the original posting / company careers page. */
  sourceUrl: string;
};

type JobInput = Omit<Job, "id">;

function toJobs(inputs: JobInput[]): Job[] {
  return inputs.map((job) => ({
    ...job,
    id: `${job.companyId}-${slugify(job.title)}`,
  }));
}

const MOCK_JOB_INPUTS: JobInput[] = [
  {
    title: "Perception Engineer",
    company: "Waymo",
    companyId: "waymo",
    country: "USA",
    salaryMin: 130,
    salaryMax: 180,
    status: "Open",
    type: "Full-time",
    category: "Perception",
    postedDate: "2026-07-18",
    description:
      "Waymo is looking for a Perception Engineer to help build the sensing and detection systems that let our vehicles understand the world around them.\n\nYou'll work across camera, lidar, and radar pipelines to improve how the vehicle detects and classifies objects in real time, partnering closely with the planning and controls teams to make sure perception output is accurate and reliable enough to drive on.",
    requirements: [
      "3+ years of experience in computer vision or sensor fusion",
      "Strong background in deep learning for object detection or tracking",
      "Experience with C++ or Python in a production ML pipeline",
      "Familiarity with lidar or radar point cloud processing",
    ],
    skills: [
      "Computer Vision",
      "Sensor Fusion",
      "C++",
      "Python",
      "Deep Learning",
    ],
    sourceUrl: "https://careers.withwaymo.com/",
  },
  {
    title: "Localization & Mapping Engineer",
    company: "Zoox",
    companyId: "zoox",
    country: "USA",
    salaryMin: 120,
    salaryMax: 165,
    status: "Open",
    type: "Full-time",
    category: "Localization",
    postedDate: "2026-07-15",
    description:
      "Join Zoox's Localization & Mapping team to build the systems that let our robotaxi know exactly where it is on the road at all times.\n\nYou'll work on HD map generation and real-time pose estimation, combining lidar, GPS, and IMU data to keep localization accurate down to the centimeter.",
    requirements: [
      "Experience with SLAM or pose estimation algorithms",
      "Strong C++ skills in a real-time systems environment",
      "Background in HD mapping or geospatial data pipelines",
      "Comfortable working with large-scale sensor datasets",
    ],
    skills: ["SLAM", "HD Mapping", "C++", "Point Cloud Processing", "GNSS/IMU"],
    sourceUrl: "https://zoox.com/careers",
  },
  {
    title: "Motion Planning Engineer",
    company: "Aurora",
    companyId: "aurora",
    country: "USA",
    salaryMin: 125,
    salaryMax: 175,
    status: "Open",
    type: "Full-time",
    category: "Planning",
    postedDate: "2026-07-20",
    description:
      "Aurora is hiring a Motion Planning Engineer to design trajectory generation and behavior planning for our self-driving trucks.\n\nYou'll build algorithms that decide how the vehicle should move through traffic — lane changes, merges, and highway driving — balancing safety, comfort, and efficiency at highway speed.",
    requirements: [
      "Experience with trajectory optimization or behavior planning",
      "Strong background in robotics, controls, or applied math",
      "Proficiency in C++ or Python for planning algorithms",
      "Understanding of vehicle dynamics is a plus",
    ],
    skills: ["Motion Planning", "Trajectory Optimization", "C++", "Robotics"],
    sourceUrl: "https://aurora.tech/careers",
  },
  {
    title: "Controls Engineer",
    company: "GM",
    companyId: "gm",
    country: "USA",
    salaryMin: 110,
    salaryMax: 150,
    status: "Open",
    type: "Full-time",
    category: "Control",
    postedDate: "2026-07-10",
    description:
      "GM is looking for a Controls Engineer to develop the low-level control systems that translate a planned trajectory into steering, throttle, and braking commands.\n\nYou'll tune and validate control algorithms across a range of driving conditions, working closely with the vehicle platform and planning teams.",
    requirements: [
      "Experience with PID or MPC-based control systems",
      "Background in vehicle dynamics or automotive controls",
      "Proficiency in MATLAB/Simulink or C++",
      "Comfortable with in-vehicle testing and validation",
    ],
    skills: ["Vehicle Controls", "MPC", "MATLAB/Simulink", "C++"],
    sourceUrl: "https://search-careers.gm.com/en/",
  },
  {
    title: "Sensor Fusion Engineer",
    company: "Motional",
    companyId: "motional",
    country: "USA",
    salaryMin: 115,
    salaryMax: 160,
    status: "Open",
    type: "Full-time",
    category: "Perception",
    postedDate: "2026-07-22",
    description:
      "Motional is hiring a Sensor Fusion Engineer to combine data from camera, lidar, and radar into a single, reliable picture of the environment around our robotaxis.\n\nYou'll design fusion algorithms that are robust across weather, lighting, and traffic conditions, directly feeding the perception stack that keeps the vehicle safe.",
    requirements: [
      "Experience fusing multi-modal sensor data (camera/lidar/radar)",
      "Strong understanding of probabilistic estimation (Kalman filters, etc.)",
      "Proficiency in C++ and/or Python",
      "Background in autonomous systems or robotics preferred",
    ],
    skills: ["Sensor Fusion", "Kalman Filtering", "C++", "Robotics"],
    sourceUrl: "https://boards.greenhouse.io/motional",
  },
  {
    title: "V&V Test Engineer",
    company: "Bosch",
    companyId: "bosch",
    country: "Germany",
    salaryMin: 85,
    salaryMax: 120,
    status: "Open",
    type: "Full-time",
    category: "System",
    postedDate: "2026-07-05",
    description:
      "Bosch is looking for a V&V Test Engineer to design and run the verification and validation processes behind our driver-assistance and autonomous systems.\n\nYou'll build test scenarios, run simulation and track-based validation, and help define the safety cases our systems need to pass before deployment.",
    requirements: [
      "Experience in automotive V&V, functional safety, or test engineering",
      "Familiarity with ISO 26262 or similar safety standards",
      "Comfortable working with simulation and scenario-based testing tools",
      "Strong attention to detail and documentation",
    ],
    skills: ["V&V", "Functional Safety", "ISO 26262", "Scenario Testing"],
    sourceUrl: "https://jobs.smartrecruiters.com/BoschGroup",
  },
  {
    title: "Autonomous Driving Engineer",
    company: "Baidu Apollo",
    companyId: "baidu-apollo",
    country: "China",
    salaryMin: 60,
    salaryMax: 90,
    status: "Open",
    type: "Full-time",
    category: "System",
    postedDate: "2026-07-08",
    description:
      "Baidu Apollo is looking for an Autonomous Driving Engineer to help integrate perception, planning, and control modules into a reliable end-to-end system.\n\nYou'll work across the Apollo open-source stack, debugging system-level issues and helping ship updates to our robotaxi fleet.",
    requirements: [
      "Experience with autonomous driving software stacks (Apollo, Autoware, or similar)",
      "Strong systems-level debugging skills",
      "Proficiency in C++ and Linux-based development",
      "Familiarity with Cyber RT or ROS-style middleware is a plus",
    ],
    skills: ["System Integration", "Apollo", "C++", "Linux"],
    sourceUrl: "https://www.apollo.auto/",
  },
];

const FEATURED_JOB_INPUTS: JobInput[] = [
  {
    title: "Senior Perception Engineer",
    company: "Waymo",
    companyId: "waymo",
    country: "USA",
    salaryMin: 160,
    salaryMax: 220,
    status: "Open",
    type: "Full-time",
    category: "Perception",
    postedDate: "2026-07-25",
    description:
      "Waymo is hiring a Senior Perception Engineer to lead improvements to our object detection and tracking systems.\n\nYou'll set technical direction for a small team, working across camera and lidar pipelines to push perception accuracy and reliability in increasingly complex driving scenarios.",
    requirements: [
      "6+ years of experience in computer vision or perception systems",
      "Track record of shipping production ML models",
      "Experience mentoring or leading engineers",
      "Deep familiarity with sensor fusion and object tracking",
    ],
    skills: ["Computer Vision", "Sensor Fusion", "Leadership", "Deep Learning"],
    sourceUrl: "https://careers.withwaymo.com/",
  },
  {
    title: "Staff ML Engineer",
    company: "NVIDIA",
    companyId: "nvidia",
    country: "USA",
    salaryMin: 180,
    salaryMax: 240,
    status: "Open",
    type: "Full-time",
    category: "Perception",
    postedDate: "2026-07-28",
    description:
      "NVIDIA is looking for a Staff ML Engineer to help build the AI platforms that power perception and planning for autonomous vehicle customers worldwide.\n\nYou'll work on training infrastructure and model architectures used across the AV industry, collaborating with partner teams to optimize for both accuracy and in-vehicle inference performance.",
    requirements: [
      "8+ years of experience in machine learning engineering",
      "Deep understanding of GPU-accelerated training and inference",
      "Experience with large-scale ML infrastructure",
      "Strong publication or shipped-product track record",
    ],
    skills: ["Machine Learning", "GPU Computing", "Deep Learning", "Python"],
    sourceUrl: "https://www.nvidia.com/en-au/about-nvidia/careers/",
  },
  {
    title: "HD Map Engineer",
    company: "Mobileye",
    companyId: "mobileye",
    country: "Israel",
    salaryMin: 110,
    salaryMax: 150,
    status: "Open",
    type: "Full-time",
    category: "Map",
    postedDate: "2026-07-14",
    description:
      "Mobileye is hiring an HD Map Engineer to work on the crowdsourced mapping technology behind our autonomous driving systems.\n\nYou'll build pipelines that turn crowdsourced camera data into high-definition maps used for localization across millions of vehicles.",
    requirements: [
      "Experience with HD mapping or geospatial data processing",
      "Strong software engineering skills (C++ or Python)",
      "Background in computer vision is a plus",
      "Comfortable working with large-scale, crowdsourced datasets",
    ],
    skills: ["HD Mapping", "Geospatial Data", "C++", "Computer Vision"],
    sourceUrl: "https://www.mobileye.com/about/",
  },
];

export const MOCK_JOBS: Job[] = toJobs(MOCK_JOB_INPUTS);
export const FEATURED_JOBS: Job[] = toJobs(FEATURED_JOB_INPUTS);
export const ALL_JOBS: Job[] = [...MOCK_JOBS, ...FEATURED_JOBS];

export function getJobById(id: string): Job | undefined {
  return ALL_JOBS.find((j) => j.id === id);
}

export function getJobsByCompanyId(companyId: string): Job[] {
  return ALL_JOBS.filter((j) => j.companyId === companyId);
}

export function getSimilarJobs(job: Job, limit = 3): Job[] {
  return ALL_JOBS.filter(
    (j) => j.id !== job.id && j.category === job.category,
  ).slice(0, limit);
}
