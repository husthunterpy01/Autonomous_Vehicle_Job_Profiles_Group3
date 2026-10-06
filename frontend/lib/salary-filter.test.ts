import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  parseSalaryField,
  salaryFilterLabel,
  salaryRangeError,
  sanitizeSalaryDigits,
} from "./salary-filter.ts";

describe("sanitizeSalaryDigits", () => {
  it("keeps only digits", () => {
    assert.equal(sanitizeSalaryDigits("60,000"), "60000");
    assert.equal(sanitizeSalaryDigits("$60000"), "60000");
  });

  it("strips a negative sign and a decimal point", () => {
    assert.equal(sanitizeSalaryDigits("-60000"), "60000");
    assert.equal(sanitizeSalaryDigits("60000.50"), "6000050");
  });

  it("strips letters", () => {
    assert.equal(sanitizeSalaryDigits("60000abc"), "60000");
  });

  it("leaves empty input empty", () => {
    assert.equal(sanitizeSalaryDigits(""), "");
    assert.equal(sanitizeSalaryDigits("abc"), "");
  });
});

describe("parseSalaryField", () => {
  it("parses a plain number", () => {
    assert.equal(parseSalaryField("60000"), 60000);
  });

  it("parses through formatting characters", () => {
    assert.equal(parseSalaryField("$60,000"), 60000);
  });

  it("returns null for empty or non-numeric input", () => {
    assert.equal(parseSalaryField(""), null);
    assert.equal(parseSalaryField("abc"), null);
    assert.equal(parseSalaryField("-"), null);
  });
});

describe("salaryRangeError", () => {
  it("flags min greater than max", () => {
    assert.equal(
      salaryRangeError(100000, 60000),
      "Minimum salary must not be greater than the maximum.",
    );
  });

  it("allows min equal to max", () => {
    assert.equal(salaryRangeError(60000, 60000), null);
  });

  it("allows either bound alone", () => {
    assert.equal(salaryRangeError(60000, null), null);
    assert.equal(salaryRangeError(null, 60000), null);
  });

  it("allows neither bound set", () => {
    assert.equal(salaryRangeError(null, null), null);
  });
});

describe("salaryFilterLabel", () => {
  it("shows both bounds", () => {
    assert.equal(
      salaryFilterLabel(60000, 100000),
      "Salary: US$60,000 - US$100,000",
    );
  });

  it("shows a minimum-only label", () => {
    assert.equal(salaryFilterLabel(60000, null), "Salary: US$60,000+");
  });

  it("shows a maximum-only label", () => {
    assert.equal(salaryFilterLabel(null, 100000), "Salary: Up to US$100,000");
  });

  it("returns null when neither bound is set", () => {
    assert.equal(salaryFilterLabel(null, null), null);
  });
});
