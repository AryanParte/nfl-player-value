# Project status

Updated: October 18, 2026, America/New_York.

## Current unit

Foundation and statistical contracts are implemented on
`codex/foundation-and-benchmark-contracts`, pending human review. `main` contains
only the empty repository bootstrap. Do not merge or overwrite the feature branch
automatically.

Implemented:

- First-unit team/game/member weighting; equal-player and opportunity-weighted
  sensitivities; completed-game, pregame membership, ID and coverage contracts.
- Provisional role-specific qualification and three-game minimum; separate source,
  attribution, and cross-position comparability gates.
- Exact rounding for the bounded historical threshold grid; no score-based
  eligibility filter.
- A tested repository-wide development lease shared across linked worktrees.
- Python package, offline tests, CI, methodology, architecture, data/rights audit,
  evaluation plan, required defensive experiment, and learning log.
- Separate daily development heartbeat at 7:30 PM America/New_York, using the
  canonical clone. Existing Opponent Intelligence automation is untouched.

No real NFL data have been ingested by this repository, no model has been fitted,
and no positions have been admitted to a real CAVAA leaderboard. Test fixtures are
synthetic. The website and production refresh are not deployed.

## Next highest-priority unit — October 19

Implement immutable 2026 source ingestion and provenance manifests, beginning with
play-by-play, authoritative completed regular-season games, rosters/IDs, and
timestamped depth charts. Check current source schemas and terms before coding
adapters. Preserve exact source bytes, SHA-256, source/retrieval timestamps,
license references, code revision, and game-level coverage. Add offline replay and
failure tests. A file's existence is not evidence of complete game coverage.

Resolve first-unit source role mappings and as-of availability; never silently
drop a missing required team-game/role cell. Confirm real player ID coverage before
deciding how to represent unmatched IDs. Reconcile team stints, missed games,
late signings and byes to the supplied eligibility denominators.

In the same October 19–23 milestone, start historical participation/snap coverage
for the defensive information-loss experiment. Keep it on the critical path.

## Review and release gates

Review the first-unit weighting, observed-participant sensitivity populations,
season denominator rules, and required defense plan. Check GitHub for current PR
and CI state before selecting new work. Tests of contracts establish software
behavior, not football attribution validity. Historical threshold testing and
module admission are still required before any ranking publication.

Launch target remains November 7. Budget remains near zero with no purchases
authorized. Consult [ROADMAP.md](ROADMAP.md) for dated milestones and
[the daily workflow](docs/DAILY_WORKFLOW.md) for safe continuation.
