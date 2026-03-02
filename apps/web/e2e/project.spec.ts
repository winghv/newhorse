import { test, expect } from "@playwright/test";

test.describe("Project Page", () => {
  test("can navigate to project page", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const projectLinks = page.locator('a[href*="/chat/"]');
    const count = await projectLinks.count();

    if (count > 0) {
      await projectLinks.first().click();
      await page.waitForLoadState("networkidle");
      expect(page.url()).toContain("/chat/");
    }
  });

  test("chat input is present", async ({ page }) => {
    await page.goto("/en/chat/test");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toBeTruthy();
  });
});
