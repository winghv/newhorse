import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3000";
const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("Newhorse Platform UX Verification", () => {
  // ─── Homepage ───────────────────────────────────────────
  test("1. Homepage loads and shows project list", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01-homepage.png`, fullPage: true });

    // Check title
    await expect(page).toHaveTitle(/Newhorse/);

    // Should show some UI element indicating the platform
    const body = await page.textContent("body");
    console.log("Homepage text (first 300 chars):", body?.substring(0, 300));
  });

  // ─── Create Project ─────────────────────────────────────
  test("2. Create a new project", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Look for create/new project button
    const createBtn = page.locator('button, a').filter({ hasText: /创建|新建|create|new/i }).first();
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/02-create-project-dialog.png`, fullPage: true });

      // Fill project name if there's an input
      const nameInput = page.locator('input[type="text"], input[name*="name"], input[placeholder*="名称"], input[placeholder*="name"]').first();
      if (await nameInput.isVisible()) {
        await nameInput.fill("E2E Test Project");
      }

      // Look for template selector
      const templateSelect = page.locator('select, [role="combobox"], [role="listbox"]').first();
      if (await templateSelect.isVisible()) {
        await page.screenshot({ path: `${SCREENSHOT_DIR}/02b-template-selector.png`, fullPage: true });
      }

      // Submit
      const submitBtn = page.locator('button[type="submit"], button').filter({ hasText: /创建|确定|submit|create|保存/i }).first();
      if (await submitBtn.isVisible()) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: `${SCREENSHOT_DIR}/02c-after-create.png`, fullPage: true });
      }
    } else {
      console.log("No create button found on homepage");
      await page.screenshot({ path: `${SCREENSHOT_DIR}/02-no-create-btn.png`, fullPage: true });
    }
  });

  // ─── Chat Page ──────────────────────────────────────────
  test("3. Chat page layout and WebSocket", async ({ page }) => {
    // First get a project ID
    const res = await page.request.get(`${BASE}/api/projects/`);
    const projects = await res.json();
    const projectId = projects[0]?.id;
    if (!projectId) {
      console.log("No projects found, skipping chat test");
      return;
    }

    await page.goto(`${BASE}/chat/${projectId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-page.png`, fullPage: true });

    // Check key UI elements
    const connectionStatus = page.locator("text=Connected, text=Disconnected").first();
    const statusText = await connectionStatus.textContent().catch(() => "not found");
    console.log("Connection status:", statusText);

    // Check file panel is visible
    const filePanel = page.locator('[class*="border-r"]').first();
    const filePanelVisible = await filePanel.isVisible();
    console.log("File panel visible:", filePanelVisible);

    // Check input box
    const input = page.locator('input[placeholder*="message"], input[placeholder*="消息"], textarea').first();
    const inputVisible = await input.isVisible();
    console.log("Input box visible:", inputVisible);

    // Check send button
    const sendBtn = page.locator('button').filter({ has: page.locator('svg') }).last();
    console.log("Send button visible:", await sendBtn.isVisible());
  });

  // ─── File Panel ─────────────────────────────────────────
  test("4. File panel toggle and file tree", async ({ page }) => {
    const res = await page.request.get(`${BASE}/api/projects/`);
    const projects = await res.json();
    const projectId = projects[0]?.id;
    if (!projectId) return;

    // Create a test file for the project via API
    await page.request.put(`${BASE}/api/projects/${projectId}/files/test-e2e.txt`, {
      data: { content: "E2E test file content" },
    });

    await page.goto(`${BASE}/chat/${projectId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Screenshot with file panel open
    await page.screenshot({ path: `${SCREENSHOT_DIR}/04a-file-panel-open.png`, fullPage: true });

    // Toggle file panel
    const toggleBtn = page.locator('button[title*="file"], button[title*="Files"], button[title*="Hide"], button[title*="Show"]').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04b-file-panel-closed.png`, fullPage: true });

      // Toggle back
      await toggleBtn.click();
      await page.waitForTimeout(500);
    }

    // Check if file tree shows any files
    const fileItems = page.locator('[class*="cursor-pointer"]').filter({ hasText: /\.\w+$/ });
    const fileCount = await fileItems.count();
    console.log("Files visible in tree:", fileCount);

    // Click on a file if available
    if (fileCount > 0) {
      await fileItems.first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04c-file-selected.png`, fullPage: true });
    }
  });

  // ─── Visual Preview ─────────────────────────────────────
  test("5. Visual preview for HTML files", async ({ page }) => {
    const res = await page.request.get(`${BASE}/api/projects/`);
    const projects = await res.json();
    const projectId = projects[0]?.id;
    if (!projectId) return;

    // Ensure an HTML file exists
    await page.request.put(`${BASE}/api/projects/${projectId}/files/preview-test.html`, {
      data: {
        content: '<!DOCTYPE html><html><head><title>Preview Test</title></head><body style="background:#1a1a2e;color:#fff"><h1>Preview Works!</h1></body></html>',
      },
    });

    await page.goto(`${BASE}/chat/${projectId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Find and click the HTML file in the tree
    const htmlFile = page.locator('text=preview-test.html').first();
    if (await htmlFile.isVisible()) {
      // Look for a preview button near the HTML file
      await htmlFile.hover();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/05a-html-file-hover.png`, fullPage: true });

      // Click the file or preview button
      await htmlFile.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/05b-preview-or-content.png`, fullPage: true });

      // Check for preview/code toggle buttons
      const previewBtn = page.locator('button').filter({ hasText: /preview|预览/i }).first();
      const codeBtn = page.locator('button').filter({ hasText: /code|代码|源码/i }).first();

      if (await previewBtn.isVisible()) {
        await previewBtn.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: `${SCREENSHOT_DIR}/05c-preview-iframe.png`, fullPage: true });
      }

      if (await codeBtn.isVisible()) {
        await codeBtn.click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: `${SCREENSHOT_DIR}/05d-code-view.png`, fullPage: true });
      }

      // Check for iframe
      const iframe = page.locator("iframe");
      const iframeCount = await iframe.count();
      console.log("Iframes found:", iframeCount);
    } else {
      console.log("HTML file not visible in tree");
      await page.screenshot({ path: `${SCREENSHOT_DIR}/05-no-html-file.png`, fullPage: true });
    }
  });

  // ─── Agent Config ───────────────────────────────────────
  test("6. Agent config UI", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Look for settings/config link on any project
    const settingsLink = page.locator('a, button').filter({ hasText: /设置|配置|config|setting/i }).first();
    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/06a-agent-config.png`, fullPage: true });
    } else {
      // Maybe config is on the chat page
      const res = await page.request.get(`${BASE}/api/projects/`);
      const projects = await res.json();
      const projectId = projects[0]?.id;
      if (projectId) {
        await page.goto(`${BASE}/chat/${projectId}`);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(1000);

        // Look for config/settings icon or button
        const configBtn = page.locator('button, a').filter({ hasText: /配置|设置|config|agent/i }).first();
        if (await configBtn.isVisible()) {
          await configBtn.click();
          await page.waitForTimeout(500);
          await page.screenshot({ path: `${SCREENSHOT_DIR}/06a-agent-config.png`, fullPage: true });
        } else {
          console.log("No config button found");
          await page.screenshot({ path: `${SCREENSHOT_DIR}/06-no-config-btn.png`, fullPage: true });
        }
      }
    }
  });

  // ─── Responsive Layout ──────────────────────────────────
  test("7. Responsive layout check", async ({ page }) => {
    const res = await page.request.get(`${BASE}/api/projects/`);
    const projects = await res.json();
    const projectId = projects[0]?.id;
    if (!projectId) return;

    await page.goto(`${BASE}/chat/${projectId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // Desktop view
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07a-desktop.png`, fullPage: true });

    // Tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07b-tablet.png`, fullPage: true });

    // Mobile view
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07c-mobile.png`, fullPage: true });
  });
});
