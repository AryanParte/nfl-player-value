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
