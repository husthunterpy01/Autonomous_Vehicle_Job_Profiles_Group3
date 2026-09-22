import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { AuthUser } from "../../lib/services/auth";
import AccountClient from "./account-client";
import AccountView from "./account-view";

const user: AuthUser = {
  user_id: "internal-id-123",
  full_name: "Alex Driver",
  username: "alex.driver",
  email: "alex@example.com",
  created_at: "2025-06-15T12:30:00Z",
};

describe("AccountView", () => {
  it("displays the four personal fields for a fully populated user", () => {
    const html = renderToStaticMarkup(
      <AccountView state={{ status: "success", user }} />,
    );

    assert.match(html, /<dt[^>]*>Full name<\/dt><dd[^>]*>Alex Driver<\/dd>/);
    assert.match(html, /<dt[^>]*>Username<\/dt><dd[^>]*>alex.driver<\/dd>/);
    assert.match(html, /<dt[^>]*>Email<\/dt><dd[^>]*>alex@example.com<\/dd>/);
    assert.match(
      html,
      /<dt[^>]*>Member since<\/dt><dd[^>]*><time[^>]*>June 15, 2025<\/time><\/dd>/,
    );
    assert.match(html, /<time dateTime="2025-06-15T12:30:00.000Z">/);
    assert.ok(!html.includes(user.user_id));
    assert.ok(!html.includes("Not provided"));
  });

  it("uses the fallback for null, undefined, empty, and whitespace values", () => {
    const partialUser = {
      ...user,
      full_name: null,
      username: undefined,
      email: "   ",
      created_at: "",
    } as unknown as AuthUser;
    const html = renderToStaticMarkup(
      <AccountView state={{ status: "success", user: partialUser }} />,
    );

    assert.equal(html.match(/Not provided/g)?.length, 4);
    assert.ok(!html.includes("undefined"));
    assert.ok(!html.includes("null"));
    assert.ok(!html.includes("<time"));
  });

  it("handles malformed values without rendering objects or invalid dates", () => {
    const malformedUser = {
      ...user,
      full_name: { unexpected: true },
      created_at: "not-a-date",
    } as unknown as AuthUser;
    const html = renderToStaticMarkup(
      <AccountView state={{ status: "success", user: malformedUser }} />,
    );

    assert.equal(html.match(/Not provided/g)?.length, 2);
    assert.ok(!html.includes("[object Object]"));
    assert.ok(!html.includes("Invalid Date"));
  });

  it("starts in loading state before user information is available", () => {
    const html = renderToStaticMarkup(<AccountClient />);

    assert.match(html, /role="status"/);
    assert.match(html, /Loading your information/);
    assert.match(html, /aria-busy="true"/);
    assert.ok(!html.includes("Not provided"));
    assert.ok(!html.includes("<dl"));
  });

  it("shows a generic error without exposing exception details", () => {
    const html = renderToStaticMarkup(
      <AccountView state={{ status: "error" }} />,
    );

    assert.match(html, /role="alert"/);
    assert.match(html, /Unable to load your information/);
    assert.ok(!html.includes("Not provided"));
    assert.ok(!html.includes("<dl"));
  });
});
