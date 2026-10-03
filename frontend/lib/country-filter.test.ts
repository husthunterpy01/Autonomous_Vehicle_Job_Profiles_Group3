import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ALL_COUNTRIES,
  countryOptions,
  resolveCountry,
} from "./country-filter.ts";

const COUNTS = [
  { country: "Israel", job_count: 47 },
  { country: "United States", job_count: 770 },
  { country: "Sweden", job_count: 2 },
  { country: "Hungary", job_count: 2 },
];

test("All Countries comes first with an empty value", () => {
  assert.equal(ALL_COUNTRIES, "");
  assert.deepEqual(countryOptions([]), [
    { value: ALL_COUNTRIES, label: "All Countries" },
  ]);
});

test("countries are listed with their job counts, most jobs first", () => {
  assert.deepEqual(countryOptions(COUNTS), [
    { value: "", label: "All Countries" },
    { value: "United States", label: "United States (770)" },
    { value: "Israel", label: "Israel (47)" },
    // A tie is broken alphabetically.
    { value: "Hungary", label: "Hungary (2)" },
    { value: "Sweden", label: "Sweden (2)" },
  ]);
});

test("a URL country is kept only while it still has jobs", () => {
  const options = countryOptions(COUNTS);
  assert.equal(resolveCountry("Israel", options), "Israel");
  assert.equal(resolveCountry(null, options), ALL_COUNTRIES);
  assert.equal(resolveCountry("", options), ALL_COUNTRIES);
  assert.equal(resolveCountry("Russia", options), ALL_COUNTRIES);
  assert.equal(resolveCountry("israel", options), ALL_COUNTRIES);
});
