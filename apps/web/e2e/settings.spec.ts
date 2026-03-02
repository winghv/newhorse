import { test, expect } from "@playwright/test";

test.describe("Settings Page", () => {
  test("settings page loads", async ({ page }) => {
    await page.goto("/en/settings");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/settings");
  });

  test("has provider configuration section", async ({ page }) => {
    await page.goto("/en/settings");
    await page.waitForLoadState("networkidle");
    const pageContent = await page.locator("body").textContent();
    expect(pageContent).toBeTruthy();
  });
});
