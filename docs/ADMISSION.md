# Module admission contract

The [November 2 decision](decisions/2026-11-02-module-admission.md) withholds CAVAA
scores for all 17 current role modules. The overdue October 30 freeze is recorded
on its actual date. This turns research limitations into an executable prerequisite
for future publication; it does not create a ranking or a deployed publisher.

## Three separate questions

1. **Can we observe/model the player?** A small sample can inform fitting and
   benchmark membership even when the player cannot qualify for a leaderboard.
2. **Does the player meet participation rules?** The provisional three-game and
   position-specific opportunity rules still apply independently of admission.
3. **May this contribution module supply a CAVAA score?** This requires evidence
   about data, benchmark, denominators, accounting, attribution, uncertainty and
   cross-position comparability. A participation pass cannot answer this question.

The registry preserves the first-unit primary comparison, both sensitivity
benchmarks, cumulative expected points, no recency discount and no eligibility
filter on benchmark membership. No existing fit, interval or threshold changes.

## Version 1 and evidence

[`config/admission-2026-v1.json`](../config/admission-2026-v1.json) contains exact
module IDs, roles, scope labels, related research plan references, seven evidence
gates and reasons. All roles from the existing contracts are covered: QB, RB, WR,
TE, OT, OG, C, IDL, EDGE, LB, CB, S, K, P, LS, KR and PR. The specialist/OL entries
record unimplemented modules; they do not invent fitted effects. Generic defensive
research references do not claim that position-specific defender fits exist.

Thirteen SHA-256 references bind three model plans, the benchmark/eligibility
implementations, seven dated audits and the dated decision. The validator checks
every byte hash, exact field sets, required modules/gates, scope/model consistency,
timezone-aware decision date and policy values. Duplicate JSON keys, nonfinite
constants, unknown references, path escapes and malformed fields fail explicitly.
An accounting finding cannot be reused as uncertainty evidence.

`passed`, `failed`, `insufficient` and `not_evaluated` describe evidence for a
specific gate. Successful component reconstruction is not correct attribution.
The failed defensive prediction criterion is not proof that defenders lack value.
Failed simulated interval coverage is not a measured real-player error rate.

**Version 1 cannot grant positive score admission**, even if a caller changes a
Boolean or calls the result experimental. A future positive decision needs a new
reviewed contract/registry version and the evidence described in the dated record.
The returned objects use immutable tuples; changing a summary cannot mutate a
decision. Unavailable `cavaa_ep` and `rank` values remain null, never zero.

## Use from the repository root

```sh
PYTHONPATH=src python -m nfl_value.admission_cli check
```

This verifies the committed evidence and prints all module blockers and the
registry's byte digest. Exit 0 means **the non-admission registry is internally
valid**, not that rankings are ready. It does not refresh source coverage or
rerun the historical models. Restoring this registry on a clean machine uses the
matching Git revision; a hash alone cannot restore missing NFL source objects.

A prospective score caller must pin the reviewed registry digest:

```sh
PYTHONPATH=src python -m nfl_value.admission_cli require-score qb_observed \
  --role QB --registry-sha256 3ef6eac4de93a8b9a878eec24b50e8db550c7fd04d309e8501fc98c4ba5d89c7
```

The example pins the reviewed November 2 registry.
Pin the reviewed bytes; computing a new digest from an untrusted candidate is not
approval. Hash matching establishes integrity, not authenticity or scientific
validity.
This command intentionally fails for every v1 module, with explicit blockers.
Unknown modules, role mismatches and an altered digest also fail. Do not interpret
failure as a reason to fall back to an unguarded numerical estimate. The API
equivalents are `load_registry(..., expected_sha256=...)` and `require_score(...)`.
`AdmissionRegistry.qualify(exposure, module_id, ...)` delegates to the existing
participation rules while preserving non-admission. No score is an eligibility
input and no benchmark population is constructed from qualification output.

The command is read-only and uses no network, new dependency, credentials or
service. It opens no publication pointer. The regression asserting unchanged
files after rejection tests this gate only, not a future publisher's atomicity.

## Remaining production integration

The [dashboard availability panel and static review command](STATIC_REVIEW.md)
now consume the exact pinned registry bytes. The panel preserves all 17 roles,
scope labels and evidence reasons with no numerical values. The review command
also validates evidence-link Git bytes. This is an exploratory presentation;
the registry and game cutoff remain separate and no positive admission is possible.

The actual ranking schema, source-readiness/freshness checks, model numerical
replay, validated stints and benchmark coverage, immutable release manifest,
position admission, deployment concurrency and last-good publication handling
must still be connected end to end. A future release must pin the registry digest
alongside source/model/benchmark versions, check every scored module and reject
the whole candidate before any pointer update. Unknown or duplicate module claims,
mixed scopes and unavailable contributions must not silently become full-player
scores. Preserve prior releases when validation fails.

The existing Defense Explorer contract still independently rejects non-null CAVAA
and rank fields. This unit leaves its payload/replay schema intact and does not
attach new admission metadata to old archived payloads. The next product unit
should expose module availability and the supporting reasons in the dashboard,
with accurate archived/live labels and a reproducible static release bundle.
