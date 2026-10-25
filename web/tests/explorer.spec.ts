import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { createHash } from "node:crypto";
import fixture from "./fixture.json" with { type: "json" };

async function snapshot(
  page: Page,
  value: unknown = fixture,
  wrongHash = false,
) {
  const body = JSON.stringify(value);
  const digest = wrongHash
    ? "0".repeat(64)
    : createHash("sha256").update(body).digest("hex");
  await page.route("**/data/latest.json", (route) =>
    route.fulfill({ json: { schema_version: 1, snapshot_id: digest } }),
  );
  await page.route(`**/data/${digest}.json`, (route) =>
    route.fulfill({ body, contentType: "application/json" }),
  );
  return digest;
}

test("loads evidence, labels synthetic data, and exposes provenance without scores", async ({
  page,
}) => {
  const digest = await snapshot(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Defense Explorer." }),
  ).toBeVisible();
  await expect(
    page.getByText("SYNTHETIC TEST DATA · Not real NFL observations"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Synthetic Player 1" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Download snapshot" }),
  ).toHaveAttribute("href", `./data/${digest}.json`);
  await expect(
    page.getByRole("columnheader", { name: "CHART GAMES" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Observed is not attributed." }),
  ).toBeVisible();
  await expect(page.getByText("Not estimated", { exact: true })).toBeVisible();
});

test("filters by role and team, handles empty search and reset", async ({
  page,
}) => {
  await snapshot(page);
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Chart role", exact: true })
    .selectOption("UNMAPPED");
  await expect(
    page.getByRole("button", { name: "Synthetic Player 2" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Synthetic Player 1" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Observed team", exact: true })
    .selectOption("NYJ");
  await expect(
    page.getByRole("button", { name: "Synthetic Player 4" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Synthetic Player 1" }),
  ).toHaveCount(0);
  await page
    .getByRole("searchbox", { name: "Find a player" })
    .fill("no such player");
  await expect(
    page.getByRole("heading", { name: "No matching players" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(
    page.getByRole("button", { name: "Synthetic Player 1" }),
  ).toBeVisible();
});

test("player details preserve half credits and unknown chart roles", async ({
  page,
}) => {
  await snapshot(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Synthetic Player 2" }).click();
  const panel = page.getByRole("complementary", {
    name: "Player evidence details",
  });
  await expect(
    panel.getByRole("heading", { name: "Synthetic Player 2" }),
  ).toBeVisible();
  await expect(panel.getByText("0.5", { exact: true })).toBeVisible();
  await panel.getByText("Inspect game evidence (1)").click();
  await expect(panel.getByText("Chart: No valid role record")).toBeVisible();
  await expect(panel.getByText("Not estimated", { exact: true })).toBeVisible();
});

test("mobile has no document overflow and remains keyboard operable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await snapshot(page);
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Synthetic Player 1" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const input = page.getByRole("searchbox", { name: "Find a player" });
  await input.focus();
  await page.keyboard.type("Player 3");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("combobox", { name: "Observed team", exact: true }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Synthetic Player 3" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page
      .getByRole("complementary", { name: "Player evidence details" })
      .getByRole("heading", { name: "Synthetic Player 3" }),
  ).toBeVisible();
});

test("negative team EPA remains negative and unavailable values are explicit", async ({
  page,
}) => {
  const changed = structuredClone(fixture);
  changed.team_games[0].defense_epa = null;
  changed.team_games[0].epa_observed_plays = 0;
  await snapshot(page, changed);
  await page.goto("/");
  await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Team context", exact: true })
    .selectOption("NYJ");
  await expect(page.getByText("-0.5", { exact: true })).toBeVisible();
});

test("hash failure withholds the entire payload", async ({ page }) => {
  await snapshot(page, fixture, true);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Snapshot unavailable" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("integrity");
  await expect(page.getByRole("table")).toHaveCount(0);
});

test("invented CAVAA is rejected even with a valid content hash", async ({
  page,
}) => {
  const changed: any = structuredClone(fixture);
  changed.players[0].cavaa = 40;
  await snapshot(page, changed);
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("quality checks");
  await expect(page.getByRole("table")).toHaveCount(0);
});

test("missing export offers a working retry without fabricated fallback data", async ({
  page,
}) => {
  await page.route("**/data/latest.json", (route) =>
    route.fulfill({ status: 404 }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("unavailable");
  await page.unroute("**/data/latest.json");
  await snapshot(page);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "The player ledger" }),
  ).toBeVisible();
});
