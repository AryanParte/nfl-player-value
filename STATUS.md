# Project status

Updated: October 24, 2026, America/New_York.

## Current unit

The first bounded **defensive information-loss comparison is implemented, fitted,
and replayed**. See the [specification](docs/DEFENSE_MODEL.md),
[audit](docs/audits/2026-10-24-defensive-model.json) and
[learning report](docs/learning/2026-10-24.md). No defensive CAVAA is admitted.

PR #6 remains open with green CI and no review comments. Today's branch,
`codex/defensive-information-loss`, is explicitly stacked on
`codex/regularized-offensive-baseline` at `8488ed5`. It reuses the pinned numerical
dependencies and replay helper. Review/merge #6 first, then retarget this PR to
main; agents must not merge either PR or force-push.

## Measured evidence

The fixed 2025 cohort has 243 games / 29,297 plays. Its chronological split is
131 training games (Weeks 1–10), 54 validation games (11–14) and 58 test games
(15–18). Both views select the strongest declared defender penalty, 1000, using
validation alone. Final refits use the same 22,372 plays, represented as either
play-level lineups or 370 defensive team-game aggregates. Tests cover 6,925 plays.

| View | Team/context weighted RMSE | Adding defenders | Defender minus team 95% interval |
| --- | ---: | ---: | --- |
| Play-level lineups | 0.201203 | 0.202948 | [-0.003341, +0.006877] |
| Game-level fractions | 0.145339 | 0.146772 | [-0.002168, +0.004774] |

Errors are EP per eligible play, evaluated at team-game means. Neither interval
supports an incremental defender prediction claim. The lower aggregate error is
not evidence of better individual attribution: aggregation changes the loss and
within-game covariance, and realized game-average context includes score states
partly produced by earlier performance. This is not a pregame forecast or an
approved CAVAA adjustment. The richer model is not ground truth.

After projecting off context and teams, numerical defender rank falls from 922
to 301 across 951 columns. There are 29 versus 650 unidentified linear dimensions
at the fixed tolerance. Both views have six identical-column groups. Selected
coefficient correlation is 0.443; penalty sensitivity remains large. These are
identification diagnostics, not player intervals or first-unit contrasts.

Selection checks account for all 32,813 candidate plays: 29,297 retained and
3,516 from 29 lineup-excluded games. No measured context/outcome standardized
mean difference crosses the predeclared 0.1 flag; this does not establish ignorable
selection. Retained team coverage still varies from 13 to 17 games.

171 offline tests pass (19 new). Real build and numerical replay succeeded with
network construction/connections blocked. Model and prediction JSON objects carry
independent FTN/nflverse attribution, derivative license, plan and source hashes.
Shared-value accounting is checked without allocating the full outcome to each
defender. All research outputs retain `ranking_ready=false`.

## Next highest-priority unit — October 25

Build the required Defense Explorer foundation from verified observations, with
source age, supported denominators and missing contributions visible. Audit a
permitted live workload source before showing 2026 snap fractions; the historical
fraction experiment does not certify live coverage. Unsupported positions retain
missing scores. Keep the initial React/TypeScript view small and compatible with
the versioned JSON pipeline; do not delay the website for extra model complexity.

Finish position/roster-stint evidence and correct `SeasonExposure`'s observed-by
completion timestamp handling before benchmark contrasts or qualification. Do not
infer missed-game denominators from positive appearances. Reserve the October
28–30 freeze for bounded first-unit/equal-player/opportunity-weighted contrasts,
qualification and module admission. Any additional historical folds, absence
checks or live-like degradation must disclose that the present tests are observed.
No tuning on these test results. The defensive workstream remains required.

## Unfinished release gates

No 2026 CAVAA score is published and no position has passed attribution/comparability
admission. The broader defensive experiment still needs additional seasons,
verified positions/live missingness, absence cases and player uncertainty. Defense
Explorer, supported offensive contrasts, joint player/benchmark intervals,
qualification tests, React/TypeScript dashboard, durable off-machine retention and
independent production refresh remain unfinished. The last 2026 chart audit has
11 IDL/CB/S/LS issues; the latest archived 2026 outcome cohort is through Week 6.

November 7 remains the target. A working site must show measured coverage and
only admitted values; if no module passes, an exploratory site does not fulfill
the MVP-ranking objective. Protect the freeze/release dates and record that risk.
Today's October 24 unit makes no schedule change, no purchase, and no change to
NFL Opponent Intelligence. The production refresh remains independent of Codex.
