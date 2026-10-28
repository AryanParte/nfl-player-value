# Bounded calibration and attribution stress test

This plan is committed before numerical results. It tests the October 27
diagnostic estimator; it cannot establish causal NFL value or authorize a score.
The [frozen plan](../config/calibration-v1.json) and upstream contrast report IDs
are preserved in every result. The first-unit benchmark, both existing benchmark
sensitivities, qualification rules and primary penalty remain unchanged.

## Fixed design and known truth

Rebuild and verify the complete archived contrast chains for 2025/2026. Use the
Week 6 design from each season, where the existing audit found complete QB/RB/WR/TE
benchmark populations. Keep actual context, team/actor incidence, prior-only
parameters, first-unit weights and role-specific cumulative opportunities fixed.
All model actors remain in the joint fit. Evaluate every observed role-player's
first-unit contrast independently of qualification. The two alternative benchmark
populations remain in their original sensitivity reports; this bounded calibration
test evaluates the primary estimand only.

Generate **synthetic outcomes**, never simulated scores presented as real NFL
findings. Actual EPA is not used to choose effect sizes, generate truth, select
cases or tune penalties. Four prespecified scenarios use noise SD 1.5 EP:

1. **Matched-prior iid control:** independent Gaussian coefficient draws with
   variance `sigma² / D_jj` under the primary-penalty model, an intercept of zero,
   and independent play errors. This checks average coverage under the assumed
   coefficient population; it does not prove fixed-player frequentist coverage.
2. **Fixed-signal iid:** actor effects of ±0.25 EP, context ±0.1, team ±0.15 and
   observed-role ±0.05, with signs determined by the first SHA-256 byte of the
   feature name (even = positive). Intercept is zero. These illustrative effects
   deliberately test shrinkage away from stronger signals; they are not an
   empirically estimated NFL effect distribution.
3. **Fixed-signal game dependence:** same fixed effects; half the error variance
   is a shared game shock, half independent play noise.
4. **Fixed-signal team dependence:** half the error variance is a persistent
   offensive-team shock across its games. This violates independence across game
   clusters and tests that limitation explicitly.

Use PCG64 with seed components `[seed, season, week, scenario_index]`, 256 draws
per scenario, and the same synthetic outcomes for penalties 10/100/1000. No
penalty is reselected. Matrix factorization may be cached because X is fixed;
independent tests must match direct fits on the same synthetic responses. Neither
historical outcomes nor future windows add points to a 2026 player ledger.

## Intervals, bias and controls

For `H = X'X + D` and a contrast row L, let `A = X H^-1 L'`. The point estimate
is `A' y`. Evaluate three distinct diagnostics:

- The existing conditional Gaussian interval, using `(SSE/n) L H^-1 L'`.
- An **experimental game-cluster CR0** sampling-variance diagnostic:
  `sum_g (A_g' residual_g)^2`. This uses penalized normal-equation bread and
  uncorrected cluster scores. It is not a Bayesian posterior, has no small-sample
  or leverage adjustment, can be poor with few clusters, and does not repair
  shrinkage bias or repeated-team dependence. It is not a production replacement.
- An **oracle sampling** interval using the known simulated error covariance:
  `sigma² [(1-rho) sum_p A_p² + rho sum_c (sum_{p in c} A_p)^2]`. Its center is
  the same ridge estimate, so coverage of true Lβ can still fail from shrinkage.

The exact conditional bias for a known coefficient vector is `-L H^-1 D beta`.
Also report oracle coverage around the estimator's known expectation as a
numerical/distribution control. That bias-aware control uses unavailable truth
and must never be offered as a real-data correction. All intervals use the fixed
normal 95% critical value; none includes model-selection or structural uncertainty.

Report coverage, mean interval width, bias and RMSE by role and overall, plus
per-player diagnostics. Monte Carlo uncertainty uses the standard deviation of
per-replicate coverage fractions divided by sqrt(replicates), preserving the
shared-player/benchmark dependence within each draw. Do not treat all
player-by-replicate cells as independent trials. Flag severe undercoverage when
`coverage + 1.96 * Monte Carlo SE < 0.90`. This is a prespecified failure flag,
not an automatic admission rule or a claim that 90% satisfies nominal 95% coverage.

## Attribution impossibility check

For any two exactly identical observed actor columns, shift their coefficients by
`+0.25/-0.25`. Verify unchanged fitted play expectations and report the change in
first-unit contrasts. Also report a shift in each prior-only actor column, whose
observed design is zero. These are explicit pairs of observationally equivalent
attributions, not another fitted model or evidence that all players are equally
unidentified. A prior can choose one allocation but does not create information.

## Scope and evidence

This unit implements simulation calibration and exact-alias stress tests. Real
absence/supporting-cast cases, broader verified missed-game denominators, repaired
historical chart evidence and admission decisions remain separate work before
the October 30 freeze. Do not call this simulation a held-out prediction test,
an injury experiment, or a validation of the observed-role conditioning policy.
No individual position is admitted automatically, including if a control passes.
Defensive information-loss and Explorer outputs remain unchanged.

The cluster-score construction is motivated by the independent-cluster framework
in [Cameron and Miller, *A Practitioner's Guide to Cluster-Robust Inference*](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf).
The [statsmodels cluster-covariance documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html)
documents its regression implementation and optional correction. Our penalized
CR0 adaptation is derived explicitly above and checked against direct algebra;
we do not install statsmodels or claim its OLS results validate this ridge model.
Dependence assumptions and regularization bias require separate tests.

## Implementation and replay

The Python batch runner reuses the pinned NumPy/SciPy dependencies and immutable
JSON store. Its input is a saved positional-contrast report, not downloaded live
data. It first replays that report's entire source/cohort/model chain, then slices
the ledger before preparing the selected window. It checks the exact prepared-row
hash, game inventory, feature vocabulary and primary penalty against the archive.
All four first-unit populations must be complete; missing roles are not dropped.
Qualification does not select simulation participants or alter the benchmark.

Run from the repository root with the modeling extra installed and source changes
committed:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.calibration_cli build \
  --contrast-report CONTRAST_REPORT_SHA256 --plan config/calibration-v1.json
PYTHONPATH=src .venv/bin/python -m nfl_value.calibration_cli replay CALIBRATION_REPORT_SHA256
```

Default stores are the existing raw, offensive, roster and contrast stores;
output goes to ignored `data/derived/calibration`. Each can be overridden with
`--raw-store`, `--offensive-store`, `--roster-store`, `--contrast-store` or
`--output-store` **before** the subcommand. Replay regenerates the synthetic draws,
all interval diagnostics and alias cases, then compares structure exactly and
numbers at the existing absolute `1e-9` / relative `1e-8` tolerance. NumPy/SciPy
versions must match. A failed run does not alter earlier manifests or any dashboard
pointer. This is not a production publisher.

The manifest binds the complete plan, upstream report hash, executing code
revision, environment, source attribution, retrospective availability and both
cutoffs. In the reused snapshot writer, `objects.models` contains feature/contrast
order, first-unit weights and alias diagnostics; `objects.predictions` contains
simulation metrics by role and player. Neither contains a publishable fitted model,
real player score or ranking. Intervals and truth are in the declared cumulative
expected-point contrast units, conditional on the observed opportunity design.

Read `oracle_expectation_control` only as a numerical check: it measures sampling
coverage around the estimator's known expectation after accounting for its known
bias. A result near 95% there can coexist with almost no coverage of true player
effects. `mean_absolute_conditional_bias_ep` prevents positive/negative biases
from hiding through cancellation in `mean_bias_ep`. Alias indices refer to the
saved `contrast_order`; a reported coefficient shift is a constructed example,
not a proposed correction to that player's value.

## October 28 measured results

Plan commit `715a4bc` preceded implementation and results. Producer
`7c532b86af3692d14284351f0e2787253712707a` built and replayed both complete source
chains with HTTP/socket connections blocked. Each design contains 93 completed
games: 2025 has 11,157 plays / 444 role-player contrasts, archived 2026 has 11,441
plays / 463 contrasts. Across two designs, four scenarios, three fixed penalties
and 256 replicates, this is **6,144 synthetic-response fits**, using cached matrix
factorizations. These are not 6,144 independent NFL datasets. The source evidence
remains retrospective and the 2026 game cutoff remains October 22, Week 6.

The [audit](audits/2026-10-28-calibration.json) records report/object hashes,
environment, timing, all primary role coverages, overall interval metrics and
penalty sensitivities. Primary-penalty conditional-Gaussian coverage is:

| Known-truth scenario | 2025 coverage (MC SE) | Archived 2026 coverage (MC SE) |
| --- | ---: | ---: |
| Matched-prior iid | 94.85% (0.070 percentage points) | 94.94% (0.065 pp) |
| Fixed signal, iid noise | 1.94% (0.012 pp) | 1.13% (0.012 pp) |
| Fixed signal, game noise | 1.58% (0.019 pp) | 0.99% (0.011 pp) |
| Fixed signal, team noise | 0.96% (0.006 pp) | 0.88% (0.004 pp) |

The stronger-signal scenarios fail the prespecified severe-undercoverage flag
for every role at the primary penalty. This is evidence against treating these
intervals as generally calibrated. It does **not** establish that actual NFL
effects have the illustrative ±0.25 size or that real-player coverage is 1%.
Matched-prior coverage is an average over a favorable assumed population, not a
guarantee for each fixed player. Mean absolute conditional bias in the fixed-signal
scenarios is 8.11/8.15 cumulative EP across 2025/2026 contrasts.

Experimental game-cluster CR0 does not rescue the primary setting: overall
coverage is below 0.3% in the fixed-signal cases and about 18.7% under the
matched-prior control. Sampling variance excludes shrinkage bias and uncertainty
in prior-only parameters; this formula is not a substitute for the conditional
posterior. Even oracle sampling intervals centered at the biased estimate fail.
By contrast, the oracle **expectation** control spans 94.76–95.14% across all 24
design/scenario/penalty cells, supporting the implementation's sampling algebra.
That control uses known synthetic truth and cannot correct real player estimates.

At penalty 10 the conditional interval covers 98.66/98.72% under fixed-signal iid,
but only 85.23/85.31% under persistent team noise. Neither the favorable case nor
the 90% failure flag is an admission rule. The selected penalty remains 1000;
these now-observed simulations are not a new tuning set or grounds for a silent
penalty change. No uncertainty method is promoted to production.

The design has 41/42 prior-only actor columns. Shifting one such coefficient by
0.25 EP leaves all expected play outcomes unchanged; six/nine shifts affect the
selected first-unit contrasts, with largest changes 0.180/0.164 cumulative EP.
The 2026 design also contains two identical observed actor-column pairs. Their
constructed opposite shifts change **none** of the selected positional contrasts;
do not present those pairs as proof of ambiguity in those reported contrasts.
The audit retains that negative finding and the concrete cold-benchmark examples.
This check does not characterize all near-collinearity or team/player confounding.

The working model fails this bounded robustness check. Every admission flag
remains false. Real absence/cast evidence, broader exposure policy and formal
module decisions are still required before the October 30 methodology freeze.
No real ranking, updated game cohort, defensive score or deployment is produced.
