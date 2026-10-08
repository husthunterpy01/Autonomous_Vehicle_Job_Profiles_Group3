import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock-api";

/** The list is fetched in the browser, so once it shows the page has hydrated
 *  and clicks/typing are handled (acting earlier can be silently dropped). */
async function openSearch(page: Page) {
  await page.goto("/search");
  await expect(
    page.getByRole("link", { name: /Perception Engineer 1$/ }),
  ).toBeVisible();
}

test.describe("Find Jobs", () => {
  test("lists the first page of jobs", async ({ page }) => {
    await mockApi(page);
    await page.goto("/search");

    await expect(
      page.getByRole("heading", { name: "Find your next job" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Perception Engineer 1$/ }),
    ).toBeVisible();
    await expect(page.getByText("Page 1 of 4", { exact: true })).toBeVisible();
    await expect(page.getByText("23 jobs found")).toBeVisible();
  });

  test("searches by keyword", async ({ page }) => {
    const { listRequests } = await mockApi(page);
    await openSearch(page);

    await page.getByPlaceholder("Job title, skill or keyword").fill("Planning");
    await page.keyboard.press("Enter");

    await expect(
      page.getByRole("link", { name: /Planning Engineer 2$/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Perception Engineer 1$/ }),
    ).toHaveCount(0);
    expect(listRequests.some((p) => p.get("q") === "Planning")).toBe(true);
  });

  test("filters by country on Apply and clears the filters", async ({
    page,
  }) => {
    const { listRequests } = await mockApi(page);
    await openSearch(page);

    await page.getByLabel("Country").selectOption("Germany");
    // Nothing is requested until Apply is pressed.
    expect(listRequests.every((p) => p.get("country") === null)).toBe(true);
    await page.getByRole("button", { name: "Apply", exact: true }).click();

    await expect(
      page.getByRole("link", { name: /Planning Engineer 16$/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Perception Engineer 1$/ }),
    ).toHaveCount(0);
    expect(listRequests.at(-1)?.get("country")).toBe("Germany");
    await expect(page).toHaveURL(/country=Germany/);

    await page.getByRole("button", { name: "Clear" }).first().click();
    await expect(
      page.getByRole("link", { name: /Perception Engineer 1$/ }),
    ).toBeVisible();
  });

  test("sends the salary range to the API", async ({ page }) => {
    const { listRequests } = await mockApi(page);
    await openSearch(page);

    await page.getByLabel("Min salary (USD/yr)").fill("100000");
    await page.getByLabel("Max salary (USD/yr)").fill("250000");
    await page.getByRole("button", { name: "Apply", exact: true }).click();

    await expect
      .poll(() => listRequests.at(-1)?.get("salary_min"))
      .toBe("100000");
    expect(listRequests.at(-1)?.get("salary_max")).toBe("250000");
  });

  test("pages through the results", async ({ page }) => {
    const { listRequests } = await mockApi(page);
    await openSearch(page);

    await page.getByRole("button", { name: "Next", exact: true }).click();

    await expect(page.getByText("Page 2 of 4", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Planning Engineer 12$/ }),
    ).toBeVisible();
    expect(listRequests.at(-1)?.get("page")).toBe("2");

    await page.getByRole("button", { name: "Prev", exact: true }).click();
    await expect(page.getByText("Page 1 of 4", { exact: true })).toBeVisible();
  });

  test("shows an empty state when nothing matches", async ({ page }) => {
    await mockApi(page);
    await page.goto("/search?q=zzzz");

    await expect(page.getByText("No jobs found")).toBeVisible();
  });

  test("shows an error when the API fails", async ({ page }) => {
    await mockApi(page, { jobsStatus: 500 });
    await page.goto("/search");

    await expect(page.getByRole("alert")).toBeVisible();
  });
});
