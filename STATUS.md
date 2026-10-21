# Project status

Updated: October 20, 2026, America/New_York.

## Current unit

The owner merged PRs #1 and #2; their CI passed. Today's feature branch is
`codex/pregame-first-unit-inputs`, based on current main. Check GitHub for its
review/CI state; never merge automatically.

Implemented:

- First-unit weighting, both sensitivity benchmarks, and independent qualification,
  source, attribution and comparability gates.
- Immutable PBP, season-roster, depth-chart and schedule capture, published-hash
  verification, source/license provenance and offline replay.
- Conservative game reconciliation: terminal PBP end markers, matching schedule
  scores, explicit missing-game failures and observed-complete-by timestamps.
- Latest pre-kickoff whole-team chart selection, reviewed formation/slot mappings,
  freshness and identity checks, and a guard against partial benchmark populations.
- Content-addressed derived input reports with reproducible offline replay.
- 78 tests pass locally. The PR carries current remote CI results.
- Development lock, separate evening automation, evaluation/defense plans, roadmap,
  and daily learning reports.

## Current live evidence

The [October 20 audit](docs/audits/2026-10-20-pregame-inputs.json) records exact
receipts and report IDs. The schedule contains 272 regular-season games for 2026.
Fresh PBP reconciles 93 games through Week 6, including Monday night: 186 team-game
cells. The old PBP receipt correctly fails for missing `2026_06_WAS_SF`.

All seven offensive chart cohorts have complete coverage. The adapter retains
three first-unit WR slots per team-game, including source ranks 2 and 3.
Eleven issues block IDL, CB, S and LS cohorts: six PHI IDL identity failures, four
DAL CB/S role ambiguities and one missing DEN first-unit long-snapper slot.
These are coverage findings, not validated contribution estimates. Defensive
chart roles remain provisional formation proxies; complete cells do not admit
EDGE or LB to the leaderboard.

All 186 chart selections use data retrieved after kickoff. Their row timestamps
support retrospective selection, not verified vintage availability. The benchmark
input guard requires explicit acknowledgment for such research. Both the current
report and the old-PBP negative control replayed with network construction blocked.
Archives and derived reports currently reside locally; durable off-machine
retention remains a production requirement.

No model has been fitted, no real rankings published, and no position has passed
contribution admission. The website and production refresh are not deployed.
Every source/input report retains `ranking_ready=false`.

## Next highest-priority unit — October 21

Implement the dedicated historical participation adapter under its documented
CC-BY-SA terms, audit 2025 lineups, canonical IDs and joins against PBP, and create
reproducible inputs for the required defensive information-loss experiment. Its
rich-versus-degraded model comparison has not run. Derive degraded historical snap
fractions from permitted participation for the experiment; resolving a permitted
live-2026 workload source remains a separate product dependency. Do not quietly
substitute PFR data with unresolved rights.

Then normalize unique offensive opportunities and verify roster/stint evidence for
missed games, trades and late signings. Depth-chart membership does not establish
active status or exposure. Build the transparent regularized baseline by October
23, with historical splits and collinearity checks, before adding complexity.

Resolve flagged identities through auditable crosswalks or keep their cells
blocked. Document any change to formation roles, first-unit policy, freshness or
retrospective-data usage. Avoid tuning policies to obtain desired leaders.

## Review focus and release gates

Review [PREGAME_INPUTS.md](docs/PREGAME_INPUTS.md), the receiver slot convention,
conservative time semantics, missing-game/slot failures, and role-specific blockers.
See [today's learning report](docs/learning/2026-10-20.md).
Historical qualification testing, player attribution, defensive comparability,
uncertainty, roster/exposure denominators, durable retention and publication
controls remain required before ranking release.

Launch remains November 7. No purchases or paid services were enabled. The
existing Opponent Intelligence project and automation remain independent.
