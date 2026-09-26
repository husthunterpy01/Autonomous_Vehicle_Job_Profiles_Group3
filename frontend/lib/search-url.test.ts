import assert from "node:assert/strict";
import { test } from "node:test";
import { DEFAULT_JOB_SORT } from "./job-sort.ts";
import {
  DEFAULT_PER_PAGE,
  MAX_PER_PAGE,
  parsePositiveInt,
  searchQueryString,
} from "./search-url.ts";

test("a page number from the URL is used as-is", () => {
  assert.equal(parsePositiveInt("50", 1), 50);
  assert.equal(parsePositiveInt(" 7 ", 1), 7);
});

test("anything that isn't a positive whole number falls back", () => {
  for (const raw of [
    null,
    "",
    "abc",
    "0",
    "-3",
    "2.5",
    "1e3",
    "9".repeat(20),
  ]) {
    assert.equal(parsePositiveInt(raw, 1), 1, `raw=${raw}`);
  }
});

test("per page is capped at the API limit", () => {
  assert.equal(parsePositiveInt("500", DEFAULT_PER_PAGE, MAX_PER_PAGE), 100);
  assert.equal(parsePositiveInt("20", DEFAULT_PER_PAGE, MAX_PER_PAGE), 20);
});

test("defaults stay out of the URL", () => {
  assert.equal(
    searchQueryString({
      q: "",
      category: "",
      sort: DEFAULT_JOB_SORT,
      page: 1,
      perPage: DEFAULT_PER_PAGE,
    }),
    "",
  );
});

test("page, per page and filters all go into the URL", () => {
  const qs = searchQueryString({
    q: " lidar ",
    category: "abc",
    sort: { field: "company", direction: "asc" },
    page: 50,
    perPage: 20,
  });
  assert.equal(
    qs,
    "q=lidar&category=abc&sort=company&direction=asc&page=50&per_page=20",
  );
});
