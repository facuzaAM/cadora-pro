import { defineConfig, devices } from "@playwright/test";

/**
 * E2E / smoke tests for the frontend.
 *
 * Uses the production build (`npm run build` + `next start`) as the server so
 * it exercises the real bundle. The smoke spec only needs public pages, so it
 * runs without a backend. Full authenticated flows (login → upload →
 * detection → editor → export) need the API + DB and are a separate effort.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run build && npm run start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 300000,
  },
});
