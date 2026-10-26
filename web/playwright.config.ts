import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "*.spec.ts",
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["junit", { outputFile: "test-results/junit.xml" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:4318",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "vite preview --host 127.0.0.1 --port 4318 --strictPort",
    url: "http://127.0.0.1:4318",
    reuseExistingServer: false,
  },
});
