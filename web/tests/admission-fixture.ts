import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";
import policy from "../src/release-policy.json" with { type: "json" };
export const admissionRoute = `**/data/admission/${policy.registry_sha256}.json`;
export const admissionBytes = readFileSync(
  new URL("../../config/admission-2026-v1.json", import.meta.url),
);
export async function admission(page: Page) {
  await page.route(admissionRoute, (route) =>
    route.fulfill({ body: admissionBytes, contentType: "application/json" }),
  );
}
