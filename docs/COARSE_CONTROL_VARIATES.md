# Frozen coarse control-variate study — November 16, 2026

This plan precedes implementation and new trials. Branch
codex/coarse-control-variates is stacked on open PR #29 at 5054dc0. That
prerequisite is complete with passing hosted CI; it is not merged by this run.

## Question and rationale

The repaired functional pilot completes every case, but only the team control
passes. All point discrepancies meet tolerance; numerical uncertainty blocks
certification. Correction/coarse influence-standard-error ratios are at most
1.36e-9 in that consumed pilot. This motivates reducing coarse integration variance,
not adding fine work, changing priors, enlarging player intervals or relaxing gates.

Control variates subtract functions with known integrals. Separate fitting draws
avoid fitting and evaluating the adjustment on the same random sample. Ordinary
pointwise regression need not minimize randomized-quasi-Monte-Carlo (RQMC)
variance, so improvement is a hypothesis to test, not a guarantee. See
[Owen's practical QMC notes, control variates](https://artowen.su.domains/mc/practicalqmc.pdf).
No source code or text from that reference is copied.

## One fixed candidate

Keep the exact proposal geometry, its full mixture density q, primary posterior,
three QB prior settings and repaired fine/coarse conditional kernels. For each
of the four saved proposal components choose a normalized Gaussian density g_k
with the component's exact mean and covariance (the Student component's shape,
not a fitted replacement covariance). Let z_k be its Cholesky-whitened coordinate.
Use the fixed controls:

- g_k/q - 1;
- (g_k/q) z_ki for every coordinate;
- (g_k/q) (z_ki z_kj - delta_ij) for i <= j.

Every control has exactly zero expectation under q by Gaussian normalization
and first/second moments. Evaluation uses log densities, full-support sampling
and exact mixture masses. No truncation, empirical replacement of the known
expectation or zero-likelihood substitution. Validate these identities against
independent Gaussian quadrature and signed analytical test functions.

Fit one coefficient matrix per case/trial on **4,096 stratified proposal draws
independent of evaluation**, equally allocated to the four components, with component masses
in the fitting weights. The pre-trial implementation uses scrambled Sobol nets;
points within a net are dependent. Independence refers to fitting versus evaluation
and to separate randomized replicates. This wording clarification changes no
pre-trial sampler, design parameter or acceptance rule. Fit an unpenalized
intercept by weighted centering.
Scale columns by weighted empirical standard deviations; exactly constant
columns receive zero coefficients. Use SVD ridge with penalty
1e-6 times the largest squared singular value. No coefficient or basis selection,
hyperparameter search or result-dependent fallback. Store coefficients, geometry,
training entropy/hash and fitting diagnostics. The ridge regularizes only the
numerical approximation, not football effects.

Conditional on that separate fit, every adjusted unnormalized integral has the
same expectation. Evaluation replicates are independent conditional on the fit;
the known-answer study refits on fresh training draws for every trial. This
does not justify treating individual Sobol points as independent observations.
Finite-sample Student/Fieller coverage remains an empirical requirement.

For replicate r compute:
I_r = Q_r(coarse - controls @ coefficients) + R_r(fine - coarse).
The controls' known integral is zero. Both levels remain unnormalized until the
sum; preserve covariance and signed numerators. Do not clip negative controlled
mass replicates: retain them, and fail the existing positive-mass gate if needed.
Keep the unadjusted Q_r(coarse) from the same function evaluations as a paired
diagnostic, never a selectable alternative.

## Fixed evidence and work

Configuration: config/coarse-control-v1.json, entropy root **2026111601**.
Domains separate known trials, archived cases, training, coarse evaluation and
paired correction. Fit/evaluation/truth never share randomness. Use 64 evaluation
replicates with 1,024 coarse and 32 paired correction points each, unchanged from
the final previous design. Including 4,096 training evaluations and the fine
offset gives **73,729 conditional evaluations per archived case**, below the
unchanged 90,000 cap. Keep 1,800 seconds/case and 7,200 seconds total.

Before NFL access, run 1,024 fresh trials for each of all five fixed analytic
targets (5,120). Restore each target's own exact trial-zero proposal; retain the
same .001 sinusoidal coarse perturbation and deliberately incorrect endpoints.
All existing coverage, precision, marginal/joint undercoverage, positivity and
0.01-SD/0.001-CDF limits remain unchanged. All controls must pass. No optional
stopping, favorable seed retry, new allocation or interval multiplier.
Recompute the 144 conditional controls before archived use.

If authorized, evaluate all five consumed NFL cases and all original prior/
benchmark contrasts. Existing sources, cutoff and primary artifacts stay fixed;
Week 10 remains sealed. Numerical draws are new, football validation is not.
Retain every failed/unattempted case in its requested denominator.

## Failure analysis, reconstruction and decision

For every completed known trial report paired adjusted/unadjusted errors, coverage
and precision, and coefficient norms, numerical rank and training residuals.
The unadjusted comparator uses the same evaluation points and no fit-derived
selection. Compare empirical trial variance and estimated numerical uncertainty.
If known coverage fails, finish all controls, diagnose every failing marginal
against its exact answer, and block NFL access; a failure is not silently repaired
by applying the old control certificate.

For every completed NFL case report point discrepancy, simultaneous numerical
error, coarse/correction influence variation, adjusted versus unadjusted variation,
mass concentration and timings. Reconstruct decisions from raw replicate arrays.
These diagnostics do not add or replace acceptance rules.

Preserve the full failed-artifact sequence. Save per-case hashed objects from the
start, under the existing 128 MiB per-object bound. Rebuild independently offline;
retain exact source/plan/environment/provenance bindings and compare all objects.
A software defect may be corrected with a documented pre-result amendment;
statistical alternatives require a new future design.

This one-candidate study ends with a documented decision and next concrete action.
A numerical pass only permits further player calibration and prospective
observational evaluation; it does not admit CAVAA or settle attribution.
The 192-fit player-calibration denominator, benchmarks, negative season ledger,
eligibility separation and required defensive workstream remain unchanged.
No deployment, dependency, purchase or automation change is part of this study.
