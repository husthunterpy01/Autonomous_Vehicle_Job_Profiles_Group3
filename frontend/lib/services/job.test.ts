import assert from "node:assert/strict";
import { afterEach, it } from "vitest";
import { API_BASE_URL } from "./api.ts";
import { getJobs } from "./job.ts";

const originalFetch = globalThis.fetch;

function mockSuccessfulFetch(onRequest: (url: URL) => void) {
  globalThis.fetch = async (input) => {
    onRequest(new URL(String(input)));
    return new Response(
      JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  };
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

it("serializes location alongside the existing job query parameters", async () => {
  let requestedUrl: URL | undefined;
  mockSuccessfulFetch((url) => {
    requestedUrl = url;
  });

  await getJobs({
    q: "autonomy engineer",
    category_id: "category-id",
    location: "United Kingdom",
    sort: { field: "company", direction: "asc" },
    page: 2,
    page_size: 25,
  });

  assert.equal(requestedUrl?.origin, API_BASE_URL);
  assert.equal(requestedUrl?.pathname, "/api/v1/jobs");
  assert.equal(requestedUrl?.searchParams.get("q"), "autonomy engineer");
  assert.equal(requestedUrl?.searchParams.get("category_id"), "category-id");
  assert.equal(requestedUrl?.searchParams.get("location"), "United Kingdom");
  assert.equal(requestedUrl?.searchParams.get("sort"), "company");
  assert.equal(requestedUrl?.searchParams.get("direction"), "asc");
  assert.equal(requestedUrl?.searchParams.get("page"), "2");
  assert.equal(requestedUrl?.searchParams.get("page_size"), "25");
});

it.each([undefined, ""])("omits location when it is %s", async (location) => {
  let requestedUrl: URL | undefined;
  mockSuccessfulFetch((url) => {
    requestedUrl = url;
  });

  await getJobs({ location });

  assert.equal(requestedUrl?.searchParams.has("location"), false);
});
