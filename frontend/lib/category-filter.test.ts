import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ALL_CATEGORIES,
  categoryOptions,
  resolveCategory,
  type CategoryStat,
} from "./category-filter.ts";

const stats: CategoryStat[] = [
  {
    category_id: "id-perception",
    sub_type: "Perception",
    main_type: "Perception & Sensing",
    job_count: 120,
  },
  {
    category_id: "id-mapping",
    sub_type: "Mapping",
    main_type: "Localization & Mapping",
    job_count: 300,
  },
  {
    category_id: "id-control",
    sub_type: "Control",
    main_type: "System",
    job_count: 120,
  },
];

test("options lead with All categories, then the busiest categories", () => {
  const options = categoryOptions(stats);
  assert.deepEqual(options[0], {
    value: ALL_CATEGORIES,
    label: "All categories",
  });
  assert.deepEqual(
    options.slice(1).map((option) => option.label),
    ["Mapping (300)", "Control (120)", "Perception (120)"],
  );
});

test("equal counts fall back to alphabetical order", () => {
  const labels = categoryOptions(stats)
    .slice(1)
    .map((option) => option.label);
  assert.ok(
    labels.indexOf("Control (120)") < labels.indexOf("Perception (120)"),
  );
});

test("the option list is built without mutating the response", () => {
  const original = stats.map((stat) => stat.category_id);
  categoryOptions(stats);
  assert.deepEqual(
    stats.map((stat) => stat.category_id),
    original,
  );
});

test("a category that no longer exists falls back to All categories", () => {
  const options = categoryOptions(stats);
  assert.equal(resolveCategory("id-mapping", options), "id-mapping");
  assert.equal(resolveCategory("id-deleted", options), ALL_CATEGORIES);
  assert.equal(resolveCategory(null, options), ALL_CATEGORIES);
});

test("no categories yet still leaves a usable dropdown", () => {
  assert.deepEqual(categoryOptions([]), [
    { value: ALL_CATEGORIES, label: "All categories" },
  ]);
});
