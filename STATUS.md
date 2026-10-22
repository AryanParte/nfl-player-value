# Project status

Updated: October 21, 2026, America/New_York.

## Current unit

The owner merged PR #3; main CI passed on Python 3.11–3.13. Today's feature
branch is `codex/defensive-participation-inputs`, based on current main. Check
GitHub for its review/CI state; never merge automatically.

Implemented:

- First-unit weighting, both sensitivity benchmarks and independent qualification,
  source, attribution and comparability gates.
- Immutable PBP, roster, depth-chart and schedule capture with offline replay.
- Conservative completed-game reconciliation, formation-aware pregame first-unit
  selection and guards against partial benchmark populations.
- Historical FTN participation capture with separate CC-BY-SA legal text and source
  declaration provenance; structural lineup validation and PBP join audits.
- Paired rich-play and degraded-team-game research inputs with identical cohorts,
  explicit game/row exclusions, source terms and exact offline replay.
- 101 tests pass locally, including 23 new participation/cohort/replay tests.
  The PR carries current remote CI results.
- Development lock, separate evening automation, evaluation/defense plans,
  documentation and daily learning reports.

## Current evidence

The [October 21 historical audit](docs/audits/2026-10-21-defense-inputs.json)
records exact 2025 receipts and derived object IDs. FTN has 45,184 rows in 285 games;
45,005 pass structural lineup checks. Of 272 scheduled REG games, the existing
completion policy reconciles 270. Among those, 32,575 candidate pass/run plays
have 37 invalid lineups across 29 games. The fixed whole-game cohort therefore
retains 29,059 plays in 241 games, or 482 defensive team-game rows. All 32 teams
are represented, with 12–17 games each. Selection loss is not uniform.

Two completion failures are informative: `2025_05_KC_JAX` and `2025_16_NE_BAL`
have matching scores and an end-game marker, but a higher-ID row describes an
earlier timeout/kneel. Numeric play ID is not guaranteed event order. Preserve
this v1 report; implement a separately versioned, tested evidence rule before
baseline admission. Do not silently waive completion checks.

The paired views replayed with network construction blocked, as did the previous
2026 source receipts and pregame report. New source/derived receipts identify
implementation `ac2078763ed6c2f59471cd8a178b1e0bd3f81023`.
The entire historical archive is retrospectively retrieved; no live-2026
participation or historical vintage availability is established. Reduced workload
fractions mean eligible pass/run appearances, not official defensive snaps.

The [October 20 2026 audit](docs/audits/2026-10-20-pregame-inputs.json) remains
unchanged: 93 reconciled games through Week 6, 186 team-game chart cells, complete
seven-role offensive chart coverage, and 11 blocked IDL/CB/S/LS cohort issues.
These input facts do not admit any position to the leaderboard.

No model has been fitted, no defensive information-loss comparison has run, and
no real ranking has been published. Defense Explorer, the React/TypeScript website
and independent production refresh are not deployed. All input reports retain
`ranking_ready=false`. Raw/derived archives currently reside locally; durable
off-machine retention remains a production requirement.

## Next highest-priority unit — October 22–23

Version and test completion evidence against the two reordered-event cases while
preserving old report replay. Normalize unique offensive opportunities and verify
roster/stint evidence for missed games, trades and late signings. Depth charts do
not establish active status or exposure. Build the transparent regularized
baseline with chronological splits, shared-value accounting and collinearity
checks; do not replace the scientific work with more ingestion infrastructure.

For the required October 24–27 defense comparison: audit additional historical
seasons, resolve player/position crosswalks, quantify selection loss, and fit rich
versus reduced models. Find a permitted live-2026 workload source and match its
actual information loss. Do not substitute PFR data with unresolved rights or
present this controlled aggregation alone as a live-source feasibility result.
Keep unsupported defensive contributions missing and deliver Defense Explorer.

## Review focus and release gates

Review [DEFENSE_INPUTS.md](docs/DEFENSE_INPUTS.md): source-specific attribution,
whole-game selection loss, exact paired denominators, team-outcome sign, and the
completion-order finding. See [today's learning report](docs/learning/2026-10-21.md).
Historical qualification tests, attribution, defensive comparability, uncertainty,
stint denominators, durable retention and publication controls remain release gates.

Launch remains November 7. No purchases or paid services were enabled. The
existing Opponent Intelligence project and automation remain independent.
