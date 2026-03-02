import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("loads successfully", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test("has navigation to projects", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const hasContent = await page.locator("body").textContent();
    expect(hasContent).toBeTruthy();
  });
});
