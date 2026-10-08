import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api";

test.describe("Market Trends", () => {
  test("shows the skill chart and its legend", async ({ page }) => {
    await mockApi(page);
    await page.goto("/trends");

    await expect(
      page.getByRole("heading", { name: "Top Skills in Demand Over Time" }),
    ).toBeVisible();

    const skills = page.getByRole("list", { name: "Skills" });
    await expect(skills.getByRole("button", { name: /Python/ })).toBeVisible();
    await expect(skills.getByRole("button", { name: /C\+\+/ })).toBeVisible();
    await expect(skills.getByRole("button", { name: /ROS/ })).toBeVisible();
    await expect(
      page.getByRole("group", { name: /Job postings per month for/ }),
    ).toBeVisible();
  });

  test("highlights a skill when it is selected", async ({ page }) => {
    await mockApi(page);
    await page.goto("/trends");

    const python = page
      .getByRole("list", { name: "Skills" })
      .getByRole("button", { name: /Python/ });
    await expect(python).toHaveAttribute("aria-pressed", "false");
    await python.click();
    await expect(python).toHaveAttribute("aria-pressed", "true");
  });

  test("has zoom controls", async ({ page }) => {
    await mockApi(page);
    await page.goto("/trends");

    await expect(page.getByRole("button", { name: "Zoom in" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Zoom out" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Reset zoom" }),
    ).toBeVisible();
  });

  test("shows an empty state before any scrape is processed", async ({
    page,
  }) => {
    await mockApi(page, { trends: { months: [], skills: [] } });
    await page.goto("/trends");

    await expect(page.getByText("No skill trends yet")).toBeVisible();
  });

  test("shows an error when the API fails", async ({ page }) => {
    await mockApi(page, { trendsStatus: 503, trends: { detail: "down" } });
    await page.goto("/trends");

    await expect(
      page.getByText("Couldn't load skill trends right now"),
    ).toBeVisible();
  });
});
