import { z } from "zod";
import policy from "./release-policy.json";

export const GROUPS = {
  Offense: ["QB", "RB", "WR", "TE", "OT", "OG", "C"],
  Defense: ["IDL", "EDGE", "LB", "CB", "S"],
  "Special teams": ["K", "P", "LS", "KR", "PR"],
} as const;
const MODULE_ROLES: Record<string, string> = {
  qb_observed: "QB",
  rb_on_ball: "RB",
  wr_targeted: "WR",
  te_targeted: "TE",
  ot_blocking: "OT",
  og_blocking: "OG",
  c_blocking: "C",
  idl_defense: "IDL",
  edge_defense: "EDGE",
  lb_defense: "LB",
  cb_defense: "CB",
  s_defense: "S",
  k_kicking: "K",
  p_punting: "P",
  ls_snapping: "LS",
  kr_returns: "KR",
  pr_returns: "PR",
};
export const GATES = {
  data: "Data coverage",
  benchmark: "Positional benchmark",
  denominator: "Workload & eligibility",
  accounting: "Expected-point accounting",
  attribution: "Individual attribution",
  uncertainty: "Player uncertainty",
  comparability: "Cross-position comparison",
} as const;
export const STATUSES = {
  passed: "Passed for this scope",
  failed: "Validation failed",
  insufficient: "More evidence needed",
  not_evaluated: "Not evaluated",
} as const;
const gate = z.enum(
  Object.keys(GATES) as [keyof typeof GATES, ...(keyof typeof GATES)[]],
);
const ref = z.string().regex(/^[a-z][a-z0-9_]*$/);
const refs = z
  .array(ref)
  .refine((a) => new Set(a).size === a.length, "Duplicate references");
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const path = z
  .string()
  .regex(
    /^(?:config|docs|src)\/(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.(?:json|md|py)$/,
  );
export const AdmissionSchema = z
  .object({
    schema_version: z.literal(1),
    decision_version: z.literal("2026-11-02-v1"),
    decided_at: z.literal("2026-11-02T19:53:56+00:00"),
    season: z.literal(2026),
    policy: z
      .object({
        metric: z.literal("cumulative_expected_point_cavaa"),
        primary_benchmark: z.literal("first_unit"),
        sensitivity_benchmarks: z.tuple([
          z.literal("equal_player"),
          z.literal("opportunity_weighted"),
        ]),
        first_unit_weighting: z.literal(
          "equal-team-completed-game-role-slot-v1",
        ),
        eligibility_policy: z.literal("provisional-2026-v1"),
        eligibility_filters_benchmark: z.literal(false),
        recency_discount: z.literal(false),
      })
      .strict(),
    sources: z.record(ref, z.object({ path, sha256: hash }).strict()),
    findings: z.record(
      ref,
      z
        .object({
          status: z.enum(["passed", "failed", "insufficient", "not_evaluated"]),
          reason: z.string().trim().min(1),
          evidence_refs: refs.min(1),
          applies_to: z
            .array(gate)
            .min(1)
            .refine((a) => new Set(a).size === a.length),
        })
        .strict(),
    ),
    modules: z.record(
      ref,
      z
        .object({
          role: z.string(),
          scope_label: z.string().trim().min(1),
          decision: z.literal("not_admitted"),
          model_spec_refs: refs,
          gates: z.record(gate, ref),
        })
        .strict(),
    ),
  })
  .strict()
  .superRefine((d, ctx) => {
    const fail = (message: string) => ctx.addIssue({ code: "custom", message });
    if (Object.keys(d.modules).length !== Object.keys(MODULE_ROLES).length)
      fail("Incomplete module inventory");
    for (const [id, m] of Object.entries(d.modules)) {
      if (MODULE_ROLES[id] !== m.role) fail("Module and role disagree");
      if (m.model_spec_refs.some((r) => !Object.hasOwn(d.sources, r)))
        fail("Unknown model reference");
      if (
        Object.entries(m.gates).some(
          ([g, f]) =>
            !Object.hasOwn(d.findings, f) ||
            !d.findings[f].applies_to.includes(g as keyof typeof GATES),
        )
      )
        fail("Unknown or inapplicable gate finding");
      if (
        Object.values(m.gates).every((f) => d.findings[f]?.status === "passed")
      )
        fail("Missing non-admission reason");
    }
    for (const f of Object.values(d.findings)) {
      if (f.evidence_refs.some((r) => !Object.hasOwn(d.sources, r)))
        fail("Unknown evidence reference");
    }
  });
export type Admission = z.infer<typeof AdmissionSchema>;
export const registryPath = `data/admission/${policy.registry_sha256}.json`;
export function evidenceUrl(source: Admission["sources"][string]) {
  return `https://github.com/AryanParte/nfl-player-value/blob/${policy.registry_revision}/${source.path}`;
}
export async function loadAdmission(
  base: URL,
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<Admission> {
  const response = await fetcher(new URL(registryPath, base), {
    signal,
    cache: "no-cache",
  });
  if (!response.ok)
    throw new Error(
      "The reviewed availability record is missing. No admission decision has been displayed.",
    );
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength > 1_000_000)
    throw new Error("Availability record exceeds the supported size.");
  const digest = [
    ...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
  ]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  if (digest !== policy.registry_sha256)
    throw new Error(
      "Availability integrity check failed. No admission decision has been displayed.",
    );
  return AdmissionSchema.parse(
    JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)),
  );
}
