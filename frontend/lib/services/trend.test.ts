import assert from "node:assert/strict";
import { afterEach, it } from "vitest";
import { API_BASE_URL } from "./api.ts";
import { getSkillTrends, type SkillTrends } from "./trend.ts";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

it("requests the chart's 8 skills and 12 months by default", async () => {
  const expected: SkillTrends = { months: [], skills: [] };
  let requestedUrl = "";
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    requestedUrl = String(input);
    return new Response(JSON.stringify(expected), { status: 200 });
  }) as typeof fetch;

  assert.deepEqual(await getSkillTrends(), expected);
  assert.equal(
    requestedUrl,
    `${API_BASE_URL}/api/v1/trends/skills?limit=8&months=12`,
  );
});

it("surfaces a 503 when trends are not configured", async () => {
  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({ detail: "Skill trends are not configured" }),
      {
        status: 503,
      },
    )) as typeof fetch;

  await assert.rejects(getSkillTrends(), /Skill trends are not configured/);
});
