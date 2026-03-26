import { defineConfig, devices } from "@playwright/test";

const port = process.env.PLAYWRIGHT_PORT || "4100";
const apiPort = process.env.PLAYWRIGHT_API_PORT || "9100";
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${port}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `API_PORT=${apiPort} node scripts/run-api.js`,
      url: `http://127.0.0.1:${apiPort}/health`,
      cwd: "../..",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: `API_PORT=${apiPort} PORT=${port} npm run dev:no-open`,
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
});
