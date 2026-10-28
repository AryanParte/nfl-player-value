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
