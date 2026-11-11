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
