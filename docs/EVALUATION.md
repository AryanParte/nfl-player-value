# Evaluation and release gates

The model must pass separate checks for data integrity, outcome prediction, individual attribution, and honest product labeling. A good team prediction is not proof of correct player allocation. Official MVP voting is descriptive comparison material, not the training target or ground truth.

## Baselines and splits

Start with a context-only baseline and a transparent regularized additive player model. Compare added teammate, opponent, hierarchical, and time-varying components against those baselines. Use chronological held-out games and held-out seasons; estimate opponent and supporting-cast features without future information or the held-out outcome leaking into their construction.

Declare training windows and historical data availability before evaluating. Simulate the information actually available at each weekly cutoff. A historical file corrected after the season does not necessarily reproduce what was knowable live.

Evaluate appropriate outcome error/calibration and held-out predictive distributions. EPA supplied by an upstream model inherits that model's assumptions; freezing a data/model version is necessary for reproducibility and does not certify the target as perfect.

## Attribution tests

| Test | Evidence it can provide | What it cannot prove |
| --- | --- | --- |
| Known-effect simulations | Recovery, bias, interval coverage, and failures under controlled collinearity | Correct attribution in real football |
| Player absences and replacements | Whether estimates align with observed changes after measured adjustment | Random treatment assignment; injuries and substitutions are selected |
| Supporting-cast changes | Stability and sensitivity to teammate changes | Complete separation of coaching, scheme, player growth, and role |
| Team/player collinearity checks | Weak identification, shrinkage dependence, and interchangeable effects | That a narrow model interval includes unmeasured confounding |
| Accounting audit | No duplicate full-play credit or overlapping component bonuses | That the chosen allocation is uniquely correct |
| Historical case review | Plausibility and discoverable failures | Validation through agreement with famous players or narratives |
| Comparison with established metrics | Shared and divergent behavior worth investigating | That an existing metric is causal truth |

Report negative and failed results. Historical examples must include ordinary and difficult cases, not only conspicuous successes.

## Uncertainty and sensitivity

Propagate player and benchmark uncertainty jointly. Where resampling is used, preserve meaningful dependence such as games and team structure rather than treating every play as independent. For Bayesian extensions, check sampling convergence and prior sensitivity before interpreting posterior intervals. Numerical convergence alone does not resolve identification.

Present statistical intervals separately from results under alternative benchmark populations, role definitions, model structures, and eligible data sources. Missing assignments or tracking information are structural limitations; do not imply that an ordinary posterior interval fully captures them.

Rank uncertainty should be derived from joint estimate draws when available, not inferred by sorting marginal interval endpoints. Preserve the covariance between teammates and between a player and his benchmark.

## Bounded qualification study

Evaluate the provisional role-specific opportunity requirements at **0.75×, 1×, and 1.25×**, retaining the three-game rule unless evidence motivates a separately reviewed change. Specify integer rounding consistently. Test historical weekly cutoffs, not only full seasons.

Record membership coverage, shrinkage, future predictive stability, sensitivity of estimates/ranks, and position/role representation. Rank movement can reflect real new performance; stability is a diagnostic, not an objective to maximize blindly. Choose the least restrictive defensible policy and freeze it before launch. Do not tune thresholds to include favorites or force positional diversity.

All valid participants continue to inform fitting; eligibility changes must not silently change the benchmark. Exercise trade, missed-game, bye, late-signing, position-change, duplicate-opportunity, and missing-denominator cases.

October 26: [weekly roster evidence](ROSTER_INPUTS.md) covers exact-week joins,
missing/ambiguous identities, trades, byes, gaps and position changes, with real
2025/2026 offline replay. It fixes the observed-by completion-time overlap bug.
These are input-contract tests, not the bounded qualification study or evidence
of complete player exposure. Weekly status rows do not independently establish
transaction time, participation or all missed games. Every denominator remains
unvalidated, and no player is qualified by this join.

## Position/contribution admission

Before any module enters the unified leaderboard, document:

1. Its observed opportunities and unmeasured contributions.
2. Its expected-point target, sign convention, benchmark, and common-context comparison.
3. Source coverage, permitted use, identifiers, and denominators.
4. Its relationship to shared/team components and duplicate-credit prevention.
5. Historical predictive and attribution evidence, uncertainty behavior, and sensitivity failures.
6. Why comparison with the other admitted modules is defensible.

The decision is recorded per module, not inferred from a position label or sufficient snaps. An experimental tag does not authorize incomparable scores. A targeted-receiving model cannot silently become a full-player receiver model. Defensive admission additionally requires the [information-loss experiment](DEFENSE_EXPERIMENT.md).

## Release acceptance

- Reproduce the ranking bundle offline from recorded inputs, code, and configuration.
- Include only completed games with declared required-source coverage.
- Fail closed on unresolved benchmark cells, invalid denominators, and output-schema failures.
- Expose supported scope, unavailable contributions, as-of time, benchmark, and uncertainty interpretation.
- Preserve original weekly releases and identifiable revisions.
- Keep last-good output available when the next refresh fails.

No live rankings or empirical evaluation results existed in the foundation unit.
Numeric success tolerances must be documented before inspecting final held-out results.

October 23: the [first baseline experiment](BASELINE.md) now has a committed
pre-evaluation plan and [real results](audits/2026-10-23-offensive-baseline.json).
The historical actor-identity increment over observed-role information has a
game-bootstrap interval spanning zero. The 2026 transfer increment is small and
does not establish individual attribution. The validation-selected penalty remains
1000 even though 100 has a better final historical test RMSE: changing it using
that test would leak evaluation information. Further model development must use
new validation windows/folds and disclose that these test results are now observed.
No defensive, qualification, benchmark-contrast or player-interval gate passed.

October 24: the [bounded defensive comparison](DEFENSE_MODEL.md) uses the exact
same games/targets for lineup and aggregate fits. Neither selected defender model
beats its own team/context baseline with a 95% interval below zero. Lower aggregate
prediction error is not evidence of correct allocation, especially with 650
unidentified linear dimensions across 951 defender columns. The [audit](audits/2026-10-24-defensive-model.json)
preserves the negative result, selection diagnostics and non-admission decision.
The richer model is not ground truth; these tests are now observed. Broader
historical/live-degradation, position, benchmark and player-uncertainty gates remain
open. No aggregate error interval is relabeled as uncertainty in individual value.

October 27: the [bounded contrast experiment](CONTRASTS.md) implements both
benchmark sensitivities, joint conditional player-minus-benchmark intervals and
the qualification grid on a documented, selected exposure subset. Synthetic
tests independently verify linear algebra, shared-covariance propagation,
prior-only players, per-play accounting and no later-window leakage. Real-source
replay and measured sensitivity are reported in the dated audit. This completes
neither uncertainty calibration nor the full qualification study: game/team
dependence, general missed-game/stint coverage, selection effects, future
predictive stability and cross-position admission remain open. Do not select a
penalty or threshold using these now-observed results, and do not call these
within-prefix fits new held-out evidence.

October 28: the [frozen known-effect calibration](CALIBRATION.md) now runs 6,144
synthetic-response fits on both archived Week 6 designs. The selected penalty's
conditional intervals cover about 95% under the matched-prior population, but
below 2% under the declared stronger fixed signals. All four roles fail the
prespecified severe-undercoverage flag in those fixed-signal scenarios. That
does not measure actual NFL error rates; it falsifies a general calibration claim
for this working model. Experimental game-cluster CR0 and oracle sampling widths
cannot fix shrinkage bias. Oracle expectation controls verify sampling algebra
using unavailable truth. No method is promoted, and the penalty is not retuned.
Exact alias cases report both affected and unaffected contrasts rather than
assuming every coappearance problem affects the selected estimand. Real absence,
supporting-cast, general exposure and module admission decisions remain open.

October 29: the [frozen observed-transition audit](TRANSITIONS.md) evaluates
unchanged models on direct adjacent completed games in the original evaluation
partitions. It preserves every excluded pair and all QB-change cases, including
unsupported identity swaps. The eight historical/five 2026 QB changes do not
improve mean change prediction over the observed-role baseline. The target-mix
subgroups are sparse and selected; a favorable subgroup cannot admit a module.
Leave-one-offense-team-out ranges describe sensitivity, not confidence intervals.
These previously examined outcomes, retrospective rosters and realized target
counts do not establish injury causes, causal substitution or cast quality.
The [audit](audits/2026-10-29-transitions.json) binds all source hashes and cutoffs.
Formal module decisions remain due October 30; scientific gaps are not waived.

November 2: the overdue decision is now [formally recorded](decisions/2026-11-02-module-admission.md)
with an [executable non-admission registry](ADMISSION.md). Every role has an
explicit module scope and data/benchmark/denominator/accounting/attribution/
uncertainty/comparability findings. All current modules remain unadmitted.
The gate checks exact evidence/policy hashes and preserves participation rules;
it does not refit models, establish scientific truth or validate a production
ranking bundle. Positive admission requires new reviewed evidence and a contract
revision. No numerical criterion is relaxed or new validation result claimed.


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

## Continuous-variance numerical acceptance (November 9)

The [continuous plan](CONTINUOUS_VARIANCE.md) separates numerical integration
from model calibration. Independent and nested posterior means/endpoints must
agree within the frozen fractions of posterior SD, with adequate effective
samples. Failure at the cap leaves the candidate numerically unverified. It must
not enter the prospective comparison or imply that its interval is calibrated.

The [one bounded numerical repair](CONTINUOUS_NUMERICS.md) keeps the exact target
distribution and scientific decision rules. Heavy-tailed, stratified proposals
change sampling efficiency; full importance-density corrections preserve the
posterior. The interrupted attempt and completed checkpoints are retained.
Repeated synthetic responses check this numerical change; they do not constitute
an independent second scientific experiment. No selected unfavorable trial can
disappear from the requested calibration denominator. Success-only coverage is
explicitly conditional, with all-trial bounds that include failed/unverified draws.

Independent known-normal and scalar-quadrature references supplement the inherited
observation-space likelihood checks. Numerical agreement is necessary but not a
proof of exact integration. Conditional calibration under a proper random-effect
generator remains different from NFL model adequacy, correct attribution or
cross-position comparability. The Week 10 prospective window stays sealed.

The [completed diagnostic scope](CONTINUOUS_RESULTS.md) has eight attempts per
generator, not all 64 requested fits. The [predeclared scope stop](CONTINUOUS_DIAGNOSTIC_STOP.md)
retains 56 unattempted fits in each denominator. Both real candidates fail
numerical accuracy; no complete calibration or observational admission follows
from this study. An independent numerical reference and small runtime pilot must
precede another full calibration campaign.

## Numerical-reference pilot (November 10)

The [frozen five-case pilot](VARIANCE_REFERENCE.md) retains the existing
independent/nested QMC mean/endpoint checks and adds an independent deterministic
reference. The reference must converge and meet explicit posterior-mean and
endpoint-CDF discrepancy limits after propagating both numerator and normalizing
mass error estimates. Its estimated error is not a rigorous bound. Smooth
reference coordinates and an exact mass-offset identity fix poor numerical
conditioning observed in known-answer controls; all tolerances remain unchanged.
The documented [repair chronology](VARIANCE_REFERENCE_SMOOTH.md) precedes NFL results.

Evaluation and time caps are enforced, and each of the five declared cases is
retained as passed, failed or unattempted. A success cannot silently omit a hard
case. Timing is execution metadata, separate from the reproducible numerical
artifact. A replay must match all case decisions and mathematical outputs;
wall-clock stopping can make an interrupted or time-limited run irreproducible,
which must be reported rather than ignored. Passing software tests and analytic
references do not constitute fresh NFL or uncertainty validation. Bounded exact
node reuse must preserve the uncached reference's numerical outputs and failure
decisions; its [frozen execution policy](VARIANCE_REFERENCE_REUSE.md) keeps the
same case selection, model, tolerances and resource limits.

## Dimension-adaptive numerical reference (November 11)

The [frozen binary-refinement plan](VARIANCE_REFERENCE_ADAPTIVE.md) keeps the
posterior and error gates fixed while selecting one local refinement direction.
Analytic polynomial and anisotropic Gaussian integrals check its actual error,
not just its success flag. The following
[correlation-aware coordinates](VARIANCE_REFERENCE_WHITENED.md) use primary-QMC
geometry but a separate adaptive integration method, with exact density/Jacobian
correction. Shared geometry is disclosed; neither calculation is independent
football evidence. There is no guarantee for arbitrary untested integrands.

A known correlated control has inaccurate QMC endpoints: both the sampler's own
diagnostics and the deterministic reference reject them. Separate scalar
Normal/Student-t convolution roots verify the correct interval. Preserve that
regression, complete failed references and every consumed stress case. A numerical
pass is separate from fresh calibration, predictive validation and observational
admission. No expected coverage requirement, prior, scientific threshold or
eligibility policy changes in this numerical unit.

## Higher-order numerical controls (November 12)

The [frozen sparse rule](HIGHER_ORDER_REFERENCE.md) requires two small complete
level increments before checking the unchanged normalized mean/CDF tolerances.
Node counts and integer-angle nesting are independently verified; the integrator
retains only complete levels at the work cap. Error indicators are estimates,
not rigorous bounds for arbitrary integrands. Correlated/skewed moment controls
honestly retain nonconvergence; a correct scalar-convolution interval passes and
an incorrect one is rejected.

The [frozen tensor follow-up](HIGHER_ORDER_TENSOR.md) selects neither candidate.
Gauss–Hermite resolves the basic known moments but fails the interval control at
the fixed order cap. Gauss–Legendre also underestimates error on some controls;
these cases do not falsely declare convergence. The archived pilot rejects both
configurations explicitly, while the analytical study remains reproducible.
Do not increase order or relax an indicator after looking at results and call it
the same experiment. Repeated numerical controls are not fresh calibration or
evidence of correct football attribution. Preserve all failures and the sealed
Week 10 window; [complete results](HIGHER_ORDER_REFERENCE_RESULTS.md) record the
case-level decisions and independent replay.

## Replicated numerical-error coverage (November 12 manual follow-up)

The [frozen randomized study](RANDOMIZED_REFERENCE.md) checks actual error against
analytic masses/means/variances and independently solved scalar-convolution
endpoints. Independent replicate integrals supply approximate Student-t/Fieller
sets; individual points within a Sobol net do not supply independent errors.
All trials remain in denominators, and unbounded mass/ratio sets fail explicitly.
Positive mass uncertainty, signed ratios, multiple quantities and all QB-prior
sensitivities remain in the numerical check. Exact reproduction is not coverage.

Initial local-t/prior-mixture proposals fail precision. A predeclared density-only
adaptation repairs known-answer precision but fails the 128-trial tail coverage
gate. Its failure is retained. The original lower-bound test has only 0.540714
pass probability at true 95% coverage and n=128. The subsequent fixed 1,024-trial
audit preserves the exact proposal geometries and every original gate, adds a
joint undercoverage test, uses fresh randomizations, and has no optional stopping
or follow-on retries. This rationale is committed before those new outcomes.

All four fixed confirmation gates pass: measured joint coverage is 94.34–95.31%
and precision passes in 99.12–100% of trials. Binomial uncertainty and all marginal
tests are retained in the [results](RANDOMIZED_REFERENCE_RESULTS.md). These reused
diagnostic functions with fresh numerical randomizations do not supply fresh
football validation. Empirical coverage is conditional on the four proposals and
integrands tested; it is not a guarantee for NFL tail behavior or a larger family
of functionals. The raw deterministic integration stopping indicator is replaced
by positive mass and ratio uncertainty for this fixed randomized design, with
the same 0.01 posterior-SD mean and 0.001 endpoint-CDF accuracy requirements.

The archived pilot is authorized only by a complete verified control certificate.
It retains all five cases and the original primary-QMC checks/work caps. No
extra primary samples, interval inflation, selective case removal or calibration
claim follows a reference failure. Report point discrepancy and numerical error
separately: an inconclusive reference cannot establish a biased football estimate.
The 192-fit player calibration, prospective prediction and observational admission
remain distinct outstanding decisions. No module is admitted by this study.

## Paired density holdouts (November 13)

The [frozen plan](DENSITY_HOLDOUT.md), its pre-result [tail amendment](DENSITY_HOLDOUT_TAIL_AMENDMENT.md)
and `config/density-holdout-v2.json` declare one stabilized proposal, 32 paired
fits for each of five known targets and four pairs for each of the five consumed
archived targets. Proposal fitting uses density-only pilot points. Independent
holdout points estimate log-score gain and normalized second moments; raw
replicates, training-point/weight hashes, all starts and convergence flags remain
available. Descriptive intervals across pilot fits are not admission tests.

Coverage uses only pilot zero, never a proposal selected for a favorable result.
Exactly 1,024 fresh numerical trials per known target retain the original
mass/mean/CDF accuracy limits and wrong-endpoint rejection. Every requested trial
remains in the denominator. Joint and marginal binomial undercoverage checks,
positive bounded Fieller sets and precision must all pass. A failed control blocks
the optional archived CAVAA reference; density-only failure analysis may still
run. No additional confirmation retry is allowed within this frozen study.

The archived numerical pilot, if authorized, preserves primary-QMC samples and
the existing five-case budgets. Independent reconstruction disables sockets and
DNS after imports, and compares the immutable manifests and all study objects.
Prior studies remain untouched. This unit does not consume new calibration draws
or the sealed Week 10 outcomes. No known-answer or density-overlap result can
validate the QB/team attribution assumptions by itself.

## Conditional solver equivalence (November 14)

The [frozen conditional study](CONDITIONAL_SOLVER.md) requires independent
80-/110-digit answers on all 72 small cases before archived use. It checks signed
means, joint contrast variance, residual quadratics and integrated likelihoods,
including exact/near aliases, prior-only players and tiny game precision. Plain
QR fails eleven local cases and is blocked; exact-alias QR initially passes
locally but later fails the hosted portability gate. The [results](CONDITIONAL_SOLVER_RESULTS.md) retain all
candidate and baseline failures rather than replacing unsuccessful controls.

Eighty-five archived coordinate comparisons and the recorded failure point pass
their declared checks; the formerly failed density fit now completes under its
original cap. These consumed cases are numerical diagnostics. Raw-row and
reordered-basis checks share the new algebra; they are not an independent
arbitrary-precision NFL solve. Both full artifacts reconstruct with network
access disabled, and software regression tests require the complete preferred
control gate. The near-alias residual error lies close to its strict bound, so
platform/implementation regressions must fail visibly rather than weaken it.

No new numerical-error coverage experiment, full posterior pilot, player
calibration or admission follows automatically. The next functional comparison
must be frozen separately with independent randomizations and unchanged scientific
limits. Keep Week 10 sealed and the failed prior versions immutable.


The [residual amendment](CONDITIONAL_RESIDUAL_AMENDMENT.md), frozen at `92d21ea`,
requires the repaired candidate to pass the original 72 controls plus 72 controls
from the new declared response seed. All 144 pass locally against independent
80-/110-digit answers. The original 1e-9 quadratic limit remains unchanged;
platform failure is never grounds for skipping this gate. Archived equivalence,
failed-fit completion, offline replay and hosted Python portability must be reported
separately for this amended candidate. Original results cannot authorize it by
inheritance. No new football outcomes or post-result coverage tuning are used.

## Two-level reference acceptance (November 15)

The [frozen repaired-target experiment](REPAIRED_FUNCTIONAL.md) retains the
0.01 posterior-SD mean and 0.001 endpoint-CDF limits and simultaneous family
adjustment. Both numerical levels use independent replicate randomizations;
each correction pairs fine/coarse calculations at identical points. Raw levels
must reconstruct the combined integrals, confidence sets and reported decisions.
Known-answer authorization includes independent analytic truth, all 5,120 trial
outcomes, the complete saved sampling components and the executing source hash.

The source-restoration defect and its [pre-result correction](REPAIRED_FUNCTIONAL_CORRECTION.md)
are recorded separately. No failed study may be overwritten or silently excluded.
Fresh numerical draws on consumed football targets are not fresh football
validation. Keep prediction, player calibration, participation and cross-position
admission gates separate even if numerical comparisons pass. The previous
192-fit calibration denominator remains unchanged by this experiment.

The corrected 32-replicate study completes and reproduces independently, but one
marginal numerical coverage test fails. Its descriptive error decomposition is
not a replacement acceptance rule. The single frozen equal-work alternative uses
fresh entropy, 64 independent replicates and half as many points per net, with
the original 5,120-trial denominator and all original gates. If it fails, stop
this bounded family of alternatives; no further replicate increase or favorable
seed is selected within the unit. Preserve the failure and diagnose it separately.

The final alternative passes all five controls; all archived cases complete,
but only one passes the unchanged numerical limits. This ends the bounded family.
The [results](REPAIRED_FUNCTIONAL_RESULTS.md) distinguish raw agreement from
agreement certified with numerical error. Post-result influence diagnostics are
descriptive, not new acceptance rules. The next candidate requires a new frozen
design and fresh numerical draws; it cannot inherit player calibration or admission.

## Independently fitted control-variate acceptance (November 16)

Design d60052d freezes [one candidate](COARSE_CONTROL_VARIATES.md) before new trials.
It preserves the five known targets, 1,024 trials each, all numerical coverage and
precision rules, and every archived comparison. Separate fitting and evaluation
entropy domains are mandatory. All controls must pass before archived use; the
previous reference's passing certificate cannot authorize this changed estimator.

The unadjusted calculation uses exactly the same evaluation points. Report paired
actual-error variance and RMSE, measured coverage, first-order variance diagnostics,
fit rank and residuals. A fitting residual or a lower point estimate is not an
acceptance criterion. Every requested trial stays in its denominator, including
failed fitting or unbounded mass/ratio sets. Any paired complete subset is labeled
and cannot replace the full acceptance denominator.

New regression tests use independent Gaussian quadrature, exact signed functions,
collinear bases, source and artifact corruption, and omitted fitting evaluations.
The study retains raw adjusted/unadjusted/correction vectors, coefficient hashes,
training-draw hashes and all gates. Reconstruct independently with networking
blocked and preserve failed artifacts. Football data still ends November 7 evening;
these are fresh numerical draws on consumed targets, not new football validation.

The [completed results](COARSE_CONTROL_RESULTS.md) pass all known-answer numerical
coverage gates but fail four of five archived comparisons. Independent offline
reconstruction is exact. The tested pointwise-fit candidate is not adopted for
certification or player calibration; its passing team control is not an individual
CAVAA module. The paired plain comparison prevents attributing a seed-to-seed
improvement to the new method. All priors, primary artifacts and admission rules
remain unchanged.

## Integration-aware control acceptance (November 17)

Design 471fe97 freezes [one two-stage candidate](INTEGRATION_CONTROL_DESIGN.md).
Use fresh root 2026111701, 1,024 trials for each of all five known targets, and the
same coverage/precision/admission rules. Training-net size equals evaluation-net
size; entropy domains for pointwise fit, integration fit, evaluation and paired
correction are disjoint. Test exact signed covariance slopes and zero variance
against analytical answers, both-stage work accounting and altered raw training
arrays. Recompute the stored slopes and coefficient product during artifact load.

Keep 88,065 evaluations within the original 90,000 work cap and original time
caps. Retain timeouts as failures in the full requested five-case denominator.
Known-answer failure blocks archived NFL comparison. If controls pass, compare
all saved benchmark/prior contrasts without reading Week 10. Passing software
checks or numerical coverage does not complete the 192-fit player-calibration
study or establish observational attribution. Training variance, learned scales
and paired plain comparisons are descriptive diagnostics, not new gates.

The [recorded result](INTEGRATION_CONTROL_RESULTS.md) passes all five known-answer
gates but fails four of five archived cases. All complete within their original
caps. Retain point failures in the hierarchy/fixed-year stress cases and distinguish
them from confidence sets that exclude the tolerance region; none excludes it
here. Large uncertainty is not proof of agreement. Fixed-anchor ratio-influence
diagnostics and their analytical test explain the failure after results; they
are neither preregistered acceptance gates nor new held-out evidence. The current
known targets do not certify the stronger mass concentration seen in the hierarchy
case. Future tail controls and any changed fitting objective must be frozen before
new draws, with all original cases/limits retained and no selected plain fallback.

## Joint ratio-control and tail stress study (November 18)

Follow [JOINT_RATIO_DESIGN.md](JOINT_RATIO_DESIGN.md), frozen at 4d5f6bb before
implementation/results. Seven targets each require 1,024 trials: the original
five retain their original gates, while two additional targets use a separately
specified stress family. All seven must pass before archived NFL evaluation.
Tests independently verify covariance cancellation, signed/collinear directions,
per-prior mass ownership, complete work, separate entropy, corrupted coefficients,
seven-case storage and tail moments/CDFs. The CDF check integrates Student noise
against a normal CDF, independently of the fixture's normal-density convolution.
Numerical error and player uncertainty remain separate; the original player
calibration and observational attribution decisions are still required.

The completed [result](JOINT_RATIO_RESULTS.md) fails the combined certificate:
all finite coverage checks pass, but precision is only 6.0547%/0% for the added
tails. All 7,168 trials and two full executions remain in the audit; replay is
not extra independent evidence. The actual failed certificate is blocked before
NFL inputs. Diagnose point gaps separately from numerical allowances. Retain
point estimates whose confidence construction failed whenever they are defined,
and report their denominator explicitly. Isolated wrong-endpoint diagnostics
cannot count a mean/lower-endpoint failure as detection of an altered endpoint.
These post-result diagnostics do not change the frozen gate or its rejection.

## Functional proposal validation (November 19)

[FUNCTIONAL_PROPOSAL_DESIGN.md](FUNCTIONAL_PROPOSAL_DESIGN.md), committed as
ba3f5da before fresh study draws, fixes all eight cases, independent pilot/control/
evaluation entropy domains and the original archived work caps. The added target
has a separate declared undercoverage family; none of the first seven gates is
weakened. Every case requires all 1,024 requested trials, including failed intervals.
A separate 32-trial initial-proposal concentration diagnostic does not select the
candidate or replace the finite coverage/precision decision.

Analytical software checks cover Gaussian moments, per-prior normalization,
signed contributions, zero-envelope behavior, original defensive support,
independent samples, exact work, zero-mean controls, saved geometry corruption
and reverse Student-noise convolution. Retained failed-confidence records undergo
the same proposal provenance checks. Eight-case storage cannot accept an old
seven-case certificate; archived references must bind the actual fitted proposal.

Population-envelope moments are an explicitly declared analytic diagnostic, with
independent normal absolute/linear/quadratic-moment tests. They refer to unperturbed
fine-target envelopes, not the exact coarse-pilot population. Source-review
clarification d267f8d precedes complete tail results and adds a deterministic
mean-displacement bound for the .001 surrogate tilt, verified against an independent
sine-tilted Gaussian identity. It changes no candidate, gate or error allowance.
No oracle proposal is evaluated or selected. Exact offline reproduction does not supply additional
independent trials, validate attribution, or resolve the 192-fit player study.

Initial-pilot box calculation a660aba is declared before complete tail results.
Gaussian box masses and the fixed 2,048-point allocation per stratum yield expected
counts and a Markov bound on any point in that box. This uses no iid discovery
assumption or extra draws. It is an initial-allocation diagnostic, not a final
precision result, surrogate correction or new admission gate.

The [complete November 19 results](FUNCTIONAL_PROPOSAL_RESULTS.md) reject this
candidate. All 8,192 requested trials are retained and the two full executions
reproduce the manifest/all 17 objects. Broad-tail precision passes, displaced
precision is 33.5938%, and remote precision/coverage fail at 0%/30.9570%, with
47 failed confidence constructions retained. The actual saved certificate blocks
before NFL inputs. These findings support a bounded mode-resolving proposal
hypothesis, not an adopted fix, changed football model or player admission.

## November 20 bounded feasibility screen

The [mode-discovery design](MODE_PREFLIGHT_DESIGN.md) freezes 32 independent trials
per retained case plus two geometry extensions and four diagnostic oracle cases.
The smaller study is a feasibility screen: unchanged .01-SD/.001-CDF precision,
complete work accounting and severe-undercoverage checks may stop a poor candidate
before another full coverage campaign. It cannot replace the full certificate's
coverage lower-bound requirement, authorize NFL inputs or validate player effects.
Oracle truth is unavailable to the candidate; plain estimates are not selectable.

The [complete preflight](MODE_PREFLIGHT_RESULTS.md) clears eight candidate screens
but fails case 3 (0% precision) and case 7 (68.75% precision, 75% joint coverage).
All 448 requested trials are attempted with raw evidence; one confidence
construction fails. Both full offline builds match all objects. The actual saved
preflight report is rejected before archived NFL access. A post-result fine-target
mode-count calculation explains a limitation of local-peak search without changing
the candidate or gates. A separately frozen tail-preserving hypothesis is required
before new draws; the failed candidate does not proceed to full certification.

## November 22 tail-mixture comparison

Design a3dd981 freezes all ten cases, 32 candidate trials each and four 32-trial
matched mode-only diagnostics. Initial fits must reproduce exactly; evaluation
randomness is separate. Independent finite-sum/Gaussian tests verify adaptation,
and the full suite passes after repairing zero-count work validation, before draws.

All 448 trials retain raw integrals; 446 confidence sets finish and two complete
offline builds match every object. Six candidate screens pass, four fail. Case 3
improves 0/32 to 30/32 precision against the matched diagnostic, but case 6 falls
31/32 to 10/32 despite better means. The [failure analysis](TAIL_MIXTURE_RESULTS.md)
keeps failed-confidence point estimates, separate endpoint allowances and complete
denominators. No conditional subgroup, plain result or diagnostic arm is selected.
The actual saved preflight blocks NFL access; neither this screen nor exact replay
substitutes for full numerical certification, player calibration or attribution.

## November 23 protected proposal and matched diagnostics

Design 0b85e56 freezes 320 candidate, 128 mode-only and 128 tail-only trials
before numerical producer 1bc5718 and all study draws. Initial mode fits match
all arms; adaptation matches candidate versus tail-only. Evaluation and control
training use separate random domains. All ten retained synthetic cases remain,
with unchanged work, precision and severe-undercoverage rules.

The [results](PROTECTIVE_MIXTURE_RESULTS.md) reject progression after four failed
candidate screens. Independent Gaussian density and signed-integral tests verify
the implementation, but cannot validate numerical-error coverage. The known-answer
experiment supplies that separate evidence, retaining failed confidence sets and
defined point errors. The remote case has only 21/32 joint coverage. Full numerical
certification, the archived NFL comparison and unfinished player-calibration study
remain required. No new NFL outcomes or sealed Week 10 data enter this experiment.
