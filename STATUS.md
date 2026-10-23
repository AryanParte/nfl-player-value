# Project status

Updated: October 22, 2026, America/New_York.

## Current unit

The owner merged PR #4; main CI is green and no review comments were pending.
Today's branch is `codex/completion-and-offensive-inputs`, based on current main.
Check GitHub for review/CI state; never merge automatically.

Implemented:

- First-unit benchmark weighting, equal-player/opportunity-weighted sensitivities,
  and independent participation, source and model-admission contracts.
- Immutable source capture, license provenance, raw audit and offline replay.
- Formation-aware pregame first-unit selection with missing-cell/identity guards.
- Historical FTN participation and paired rich/degraded defensive input artifacts.
- Completion v2 using quarter/clock evidence, end markers and matching schedule
  scores. Legacy v1 reports replay with their original policy and exclusions.
- One-row-per-play offensive EPA ledger with observed actor links, explicit
  missingness, and nonduplicated dropback/rush/target workload unions.
- Shared preplay parsing, immutable offensive objects and exact offline replay.
- 129 local tests pass (28 new); compilation and whitespace checks pass. The PR
  carries current remote CI results.

## Current evidence

The [October 22 audit](docs/audits/2026-10-22-offensive-inputs.json) records exact
source receipts and derived reports using implementation
`bab4b39a98123bfdd4cd844120a04c7ca409360b`.

With identical 2025 receipts and cutoff, completion v2 accepts all 272 REG games.
The two reordered-event cases are restored without relaxing lineup validation.
The defensive paired cohort increases from 241 / 29,059 to **243 games / 29,297
plays**. The same 29 games fail lineup requirements; retained coverage ranges from
13 to 17 games per team. The legacy defensive report still reproduces exactly.

The new 2026 offensive ledger uses fresh PBP/schedule snapshots retrieved October
22, with evidence cutoff `2026-10-22T23:50:38.680415+00:00`. It contains **11,441
candidate plays in 93 completed games through Week 6**, including 429 sacks and
355 scrambles. All candidate rows have finite EPA and valid preplay context.
There are 27 aborted plays with unallocated actor links and 269 passes without a
recorded target. Those outcomes remain visible, not silently removed or assigned
invented player effects. The 2025 ledger has 32,813 candidate plays in 272 games,
87 aborted plays and 749 passes without a recorded target.

The corrected pregame report preserves the previous 93-game/186-team-game cohort
and first-unit selection exactly, including 11 unresolved IDL/CB/S/LS issues.
Old and new reports replayed with network construction blocked. All source data
are retrospectively retrieved; archived row dates do not prove vintage availability.

No model is fitted, no defensive model comparison has run, and no CAVAA ranking
is published. Observed actor roles are not verified positions. Roster stints,
missed-game denominators and qualification are explicitly incomplete. Defense
Explorer, React/TypeScript presentation and independent production refresh remain
unimplemented. Raw/derived archives are local; durable off-machine retention is
still a production gate. All reports retain `ranking_ready=false`.

## Next highest-priority unit — October 23

Fit the first context-only and transparent regularized joint-actor baselines on
chronological game splits, with explicit team/shared/unallocated components and
accounting checks. Record held-out errors, collinearity and sensitivity before any
player-value claim. Do not spend the entire next unit expanding ingestion.

In the necessary data adapter, verify identity/position and roster stints for
missed games, trades and late signings before positional contrasts or qualification.
`SeasonExposure` currently tests overlap using `completed_at`; observed-by retrieval
bounds are not physical game intervals. Correct this timing contract and add
fixtures before converting source-derived games into season exposure. Never invent
exact finish times or infer a full roster stint from positive on-ball appearances.
Review aborted-play attribution and unrecorded target semantics before admission.

Keep October 24–27 reserved for the defensive information-loss comparison and
context validation. Audit additional historical seasons, positional crosswalks and
selection loss; match the actual coverage/rights of a permitted live workload
source. Defense Explorer remains mandatory even if defensive CAVAA is unsupported.

## Review focus and release gates

Review [completion policy](docs/PREGAME_INPUTS.md), [offensive accounting](docs/OFFENSIVE_INPUTS.md),
and [today's learning report](docs/learning/2026-10-22.md). Key boundaries are
one outcome per play, workload set unions, retained negative/missing outcomes,
versioned replay, and the distinction between actor roles and positional value.
Attribution, uncertainty, bounded qualification tests, cross-position comparability,
durable retention and publication controls remain release gates.

November 7 remains the launch target. No purchases or paid services were enabled.
The other NFL project and its automation remain untouched. Production refresh
will operate independently of this development heartbeat.
