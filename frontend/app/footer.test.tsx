import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Footer, { FOOTER_COLUMNS } from "../components/Footer";

describe("Footer", () => {
  it("has no placeholder links", () => {
    for (const link of FOOTER_COLUMNS.flatMap((col) => col.links)) {
      assert.notEqual(link.href, "#");
    }
  });

  it("links to the existing pages and opens external links in a new tab", () => {
    const html = renderToStaticMarkup(<Footer />);
    for (const href of [
      "/search",
      "/companies",
      "/trends",
      "/favorites",
      "/account",
      "/login",
      "/about",
    ]) {
      assert.ok(html.includes(`href="${href}"`), `missing ${href}`);
    }
    const external = FOOTER_COLUMNS.flatMap((col) => col.links).filter(
      (link) => link.external,
    );
    assert.equal(external.length, 2);
    assert.equal(html.match(/target="_blank"/g)?.length, 2);
    assert.equal(html.match(/rel="noopener noreferrer"/g)?.length, 2);
  });
});
