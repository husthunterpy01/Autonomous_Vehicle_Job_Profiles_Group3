import assert from "node:assert/strict";
import { it } from "vitest";
import { API_BASE_URL } from "./api.ts";
import { getCurrentUser } from "./auth.ts";

it("fetches the current user from /api/v1/auth/me with the auth cookie", async () => {
  const originalFetch = globalThis.fetch;
  const expectedUser = {
    user_id: "user-id",
    email: "alex@example.com",
    username: "alex.driver",
    full_name: "Alex Driver",
    created_at: "2025-06-15T12:30:00Z",
  };
  let requestedUrl: string | undefined;
  let requestedCredentials: RequestCredentials | undefined;

  globalThis.fetch = async (input, init) => {
    requestedUrl = String(input);
    requestedCredentials = init?.credentials;
    return new Response(JSON.stringify(expectedUser), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    assert.deepEqual(await getCurrentUser(), expectedUser);
    assert.equal(requestedUrl, `${API_BASE_URL}/api/v1/auth/me`);
    assert.equal(requestedCredentials, "include");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
