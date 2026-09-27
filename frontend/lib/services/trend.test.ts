import assert from "node:assert/strict";
import { afterEach, it } from "vitest";
import { API_BASE_URL } from "./api.ts";
import { getSkillTrends, type SkillTrends } from "./trend.ts";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

it("requests the top skills and months from /api/v1/trends/skills", async () => {
  const expected: SkillTrends = { months: [], skills: [] };
  let requestedUrl = "";
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    requestedUrl = String(input);
    return new Response(JSON.stringify(expected), { status: 200 });
  }) as typeof fetch;

  assert.deepEqual(await getSkillTrends(10, 12), expected);
  assert.equal(
    requestedUrl,
    `${API_BASE_URL}/api/v1/trends/skills?limit=10&months=12`,
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
