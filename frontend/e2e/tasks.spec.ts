import { test, expect } from "@playwright/test";

test.describe("Task Management", () => {
  test("should display task list page", async ({ page }) => {
    await page.goto("/tasks");
    await expect(page.locator("text=Evaluation Tasks")).toBeVisible();
  });

  test("should navigate to create task page", async ({ page }) => {
    await page.goto("/tasks");
    await page.click("text=Create Task");
    await expect(page).toHaveURL(/\/tasks\/create/);
    await expect(page.locator("text=Create Evaluation Task")).toBeVisible();
  });

  test("should show 404 for unknown route", async ({ page }) => {
    await page.goto("/nonexistent");
    await expect(page.locator("text=404")).toBeVisible();
  });
});
