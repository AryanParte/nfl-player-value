# QB dropback recovery experiment — frozen before results

The launch failure is a scoring failure, not a missing test-count milestone.
This bounded unit diagnoses the old target-observation conditioning, strong
shared ridge prior and QB/team confounding; implements justified alternatives;
evaluates fresh windows, calibration and sensitivity; and produces reproducible
research contrasts with an evidence-based decision. It cannot redefine the whole
product as QB-only. Defense/Explorer and all other admission gates remain active.

## Scope and causes

The candidate estimates an **observational QB dropback component**, not full QB
value: recorded passes, sacks and scrambles with complete context/outcome and an
unambiguous same-week roster-verified QB. Designed runs, non-QB passes and ambiguous
links are excluded with counts; missing value is never zero. Every completed
season game must have modeled observations. No outcome-based exclusion is allowed.
No target/carry availability, receiver identity, pressure, sacks-as-features or
yards/YAC enter the context adjustment. Those can be player-created outcomes.

The existing first-unit benchmark and equal-player/opportunity-weighted policies
apply to this module's opportunities. First-unit membership is independent of
usage and qualification; cold benchmark QBs retain parameters and uncertainty.
Every modeled 2026 game contributes; no recency weight is used. A within-season
constant-effect fit describes that season, not current form multiplied backward.
QB CAVAA contrasts retain the team/context/game components and residual separately.
Do not add this component to overlapping old full-play or receiving scores.

## Alternatives and validation data

The frozen [plan](../config/qb-recovery-v1.json) defines four fits on identical
observations and preplay context transforms from the existing baseline:

- `team`: context plus offense-team, defense-team and game random effects.
- `qb_proxy`: context plus QB, defense-team and game random effects, without
  offense-team effects. This is a deliberately confounded association control,
  never an individual-value admission candidate even if prediction improves.
- `joint` (primary): context plus QB, offense-team, defense-team and game random
  effects with separate variance components estimated by restricted likelihood.
- `fixed_precision`: the same joint design with QB penalty 1000 and other group
  penalties 50, a controlled strong-shrinkage reference. This is not a replay of
  the old all-role estimator: context is unpenalized and game effects are new.

Use previously unmodeled **2024 weeks 1–10** for fitting, 11–14 for validation,
then refit through 14 and evaluate 15–18 once. No variant/penalty is selected using
the final test; `joint` is declared primary now. All alternatives are reported.
Earlier 2025/2026 tests motivated this recovery but are not tuning data. The 2024
study is retrospective development evidence, not a historical-vintage backtest.
As a secondary transfer check, fit 2026 weeks 1–6 and predict completed weeks 7+
from the archived November 7 snapshot. Those later sources were used in Explorer;
their model errors have not been inspected. Do not describe them as a prospective
blind test. Finally fit all completed 2026 games for the season research ledger.
The new 2024 PBP/schedules and 2026 sources must pass existing ingestion/replay checks.

**Source amendment before fitting:** GitHub's 2024 weekly and season roster assets
all lack a published digest (March 14, 2025 uploads). Ordinary ingestion correctly
rejects them. Preserve that production gate. A separate retrospective-only adapter
pins weekly asset 237398166, update time and size, verifies unchanged release
metadata before/after download, and archives metadata, local SHA-256 and schema
audit. A local checksum establishes replay integrity, not an upstream checksum or
historical availability. This narrow exception preserves the same-week identity
definition and the untouched 2024 validation windows. It cannot authorize a
production ranking or other legacy asset. No model outcomes were inspected before
this amendment; a changed asset requires a new reviewed source policy.

Held-out games/teams/QBs never expand a training vocabulary or estimate variance
components; unseen random effects predict zero and are counted. Report paired
game-bootstrap RMSE differences against `team`, MAE and team-game mean errors.
The existing requirement for a primary improvement interval wholly below zero
is retained as predictive evidence, **not** proof of individual allocation. Its
reference is now preplay team context, since realized target availability is not
an appropriate preplay hardship control for QB-created dropback outcomes.

## Restricted likelihood and uncertainty

For `y=F beta+Z b+e`, unpenalized context F is reduced to an independent column
basis using X alone; `b_g ~ N(0,tau_g^2 I)` and `e ~ N(0,sigma^2 I)` are working
assumptions. Profile the restricted likelihood over `lambda_g=sigma^2/tau_g^2`,
using the declared bounded log parameters and three deterministic starts.
For `H=X'X+diag(0_F,lambda)`, `Q=y'y-y'X H^-1 X'y` and `r=rank(F)`, minimize
`(n-r) log(Q/(n-r)) + log|H| - sum_j log(lambda_j)` (constant omitted).
This equals the observation-space marginal REML objective; test that equality
against an independent small dense V calculation. Reject nonconvergence/nonfinite
systems and report boundary solutions and multiple-start objective differences.

The candidate interval uses `sigma^2 H^-1`, including player/benchmark covariance
and nuisance-context uncertainty. It is an empirical-Bayes **conditional** interval
with estimated hyperparameters, not automatically calibrated confidence. Its
limitations must be measured, not hidden by calling every interval a posterior.
No variance multiplier is chosen to widen a failed interval.

Run 128 fresh deterministic replicates per scenario on the current observed QB
design. Reestimate variance components in every primary fit. Compare the fixed
precision control on the same synthetic outcomes. Scenarios: (1) Gaussian effects
drawn from the declared hierarchy; (2) fixed hash-signed QB ±0.25, offense ±0.15,
defense ±0.10 EP, fixed context ±0.1 and iid noise SD 1.5; (3) the same fixed
effects with half of error variance shared within game, half independent. No real
EPA chooses the truth or seeds. Report coverage, widths, bias, RMSE and Monte Carlo
SE using replicate-level coverage fractions. Retain the original severe-failure
flag `coverage + 1.96 MC_SE < .90`; absence of that flag is not a 95% admission.

Also perturb the primary fitted QB variance by 0.5×/2× with other variances held
fixed and report first-unit contrast changes. Compute full-design null-space
projections of each contrast (Gram eigenvalue cutoff 1e-10 of its maximum; contrast
relative projection >1e-8 is non-estimable under unrestricted fixed nuisance
effects). Provide a concrete unchanged-prediction/different-QB-contrast witness.
Hierarchical assumptions can select an allocation; they cannot make it assumption
free. General non-estimability is not the same as a numerical optimizer failure.

## Decision and remaining gates

Report all alternatives and diagnose failures through the declared controls,
calibration, null directions and variance sensitivity. Fix implementation defects
with tests; do not retune this plan on revealed test outcomes. A positive module
decision additionally needs complete benchmark coverage, defensible attribution
under its declared assumptions, calibrated uncertainty, qualification evidence
and cross-module accounting. Missing those remains a blocker even if prediction
passes. This experiment does not relax the immutable v1 non-admission registry.
Any proposed positive decision must cite new evidence in a reviewed v2 contract.

No automatic overall rank is produced from research contrasts. No validation
requirement is changed simply to pass. Deployment repair is bounded and independent
of model progress. Keep a follow-up defensive recovery milestone in the backlog.

Method references: the [statsmodels mixed-effects model specification](https://www.statsmodels.org/stable/mixed_linear.html)
describes ML/REML variance-component estimation; [estimability](https://cran.r-project.org/web/packages/estimability/index.html)
documents linear-function estimability checks. We use the existing NumPy/SciPy
stack and independent algebraic tests, without importing or copying either package.
