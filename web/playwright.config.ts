import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.PHASE4_BASE_URL ?? "http://127.0.0.1:15173",
    browserName: "chromium",
    screenshot: "only-on-failure",
    trace: "off",
  },
});
