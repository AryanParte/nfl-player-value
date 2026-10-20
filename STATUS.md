# Project status

Updated: October 19, 2026, America/New_York.

## Current unit

Foundation PR #1 was merged by the owner and its CI passed. Today's feature branch
is `codex/versioned-source-ingestion`, based on current main. Check GitHub for its
review/CI state; do not merge automatically.

Implemented across the two units:

- First-unit weighting, both sensitivity benchmarks, and independent participation,
  source, attribution and comparability gates.
- Immutable PBP, season-roster and 2025+ depth-chart receipts: exact source bytes,
  published hashes, metadata/license records, timestamps, schema, code revision,
  coverage and quality reports. No new runtime dependencies.
- Atomic non-overwriting object publication, source-race/corruption detection,
  and strictly offline integrity/audit replay.
- Three real 2026 captures replayed offline. The committed
  [audit](docs/audits/2026-10-19-sources.json) identifies exact local snapshots.
- 47 tests pass locally. The PR carries current remote CI results.
- Development lock, separate evening automation, design/roadmap, defense and
  evaluation plans, and daily learning logs.

The PBP snapshot contains 92 games, including 13 Week 6 games, with end markers.
It is not independently reconciled complete-game coverage. Missing and legacy
player IDs are exposed, not guessed. Archives currently reside in the stable
local clone; off-machine retention is still a production gate.

No model has been fitted, no real rankings published, and no position has passed
contribution admission. The website and production refresh are not deployed.
Every source audit explicitly reports `ranking_ready=false`.

## Next highest-priority unit — October 20

Build normalized completed-game and pregame-context inputs from verified receipts.
Pin an independent schedule/final-status source and document its rights and time
semantics. Reconcile expected completed regular-season games with PBP; do not infer
completeness from a present file, scores or a zero game clock.

Select the latest defensible pre-kickoff depth snapshot per team, map formation
slots to roles, retain multiple first-unit receivers, and fail on missing cells
or unresolved identities. Add stale-snapshot, trade, missing-ID, bye, late-signing
and missed-game fixtures. Current season rosters alone cannot establish stints.

Historical defensive data remain on the October 19–23 critical path. Participation
metadata confirms assets through 2025 and no live 2026 file. Add its dedicated
CC-BY-SA adapter, audit lineups/joins, and resolve snap-source use rights before
the information-loss experiment. That experiment has not run yet.

## Review focus and release gates

Review [INGESTION.md](docs/INGESTION.md), source correction/corruption tests, and
raw preservation versus modeling admission. See [today's learning report](docs/learning/2026-10-19.md).
Historical threshold testing, attribution validation, defensive comparability,
and durable input retention remain required before ranking publication.

Launch remains November 7. No purchases or paid services are authorized. The
existing Opponent Intelligence project and automation remain independent.
