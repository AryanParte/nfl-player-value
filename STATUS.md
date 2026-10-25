# Project status

Updated: October 23, 2026, America/New_York.

## Current unit

The owner merged PR #5; main CI is green and no review feedback was pending.
Today's immediate run uses `codex/regularized-offensive-baseline` from current
main. Its PR remains for human review; never merge automatically.

The first actual outcome-model experiment is implemented and fitted, alongside
the existing benchmark/qualification contracts, immutable ingestion, pregame
first-unit selection, historical defensive paired inputs and offensive ledger.
See the [experiment specification](docs/BASELINE.md), [audit](docs/audits/2026-10-23-offensive-baseline.json)
and [learning report](docs/learning/2026-10-23.md).

## Measured evidence

The frozen 2025 split has 149 training, 59 validation and 64 final-test games.
Validation selected actor penalty 1000; the final refit uses 25,163 plays through
Week 14. The 2025 test has 7,650 plays; the separate 2026 transfer test has 11,441
plays in 93 completed games through Week 6, using the October 22 source snapshot.
No fresh source capture was needed for this fixed-input experiment.

| Model | 2025 test RMSE (EP/play) | 2026 transfer RMSE (EP/play) |
| --- | ---: | ---: |
| Preplay context | 1.384803 | 1.353829 |
| Context + teams | 1.382101 | 1.355002 |
| Context + teams + observed roles | 1.346707 | 1.325424 |
| Above + actor identity | 1.346298 | 1.324947 |

The actor-identity RMSE increment over the role model is -0.000410 with a
95% game-bootstrap interval of [-0.000925, +0.000056] on the historical test.
The 2026 increment is -0.000477 [-0.000786, -0.000155]. The historical interval
includes zero; the transfer gain is small. Most of the gain over team-only comes
from realized role information. That information can absorb player-created
outcomes, so this is a diagnostic ablation, not an approved CAVAA adjustment.
2026 team-game mean-EPA error is also worse than context-only, despite better
play RMSE. Do not claim a uniformly better model or validated player attribution.

All 32,813 historical and 11,441 transfer plays are retained, including 87/27
aborted or ambiguous actor records with no invented actor effects. Fitted state,
component predictions and diagnostics are immutable JSON, linked to exact raw
receipts. Build and replay both succeeded with network construction/connections
blocked. The outcome-accounting error is below 2e-15 EP. There are 152 offline
tests (23 new); the PR carries current remote CI evidence.

Three identical actor-column groups and sensitivity up to 0.775 EP/coefficient
across declared penalties illustrate weak identification. Bootstrap intervals here
concern outcome RMSE differences, not player-value uncertainty or ranks. The
penalty is not reselected using either final test.

## Next highest-priority unit — October 24

Run the first bounded defensive rich-versus-degraded model comparison on the
existing identical cohort (243 games / 29,297 plays), with chronological splits,
shared-value accounting, collinearity and whole-game selection-loss diagnostics.
Reuse the numerical approach where appropriate; do not replace this required
workstream with more offense-only feature development. Declare any needed model
extensions and thresholds before evaluation. The existing paired cohort is a
controlled information loss, not yet a verified replica of a permitted live feed.
Audit additional seasons and live workload coverage before broader admission.
Start the required Defense Explorer with verified observations and missingness.

In parallel within the roadmap, finish position/roster-stint evidence and the
`SeasonExposure` observed-by timestamp correction before benchmark contrasts or
qualification. Never infer missed-game denominators from positive actor appearances.
Evaluate offensive actor effects using additional folds/absence cases without
reusing today's observed tests as untouched tests. First-unit, equal-player and
opportunity-weighted policies remain unchanged; none is silently replaced by the
ridge origin. Preserve the bounded participation tests and all earlier season games.

## Unfinished release gates

No CAVAA score is published and no position has passed attribution/comparability
admission. Position/stint verification, player/benchmark uncertainty, defensive
information-loss results, Defense Explorer, React/TypeScript dashboard, durable
off-machine retention and independent production refresh remain open. The 2026
chart audit still has 11 IDL/CB/S/LS issues. All experiment outputs explicitly
retain `ranking_ready=false`.

Today's immediate run counts as October 23 development. The existing automation
was updated through the app with a start date of October 24, 2026 at 7:30 PM
America/New_York; its daily recurrence, prompt and destination were preserved.
Tonight's occurrence is excluded. No duplicate automation was created. The other
NFL project and automation were untouched. November 7 remains the launch target;
no purchases or paid services were enabled.
