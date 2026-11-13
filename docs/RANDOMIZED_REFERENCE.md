# Replicated randomized reference — frozen November 12 follow-up

Freeze this design before implementation or new results. PR #25 is merged at
`55e8f02`; its five sparse failures and rejected tensor controls remain evidence.
This study changes integration and its numerical error assessment, not the
continuous posterior, football data, player intervals, benchmark or admission.
The user explicitly authorized this follow-up after the earlier November 12 run.

## Estimator and error contract

Use **32 independent scrambled Sobol replicates**, each with 2,048 total target
evaluations. Retain entire power-of-two nets; no thinning, dropped initial point,
adaptive stopping, seed search or within-net iid standard errors. Derive each
scramble from `SeedSequence([base_seed, stage, fixture_or_case, trial, replicate,
component])`. Different stages/cases/trials/components have distinct entropy.
Use the existing pinned NumPy/SciPy implementation and record its environment.

For each replicate retain unbiased unnormalized integrals: mass and weighted
conditional means/CDFs. Pool these integrals before dividing; do not average
self-normalized replicate ratios. Exact target/proposal densities and a common
log offset preserve the original posterior. Conditional Student-t probabilities
integrate coefficient/noise uncertainty analytically, as in the existing model.

Construct approximate Student-t/Fieller numerical confidence sets using the
sample covariance of the **32 replicate integrals**, divided by 32. Invert
`(xbar - theta*ybar)^2 <= t^2 Var(xbar - theta*ybar)` for each numerator/mass
ratio. Require a positive mass confidence lower bound and bounded finite ratio
sets; unbounded or invalid sets fail explicitly, never clipped into probabilities.
This propagates numerator/denominator covariance, including negative contrasts.
Retain ordinary marginal 95% intervals and **Bonferroni simultaneous 95%** sets
over every mass and mean/CDF functional, including all three QB-prior settings
within a case. A nominal confidence level is approximate, not a finite-sample
guarantee. Known-answer coverage must be measured before NFL use.

For archived comparisons, absolute discrepancy plus the largest distance from
the ratio estimate to its simultaneous confidence endpoints must remain within
**0.01 posterior SD for means / 0.001 for endpoint CDFs**. The original primary
QMC checks remain required. The raw deterministic cubature atol/rtol stopping
indicator does not apply to a fixed randomized design: it depends on an arbitrary
unnormalized mass scale. Positive, bounded Fieller mass and ratio uncertainty
replace that algorithm-specific indicator; the scientific functional limits are
unchanged. Document this distinction before seeing results.

## Two fixed proposals, equal work

Both proposals use a separately fitted mode and full Hessian of the exact target,
not primary-QMC samples or weights. Reuse the existing validated optimizer and
finite-difference Hessian routine with its three starts, step, eigenvalue bounds
and 1.5 covariance multiplier. Select the best successful mode; record all starts
and any covariance clipping. The optimization box bounds mode finding only.
Sampling retains full support and exact density correction.

1. **local-t:** a multivariate Student-t(5) at that mode/covariance, 2,048 nodes
   per replicate, normal/chi-square inverse transformation (dimension d+1).
2. **defensive-mixture:** 90% that local-t plus 10% the original full-support
   prior normal. Stratify with 1,024 nodes per component per replicate and correct
   by the exact mixture density and component probability. Equal allocation is
   computational allocation, not a changed 50/50 proposal density or prior.

These are sampling proposals, not alternative football priors. Prefer local-t
if both pass; use the defensive mixture only if it passes all controls and local-t
does not. No selection by names, NFL results, smallest reported error or likelihood.
Shared target/conditional code and Sobol family remain dependencies; this is an
independently randomized/proposed cross-check, not independent football evidence
or a fully independent implementation of the posterior.

## Known-answer design and selection

Four fixed targets on log coordinates, with two linear contrast functionals each:

- Correlated Gaussian mixtures in d=2,3,4. First mean `linspace(0.4,-0.8,d)`;
  second adds `[2,-0.5,1,-1][:d]`; weights 0.8/0.2. Shared covariance is
  `sd[i]*sd[j]*0.65**abs(i-j)`, with `sd=linspace(0.6,1.3,d)`.
- Four-dimensional tail mixture: 95% N(0,I), 5% N([4,0,0,0],diag(4,1,1,1)).

Contrasts are `[1,-1,0.5,-0.25][:d]` and `[0.5,0.5,-0.5,0.5][:d]`.
Add independent conditional Student-t(20) noise with scale squared 0.2/0.4.
Mass/means/variances are analytical; 0.025/0.975 endpoints use independent scalar
normal/Student-t convolution and root finding at 1e-10 accuracy. Exact target
parameters supply answers only, never proposal geometry.

Run 128 independent trials per fixture/proposal for selection (stage 0), then
256 new trials per fixture for the selected proposal (stage 1). Base seed
2026111213; do not inspect stage 1 before selection. Per fixture require:

- No nonfinite integral or unbounded interval; all trials remain in denominators.
- Simultaneous coverage's exact one-sided 95% binomial lower bound >= 0.90.
  This is bounded empirical evidence, not proof of exact nominal 95% coverage.
- No marginal undercoverage at nominal 95% using one-sided exact binomial tests
  with family threshold `0.01/(4*7)`. Report all marginal coverage and uncertainty.
- At least 90% of trials meet the unchanged mean/CDF discrepancy-plus-error
  limits against known answers. Coverage alone cannot select arbitrarily broad
  numerical intervals. Every deliberately shifted upper endpoint (-0.5) must
  be rejected by the same functional rule.

Retain bias, empirical SD, reported widths, simultaneous/marginal coverage,
replicate concentration and all failed trials. If selection or confirmation
fails, no NFL pilot runs. Diagnose coverage versus precision, proposal support
and rare-tail influence without enlarging intervals or tuning seeds. A method
repair requires an explicit new pre-result design and new confirmation seeds;
software defects may be fixed and transparently replayed under this same plan.

## Archived pilot and subsequent scoring decision

Only after both stages pass, evaluate the same five consumed cases in the same
order: real QB, real team, prior draw 0, hierarchy draw 0, fixed-year draw 0.
Keep the three QB prior settings and all benchmarks. Use stage 2 with trial 0;
hold 90,000 total conditional solves, 900 seconds/case and 3,600 seconds/pilot,
including primary fitting/proposal work. No partial replicate or favorable subset
can pass. Keep all failed/unattempted cases and independently rebuild offline.
No automatic extra primary sample escalation is authorized in this study; a
precise reference disagreement must be diagnosed, not overwritten.

Compare all estimates/intervals/ledgers to the saved primary version and preserve
all archived 2026 games and negative contributions. General qualification remains
independent of benchmark membership. No new NFL downloads or Week 10 outcomes.
The consumed synthetic cases are numerical stress tests, not fresh calibration.

A complete numerical pass permits a separately frozen calibration stage; it does
not admit the QB module, establish causal attribution or satisfy the cross-position
product. Required defense/Explorer, live workload evidence, general participation,
fresh prediction and admission remain on the milestone backlog. No extra service,
dependency or automation change. Known-answer experiments run outside ordinary
PR CI; CI exercises small deterministic algebra/integrity regressions.

## Primary sources

[L'Ecuyer et al.](https://www.gerad.ca/en/papers/G-2023-67) study approximate
Student-t intervals across independent RQMC replications, including limitations.
[SciPy QMC](https://docs.scipy.org/doc/scipy-1.15.3/reference/stats.qmc.html)
documents power-of-two Sobol nets and the dependence within one randomization.
[NIST's Fieller specification](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/ratimean.htm)
gives covariance-aware ratio intervals and the unbounded-denominator condition.
These sources motivate the design; they do not validate this model or guarantee
coverage for its integrands.
