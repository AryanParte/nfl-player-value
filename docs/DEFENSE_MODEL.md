# Bounded defensive information-loss experiment

This first fitted comparison is a **historical aggregation diagnostic**, not a
live-2026 feasibility result or defensive CAVAA. It does not complete the broader
[defensive workstream](DEFENSE_EXPERIMENT.md). Positions/assignments, additional
seasons, actual live-source degradation, absence cases and player uncertainty remain
admission prerequisites. No defender is admitted by this experiment alone.

The [fixed plan](../config/defense-2025-v1.json) is committed before inspecting
defensive model results. Use the existing 2025 complete-game paired cohort: fit
Weeks 1–10, choose defender penalty on Weeks 11–14, refit through Week 14, evaluate
Weeks 15–18. These test games are held out from all defensive fitting; their EPA
outcomes have already appeared in the offensive experiment. This is not a pristine
blinded test or a simulation of contemporaneous historical data availability.

## Matched estimands and information boundaries

The rich view has one row per eligible play and 11 defender indicators. The
degraded view has one row per defensive team-game with mean context, mean signed
EPA, and defender appearance fractions. Use the exact same game/play cohort and
outcomes, with `defense_epa = -offense_epa`. Positive values describe a better team
defensive outcome. Fractions measure eligible pass/run appearances, not official
total snaps or pass-rush opportunities. Neither view supplies verified positions.

Both models have an intercept, fixed linear scales of down, distance, field
position, remaining time, quarter and offense-relative score, and offense/defense
team indicators. Linear transforms commute with averaging; do not compare nonlinear
functions of means with means of those functions. Offense player IDs, pressure,
sacks, target labels and tracking features are not model inputs in either view.
Both lineups and game exposure are realized information, not pregame forecasts.

Fit a team/context-only baseline and a defender model for each view. Rich loss is
the sum of squared play residuals. Degraded loss is the sum of squared team-game
mean residuals weighted by the number of included plays. Add squared-coefficient
penalties: context 1, teams 50, defenders in the fixed grid 10/100/1000; leave the
intercept unpenalized. This keeps penalty units consistent but cannot restore the
within-game covariance discarded by aggregation. Information loss includes that
covariance for context, outcomes and participation, not only lineup identity.

Choose each view's defender penalty using validation **team-game weighted RMSE**,
breaking exact ties toward stronger shrinkage. Compare final predictions at the
common team-game mean-EPA level. Report opportunity-weighted RMSE, equal-team-game
RMSE, bias and MAE. Show selected-penalty and same-penalty sensitivity comparisons;
do not reselect from the test. Keep all fitting observations irrespective of any
leaderboard participation threshold. Ridge's origin is not a positional average.

## Evidence, accounting and admission

Use a paired game-cluster bootstrap for degraded-minus-rich weighted RMSE and
each defender model minus its team-only baseline. A positive difference means
the first model has larger error. An interval spanning zero does not establish
equivalence. These are prediction-error intervals, not player-effect intervals;
cross-game team dependence is not fully captured by game resampling.

Report coefficient correlation and differences as **agreement with a fallible
reference**, never recovery of true NFL value. Report penalty sensitivity,
defender/team coappearance and numerical rank after projecting the defender block
off context/team columns. Use the declared relative Gram-eigenvalue tolerance against the unprojected
defender Gram scale (and the same tolerance for the nuisance pseudoinverse);
regularization and a converged solver do not supply missing identification.
Synthetic rotation/coappearance tests demonstrate what aggregation can conceal.

Reconcile every modeled row to context + offense team + defense team + defender
sum + residual, then aggregate rich predictions to the same team-game units as
degraded predictions. No player independently receives the entire team EPA.
Shared effects remain unallocated. Negative outcomes are retained.

Compare the retained and excluded complete-game candidate populations against the
already archived offensive ledger from identical PBP/schedule receipts. Report
team/week coverage, context and signed-EPA mean differences, with descriptive
standardized differences flagged at absolute 0.1. These are selection diagnostics,
not causal tests or permission to silently change the fixed lineup policy.

An incremental prediction claim requires a defender-model-minus-team-baseline
95% interval entirely below zero. Even that cannot authorize an individual
leaderboard: the richer model is not ground truth, a failure to detect predictive
loss is not equivalence, and live-source/position/benchmark/uncertainty gates
remain open. All outputs retain `ranking_ready=false` and no positional scores.

## Implementation and provenance

Use the existing pinned NumPy/SciPy extra and sparse LSQR. Store hashed JSON model
state, team-game component predictions and a report containing the exact plan,
code, input IDs, source terms and runtime. Revalidate both source-derived views
and the selection ledger before fitting. The degraded fitter accepts only its
strict aggregate schema, never rich records. Preserve FTN Data via nflverse
CC-BY-SA-4.0 attribution and transformation notices on independently reusable
model/prediction derivatives; the repository software license does not relicense
source data. Numerical replay uses the same tolerances as the offensive baseline.

This unit is stacked on the unmerged offensive baseline PR #6. Review/merge #6
first, then retarget this unit to main; no automated merge or force-push.

## October 24 result and decision

The [measured audit](audits/2026-10-24-defensive-model.json) records 131 training,
54 validation and 58 test games. Both views select penalty 1000. Test team-game
weighted RMSE is 0.202948 for the rich defender model versus 0.201203 for its
team/context baseline; degraded values are 0.146772 versus 0.145339. Neither
increment's 95% game-bootstrap interval is entirely negative. Residualized defender
rank is 922 versus 301 across 951 columns. No defensive CAVAA is admitted.

The reduced model's lower absolute error compares conditional outcome models,
not player attribution. Aggregation changes the covariance/loss, and full-game
average preplay score states reflect earlier performance; this is neither a
pregame forecast nor a justified CAVAA adjustment. Positional/player uncertainty
and first-unit contrasts remain uncomputed. The [learning report](learning/2026-10-24.md)
explains the selection diagnostics, limitations and next Defense Explorer unit.

## Reproduce the fixed experiment

Install the existing model extra and use the recorded local content-addressed
stores. Source replay validates their exact bytes and transitive receipts; no
network call or download occurs inside fitting. Raw/generated objects are excluded
from Git, so a clean clone needs the recorded source snapshots; durable artifact
hosting remains a release prerequisite. The audit retains the full source IDs,
terms, code and output hashes. It does not pretend that mutable upstream downloads
are identical substitutes for missing archived bytes.

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.defensive_model_cli build \
  --defensive-report 62f3bfabba7ca58f1f4c3b3b9e3c8993b327ca96772ab232d63666e9819433c9 \
  --candidate-report 97363672ae959a88782a4fd459e5711eabfd1cccdcf9a83dae11047579b5e293 \
  --plan config/defense-2025-v1.json

PYTHONPATH=src .venv/bin/python -m nfl_value.defensive_model_cli replay \
  f447fc8a36ff59f968c62f56aaa5d03cea962156afb63800fd827e50afaf19fb
```

The report's implementation revision is `cd8a98774ea62024d48a0f954ab03414d5255c09`.
A build from a later documentation-only commit records a new code revision and
artifact identity; use replay to verify the preserved original. Do not replace its
manifest or change its plan to improve an observed test result.
