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

  test("zooming resizes the chart and reset restores it", async ({ page }) => {
    await mockApi(page);
    await page.goto("/trends");

    const plot = page.getByTestId("chart-plot");
    const frame = page.getByTestId("chart-scroll");
    const zoomIn = page.getByRole("button", { name: "Zoom in" });
    const zoomOut = page.getByRole("button", { name: "Zoom out" });
    const reset = page.getByRole("button", { name: "Reset zoom" });
    const size = async () => ({
      width: Number(await plot.getAttribute("width")),
      height: Number(await plot.getAttribute("height")),
    });
    const scrolls = () =>
      frame.evaluate((el) => el.scrollWidth > el.clientWidth);

    // Starts at 100%: nothing to zoom out or reset, and the plot fits its frame.
    await expect(page.getByText("100%", { exact: true })).toBeVisible();
    await expect(zoomOut).toBeDisabled();
    await expect(reset).toBeDisabled();
    const base = await size();
    expect(base.width).toBeGreaterThan(0);
    expect(await scrolls()).toBe(false);

    // 150%: both axes grow by half and the plot now scrolls inside its frame.
    await zoomIn.click();
    await expect(page.getByText("150%", { exact: true })).toBeVisible();
    await expect(zoomOut).toBeEnabled();
    await expect(reset).toBeEnabled();
    await expect
      .poll(async () => (await size()).width)
      .toBeCloseTo(base.width * 1.5, 0);
    expect((await size()).height).toBeCloseTo(base.height * 1.5, 0);
    expect(await scrolls()).toBe(true);

    // 200%.
    await zoomIn.click();
    await expect(page.getByText("200%", { exact: true })).toBeVisible();
    await expect
      .poll(async () => (await size()).width)
      .toBeCloseTo(base.width * 2, 0);

    // Zoom out one step, then reset all the way.
    await zoomOut.click();
    await expect(page.getByText("150%", { exact: true })).toBeVisible();
    await expect
      .poll(async () => (await size()).width)
      .toBeCloseTo(base.width * 1.5, 0);
    await reset.click();
    await expect(page.getByText("100%", { exact: true })).toBeVisible();
    await expect.poll(size).toEqual(base);
    await expect(reset).toBeDisabled();
  });

  test("zoom in stops at the largest level", async ({ page }) => {
    await mockApi(page);
    await page.goto("/trends");

    const zoomIn = page.getByRole("button", { name: "Zoom in" });
    for (const label of ["150%", "200%", "300%", "400%"]) {
      await zoomIn.click();
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    }
    await expect(zoomIn).toBeDisabled();
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
