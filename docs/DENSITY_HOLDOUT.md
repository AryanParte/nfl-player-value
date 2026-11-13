# Density holdout and covariance stabilization — frozen November 13

**Pre-result amendment:** use [the tail-compatible curved control](DENSITY_HOLDOUT_TAIL_AMENDMENT.md)
and `config/density-holdout-v2.json`. The initial design below is preserved. No
density comparison, coverage trial or archived study ran under version 1.

PR #26 is merged at `e28bdb2`; its negative numerical evidence is unchanged.
Freeze this document and `config/density-holdout-v1.json` before implementing or
evaluating this study. No posterior, CAVAA benchmark, qualification, source cohort,
scientific accuracy limit, calibration generator or sealed Week 10 window changes.

## Hypothesis and one bounded alternative

Yesterday's density pilots had 187.6 effective samples for real QB and only
5.8/9.5 for two stress cases, out of 4,096 points. Selected mixture covariances hit
their numerical floor. Hypothesis: fitting flexible covariances to concentrated
importance weights overfits the pilot and leaves poor integration coverage.
This is not established by those diagnostics. Test it using independent density
holdouts, then verify numerical-error coverage on known answers.

Compare the existing three-Gaussian adaptive proposal with **one** stabilized
version. Both see exactly the same density-only pilot: four independently
scrambled nets, 1,024 total nodes each, from the existing 90% local-t / 10% prior
mixture with exact stratification weights. No football contrasts, known answers
or primary-QMC samples enter fitting. Both retain three starts, initialization,
100 iterations, objective tolerance 1e-6, component mass floor 0.01, the existing
covariance eigen bounds, 1.5 sampling inflation and the final 10% prior component.

For normalized weights w, let n_eff = 1/sum(w²) and nu = dimension + 2. If C_emp
is the weighted global covariance and C0 the independently fitted Hessian
covariance **before** the existing 1.5 multiplier, use

`C_global = (n_eff*C_emp + nu*C0)/(n_eff + nu)`.

In each mixture update, normalize the component's weighted responsibilities to
v and use n_j = 1/sum(v²). Replace its raw covariance by

`C_j = (n_j*C_emp_j + nu*C_global)/(n_j + nu)`.

Apply the existing eigen bounds afterward. Means and mixture masses are unchanged
in definition. Choose the best final weighted training likelihood among the same
three starts; retain all attempts, clipping, component effective counts and
convergence flags. Nonconvergence is reported, not silently repaired. Sampling
weights always correct the exact mixture density; no covariance estimate becomes
a football prior. This dimension-based regularizer is a fixed computational
hypothesis, not a claim of an optimal Ledoit–Wolf or Bayesian covariance estimator.

## Paired density holdouts

Use seed root 2026111301 with explicit entropy `[base,stage,target,trial,...]`.
Stages: 10 density pilot; 11 mixture initialization; 12 independent holdout;
13 known-answer reference trials; 2 archived reference integration. Known targets
have indices 0–4; archived cases have indices 100–104. No seed retries.

For each pair, hold out four independent 2,048-node nets from the equal mixture
of the two fitted proposals. Eight component strata each receive 256 nodes per
net; exact component probabilities correct the equal allocation. This evaluates
both proposals on the same independent points without reusing training weights.
Retain raw replicate integrals for:

- normalizing mass Z;
- target-weighted log(q_stable/q_existing), divided by Z for held-out log-score gain;
- integral target²/q_existing and integral target²/q_stable, each divided by Z²
  for normalized second-moment estimates (C2).

Positive held-out log-score gain and negative log(C2_stable/C2_existing) favor
stabilization. Also record training gain, train/holdout gap, pilot effective counts,
geometry hashes and raw moments. Finite-sample C2 estimates can be below one; do
not clip them or mislabel 1/C2 as a guaranteed effective sample count. Report
paired means and ordinary 95% Student-t intervals across independent pilot fits
as descriptive diagnostics, not multiplicity-controlled admission tests.

Run exactly 32 pairs for each known target and four pairs for each of the same
five archived density targets. All pairs, failures and requested denominators
remain. Archived density runs evaluate only target density, not CAVAA functionals;
they diagnose consumed targets and cannot certify numerical accuracy or select
settings. Limit each archived case to 90,000 target evaluations / 900 seconds and
the five-case density run to 3,600 seconds. A skipped/failed trial cannot pass.

## Known answers and coverage gate

Retain the four November 12 analytical controls unchanged. Add a four-dimensional
curved density: independent standard normal z, with x0=z0, x1=z1+0.5*(z0²-1),
x2=z2, x3=z3+0.5*(z2²-1). The inverse is explicit and determinant is one. Use
the existing two contrast vectors on **z(x)** plus independent Student-t(20)
noise with scale² 0.2/0.4. Means/variances are analytical; endpoints come from
independent scalar Normal/Student-t convolution. This tests curved sampling
geometry with known nonlinear functionals; it is not a realistic football model.

For the stabilized proposal from **density trial 0**, freeze its geometry before
coverage results. Never select a favorable pilot. Run exactly 1,024 fresh reference
trials per target, each 32 independent scrambles × 2,048 nodes. Use the existing
Fieller implementation and seven mass/mean/CDF quantities; preserve shifted wrong
endpoint rejection. Require, per target: all trials finite/bounded; one-sided
95% exact joint-coverage lower bound >=0.90; no marginal undercoverage at
0.01/(5*7), no joint undercoverage at 0.01/5, >=90% precision at unchanged
0.01 SD / 0.001 CDF limits; every deliberately wrong endpoint rejected. This is
one fixed confirmation, without optional stopping, a new trial-count audit or
follow-on confirmation retries in this run. Density metrics cannot waive it.

Only a complete known-answer pass permits the existing five-case archived CAVAA
numerical pilot with this stabilized proposal. Keep its original primary-QMC
samples/checks and 90,000-solve / 900-second / 3,600-second budgets. Fit the proposal
using archived target index 100+case index, trial 0. Preserve every failure and
independently rebuild offline. A pilot pass permits separately frozen calibration,
not automatic scoring admission. A control failure still permits the declared
density-only diagnosis; it blocks CAVAA-reference use.

## Verification and decision

Test the shrinkage algebra against independent weighted matrix calculations,
rank-deficient/dominant-weight pilots, exact baseline preservation, paired-mixture
normalization, density functional ratios, known curved transformations/answers,
source/manifest integrity and failed-certificate rejection. Keep full experiments
outside ordinary PR CI. Preserve all earlier evidence and produce a documented
decision even if the alternative fails. Do not change settings from these results.

Covariance shrinkage has an established statistical motivation
([Ledoit and Wolf](https://ledoit.net/honey.pdf)), but that work does not validate
this particular weighted proposal. Independent RQMC replicates give approximate
error assessments ([SciPy's pinned QMC documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/stats.qmc.html));
the tests here measure their limitations. No new dependency, paid service or
automation change. Defense/Explorer and the original cross-position goal remain.

## Software compatibility correction after controls, before the archived functional pilot

The first implementation compared the entire control model plan to the archived
plan. The latter additionally contains exactly `diagnostic_trial_cap=8` and
`numerical_proposal="stratified_student_t5_v1"`, retained from the November 9
primary-runner repair. Neither changes this reference's fitted geometry:
`fit_proposal` extracts the optimizer/Hessian means and covariance, then explicitly
uses the existing Student-t pilot; it does not use the primary Proposal object's
sampling-family field. The calibration cap is unused here.

The compatibility check now requires the exact control plan **plus those two
specific archived settings**, rejecting missing/changed settings, extra keys or
any changed model parameter. Before the archived functional pilot, all five known
targets' two trial-zero proposal geometries and exact functionals were recomputed
under the full archived policy and matched the saved control bytes exactly.
Both ordinary and offline control studies retain their original report ID.
No numerical result, accuracy gate, prior or declared experiment changes.
