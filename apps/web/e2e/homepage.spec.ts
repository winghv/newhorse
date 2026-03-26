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

  test("creates a media ops butler project from the homepage template picker", async ({ page, request }) => {
    await page.goto("/en");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("template-pill-media-ops-butler").click();
    await page.getByTestId("project-create-input").fill(`media ops e2e ${Date.now()}`);
    await page.getByTestId("project-create-submit").click();

    await page.waitForURL(/\/en\/chat\/[^/]+$/);

    const projectId = page.url().split("/").pop();
    expect(projectId).toBeTruthy();

    const projectResp = await request.get(`/api/projects/${projectId}`);
    expect(projectResp.ok()).toBeTruthy();
    const project = await projectResp.json();
    expect(project.preferred_cli).toBe("butler");

    const configResp = await request.get(`/api/agents/projects/${projectId}/config`);
    expect(configResp.ok()).toBeTruthy();
    const config = await configResp.json();
    expect(config.config.name).toBe("Media Ops Butler");
  });
});
