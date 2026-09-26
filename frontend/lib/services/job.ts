import type { JobSort } from "@/lib/job-sort";
import type { SalaryInput } from "@/lib/salary";
import { apiFetch, type PageResponse } from "./api";

/* Matches backend/app/enums/employment_type.py's EmploymentType IntEnum. */
export const EMPLOYMENT_TYPE_LABELS: Record<number, string> = {
  1: "Full-time",
  2: "Part-time",
  3: "Contract",
  4: "Temporary",
  5: "Internship",
  6: "Other",
};

/* Matches backend/app/enums/seniority_type.py's SeniorityLevel IntEnum. */
export const SENIORITY_LEVEL_LABELS: Record<number, string> = {
  1: "Junior",
  2: "Mid-level",
  3: "Senior",
  4: "Principal",
  5: "Lead",
  6: "Manager",
  7: "Director",
  8: "CEO",
  9: "Other",
};

const JOB_UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True for backend job ids; mock landing-page slugs fail this check. */
export function isJobUuid(id: string): boolean {
  return JOB_UUID.test(id);
}

export type JobListItem = {
  job_id: string;
  title: string;
  company_id: string;
  company_name: string;
  locations: string[];
  skills: string[];
  employment_type: number | null;
  /** null on a list response (the backend omits the body there for speed);
   *  always a string on a job detail response - see JobDetail below. */
  raw_description: string | null;
  source_url: string | null;
  posted_date: string | null;
  /** Posted pay (a single figure arrives as min === max). Optional so the
   *  page keeps working against a backend that predates the salary columns. */
  salary_min?: number | null;
  salary_max?: number | null;
  /** Company-wide levels.fyi estimate, sent instead of min/max. */
  salary_average?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_source?: string | null;
};

export type JobCategory = {
  main_type: string | null;
  taxonomy_version: number;
  sub_types: { category_id: string; sub_type: string }[];
};

/** Matches backend JobDetailResponse (GET /api/v1/jobs/{job_id}). */
export type JobDetail = JobListItem & {
  raw_description: string;
  category: JobCategory | null;
  department: string | null;
  seniority_level: number | null;
  requirements: string | null;
  source_platform: string | null;
  source_job_id: string | null;
};

/** Salary props for the API shape; see lib/salary.ts for the display rules. */
export function jobSalary(job: JobListItem): SalaryInput {
  return {
    min: job.salary_min ?? null,
    max: job.salary_max ?? null,
    average: job.salary_average ?? null,
    currency: job.salary_currency ?? null,
    period: job.salary_period ?? null,
    source: job.salary_source ?? null,
  };
}

export function jobDetailHref(jobId: string): string {
  /* Query string so the static export always has a real /jobs.html file.
     /jobs/<uuid> does not exist at build time and Docker's SPA fallback
     would show the home page instead of this posting. */
  return `/jobs?id=${encodeURIComponent(jobId)}`;
}

export function getJobs(
  params: {
    q?: string;
    category_id?: string;
    company_id?: string;
    /** Only jobs whose employer published a salary range (no estimates). */
    salary_disclosed?: boolean;
    sort?: JobSort;
    page?: number;
    page_size?: number;
  },
  signal?: AbortSignal,
): Promise<PageResponse<JobListItem>> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.category_id) search.set("category_id", params.category_id);
  if (params.company_id) search.set("company_id", params.company_id);
  if (params.salary_disclosed !== undefined)
    search.set("salary_disclosed", String(params.salary_disclosed));
  if (params.sort) {
    search.set("sort", params.sort.field);
    search.set("direction", params.sort.direction);
  }
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.page_size ?? 10));
  return apiFetch<PageResponse<JobListItem>>(
    `/api/v1/jobs?${search.toString()}`,
    signal ? { signal } : undefined,
  );
}

export function getJob(jobId: string): Promise<JobDetail> {
  return apiFetch<JobDetail>(`/api/v1/jobs/${jobId}`);
}

export function employmentTypeLabel(
  employmentType: number | null | undefined,
): string | null {
  return employmentType != null
    ? (EMPLOYMENT_TYPE_LABELS[employmentType] ?? "Other")
    : null;
}

export function seniorityLabel(
  seniorityLevel: number | null | undefined,
): string | null {
  return seniorityLevel != null
    ? (SENIORITY_LEVEL_LABELS[seniorityLevel] ?? "Other")
    : null;
}

export function jobCategoryLabels(
  category: JobCategory | null | undefined,
): string[] {
  if (!category) return [];
  const labels: string[] = [];
  if (category.main_type?.trim()) labels.push(category.main_type.trim());
  for (const sub of category.sub_types) {
    const name = sub.sub_type.trim();
    if (name && !labels.includes(name)) labels.push(name);
  }
  return labels;
}

/** Bullet lines from the backend's free-text `requirements` field. */
export function requirementLines(
  requirements: string | null | undefined,
): string[] {
  if (!requirements?.trim()) return [];
  return requirements
    .split(/\r?\n/)
    .map((line) => line.replace(/^[\s*•\-–]+/, "").trim())
    .filter(Boolean);
}

/** Plain-text paragraphs; strips tags if a posting stored HTML. */
export function descriptionParagraphs(raw: string): string[] {
  const text = raw
    .replace(/<\s*br\s*\/?\s*>/gi, "\n")
    .replace(/<\s*\/\s*p\s*>/gi, "\n\n")
    .replace(/<\s*\/\s*li\s*>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&#39;/g, "'")
    .replace(/&apos;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  return text
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.replace(/\s*\n\s*/g, " ").trim())
    .filter(Boolean);
}

export type DescriptionBlock =
  | { type: "heading"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

export type DescriptionSection = {
  title: string;
  blocks: DescriptionBlock[];
};

const SECTION_NAME =
  "About(?:\\s+us|\\s+you|\\s+the\\s+(?:role|company|team))?|The role|What you(?:'|’)(?:ll(?: be doing)?| will do)|Key responsibilities|Responsibilities|Qualifications|Requirements|Benefits|Essential|Desirable|Nice to have";

const SECTION_SPLIT = new RegExp(
  `(?:^|(?<=[.!?]))\\s*(${SECTION_NAME})\\s*:?\\s+(?=[A-Z“"'(])`,
  "gi",
);

const HEADING_TITLES: Record<string, string> = {
  "about us": "About Us",
  "about you": "About You",
  "about the role": "About The Role",
  "about the company": "About The Company",
  "about the team": "About The Team",
  "the role": "The Role",
  "what you'll be doing": "What You'll Be Doing",
  "what you’ll be doing": "What You'll Be Doing",
  "what you'll": "What You'll Do",
  "what you’ll": "What You'll Do",
  "what you will do": "What You Will Do",
  "key responsibilities": "Key Responsibilities",
  responsibilities: "Responsibilities",
  qualifications: "Qualifications",
  requirements: "Requirements",
  benefits: "Benefits",
  essential: "Essential",
  desirable: "Desirable",
  "nice to have": "Nice To Have",
};

const SKIP_HEADING = /^(about us|about the company)$/i;
const LIST_HEADING =
  /^(key responsibilities|responsibilities|qualifications|requirements|benefits|about you|essential|desirable|nice to have)$/i;
const MAJOR_HEADING =
  /^(key responsibilities|responsibilities|qualifications|requirements|benefits|about you|what you'll be doing|what you will do|essential|desirable|nice to have)$/i;

function headingKey(label: string): string {
  return label.trim().replace(/\s+/g, " ").toLowerCase();
}

function titleCaseHeading(label: string): string {
  const key = headingKey(label);
  if (HEADING_TITLES[key]) return HEADING_TITLES[key];
  return key.replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function splitSentences(text: string): string[] {
  return text
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+(?=[A-Z“"'(])/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

/** "Onboarding: prepare offers. Offboarding: process leavers." */
function labeledDutyItems(text: string): string[] | null {
  const parts = text
    .split(/(?<=[.!?])\s+(?=[A-Z][^:]{0,50}:\s+\S)/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (
    parts.length >= 3 &&
    parts.every((part) => /^[A-Z][^:]{1,50}:\s+\S/.test(part))
  ) {
    return parts;
  }
  return null;
}

function pushParagraphs(blocks: DescriptionBlock[], text: string) {
  const sentences = splitSentences(text);
  if (sentences.length <= 2) {
    blocks.push({ type: "paragraph", text });
    return;
  }
  for (let i = 0; i < sentences.length; i += 2) {
    blocks.push({
      type: "paragraph",
      text: sentences.slice(i, i + 2).join(" "),
    });
  }
}

function pushBody(
  blocks: DescriptionBlock[],
  body: string,
  heading: string | null,
) {
  const trimmed = body.trim();
  if (!trimmed) return;

  const lines = trimmed
    .split(/\n/)
    .map((line) => line.replace(/^[\s*•\-–]+/, "").trim())
    .filter(Boolean);
  if (lines.length >= 3 && lines.every((line) => line.length < 220)) {
    blocks.push({ type: "list", items: lines });
    return;
  }

  if (heading && LIST_HEADING.test(headingKey(heading))) {
    const labeled = labeledDutyItems(trimmed);
    if (labeled) {
      blocks.push({ type: "list", items: labeled });
      return;
    }
    const sentences = splitSentences(trimmed);
    const items: string[] = [];
    const leftover: string[] = [];
    for (const sentence of sentences) {
      if (leftover.length === 0 && sentence.length <= 180) items.push(sentence);
      else leftover.push(sentence);
    }
    if (items.length >= 2) {
      blocks.push({ type: "list", items });
      if (leftover.length) pushParagraphs(blocks, leftover.join(" "));
      return;
    }
  }

  pushParagraphs(blocks, trimmed);
}

function pushHeading(blocks: DescriptionBlock[], heading: string) {
  if (SKIP_HEADING.test(headingKey(heading))) return;
  blocks.push({ type: "heading", text: titleCaseHeading(heading) });
}

/** Turns a scraped blob into headings, short paragraphs, and lists. */
export function descriptionBlocks(raw: string): DescriptionBlock[] {
  const source = descriptionParagraphs(raw).join("\n\n").trim();
  if (!source) return [];

  const blocks: DescriptionBlock[] = [];
  const splitter = new RegExp(SECTION_SPLIT.source, SECTION_SPLIT.flags);
  let lastIndex = 0;
  let lastHeading: string | null = null;
  let match: RegExpExecArray | null;

  while ((match = splitter.exec(source)) !== null) {
    const before = source.slice(lastIndex, match.index).trim();
    if (before) {
      if (lastHeading) pushHeading(blocks, lastHeading);
      pushBody(blocks, before, lastHeading);
    }
    lastHeading = match[1];
    lastIndex = splitter.lastIndex;
  }

  const rest = source.slice(lastIndex).trim();
  if (lastHeading) pushHeading(blocks, lastHeading);
  if (rest) {
    pushBody(blocks, rest, lastHeading);
  } else if (!lastHeading && blocks.length === 0) {
    pushBody(blocks, source, null);
  }

  return blocks;
}

/** Groups blocks so Key Responsibilities etc. render as their own sections. */
export function descriptionSections(raw: string): DescriptionSection[] {
  const sections: DescriptionSection[] = [{ title: "Description", blocks: [] }];
  for (const block of descriptionBlocks(raw)) {
    if (
      block.type === "heading" &&
      MAJOR_HEADING.test(headingKey(block.text))
    ) {
      sections.push({ title: block.text, blocks: [] });
      continue;
    }
    sections[sections.length - 1].blocks.push(block);
  }
  return sections.filter(
    (section, index) => index === 0 || section.blocks.length > 0,
  );
}
