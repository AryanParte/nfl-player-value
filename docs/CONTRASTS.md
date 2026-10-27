# Bounded positional contrast experiment

This plan is committed before inspecting numerical contrast results. It extends
the existing additive baseline with positional benchmark accounting and joint
uncertainty diagnostics. It does not authorize a public CAVAA ranking.

## Fixed experiment

[The plan](../config/contrasts-v1.json) uses 2025 prefixes through weeks 6/10/14/18
and the archived 2026 prefixes through weeks 3/6. Only rows, opportunities,
positions and first-unit assignments in each prefix enter its computation.
These are retrospective source vintages, not vintage weekly publications or
fresh held-out predictive tests. Earlier 2025 test outcomes have already been
examined; this experiment cannot be described as new out-of-sample validation.

Fit the same preplay context, offense/defense team, observed-role and joint actor
design as the baseline, separately within each cumulative season prefix. Every
included play retains its original EPA, including negative outcomes. Use the
previously selected actor penalty 1000 as the primary setting and 10/100 only as
declared sensitivities; do not select a new penalty using these results. Context
and shared role penalties remain 1; team penalties remain 50. The model is a
retrospective **constant season-average** fit, not a current-form estimate. There
is no recency weighting, copying of 2025 points into 2026, or claim that fitted
actor components explain every game's realized performance.

Module scopes are QB dropback/designed-carry, RB carry/target, and WR/TE targeted
receiving. Scrambles use one initiator coefficient. In a self-target play, two
distinct fitted components may contribute, but the opportunity union counts one
play. Other actor components remain explicitly outside these modules. All valid
actors still enter the fit; leaderboard qualification never filters the fitting
or benchmark population.

## Comparisons and accounting

Reuse the approved equal-team, equal-game, equal-first-unit-member weights and
both sensitivities. Evaluate each peer in the focal player's same actor-component
opportunities. With an additive model, common context/team terms cancel; this
does not mean those terms were absent from the joint fit. A reference component
plus the above-benchmark component reconstructs each supported actor component.
Context, teams, shared observed-role terms, unsupported actors and unexplained
residuals remain separate. Never add full EPA to each involved player or force
benchmark-centered totals to sum to zero.

An incomplete first-unit role population blocks that role's contrasts. Candidate
positions must agree with exact-week roster evidence; future-week labels cannot
fill earlier gaps. First-unit members with no observed component receive explicit
zero-observation prior parameters, not a falsely certain average prediction.
Their prior dependence is reported. No position is admitted by this calculation.

## Joint uncertainty: a working-model diagnostic

For design X, outcome y and penalty matrix D, the ridge mean solves
`H beta = X' y`, where `H = X' X + D`. The intercept is unpenalized. Under a
Gaussian iid residual model and Gaussian coefficient priors with precision
`D / sigma_squared`, the conditional covariance is `sigma_squared H^-1`.
Use the declared plug-in residual scale `SSE / n`. This scale and iid assumption
are not calibrated NFL uncertainty; they ignore residual game/team dependence,
variance-estimation uncertainty, shrinkage bias and unmeasured confounding.

For a cumulative player-minus-benchmark vector L, calculate `L' beta` and
`L' covariance L`. This preserves player/benchmark covariance, including the
player's own membership in the benchmark. A shared coefficient shift cancels.
Report conditional normal 95% intervals separately from benchmark/penalty
sensitivity. No interval is labeled causal, calibrated, or a rank interval.
Independent linear-algebra references and controlled synthetic cases must verify
the calculation before any real-data run. Calibration and clustered robustness
remain admission work; do not let narrow conditional intervals overrule failures.

## Narrow exposure proof and qualification sensitivity

The three-game minimum and existing 0.75x/1x/1.25x grid are unchanged. For this
diagnostic, certify G only for players with one consistent team/position in the
window and positively observed offensive participation in **every completed
game of that team's full prefix**, with unambiguous weekly roster joins. This is
a sufficient observed-game case, not a general interpretation of roster status.
It never turns an ACT label, an unobserved game or a zero target count into proof
of participation. Measured zero targets in a positively observed carry game
remain zero opportunities for a targeted-receiving module.

Trades, late entry, gaps, position changes and possible missed games remain
explicitly unresolved under this narrow policy. The study must report how many
players it excludes; these exclusions can be selective. Qualification results
are diagnostic only and do not imply model admission. Broader verified stint and
missed-game rules are required before production eligibility. Preserve benchmark
weights unchanged across qualification thresholds and unresolved exposures.

## Required outputs and decisions

Save exact source/report/plan identifiers, selected first-unit evidence, every
window's coverage and exclusion counts, fitted models, shared-component accounting,
benchmark weights, conditional contrast intervals, cold-parameter counts,
qualification-grid membership and benchmark/penalty sensitivity. Rebuild from
archived sources offline and compare identities/structure exactly and floating
values under the existing 1e-9 absolute / 1e-8 relative replay tolerances.

Every report remains `ranking_ready=false` and `individual_attribution_validated=false`.
Observed-role availability can absorb value created by a QB and remains a known
baseline limitation. Historical predictive, attribution, calibration, scope and
comparability gates still control admission. Defense Explorer and the failed
defensive information-loss admission decision remain unchanged.
