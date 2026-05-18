import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — the Querymancer demo walkthrough.
 *
 * Default target is the deployed app. Override with PLAYWRIGHT_BASE_URL to
 * point at a local `npm run dev` (http://localhost:3000) instead.
 *
 * `video: "on"` records every run. `e2e/demo.spec.ts` is scripted as a
 * watchable, narratable walkthrough, so the recording doubles as the README
 * demo asset — see the spec header for the MP4/GIF conversion steps.
 *
 * This also satisfies the plan's §17 frontend smoke-test requirement.
 */
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/.artifacts",
  // The walkthrough fires four /query calls. On the free tier each takes
  // ~12-25s and may back off through a 503 — give the whole test room.
  timeout: 9 * 60 * 1000,
  expect: { timeout: 2 * 60 * 1000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "https://querymancer.vercel.app",
    video: "on",
    trace: "retain-on-failure",
    actionTimeout: 30 * 1000,
  },
  projects: [
    {
      name: "chromium",
      // 1440x900 keeps all three panels (sidebar | chat | results) on screen,
      // which is what makes the recording read as a finished product.
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
});
