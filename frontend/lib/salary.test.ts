import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  formatPayPeriod,
  formatSalary,
  formatSalaryAmount,
  resolveSalaryRange,
  salaryLabel,
} from "./salary.ts";

describe("resolveSalaryRange", () => {
  it("returns the pair when both bounds are positive numbers", () => {
    const range = resolveSalaryRange({ min: 189000, max: 303000 });
    assert.deepEqual(range, { min: 189000, max: 303000 });
  });

  it("orders a swapped pair", () => {
    const range = resolveSalaryRange({ min: 303000, max: 189000 });
    assert.deepEqual(range, { min: 189000, max: 303000 });
  });

  it("falls back to the average when no posted pair is present", () => {
    const range = resolveSalaryRange({ min: null, max: null, average: 266754 });
    assert.deepEqual(range, { min: 266754, max: 266754 });
  });

  it("prefers the posted pair over an average", () => {
    const range = resolveSalaryRange({ min: 1, max: 2, average: 266754 });
    assert.deepEqual(range, { min: 1, max: 2 });
  });

  it("returns null for missing, partial, or non-positive data", () => {
    assert.equal(resolveSalaryRange({}), null);
    assert.equal(resolveSalaryRange({ min: null, max: null }), null);
    assert.equal(resolveSalaryRange({ min: 189000 }), null);
    assert.equal(resolveSalaryRange({ min: 0, max: 0 }), null);
    assert.equal(resolveSalaryRange({ min: Number.NaN, max: 1 }), null);
  });
});

describe("formatSalaryAmount", () => {
  it("adds the currency symbol and thousands separators", () => {
    assert.equal(formatSalaryAmount(185000, "USD"), "US$185,000");
  });

  it("keeps dollar currencies distinguishable", () => {
    assert.equal(formatSalaryAmount(150000, "usd"), "US$150,000");
    assert.equal(formatSalaryAmount(150000, "AUD"), "A$150,000");
    assert.equal(formatSalaryAmount(150000, "CAD"), "CA$150,000");
    assert.equal(formatSalaryAmount(150000, "EUR"), "€150,000");
  });

  it("shows decimals only for non-whole amounts", () => {
    assert.equal(formatSalaryAmount(26.39, "USD"), "US$26.39");
    assert.equal(formatSalaryAmount(31, "USD"), "US$31");
  });

  it("falls back to the raw code when the currency is malformed", () => {
    assert.equal(formatSalaryAmount(185000, "us"), "US 185,000");
  });

  it("omits the symbol when no currency is known", () => {
    assert.equal(formatSalaryAmount(185000), "185,000");
    assert.equal(formatSalaryAmount(185000, "  "), "185,000");
  });
});

describe("formatSalary", () => {
  it("shows a posted range with its period", () => {
    const display = formatSalary({
      min: 189000,
      max: 303000,
      currency: "USD",
      period: "yearly",
      source: "regex",
    });
    assert.deepEqual(display, {
      amount: "US$189,000 – US$303,000",
      period: "/ year",
      estimated: false,
    });
  });

  it("collapses min === max to a single figure", () => {
    const display = formatSalary({
      min: 180923,
      max: 180923,
      currency: "USD",
      period: "yearly",
      source: "api",
    });
    assert.equal(display?.amount, "US$180,923");
    assert.equal(display?.estimated, false);
  });

  it("shows a levels.fyi average-only record as an estimate", () => {
    const display = formatSalary({
      min: null,
      max: null,
      average: 266754,
      currency: "USD",
      period: "yearly",
      source: "levels_fyi_average",
    });
    assert.deepEqual(display, {
      amount: "~US$266,754",
      period: "/ year",
      estimated: true,
    });
    assert.equal(
      salaryLabel({
        average: 266754,
        currency: "USD",
        period: "yearly",
        source: "levels_fyi_average",
      }),
      "~US$266,754 / year",
    );
  });

  it("marks levels.fyi figures as estimates", () => {
    const display = formatSalary({
      min: 180923,
      max: 180923,
      currency: "USD",
      period: "yearly",
      source: "levels_fyi_average",
    });
    assert.equal(display?.amount, "~US$180,923");
    assert.equal(display?.estimated, true);
  });

  it("supports hourly pay", () => {
    const input = { min: 26.39, max: 39.59, currency: "USD", period: "hourly" };
    assert.equal(salaryLabel(input), "US$26.39 – US$39.59 / hour");
  });

  it("omits the period when it is unknown", () => {
    const display = formatSalary({ min: 50, max: 60, currency: "EUR" });
    assert.equal(display?.period, null);
    assert.equal(display?.estimated, false);
    assert.equal(
      salaryLabel({ min: 50, max: 60, currency: "EUR" }),
      "€50 – €60",
    );
  });

  it("names the pay period for its own column", () => {
    const posted = {
      min: 26.39,
      max: 39.59,
      currency: "USD",
      period: "hourly",
    };
    assert.equal(formatPayPeriod(posted), "Hourly");
    assert.equal(
      formatPayPeriod({ average: 180605, period: "YEARLY" }),
      "Yearly",
    );
    assert.equal(formatPayPeriod({ min: 50, max: 60, period: "annual" }), null);
    assert.equal(formatPayPeriod({ period: "yearly" }), null);
  });

  it("returns null when salary data is missing", () => {
    assert.equal(formatSalary({}), null);
    assert.equal(formatSalary({ min: null, max: null, currency: "USD" }), null);
    assert.equal(salaryLabel({ period: "yearly", source: "api" }), null);
  });
});
