import { test, expect } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`restored Explorer loads exact release at ${width}px`, async ({
    page,
    request,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("requestfailed", (req) => errors.push(req.url()));
    await page.setViewportSize({ width, height: 1000 });
    const record = await (await request.get("release.json")).json();
    const manifest = await (await request.get("review-manifest.json")).json();
    expect(record.ranking_ready).toBe(false);
    expect(record.explorer_report).toBe(manifest.explorer_report);
    expect(record.code_revision).toBe(manifest.code_revision);
    await page.goto("./");
    await expect(
      page.getByRole("heading", { name: "Defense Explorer." }),
    ).toBeVisible();
    await expect(
      page.getByText("Not estimated", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Download snapshot" }),
    ).toHaveAttribute("href", `./data/${manifest.explorer_snapshot}.json`);
    await expect(page.locator(".hero")).toContainText(
      `INCLUDES WEEK ${manifest.coverage.through_week}`,
    );
    await expect(page.locator("#availability").getByRole("alert")).toHaveCount(
      0,
    );
    await expect(page.locator("#availability").getByRole("button")).toHaveCount(
      17,
    );
    await expect(
      page.locator("#availability").getByText("No CAVAA rankings published."),
    ).toBeVisible();
    await expect(
      page.getByText("SYNTHETIC TEST DATA · Not real NFL observations"),
    ).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(errors).toEqual([]);
  });
}
