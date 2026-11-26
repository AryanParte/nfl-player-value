# Allocation/discovery preflight — frozen November 24, 2026

The owner merged #35 and #36; base main is da12cbf. The previous fixed protective
mixture is rejected, not unfinished. It loses endpoint precision even after mode
discovery, and also misses remote modes. This study tests one bounded combination
of changed search allocation and independent component allocation. No football
model, benchmark, cumulative ledger, interval or admission requirement changes.

## One candidate, fixed total budget

Retain the .5 mode/.5 tail proposal, defensive mass .1, all tail adaptation,
Gaussian controls, 2,048 control-fit points, 64 coarse replicates of 1,024 points,
64 paired corrections of 32 points, and the Student-t/Fieller error assessment.

Change the search from 256 points / 24 optimizer starts to **1,024 / 16**.
Keep 12 ratio-priority starts, three density-priority starts and the initial
center. All spacing, Hessian, acceptance and per-start 384-call limits stay fixed.
The motivation is wider candidate exploration instead of repeated optimization
of similar basins. Fewer starts may hurt; this is tested, not assumed beneficial.

After independent control fitting, run a new pilot of **eight independent scrambled
nets, 32 points per each of eight components** (2,048 coarse calls). Retain raw
plain and controlled component means. The pilot never enters the final estimate.
Use only the coarse function, fitted controls and proposal. No target index, true
component labels, exact answers, failed-test labels or evaluation draws enter the
allocator. The synthetic integrand's inherited standardized coordinates are part
of the test function, not an extra oracle input to allocation; this does not
establish suitability for NFL functionals.

Let a_j be mixture mass, Y_jr and U_jr the plain and controlled component means
in pilot replicate r. Estimate each ratio anchor c_k from the full weighted plain
pilot mean N_k/Z (positive Z required). For the two mean and four endpoint columns,
compute residuals R_jrk = U_jrk - c_k U_jrZ. With the unchanged scales
t = [.01,.01,.001,.001,.001,.001], define

```text
A_j = a_j² * 32 * sum_k sample_variance_r(R_jrk) / t_k²
predicted allocation loss = sum_j A_j / n_j
```

This uses ratio influence, including numerator/mass covariance. It does not use
the true ratio, and excludes the deliberately wrong endpoint columns. The
independent pilot diagnoses which component contributes residual variation.
The inverse-count model is inspired by stratified Monte Carlo allocation
([Owen, chapter 8](https://artowen.su.domains/mc/Ch-var-basic.pdf)); QMC error may
scale differently. No optimality or coverage guarantee is imported from IID theory.

Choose n_j by exact finite dynamic programming over powers of two >=32, with
sum n_j=1,024; break exact cost ties lexicographically. If every A_j is exactly
zero, use equal allocation. Keep full mixture density and masses: the estimator
is sum_j a_j * component_mean, **not** sample-count-weighted pooling. Every
component retains at least 32 evaluation points. The paired correction remains
four points per component. No fallback estimator or increase of total samples.

Worst-case target calls: 89,447 - 8*384 + (1,024-256) + 2,048 = **89,191**.
All search/derivative, mass/EM/control/pilot, coarse and fine calls count. Keep
90,000 maximum calls, 180 seconds per trial and 3,600 seconds aggregate trial
loops. Report arithmetic and preparation/storage/validation overhead separately.

## Frozen arms and random domains

Base seed 2026112401. All ten retained cases 0–9 have 32 candidate trials.
Cases 3,6,7,9 each have 32 equal-allocation diagnostics with the **new search**,
and 32 previous-setting diagnostics with **256/24 search and equal allocation**.
Total: **576 requested trials**. These are new numerical randomizations of
consumed known-answer geometries, not fresh football validation.

Use common fitting entropy [base,0,case,trial] for all arms, with existing search
10, mass 11, EM [20,round], and control-fit suffix 2. All arms use a common pilot
domain suffix 30; the previous-setting arm also records this diagnostic pilot
but never changes allocation from it. Its actual cost includes the pilot and may
hit 90,000 sooner (formal bound 91,495); retain any such failures without retry.
This comparator preserves the previous estimator/settings but has diagnostic
overhead, so do not claim equal total work or unchanged failure probability.

Candidate and new-search equal diagnostic must have identical geometry, control
fit and pilot evidence. The previous-setting arm intentionally differs in search
geometry; compare discovery frequencies and downstream failures without asserting
matched geometry. Evaluation arm domains are 0 (candidate), 4 (equal), 5
(previous), with existing suffix 0 (coarse) and 1 (correction); fitting and pilot
domains are disjoint from evaluation. All arms record component evaluation means
to reconcile totals and compare pilot predictions with observed variation.

## Unchanged decision, diagnostics and verification

Candidate screens require every trial to complete, >=90% discrepancy-plus-error
precision at .01 SD / .001 CDF, and no severe undercoverage at .01/70 marginal or
.01/10 joint. Keep wrong-endpoint checks and all raw failed-confidence evidence.
No gate, prior, seed, interval or work setting changes after outcomes.

Complete every case unless the frozen operational cap is reached. Analyze
candidate versus identical-fit equal allocation to assess the allocation change;
compare equal versus previous settings to assess discovery changes. Keep all
point errors, interval failures, component variance/covariance, pilot scores,
allocation frequencies, predicted versus observed variance, and mode-count
groups. Groups, diagnostic arms and the plain calculation are never selectable.

If any candidate screen fails, reject progression and diagnose the failure; do
not automatically add samples, optimize consumed outcomes or relax precision.
If all pass, freeze a separate full coverage study before the unchanged archived
NFL pilot and unfinished 192-fit player calibration. This preflight cannot
authorize NFL access, score publication or admission. Week 10 stays sealed.

Test finite allocation against independent exhaustive enumeration, full mixture
weighting and signed answers, equality with the existing equal-net integrator,
ratio covariance with hand-computed arrays, independent pilot/evaluation domains,
complete work and corrupted evidence rejection. Raw component means must sum to
saved integrals; pilot means must reconstruct the chosen allocation. Run two
complete offline builds and compare all objects/manifest bytes. Replay is not
additional independent evidence. Retain all unsuccessful/unattempted trials.

Reuse the existing pipeline, NumPy/SciPy, unittest and CI. No new dependency,
service, purchase, automation or other-repository change. Update M1–M6 honestly:
qualification, defensive comparability, scored history and Explorer deployment
remain separate unfinished milestones.
