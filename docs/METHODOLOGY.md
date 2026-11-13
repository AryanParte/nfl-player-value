# CAVAA methodology specification

Approved research direction, October 18, 2026. This is the implementation contract, not a claim that the model has already been fitted or validated.

## Estimand and units

For player `i` and completed games through cutoff `W`, estimate:

```text
CAVAA_i(W) = sum over observed opportunities p of
             [predicted contribution with player i in context p
              - weighted mean prediction with first-unit peers in context p]
```

The unit is **cumulative expected points** during the 2026 regular season. Preseason and postseason games are outside the MVP ledger and its qualification/benchmark windows. Defensive benefit is expressed as points prevented. The benchmark shares the player's modeled role and comparable observed circumstances. In a nonlinear model, average predictions over benchmark players; do not substitute a vector of average features into the model and assume the results are equivalent.

This is an opportunity-conditioned observational contrast. It does not simulate every change in play calling, target selection, teammates, or opponent behavior that a real substitution would cause. On-ball receiving value is not complete receiver value; blocking, decoy routes, target earning, and coverage deterrence require additional evidence.

Every season game remains in the cumulative ledger. Games missed add no opportunities or contribution, with no separate injury penalty. Prior seasons may inform shrinkage but do not add points to the 2026 total. Current skill is a separate possible display; do not retroactively multiply today's skill estimate by all earlier opportunities.

## First-unit positional benchmark

Define role membership using timestamped depth-chart information available **before kickoff**, supported by a documented mapping from source positions to model roles. This is a measurable proxy for ordinary starting-caliber performance, not a claim that depth-chart labels reveal latent talent perfectly.

For each role:

1. Give each team equal weight.
2. Within each team, average across its completed team games at the ranking cutoff.
3. Within each team-game role cell, split weight equally across the pregame first-unit members.
4. Aggregate repeated memberships into player weights and average their partially pooled model predictions in the evaluated context.

A player named first unit for one game therefore does not receive the same season benchmark weight as a sustained first-unit player. An injury replacement can enter this observable cohort; this limitation must be disclosed. A role with several first-unit members does not receive additional team weight merely because of its roster structure.

The expected team-game/role universe must be declared before constructing weights. Missing required cells, stale or post-kickoff membership evidence, unresolved identifiers, and an unsupported role mapping are failures, not permission to silently renormalize a convenient subset. Any narrower benchmark scope must be explicit and versioned. The ingestion stage must validate the as-of evidence; mathematical weights alone do not establish pregame availability.

Three populations are distinct:

| Population | Purpose |
| --- | --- |
| Model observations | All valid measured opportunities, including low-volume players |
| Benchmark cohort | Players weighted by the declared comparison policy |
| Qualified leaderboard | Players satisfying participation, source coverage, and model-admission rules |

Leaderboard qualification never defines who is allowed to inform the model or the benchmark. A first-unit member with zero observed opportunities remains in the primary benchmark when a valid model prediction exists; membership weights reflect the declared pregame role rather than realized usage. Such a prediction may rely heavily on partial pooling and must carry its uncertainty.

## Required benchmark sensitivities

- **Equal-player:** equal weight to each player with at least one valid observed role-specific opportunity in the declared positional population. Include one-opportunity reserves; exclude zero-opportunity predictions from this sensitivity population. Sparse samples are partially pooled rather than treated as precise estimates.
- **Opportunity-weighted:** weight that same positive-opportunity population by valid role-specific opportunities. It describes the player performance encountered on a typical opportunity and can be influenced by who receives playing time.
- **First-unit:** the primary comparison above. It avoids giving every briefly appearing reserve equal benchmark weight while making the first-unit proxy explicit.

Report population definitions with every comparison. Average-starter and replacement-level variants beyond this first-unit proxy are optional research, not the primary metric. If the benchmark rises by `delta` points per opportunity in an additive constant-effect example, a player's cumulative value falls by `opportunities × delta`. High-volume players can therefore change rank substantially even with unchanged player-effect estimates.

Benchmark sensitivity is not a confidence interval. Statistical uncertainty must include uncertainty and covariance in both the evaluated player and benchmark predictions. A benchmark-centered model need not produce cumulative player totals summing to zero when players have different workloads and contexts.

## Provisional participation policy

Require at least **three games with participation** for the main board. Earlier results may appear as provisional. Let `G` be completed available team games, including games the player missed and excluding byes. Trades use nonoverlapping team stints; neither reset the season nor add two teams' full-season denominators. Late signings, trades, position changes, and injury absences require explicit denominator fixtures before live publication.

| Role/module | Provisional opportunity minimum |
| --- | --- |
| QB | `max(50, 14 × G)` unique modeled QB plays |
| RB on-ball | `max(25, 6 × G)` carries and targets |
| WR targeted receiving | `max(15, 3 × G)` targets |
| TE targeted receiving | `max(10, 2 × G)` targets |
| OL, if supported | `max(100, 35% of available team offensive snaps)` |
| IDL / EDGE explorer | `max(75, 20% of available team defensive snaps)` |
| LB / CB / S explorer | `max(100, 35% of available team defensive snaps)` |

QB opportunities combine dropbacks and designed non-kneel rushes; count scrambles once. Receiving qualification only supports the targeted receiving module. Specialist modules need task-specific denominators before admission. Meeting a defensive snap threshold does not qualify a defender for an overall CAVAA score.

The [offensive ledger](OFFENSIVE_INPUTS.md) now implements unique observed actor
counts, including the dropback/rush union. Those event roles are not verified
positional labels, and its observed player games do not yet establish roster-stint
or missed-game denominators. It deliberately does not produce qualification.

These are product-policy hypotheses, not scientifically established cutoffs. Historical tests compare 0.75×, 1×, and 1.25× requirements and select the least restrictive stable policy without tuning to names, desired winners, or positional diversity. Source coverage and attribution admission remain separate gates.

Partial pooling reduces low-sample extremes but does not create missing information. Do not require a positive estimate, a confidence interval excluding zero, or one universal interval-width cutoff to qualify; those rules select favorable outcomes or privilege easily measured positions.

## Attribution and context

Start with regularized additive player effects, role structure, and a declared context model. Allow team/system and unallocated shared components where individual effects are not identifiable. Preserve a reconciliation between the modeled outcome, fitted components, and residual; do not award full play EPA independently to the quarterback, receiver, line, and defenders.

Use reliable preplay situation and chronologically estimated opponent context. Teammate effects should be joint where identifiable; otherwise consider lagged or leave-player-out proxies with sensitivity tests. Team and player effects can be strongly confounded, especially when teammates nearly always play together.

Pressure, sacks, time to throw, separation, YAC, and targets can be consequences of player decisions or skill. They are not automatic hardship adjustments. Do not add overlapping pressure, accuracy, or sack bonuses to a value estimate already accounting for the same outcome. Coaching and injury information cannot justify invented scheme scores or injury-severity penalties.

Nonlinear interactions need an explicit shared-value allocation before individual contrasts can be summed. Shapley-style allocations encode a chosen coalition/counterfactual definition and are not automatically causal. Graph models and tracking methods remain optional research until they improve evidence, not just fit.

The October 23 [diagnostic baseline](BASELINE.md) includes an observed-role
ablation to distinguish actor identity from knowing a target/carry/dropback link
was recorded. Target availability is realized information and can absorb a QB's
avoidance of sacks or throwaways. This ablation is not an approved hardship
adjustment for final CAVAA. Its model coefficients are not positional scores.
October 27 adds the [bounded positional contrast experiment](CONTRASTS.md), which
applies the first-unit and two sensitivity populations to these joint actor
components. It is a retrospective constant season-average fit, not a current-form
estimate. Context/team/shared-role terms and residuals remain outside individual
contrasts. All model/benchmark participants are retained independently of
qualification; cold benchmark parameters carry prior uncertainty.

The contrast layer's conditional Gaussian intervals use the full covariance of
the player-minus-benchmark calculation. They are working-model diagnostics with
an iid residual assumption and plug-in scale, not calibrated football confidence
intervals. Its narrow exposure proof accepts only a consistent single team/role
with positive observed participation in every completed team game in the window.
This selected subset does not resolve general stints, injured/missed games, trades
or late signings. The three-game rule and threshold grid remain provisional,
and every main-admission flag stays false.

October 28 [calibration results](CALIBRATION.md) demonstrate why that distinction
matters: near-nominal coverage under effects drawn from the prior coexists with
severe undercoverage for the prespecified stronger effects. Sampling uncertainty
around a biased estimator is not uncertainty about the true player contrast.
Neither an uncorrected game-cluster diagnostic nor known-noise oracle width
resolves this bias. No interval is relabeled as calibrated NFL uncertainty, no
penalty is reselected and no position is admitted. The simulations preserve the
same first-unit benchmark and observed opportunities; they do not validate the
observed-role conditioning policy or recover unobserved contributions.

October 29 [observed-transition diagnostics](TRANSITIONS.md) distinguish zero
recorded dropbacks from missing identity/roster evidence and from a verified
absence. Recorded target-share distance measures usage, not teammate quality.
The isolated new-minus-prior QB coefficient contrast is explicitly a predecessor
comparison, never the approved first-unit CAVAA benchmark. It holds realized
decisions, targets and opportunity fixed and is withheld when either player lacks
training exposure. Team EPA changes are reconciled across all model components
and residual, never assigned wholesale to the QB. No eligibility, benchmark,
penalty, position admission or cumulative season-value policy changes.

## Evidence and release labels

Prediction accuracy supports the outcome model but does not establish correct player attribution. Cross-position admission requires a comparable estimand, benchmark, opportunity definition, accounting policy, and meaningful validation. Unsupported contributions stay unmeasured; missing is not zero. See [evaluation](EVALUATION.md) and the required [defensive experiment](DEFENSE_EXPERIMENT.md).

Research foundations include [nflWAR](https://arxiv.org/html/1802.00998v2), [football adjusted plus-minus](https://ideas.repec.org/a/bpj/jqsprt/v17y2021i4p313-364n4.html), and [causal limitations of feature relevance](https://proceedings.mlr.press/v108/janzing20a.html). These motivate methods and cautions; none validates this project's unbuilt 2026 metric.


## November 7 QB model-recovery decision

The [preregistered recovery](QB_RECOVERY.md) and [measured decision](QB_RECOVERY_RESULTS.md)
replace optional infrastructure with the scoring critical path. A preplay QB
dropback module learns separate QB/team/opponent/game variances, preserves the
first-unit benchmark and both sensitivities, and produces cumulative research
contrasts from every completed 2026 game. No source, qualification or admission
policy is silently relaxed; the retrospective 2024 roster integrity exception is
explicit and isolated from production ingestion.

The fresh 2024 test and archived 2026 transfer increments remain inconclusive.
Fixed-signal calibration improves, but hierarchy coverage and QB/team allocation
remain inadequate. An independently preregistered known-variance control diagnoses
variance estimation/boundary effects; its synthetic knowledge cannot set real
intervals. Full-design non-estimability identifies dependence on hierarchical
assumptions, not a requirement to identify causal effects. These results do not
admit QB CAVAA or establish cross-position comparability. Every revealed test is
now consumed. Future model changes require a frozen rationale and new validation;
no scalar interval inflation or outcome-driven gate changes are authorized.


## November 8 multi-season decision

The [frozen multi-season study](MULTISEASON.md), [fresh failure control](MULTISEASON_CONTROL.md)
and [measured decision](MULTISEASON_RESULTS.md) integrate variance uncertainty and
historical QB/team-season information. Only archived 2026 opportunities contribute
season points; the first-unit benchmark and both sensitivities remain separate
from qualification. All 17 public modules remain unadmitted.

Matched-finite-prior coverage is 95.13%, but off-grid coverage is 90.78% and a fresh
control gives 89.56% versus 94.34% with unavailable true variance ratios. Avoiding
the severe-undercoverage flag is not a nominal-95% pass. Known ratios cannot set
real intervals. Small sensitivity within the same coarse grid is not robustness
to different variance assumptions. Historical links leave important QB/team
allocation ambiguity; null directions describe assumptions rather than impose a
causal-identification requirement on an observational estimand.

The required defensive follow-up measures a residualized player-rank loss from
856 to 193 on identical rich/degraded populations. Its unweighted mean contrasts
are not positional CAVAA, and its likelihoods have different observational units.
No defensive uncertainty or cross-position comparability pass is claimed.

All newly inspected simulation outcomes are consumed. One subsequent continuous-
variance candidate needs a new frozen rationale, numerical integration checks,
new draws and prior sensitivity; do not inflate intervals or add complexity to
manufacture coverage. The saved models and 2026 Week 10 prospective window remain
frozen. Fresh prediction is necessary evidence and still cannot prove allocation.

## Continuous variance candidate (November 9)

The [frozen continuous candidate](CONTINUOUS_VARIANCE.md) replaces the finite
precision grid with independent Normal(log(400), 3²) priors on log precision.
This removes the coarse support restriction while leaving the outcome model,
first-unit benchmark, both sensitivities and noise prior intact. It estimates
observational QB dropback contrasts under explicit hierarchical assumptions;
team-season effects remain coarse cast/scheme controls, not measured individual
protection or receiver quality. No new post-play mediator is adjusted away.

Historical opportunities contribute no 2026 points. The season ledger retains
every archived completed game's observed QB dropbacks and negative contributions.
It distributes the estimated season-level QB effect over that player's observed
opportunities; it is not a play-specific causal reward or a time-varying weekly
skill estimate. A new fitted version may revise earlier contributions and must
not overwrite a previously published version. Benchmarks remain independent of
qualification. Unresolved stints and unsupported positions stay unavailable.

Changing an integration proposal does not change these priors or the estimand:
the [numerical repair](CONTINUOUS_NUMERICS.md) corrects every draw by its exact
mixture density. Numerical precision, simulated coverage, fresh prediction and
attribution/admission are separate findings. A wider computed interval by itself
is no evidence of progress. Neither this study nor its commands publish scores.

## Independent numerical reference (November 10)

The [bounded pilot](VARIANCE_REFERENCE.md) changes numerical integration, not the
continuous candidate's scientific assumptions. Axis conditional density curves
construct a full-support proposal; exact joint-density corrections preserve
dependence among QB, team and game variance parameters. They are not estimated
posterior marginals or additional player-quality features. First-unit and both
sensitivity contrasts retain shared player/benchmark covariance.

A [separate smooth transform](VARIANCE_REFERENCE_SMOOTH.md) supplies deterministic
adaptive cubature as an independent numerical check. Agreement can establish
useful numerical evidence for this fixed target, not correctness of the target's
allocation assumptions. The five pilot cases include three already consumed
synthetic stress draws, so their outcomes cannot supply a fresh calibration pass.
Every resulting estimate remains uncalibrated and unadmitted. No context variable,
benchmark population, qualification rule or defensive admission changes here.

[Exact bounded node reuse](VARIANCE_REFERENCE_REUSE.md) removes repeated solves
in the pinned reference rule. Identical cached/uncached integrals are required;
this changes computing cost, not the scientific target or acceptance rules.

The November 11 [dimension-adaptive reference](VARIANCE_REFERENCE_ADAPTIVE.md)
changes spatial refinement under the same work/error limits. Its
[correlation-aware follow-up](VARIANCE_REFERENCE_WHITENED.md) uses weighted
log-precision moments only to choose full-support integration coordinates. Those
moments are not substituted for posterior variance uncertainty; each node retains
the original target and exact transformation density. The geometry shares QMC
information, so independence refers to integration method, not data or all code.
No player, team, benchmark, opportunity or admission definition changes.

The November 12 [higher-order reference](HIGHER_ORDER_REFERENCE.md) uses nested
open Fejer rules and a Smolyak sum instead of local low-order subdivision. Its
negative quadrature weights are mathematical integration weights, never player
opportunities or posterior probabilities. A separately frozen
[tensor comparison](HIGHER_ORDER_TENSOR.md) tests two public SciPy quadrature
rules on known targets. Both tensor alternatives fail the complete controls and
are explicitly blocked from the archived pilot. Full-support normal coordinates
in that control do not replace the original log-precision prior. No numerical
method changes the CAVAA estimand, first-unit membership or season ledger.

The November 12 manual [randomized reference](RANDOMIZED_REFERENCE.md) computes
mass and signed mean/CDF integrals under independent scrambled Sobol replicates.
It propagates numerator/denominator covariance through Fieller confidence sets.
These are **numerical** uncertainty estimates, separate from the player posterior.
Density-only [proposal adaptation](RANDOMIZED_REFERENCE_ADAPTATION.md) changes
sampling efficiency with exact density corrections; it does not fit new football
effects, change priors or widen player intervals. No primary-QMC samples or known
control answers train that proposal. Shared target/conditional code and the Sobol
family remain explicit dependencies, so this is not wholly independent model code.

Both initial proposals and the first adapted study fail. A larger, separately
frozen [confirmation](RANDOMIZED_REFERENCE_CONFIRMATION.md) of the identical
adapted geometry passes its four known-answer gates. This permits a numerical
pilot only. It cannot validate player attribution, resolve QB/team aliasing or
admit a contribution module. The [results](RANDOMIZED_REFERENCE_RESULTS.md) retain
the failures and distinguish primary/reference disagreement from uncertainty in
the reference itself. Scientific mean/CDF limits, benchmarks, eligibility and
the full archived season ledger remain unchanged.

The November 13 [paired density study](DENSITY_HOLDOUT.md) compares that sampler
with one fixed covariance-stabilized alternative. It regularizes the sampling
covariances toward the independently fitted curvature/global covariance, with
strength determined by dimension and normalized pilot-weight concentration.
The effective count here is a weight-concentration diagnostic for dependent net
points, not an independent sample size or a football participation denominator.
This changes the integration proposal, not any player/team variance prior. Both
proposals see the same pilot; an independently sampled mixture evaluates their
density overlap on the same holdout points with exact mixture probabilities.
The original proposal remains available and its four saved control geometries
reproduce exactly.

Held-out log-score and normalized second-moment comparisons diagnose proposal
quality; neither is a football score or an admission rule. A pre-result
[tail amendment](DENSITY_HOLDOUT_TAIL_AMENDMENT.md) replaces a quadratic curved
control, whose Gaussian importance variance is infinite, with a bounded-sine
transformation with independently known answers and finite variance. Empirical
coverage remains required: finite variance alone does not make the approximate
numerical confidence construction reliable. No posterior interval, functional
tolerance, source cutoff or benchmark changes in this study.
