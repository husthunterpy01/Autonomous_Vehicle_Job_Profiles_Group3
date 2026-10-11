import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ALL_SENIORITIES,
  resolveSeniority,
  seniorityOptions,
} from "./seniority-filter.ts";

const labels = { 1: "Junior", 2: "Mid-level", 3: "Senior", 6: "Manager" };

test("lists All levels first, then each level lowest first with its count", () => {
  const options = seniorityOptions(
    [
      { seniority_level: 6, job_count: 4 },
      { seniority_level: 1, job_count: 7 },
      { seniority_level: 3, job_count: 12 },
    ],
    labels,
  );

  assert.deepEqual(options, [
    { value: "", label: "All levels" },
    { value: "1", label: "Junior (7)" },
    { value: "3", label: "Senior (12)" },
    { value: "6", label: "Manager (4)" },
  ]);
});

test("mid-level says it also holds jobs with no stated level", () => {
  const options = seniorityOptions(
    [{ seniority_level: 2, job_count: 455 }],
    labels,
  );

  assert.equal(options[1].label, "Mid-level or not stated (455)");
});

test("an unknown level is labelled Other and an empty list still has All levels", () => {
  assert.deepEqual(
    seniorityOptions([{ seniority_level: 9, job_count: 1 }], labels)[1],
    {
      value: "9",
      label: "Other (1)",
    },
  );
  assert.deepEqual(seniorityOptions([], labels), [
    { value: "", label: "All levels" },
  ]);
});

test("does not change the list it is given", () => {
  const counts = [
    { seniority_level: 3, job_count: 1 },
    { seniority_level: 1, job_count: 1 },
  ];
  seniorityOptions(counts, labels);

  assert.deepEqual(
    counts.map((c) => c.seniority_level),
    [3, 1],
  );
});

test("a level from the URL is kept only while it has jobs", () => {
  const options = seniorityOptions(
    [{ seniority_level: 3, job_count: 5 }],
    labels,
  );

  assert.equal(resolveSeniority("3", options), "3");
  assert.equal(resolveSeniority("7", options), ALL_SENIORITIES);
  assert.equal(resolveSeniority("abc", options), ALL_SENIORITIES);
  assert.equal(resolveSeniority(null, options), ALL_SENIORITIES);
  assert.equal(resolveSeniority("", options), ALL_SENIORITIES);
});
