import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_JOB_SORT,
  isDefaultJobSort,
  nextJobSort,
  parseJobSort,
} from "./job-sort.ts";

test("a new column starts newest first for dates and A-Z for names", () => {
  assert.deepEqual(nextJobSort(DEFAULT_JOB_SORT, "title"), {
    field: "title",
    direction: "asc",
  });
  assert.deepEqual(nextJobSort(DEFAULT_JOB_SORT, "company"), {
    field: "company",
    direction: "asc",
  });
  assert.deepEqual(
    nextJobSort({ field: "title", direction: "asc" }, "posted_date"),
    { field: "posted_date", direction: "desc" },
  );
});

test("clicking the sorted column flips its direction", () => {
  const ascending = nextJobSort(DEFAULT_JOB_SORT, "title");
  const descending = nextJobSort(ascending, "title");
  assert.equal(descending.direction, "desc");
  assert.equal(nextJobSort(descending, "title").direction, "asc");
});

test("the URL sort is read back, and anything unrecognized falls back", () => {
  assert.deepEqual(parseJobSort("company", "desc"), {
    field: "company",
    direction: "desc",
  });
  // A known field with a missing or nonsense direction keeps that field's
  // natural starting direction instead of failing.
  assert.deepEqual(parseJobSort("title", null), {
    field: "title",
    direction: "asc",
  });
  assert.deepEqual(parseJobSort("title", "sideways"), {
    field: "title",
    direction: "asc",
  });
  assert.deepEqual(parseJobSort("salary", "asc"), DEFAULT_JOB_SORT);
  assert.deepEqual(parseJobSort(null, null), DEFAULT_JOB_SORT);
});

test("the default sort is recognized so it stays out of the URL", () => {
  assert.equal(isDefaultJobSort(DEFAULT_JOB_SORT), true);
  assert.equal(
    isDefaultJobSort({ field: "posted_date", direction: "asc" }),
    false,
  );
  assert.equal(isDefaultJobSort({ field: "title", direction: "asc" }), false);
});
