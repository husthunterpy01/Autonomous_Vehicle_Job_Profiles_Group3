import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import LoginShowcase from "./login-showcase";

describe("LoginShowcase", () => {
  it("renders without data and shows no made-up numbers", () => {
    // Server rendering skips effects, so this is the state before the API
    // answers, which is also what a visitor sees if the API is down.
    const html = renderToStaticMarkup(<LoginShowcase />);
    assert.ok(html.includes("Companies"));
    assert.ok(html.includes("Open Roles"));
    assert.ok(html.includes("Live category data is not available right now."));
    assert.equal(html.match(/>-</g)?.length, 3);
  });
});
