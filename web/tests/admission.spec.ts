import { test, expect } from "@playwright/test";
import { admission, admissionBytes, admissionRoute } from "./admission-fixture";

test.beforeEach(async ({ page }) => {
  // Intentionally independent from observed player data; no live or local export.
  await page.route("**/data/latest.json", (route) =>
    route.fulfill({ status: 404 }),
  );
});
test("all position modules remain inspectable when the Explorer snapshot is absent", async ({
  page,
}) => {
  await admission(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Snapshot unavailable" }),
  ).toBeVisible();
  const section = page.locator("#availability");
  await expect(section.getByRole("button")).toHaveCount(17);
  await expect(section.getByText("No CAVAA rankings published.")).toBeVisible();
  await section.getByRole("button", { name: "WR", exact: true }).click();
  await expect(
    section.getByText("Recorded WR targets only; partial receiving coverage"),
  ).toBeVisible();
  await section.getByText("Player uncertainty", { exact: true }).click();
  await expect(
    section.getByText(/primary conditional intervals fail/),
  ).toBeVisible();
  await expect(
    section.getByRole("link", { name: "calibration evidence ↗" }),
  ).toHaveAttribute(
    "href",
    /\/blob\/[a-f0-9]{40}\/docs\/audits\/2026-10-28-calibration.json$/,
  );
  await section.getByRole("button", { name: "CB", exact: true }).click();
  await section.getByText("Individual attribution", { exact: true }).click();
  await expect(
    section.getByText(/Neither defender model passes/),
  ).toBeVisible();
  await section.getByRole("button", { name: "LS", exact: true }).click();
  await section.getByText("Data coverage", { exact: true }).click();
  await expect(
    section
      .locator("details")
      .filter({ has: page.getByText("Data coverage", { exact: true }) })
      .getByText(/No individual model and validated/),
  ).toBeVisible();
  await expect(
    section.getByText("Not available", { exact: true }),
  ).toBeVisible();
  await expect(
    section.getByText(/does not refresh game coverage/),
  ).toBeVisible();
  await expect(section.getByRole("table")).toHaveCount(0);
});
test("corrupted admission cannot assert availability and retry verifies the pinned bytes", async ({
  page,
}) => {
  await page.route(admissionRoute, (route) =>
    route.fulfill({
      body: admissionBytes.toString().replace('"not_admitted"', '"admitted"'),
      contentType: "application/json",
    }),
  );
  await page.goto("/");
  const section = page.locator("#availability");
  await expect(section.getByRole("alert")).toContainText("integrity");
  await expect(section.getByText("No CAVAA rankings published.")).toHaveCount(
    0,
  );
  await expect(section.getByRole("group")).toHaveCount(0);
  await page.unroute(admissionRoute);
  await admission(page);
  await section.getByRole("button", { name: "Retry availability" }).click();
  await expect(
    section.getByRole("button", { name: "QB", exact: true }),
  ).toBeVisible();
});
test("mobile position selection remains keyboard accessible without document overflow", async ({
  page,
}) => {
  await admission(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const cb = page
    .locator("#availability")
    .getByRole("button", { name: "CB", exact: true });
  await cb.focus();
  await page.keyboard.press("Enter");
  await expect(cb).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("region", { name: "CB measurement status" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
