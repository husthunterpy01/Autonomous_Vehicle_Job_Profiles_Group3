import assert from "node:assert/strict";
import { afterEach, it } from "vitest";
import { API_BASE_URL } from "./api.ts";
import {
  descriptionBlocks,
  descriptionParagraphs,
  descriptionSections,
  getJob,
  getJobs,
  isJobUuid,
  jobCategoryLabels,
  jobDetailHref,
  requirementLines,
} from "./job.ts";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

it("treats backend UUIDs as job ids and mock slugs as not", () => {
  assert.equal(isJobUuid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"), true);
  assert.equal(isJobUuid("waymo-perception-engineer"), false);
});

it("builds a static-export-safe job detail href", () => {
  assert.equal(
    jobDetailHref("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    "/jobs?id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  );
});

it("fetches one job from /api/v1/jobs/{job_id}", async () => {
  const jobId = "11111111-1111-1111-1111-111111111111";
  const expected = {
    job_id: jobId,
    title: "Perception Engineer",
    company_id: "22222222-2222-2222-2222-222222222222",
    company_name: "Waymo",
    locations: ["Mountain View, CA"],
    skills: ["Python"],
    employment_type: 1,
    raw_description: "Build perception systems.",
    source_url: "https://example.com/jobs/1",
    posted_date: "2026-09-21T08:00:00Z",
    salary_min: 140000,
    salary_max: 180000,
    salary_average: null,
    salary_currency: "USD",
    salary_period: "yearly",
    salary_source: "api",
    category: {
      main_type: "Perception",
      taxonomy_version: 1,
      sub_types: [
        {
          category_id: "33333333-3333-3333-3333-333333333333",
          sub_type: "Vision",
        },
      ],
    },
    department: "Engineering",
    seniority_level: 3,
    requirements: "Python\nC++",
    source_platform: "Greenhouse",
    source_job_id: "123",
  };
  let requestedUrl: string | undefined;

  globalThis.fetch = async (input) => {
    requestedUrl = String(input);
    return new Response(JSON.stringify(expected), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  assert.deepEqual(await getJob(jobId), expected);
  assert.equal(requestedUrl, `${API_BASE_URL}/api/v1/jobs/${jobId}`);
});

it("sends salary_disclosed and the sort when listing jobs", async () => {
  let requestedUrl: string | undefined;
  globalThis.fetch = async (input) => {
    requestedUrl = String(input);
    return new Response(
      JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        page_size: 3,
        total_pages: 0,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  await getJobs({
    salary_disclosed: true,
    sort: { field: "posted_date", direction: "desc" },
    page_size: 3,
  });
  const url = new URL(requestedUrl ?? "");
  assert.equal(url.pathname, "/api/v1/jobs");
  assert.equal(url.searchParams.get("salary_disclosed"), "true");
  assert.equal(url.searchParams.get("sort"), "posted_date");
  assert.equal(url.searchParams.get("direction"), "desc");
  assert.equal(url.searchParams.get("page_size"), "3");

  await getJobs({});
  assert.equal(
    new URL(requestedUrl ?? "").searchParams.has("salary_disclosed"),
    false,
  );
});

it("splits requirements on newlines and strips bullets", () => {
  assert.deepEqual(requirementLines("Python\n• C++\n- ROS"), [
    "Python",
    "C++",
    "ROS",
  ]);
  assert.deepEqual(requirementLines("   "), []);
});

it("lists main type then distinct sub-types for category tags", () => {
  assert.deepEqual(
    jobCategoryLabels({
      main_type: "Perception",
      taxonomy_version: 1,
      sub_types: [
        { category_id: "a", sub_type: "Vision" },
        { category_id: "b", sub_type: "Perception" },
      ],
    }),
    ["Perception", "Vision"],
  );
});

it("turns HTML descriptions into plain paragraphs", () => {
  assert.deepEqual(
    descriptionParagraphs("<p>Build cars.</p><p>Ship models.</p>"),
    ["Build cars.", "Ship models."],
  );
});

it("breaks a scraped wall of text into readable blocks", () => {
  const blocks = descriptionBlocks(
    "At the heart of our mission is safety. We are seeking an experienced safety engineer to lead the work. You will play a pivotal role in creating the evidence. Inform driverless release testing by developing datasets. Qualifications: Undergrad required; Masters or PhD preferred. 7+ years of automotive experience.",
  );
  assert.equal(blocks[0]?.type, "paragraph");
  assert.ok(
    blocks.some(
      (block) => block.type === "heading" && block.text === "Qualifications",
    ),
  );
  const paragraphs = blocks.filter((block) => block.type === "paragraph");
  assert.ok(paragraphs.length >= 2);
});

it("lifts key responsibilities into a checklist section", () => {
  const sections = descriptionSections(
    "About us Founded in 2017, Wayve builds autonomy. Our vision is to create autonomy that propels the world forward. The role As part of our People team, you will help build the operational backbone. Key responsibilities: Onboarding: preparing offers and employment contracts. Offboarding: supporting leaver processing and final pay. HRIS administration: maintaining employee data and reports. About you In order to set you up for success, we look for the following. Essential At least one year of People Operations experience. Knowledge of Japanese HR administration.",
  );
  assert.equal(sections[0]?.title, "Description");
  assert.equal(sections[0]?.blocks[0]?.type, "paragraph");
  const duties = sections.find(
    (section) => section.title === "Key Responsibilities",
  );
  assert.ok(duties);
  assert.equal(duties?.blocks[0]?.type, "list");
  if (duties?.blocks[0]?.type === "list") {
    assert.ok(
      duties.blocks[0].items.some((item) => item.startsWith("Onboarding:")),
    );
    assert.ok(
      duties.blocks[0].items.some((item) => item.startsWith("Offboarding:")),
    );
  }
});
