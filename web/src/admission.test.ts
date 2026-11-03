import registryBytes from "../../config/admission-2026-v1.json?raw";
import { describe, expect, it } from "vitest";
import {
  AdmissionSchema,
  evidenceUrl,
  loadAdmission,
  registryPath,
} from "./admission";
const registry = () => JSON.parse(registryBytes);
const fake =
  (body: string = registryBytes): typeof fetch =>
  async () =>
    new Response(body);

describe("reviewed module availability", () => {
  it("accepts the real Python-validated registry and retains all 17 roles without scores", () => {
    const d = AdmissionSchema.parse(registry());
    expect(Object.keys(d.modules)).toHaveLength(17);
    expect(
      Object.values(d.modules).every((m) => m.decision === "not_admitted"),
    ).toBe(true);
    expect(d.policy.eligibility_filters_benchmark).toBe(false);
    expect(d.policy.recency_discount).toBe(false);
    expect(evidenceUrl(d.sources.decision_record)).toMatch(
      /^https:\/\/github.com\/AryanParte\/nfl-player-value\/blob\/[a-f0-9]{40}\/docs\/decisions\//,
    );
  });
  it.each([
    (d: any) => {
      d.modules.qb_observed.decision = "admitted";
    },
    (d: any) => {
      d.modules.qb_observed.cavaa_ep = 0;
    },
    (d: any) => {
      delete d.modules.cb_defense;
    },
    (d: any) => {
      d.modules.wr_targeted.role = "QB";
    },
    (d: any) => {
      delete d.modules.qb_observed.gates.comparability;
    },
    (d: any) => {
      d.modules.qb_observed.gates.uncertainty = "offense_accounting";
    },
    (d: any) => {
      d.modules.qb_observed.gates.uncertainty = "constructor";
    },
    (d: any) => {
      d.findings.offense_data.evidence_refs = ["unknown"];
    },
    (d: any) => {
      d.sources.decision_record.path = "docs/../../secret";
    },
    (d: any) => {
      d.policy.eligibility_filters_benchmark = true;
    },
    (d: any) => {
      d.policy.recency_discount = true;
    },
  ])("rejects admission, scope, evidence and policy drift", (mutate) => {
    const d = registry();
    mutate(d);
    expect(AdmissionSchema.safeParse(d).success).toBe(false);
  });
  it("loads only the build-pinned exact record under a subdirectory", async () => {
    const urls: string[] = [];
    const fetcher: typeof fetch = async (url) => {
      urls.push(String(url));
      return fake()(url);
    };
    expect(
      (
        await loadAdmission(
          new URL("https://example.com/nfl/"),
          undefined,
          fetcher,
        )
      ).season,
    ).toBe(2026);
    expect(urls).toEqual([`https://example.com/nfl/${registryPath}`]);
    // Semantically identical JSON still isn't the approved byte sequence.
    await expect(
      loadAdmission(
        new URL("https://example.com/"),
        undefined,
        fake(JSON.stringify(registry())),
      ),
    ).rejects.toThrow("integrity");
  });
  it("fails explicitly on a missing or oversized record", async () => {
    await expect(
      loadAdmission(
        new URL("https://example.com/"),
        undefined,
        async () => new Response("", { status: 404 }),
      ),
    ).rejects.toThrow("missing");
    await expect(
      loadAdmission(
        new URL("https://example.com/"),
        undefined,
        fake(" ".repeat(1_000_001)),
      ),
    ).rejects.toThrow("size");
  });
});
