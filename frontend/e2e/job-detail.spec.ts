import { expect, test } from "@playwright/test";
import { JOB_DETAIL, JOB_ID, JOBS, mockApi } from "./mock-api";

test.describe("Job detail", () => {
  test("shows the posting", async ({ page }) => {
    await mockApi(page);
    await page.goto(`/jobs?id=${JOB_ID}`);

    await expect(
      page.getByRole("heading", { name: JOB_DETAIL.title }),
    ).toBeVisible();
    await expect(page.getByText(JOB_DETAIL.raw_description)).toBeVisible();
    await expect(page.getByText(JOB_DETAIL.requirements)).toBeVisible();
    await expect(page.getByText("Acme Autonomy").first()).toBeVisible();
    await expect(page.getByText("Python", { exact: true })).toBeVisible();
    await expect(page.getByText(/150,000/).first()).toBeVisible();
  });

  test("opens from a search result and goes back", async ({ page }) => {
    await mockApi(page, {
      detail: { ...JOB_DETAIL, job_id: JOBS[0].job_id, title: JOBS[0].title },
    });
    await page.goto("/search");

    await page.getByRole("link", { name: /Perception Engineer 1$/ }).click();

    await expect(page).toHaveURL(/\/jobs\?id=/);
    await expect(
      page.getByRole("heading", { name: JOBS[0].title }),
    ).toBeVisible();

    await page.getByRole("link", { name: "← Back to jobs" }).first().click();
    await expect(page).toHaveURL(/\/search/);
  });

  test("says when the job does not exist", async ({ page }) => {
    await mockApi(page, { detail: null });
    await page.goto(`/jobs?id=${JOB_ID}`);

    await expect(page.getByText("Job not found")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "← Back to jobs" }),
    ).toBeVisible();
  });
});
