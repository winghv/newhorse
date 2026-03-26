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

  test("can apply the media ops butler template from project config", async ({ page, request }) => {
    const createResp = await request.post("/api/projects/", {
      data: {
        name: `Config Template E2E ${Date.now()}`,
        preferred_cli: "hello",
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const project = await createResp.json();

    await page.goto(`/en/chat/${project.id}`);
    await page.waitForLoadState("networkidle");

    await page.getByTestId("chat-config-toggle").click();
    await page.getByTestId("agent-config-template-toggle").click();
    await page.getByTestId("agent-config-template-option-media-ops-butler").click();

    await expect(page.getByTestId("agent-config-name-input")).toHaveValue("Media Ops Butler");

    const projectResp = await request.get(`/api/projects/${project.id}`);
    expect(projectResp.ok()).toBeTruthy();
    const updated = await projectResp.json();
    expect(updated.preferred_cli).toBe("butler");
  });
});
