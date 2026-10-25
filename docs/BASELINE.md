# First offensive baseline experiment

This is an observational outcome-model diagnostic, **not CAVAA or a leaderboard**.
The [frozen plan](../config/baseline-2025-v1.json) is declared before examining its
held-out errors. Inputs are the already audited, completed-game offensive ledgers.
Use 2025 weeks 1–10 for fitting, 11–14 to select the joint model's actor penalty,
and 15–18 for a final historical test. Refit through week 14 only after selection.
Apply that frozen model to the available 2026 ledger as a separate transfer test;
do not tune on either final test. These are retrospective source vintages, not a
simulation of information actually available on those historical dates.

Compare four models on identical plays: preplay context only; context plus
offense/defense team effects; those components plus observed-role indicators;
and those components plus joint observed actor identity effects.
The role ablation separates a gain from knowing that a dropback/carry/target was
recorded from a gain associated with that actor's identity. It is a conditional
diagnostic using realized role availability, not a preplay hardship adjustment.
Keep incomplete actor links in the outcome cohort. Missing EPA/context
cannot be fitted and must be counted explicitly. The initial experiment requires
complete game reconciliation and rejects conflicting player-game team identities.

Context uses fixed dimensionless transforms of down, distance, field position,
time and score, including down/distance interactions. It does not use sacks,
pressure, yards gained, event outcome or target presence as hardship adjustments.
Actor links are realized dropback/carry/target roles, **not verified positions**.
Scrambles use the dropback coefficient once, not an additional carry coefficient.
Actor membership and targeted receiving are opportunity-conditional observations;
this is not a model that can forecast before the play's actors are known.
Even score and down reflect earlier player contributions: estimates conditional
on these states do not measure their entire causal effect on the game.

Minimize sum of squared EPA residuals plus squared-coefficient penalties:
context/observed-role 1, each team effect 50, each actor effect in the fixed grid 10/100/1000.
The intercept is unpenalized. Feature scales and the loss-as-sum convention are
part of this definition. Team and actor coefficients are jointly fitted. Team
components retain shared/system association; they are not allocated to players.
Unresolved actor links have no actor design entries, but keep context, team and
residual components. Unseen held-out actors use the shrinkage origin for prediction
and are counted as unseen; that origin is not an established NFL positional average.

Choose the lowest validation RMSE, breaking exact ties toward stronger shrinkage.
All three final-test penalty fits are reported as sensitivity evidence; do not
reselect using the test. Report play RMSE, MAE, signed bias, team-game mean-EPA
error, and paired game-cluster bootstrap intervals for RMSE differences. Those
intervals concern **outcome prediction**, not player effects, ranks or causal
identification. Resampling games still misses cross-game team dependence.

Accounting must reconstruct each observed outcome from context, offense team,
defense team, shared observed-role indicators, actor components and residual within 1e-9 EP. Preserve negative
plays and all weeks, with no recency weights. Report actor/team coappearance and
identical actor columns: ridge can give a unique answer when the data cannot
separate teammates. Numerical convergence is not proof of attribution.

No model is admitted by a marginal error improvement. A joint model must improve
on context-plus-team-plus-observed-role with the paired interval below zero to earn further predictive
investigation; individual publication additionally requires the attribution,
benchmark, uncertainty and comparability gates in [evaluation](EVALUATION.md).
Failure to improve is a useful negative result. First-unit, equal-player and
opportunity-weighted comparisons are unchanged and not yet applied to actor roles.

## Numerical dependencies and reproducibility

Install `python -m pip install '.[model]'` in the repository's isolated environment.
The optional model extra pins NumPy 2.2.6 and SciPy 1.15.3 for Python 3.11–3.13.
NumPy supplies arrays and deterministic seeded resampling; SciPy supplies sparse
matrices and the established [LSQR solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.lsqr.html).
Both use permissive BSD licenses ([NumPy](https://numpy.org/doc/stable/license.html),
[SciPy](https://scipy.org/about/)); wheel distributions retain their bundled notices.
No implementation code is copied. The stdlib ingestion layer stays independent.
Pin upgrades require numerical regression checks; record actual dependency/runtime
versions with every fit. Augmented sparse least squares applies a separate penalty
per component, leaving the intercept free. Reject nonconvergence and nonfinite fits.
Exact content hashes preserve artifacts; refitting may differ in floating-point
rounding across platforms and must be checked numerically, not promised byte-identical.

## Run and replay

From the canonical repository root with the recorded raw and offensive stores:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.baseline_cli build \
  --historical-report 97363672ae959a88782a4fd459e5711eabfd1cccdcf9a83dae11047579b5e293 \
  --transfer-report e09813840603bb755d03befb446c27e2435a067281744865d19b137a4bc0fd83 \
  --plan config/baseline-2025-v1.json
PYTHONPATH=src .venv/bin/python -m nfl_value.baseline_cli replay \
  1fd9e2479c71ff06590a96e7b512fb291f80ad35bc10867d81814af7452660de
```

Build requires committed source/package code. Both commands first replay and
verify the original source-derived ledgers; fitting itself makes no network calls.
The default output store is `data/derived/baseline`, excluded from Git. All four
model states and held-out per-play components are saved as hashed JSON objects.
Structural fields and identities must replay exactly; floats use absolute 1e-9
and relative 1e-8 tolerances with the recorded NumPy/SciPy versions. This does not
guarantee every platform will meet the tolerance; a mismatch is a failure to review.

## October 23 evidence and interpretation

Implementation `a595912cf16716dff479d6e3d63c8d8df4452b9b` produced the report above.
The [audit](audits/2026-10-23-offensive-baseline.json) contains exact inputs, runtime,
plan, validation selection, test errors, bootstrap intervals and sensitivity.
The 2025 split has 149 training / 59 validation / 64 test games. The available
2026 snapshot has 93 games. The selected penalty remains 1000.

The historical joint-versus-role RMSE difference is -0.000410 EP/play, with 95%
game-bootstrap interval [-0.000925, +0.000056]. The 2026 transfer difference is
-0.000477 [-0.000786, -0.000155]. The historical interval spans zero and the
transfer effect is small. Outcome gains over team-only largely reflect recorded
role availability; this can incorporate sack/throwaway selection and absorb value
the QB created. Neither that role adjustment nor these coefficients is approved
for final CAVAA. Transfer team-game mean-EPA error also worsens versus context-only.

There are 830 actor columns and three groups with identical observed columns.
One actor's coefficient changes by up to 0.775 EP across the declared penalties;
these are coefficient sensitivities, not cumulative value estimates. No role is
admitted to a leaderboard and no first-unit comparison or qualification is run.
All 87 historical and 27 transfer ambiguous-actor plays remain in the model cohort.
Both real build and replay completed with network calls blocked, about 11 seconds
each on this machine. Runtime is an observation, not a deployment guarantee.
