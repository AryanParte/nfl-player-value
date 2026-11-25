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

## Conditional arithmetic repair (November 14)

The [frozen solver study](CONDITIONAL_SOLVER.md) changes the conditional numerical
calculation, not the continuous posterior. Exact binary aliases within a common-
precision random-effect block and flat fixed context are reparameterized into
observed coordinates and independent proper-prior directions. The latter are
integrated analytically, and their full prior covariance is restored to requested
contrasts. This does not impose zero-sum player effects or delete players.
Different-precision blocks are not pooled; approximate aliases are not removed.

Square-root prior rows and stable within-game/mean decomposition retain tiny
positive precisions without adding jitter or subtracting nearly equal Gram
matrices. The [results](CONDITIONAL_SOLVER_RESULTS.md) support this opt-in kernel
on its bounded known-answer and archived checks. They do not show that every
possible prior-tail configuration is reliable, resolve QB/team attribution, or
admit scores. Existing integrated models and signed season ledgers remain
unchanged. Functional integration, player calibration and observational admission
are still separate requirements; no full posterior was recomputed in this unit.


Hosted portability testing subsequently exposed cancellation in the QR residual
quadratic. The separately frozen [amendment](CONDITIONAL_RESIDUAL_AMENDMENT.md)
keeps coefficient/covariance fitting and all prior/benchmark definitions unchanged,
but evaluates the original sparse-row penalized residual with compensated
products/summation, including game penalties. No Decimal truth is substituted into
production calculations. Original and fresh-response controls retain the exact
same tolerances; the failed earlier candidate remains archived. This corrects
arithmetic only, not attribution or uncertainty calibration.

## Repaired-target functional comparison (November 15)

The [frozen functional study](REPAIRED_FUNCTIONAL.md) estimates unnormalized
posterior integrals as a fast coarse integral plus an independent paired
fine-minus-coarse correction. The fine target uses the repaired conditional
kernel. This control-variate identity preserves that target in expectation;
normalizing the two levels separately would not. Both levels' variation and
mass/numerator covariance enter the replicate-based numerical confidence sets.
These approximate sets measure integration error, not player uncertainty or
unmeasured confounding. No prior, positional benchmark or admission rule changes.

An implementation [correction](REPAIRED_FUNCTIONAL_CORRECTION.md) restores the
synthetic controls' defensive proposal using their own zero-centered policy,
instead of the NFL model's policy. The failed attempt remains evidence of that
defect, not permission to select new seeds or change known answers. Numerical
coverage must pass before the archived targets, and every unsuccessful case
remains in its declared denominator. A reference pass does not finish the
outstanding player-calibration or observational-attribution work.

The corrected 32-replicate controls still under-cover one known endpoint. A
separately [frozen allocation alternative](REPAIRED_ALLOCATION.md) trades points
within each randomized net for more independent replicates, keeping total work
and the Student/Fieller construction unchanged. This tests the finite-replicate
approximation; it is not a multiplier applied to player intervals. Independent
quadrature and retained raw levels separate coarse error from correction error.
All controls must pass before the repaired NFL comparison is authorized.

The completed alternative passes all five known-answer controls but only the
team control in the five-case NFL pilot. Point discrepancies alone meet limits;
coarse integration error prevents certification. This is numerical imprecision,
not demonstrated primary-estimate bias or evidence to widen player intervals.
See the [results](REPAIRED_FUNCTIONAL_RESULTS.md) for retained failures, exact
replay, packaging recovery and the proposed next variance-reduction study.

## Independently fitted coarse controls (November 16)

The [frozen study](COARSE_CONTROL_VARIATES.md) adds zero-mean controls to the
coarse integration step. Each uses a normalized Gaussian density g, the complete
sampling density q, and Gaussian first/second-moment identities. For example,
g/q minus one has expectation zero under q. The fixed basis changes neither the
football posterior nor the average positional benchmark.

A separate 4,096-point sample fits the numerical approximation before evaluation.
Conditional on its fitted coefficients, subtracting these controls preserves each
unnormalized expectation. The paired repaired-minus-coarse correction remains;
only the sum is normalized. Randomized-net replicates are independent conditional
on the fit. Fresh fitting draws in every known-answer trial test the complete
procedure, including fitting variability. No control coefficients are football
player effects, and their small numerical ridge is not a player-prior adjustment.

Pointwise regression does not necessarily minimize randomized-integration error;
[Owen's QMC notes](https://artowen.su.domains/mc/practicalqmc.pdf) distinguish these
objectives. The paired unadjusted calculation is retained as a diagnostic, never
selected after observing a favorable result. Numerical confidence remains separate
from player uncertainty, observational identification and position admission.

The [completed results](COARSE_CONTROL_RESULTS.md) pass all known-answer numerical
coverage gates but fail four of five archived comparisons. Independent offline
reconstruction is exact. The tested pointwise-fit candidate is not adopted for
certification or player calibration; its passing team control is not an individual
CAVAA module. The paired plain comparison prevents attributing a seed-to-seed
improvement to the new method. All priors, primary artifacts and admission rules
remain unchanged.

## Integration-aware control fitting (November 17)

The [new frozen design](INTEGRATION_CONTROL_DESIGN.md), committed as 471fe97 before
new trials, learns a scalar rescaling of each pointwise composite control from
16 independent integration replicates. Their 1,024-point nets match evaluation.
Both fitting stages are independent of evaluation; the control's expected
integral remains zero conditional on their fitted coefficients. The numerical
ridge and scale are not player effects or football-prior modifications.

The centered covariance slope targets variance of an **unnormalized** integral.
A normalized mean or endpoint probability additionally depends on covariance
with the mass integral. Therefore neither training improvement nor improvement
of one raw integral proves improved final precision. All original signed ratios,
joint numerical confidence sets and known-answer requirements remain mandatory.
Raw fitting arrays reconstruct the scale and final coefficient product; paired
unadjusted evaluation remains a diagnostic, never a selected fallback.

The software reuses the existing study runner with an exact versioned plan hash;
it does not create another modeling pipeline. Historical experiments retain their
recorded source revisions. The complete package source hash prevents an old
certificate from authorizing a changed numerical kernel. The existing per-object
size cap, complete denominators and independent offline reconstruction remain.
Results and the retain/reject decision are recorded separately from this rationale.

The completed [November 17 study](INTEGRATION_CONTROL_RESULTS.md) rejects this
candidate for certification. Known-answer coverage passes; archived QB precision
does not. Post-result fixed-anchor covariance diagnostics show smaller numerator
variance alongside larger normalized-error variance, including within fitting.
This diagnoses an objective mismatch without changing the estimator or its gates.
The primary anchors are not known true NFL ratios. Weak mean-contrast improvement
and hierarchy-tail concentration are separate limitations; a future joint
mass/numerator fit requires a new frozen design and stronger analytic tail controls.

## Joint mass/numerator numerical controls (November 18)

The [frozen joint design](JOINT_RATIO_DESIGN.md) targets the integration error of
N-rZ using two existing zero-mean composite directions. It preserves the shared
mass adjustment algebraically and uses independent fitting/evaluation draws.
Centered means, .025/.975 endpoint anchors and each prior's own mass are fixed;
no evaluated ratio is a fitting input. The two added finite-variance analytic
mixtures challenge broad tails and displaced mass. Implementation and analytical
tests do not certify coverage, admit a player module or change the football
model. The [completed study](JOINT_RATIO_RESULTS.md) rejects this candidate:
all seven targets complete, but the two added tails fail precision. No football
reference or admission follows. Better training covariance does not guarantee
held-out variance reduction; the next hypothesis concerns proposal coverage of
required functionals, with a new freeze required before fresh draws.

## Functional proposal adaptation (November 19)

The [frozen proposal study](FUNCTIONAL_PROPOSAL_DESIGN.md) changes where numerical
integration evaluates the same target. Independent pilots fit three Gaussian
components to mass/mean, lower-CDF and upper-CDF absolute influences, retaining
the original defensive Gaussian. Each prior block has its own pilot normalizer.
Signed football contributions are never made positive: absolute values are used
only to choose a sampling distribution, and full importance ratios preserve the
original signed integrands. The paired fine correction remains exact in expectation.

Two fixed fitting rounds replace the preceding coefficient-refit allocation,
keeping 88,065 target evaluations per archived case. There is no fitting on
evaluation replicas or after-the-fact plain-estimator fallback. Proposal covariance
shrinkage/eigenvalue bounds are sampling choices, not wider player intervals or
changed football priors. Full support and a finite variance do not imply adequate
finite-work accuracy. The more remote narrow-mode fixture tests that limitation.

An independent analytic population-moment diagnostic conditions multivariate
normal moments on each scalar contrast. It uses unperturbed fine-target envelopes;
comparisons with fitted geometry also include the bounded .001 coarse-surrogate
tilt and finite-pilot covariance shrinkage. The mean-displacement bound is reported
separately, never subtracted from error or treated as a covariance/precision bound.
Point probes of the density ratio do not bound integration variance. This is never
a substituted oracle model.
The implementation and software tests alone admit no CAVAA contribution.

The [complete November 19 results](FUNCTIONAL_PROPOSAL_RESULTS.md) reject this
candidate. All 8,192 requested trials are retained and the two full executions
reproduce the manifest/all 17 objects. Broad-tail precision passes, displaced
precision is 33.5938%, and remote precision/coverage fail at 0%/30.9570%, with
47 failed confidence constructions retained. The actual saved certificate blocks
before NFL inputs. These findings support a bounded mode-resolving proposal
hypothesis, not an adopted fix, changed football model or player admission.

## November 20 mode-discovery feasibility design

The [frozen preflight](MODE_PREFLIGHT_DESIGN.md) tests bounded multi-start search,
local curvature proposals and independent mass fitting. It receives only a
log-density callable and initial geometry; analytic mixture parameters enter a
separate unavailable-to-NFL oracle diagnostic. Full importance weights preserve
the target. There is no football prior, likelihood, benchmark or ledger change.
A preflight report cannot serve as a numerical certificate or admit any score.

The [complete preflight results](MODE_PREFLIGHT_RESULTS.md) reject progression:
original case 3 fails precision and remote case 7 fails precision/coverage. All
448 candidate/diagnostic trials retain raw evidence and reproduce exactly; one
confidence construction fails. The post-result derivative diagnosis distinguishes
nonmodal tail mass from a missed density peak. Oracle results do not authorize NFL
work. The next bounded hypothesis must preserve both tail shape and mode coverage;
no new method, player calibration or scoring admission is claimed.

## November 22 tail-mixture result

The [frozen tail-mixture study](TAIL_MIXTURE_DESIGN.md) changes only the sampling
proposal: a broad component plus independent target-weighted mixture adaptation,
with original defensive support and full importance weights. The [complete result](TAIL_MIXTURE_RESULTS.md)
improves one broad-tail screen but fails four retained cases. Matched initial fits
show that better mean accuracy need not improve endpoint precision. All failed
intervals and signed integrals remain; no football prior, benchmark, ledger or
admission rule changes. A protective coverage hypothesis must be frozen separately.

## November 23 protective-mixture result

The [frozen protective mixture](PROTECTIVE_MIXTURE_DESIGN.md) preserves half the
original mode proposal and half the adapted tail proposal. Full mixture weights,
original defensive mass and signed integrals preserve the numerical target.
The pointwise density floor bounds an unnormalized second moment; it does not
certify finite fitted-control variance, ratio uncertainty or QMC coverage.

The [completed study](PROTECTIVE_MIXTURE_RESULTS.md) rejects progression: six of
ten candidate screens pass. The broad nonmodal case reaches 32/32 precision;
the displaced case reaches 21/32 versus 32/32 for matched mode-only and 11/32 for
tail-only. Every displaced-case trial finds both modes, yet 11 combined endpoint
checks fail. Density protection alone is insufficient. Remote discovery and
post-discovery precision must remain separate diagnostics. No control/diagnostic
fallback, football prior, benchmark, qualification or admission rule changes.

## November 24 independent allocation and discovery

The [frozen allocation/discovery design](ALLOCATION_DISCOVERY_DESIGN.md) allocates
computer samples, not player value. An independent pilot estimates ratio residuals
including numerator/mass covariance, then an exact finite optimizer allocates the
unchanged integration budget across all components. Final integration uses the
original mixture masses and full proposal density; unequal sample counts never
change the target. Fitting, pilot, coarse evaluation and correction use disjoint
random domains. Known answers do not enter the allocator.

The [results](ALLOCATION_DISCOVERY_RESULTS.md) improve displaced/remote precision
and mode discovery but reject progression on curved-endpoint precision. Rare
remote errors and imperfect numerical coverage remain explicit. Smooth CDF
controls with analytically known integrals are a next hypothesis to freeze and
validate, not an implemented change. No likelihood, prior, CAVAA benchmark,
cumulative ledger, qualification or position-admission rule changes.
