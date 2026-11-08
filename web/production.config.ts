import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "production.spec.ts",
  workers: 1,
  retries: 0,
  forbidOnly: true,
  outputDir: "production-results",
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "production-report" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:4319/nfl-player-value/",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "python3 -m http.server 4319 --bind 127.0.0.1 --directory ../artifacts/deployment/site",
    url: "http://127.0.0.1:4319/nfl-player-value/",
    reuseExistingServer: false,
  },
});
