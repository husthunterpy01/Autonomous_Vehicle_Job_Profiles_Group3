import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ALL_COUNTRIES,
  COUNTRY_OPTIONS,
  resolveCountry,
} from "./country-filter.ts";

test("All Countries is the first default option with an empty value", () => {
  assert.deepEqual(COUNTRY_OPTIONS[0], {
    value: ALL_COUNTRIES,
    label: "All Countries",
  });
  assert.equal(ALL_COUNTRIES, "");
});

test("country values are unique", () => {
  const values = COUNTRY_OPTIONS.map((option) => option.value);
  assert.equal(new Set(values).size, values.length);
});

test("country options after the default are alphabetical", () => {
  const countries = COUNTRY_OPTIONS.slice(1).map((option) => option.value);
  assert.deepEqual(
    countries,
    [...countries].sort((a, b) => a.localeCompare(b)),
  );
});

test("country options contain the complete authoritative scraper list", () => {
  assert.deepEqual(
    COUNTRY_OPTIONS.slice(1).map((option) => option.value),
    [
      "Canada",
      "China",
      "Germany",
      "Hungary",
      "Israel",
      "Japan",
      "Russia",
      "South Korea",
      "Sweden",
      "Turkey",
      "United Kingdom",
      "United States",
    ],
  );
});

test("a valid URL country resolves to its full English name", () => {
  assert.equal(resolveCountry("Germany"), "Germany");
  assert.equal(resolveCountry("Russia"), "Russia");
  assert.equal(resolveCountry("United Kingdom"), "United Kingdom");
});

test("missing and invalid URL countries resolve to All Countries", () => {
  assert.equal(resolveCountry(null), ALL_COUNTRIES);
  assert.equal(resolveCountry(""), ALL_COUNTRIES);
  assert.equal(resolveCountry("DE"), ALL_COUNTRIES);
  assert.equal(resolveCountry("Atlantis"), ALL_COUNTRIES);
});
