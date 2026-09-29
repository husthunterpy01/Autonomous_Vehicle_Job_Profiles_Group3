import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { TopPaidJob } from "./services/home.ts";
import {
  comparisonRange,
  computeScale,
  formatCompactUsd,
  niceStep,
} from "./salary-scale.ts";

function job(overrides: Partial<TopPaidJob>): TopPaidJob {
  return {
    job_id: "1",
    title: "Test Role",
    company_id: "1",
    company_name: "Test Co",
    salary_min: null,
    salary_max: null,
    salary_average: null,
    salary_currency: "USD",
    salary_period: "yearly",
    salary_source: "api",
    estimated_annual_usd_min: 0,
    estimated_annual_usd_max: 0,
    ...overrides,
  };
}

describe("formatCompactUsd", () => {
  it("shows a plain thousands figure below a million", () => {
    assert.equal(formatCompactUsd(210000), "US$210k");
  });

  it("rounds to the nearest thousand", () => {
    assert.equal(formatCompactUsd(209600), "US$210k");
  });

  it("switches to millions at or above 1,000,000", () => {
    assert.equal(formatCompactUsd(1_000_000), "US$1M");
  });

  it("keeps one decimal place for millions", () => {
    assert.equal(formatCompactUsd(2_600_000), "US$2.6M");
    assert.equal(formatCompactUsd(3_150_000), "US$3.2M");
  });

  it("handles zero", () => {
    assert.equal(formatCompactUsd(0), "US$0k");
  });

  it("switches to millions when rounding a near-million figure crosses the threshold", () => {
    // 999,600 is below 1,000,000 so it used to fail the millions check,
    // then separately round up to "1000k" once formatted - rounding to
    // the nearest thousand before checking the threshold fixes both at
    // once.
    assert.equal(formatCompactUsd(999_600), "US$1M");
  });
});

describe("comparisonRange", () => {
  it("shows a plain range with no prefix for an exact USD/yearly job", () => {
    const j = job({
      salary_currency: "USD",
      salary_period: "yearly",
      estimated_annual_usd_min: 210000,
      estimated_annual_usd_max: 275000,
    });
    assert.equal(comparisonRange(j), "US$210k – US$275k");
  });

  it("prefixes with ≈ when the period required annualizing", () => {
    const j = job({
      salary_currency: "USD",
      salary_period: "hourly",
      estimated_annual_usd_min: 156000,
      estimated_annual_usd_max: 176800,
    });
    assert.equal(comparisonRange(j), "≈US$156k – US$177k");
  });

  it("prefixes with ≈ when the currency required converting", () => {
    const j = job({
      salary_currency: "EUR",
      salary_period: "yearly",
      estimated_annual_usd_min: 102600,
      estimated_annual_usd_max: 129600,
    });
    assert.equal(comparisonRange(j), "≈US$103k – US$130k");
  });

  it("collapses to a single figure when there is no disclosed range", () => {
    const j = job({
      salary_currency: "USD",
      salary_period: "yearly",
      estimated_annual_usd_min: 180000,
      estimated_annual_usd_max: 180000,
    });
    assert.equal(comparisonRange(j), "US$180k");
  });

  it("formats each side independently across the k/M boundary", () => {
    const j = job({
      salary_currency: "USD",
      salary_period: "yearly",
      estimated_annual_usd_min: 850000,
      estimated_annual_usd_max: 1_200_000,
    });
    assert.equal(comparisonRange(j), "US$850k – US$1.2M");
  });
});

describe("niceStep", () => {
  it("rounds up to 1/2/5/10 x a power of ten", () => {
    assert.equal(niceStep(74_000), 100_000);
    assert.equal(niceStep(140_000), 200_000);
    assert.equal(niceStep(320_000), 500_000);
    assert.equal(niceStep(700_000), 1_000_000);
    assert.equal(niceStep(1_400_000), 2_000_000);
  });
});

describe("computeScale", () => {
  it("matches the original $100k-step design for a normal range", () => {
    // The values this feature originally shipped with (Waymo $275k max) -
    // regression check that the fix didn't change behavior for the common
    // case, only the previously-broken outlier case below.
    assert.deepEqual(computeScale(275_000), { max: 300_000, step: 100_000 });
  });

  it("keeps the tick count small for the reported outlier ($3.15M)", () => {
    // FE-21: a fixed $100k step produced 30+ overlapping ticks here before
    // this fix - the whole point of computeScale is that this stays small.
    const { max, step } = computeScale(3_150_000);
    const tickCount = max / step + 1;
    assert.ok(tickCount <= 6, `expected <=6 ticks, got ${tickCount}`);
    assert.deepEqual({ max, step }, { max: 4_000_000, step: 1_000_000 });
  });

  it("never produces a max smaller than the highest value", () => {
    for (const highest of [1, 84_000, 421_250, 3_150_000, 15_000_000]) {
      const { max } = computeScale(highest);
      assert.ok(max >= highest, `max ${max} < highest ${highest}`);
    }
  });

  it("keeps the tick count bounded across a wide range of magnitudes", () => {
    for (const highest of [1, 84_000, 421_250, 3_150_000, 15_000_000]) {
      const { max, step } = computeScale(highest);
      const tickCount = max / step + 1;
      assert.ok(
        tickCount >= 2 && tickCount <= 6,
        `highest=${highest} produced ${tickCount} ticks`,
      );
    }
  });
});
