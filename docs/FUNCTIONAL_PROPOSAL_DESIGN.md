# Frozen functional proposal study — November 19, 2026

Frozen on `codex/functional-proposal-reference`, based on owner-merged PR #32
(main 3bd3863), before implementation and fresh experimental draws. One candidate;
no post-result parameter selection. Prior studies are consumed diagnostic evidence.
This changes numerical integration only, not the football likelihood, priors,
first-unit benchmark, sensitivities, negative cumulative ledger or admission rules.
Week 10 stays sealed. No contribution module is admitted by this study.

## Rationale and exact candidate

A proposal approximating posterior mass can still miss regions important to a
mean or endpoint probability. The ratio-variance calculation motivates proposals
weighted by absolute centered functionals; see [Owen, chapter 9, section 9.2](https://artowen.su.domains/mc/Ch-var-is.pdf).
The three-component moment construction below is our hypothesis, not an optimality
or coverage theorem. Full support alone does not guarantee useful precision.

Start from each existing saved four-stratum proposal (three central components
plus its original 10% defensive Gaussian). Perform exactly two adaptation rounds
of 8,192 independently scrambled, equally allocated Sobol points. Include exact
stratum probabilities in pilot quadrature weights. Each round uses its current
full mixture density in the importance denominator. Never reuse pilot draws in
evaluation or fit to evaluation results. No NFL truth or exact analytic integrals
may normalize the fit; known endpoint/centering definitions only specify the
functionals being evaluated, as in preceding studies.

For every declared prior block b, let F_b0 be its unnormalized mass integrand and
Zhat_b its positive weighted pilot mean. Form three nonnegative pilot envelopes,
averaged equally over prior blocks:

- Mean/mass: (F_b0 + average_j abs(F_bj)) / Zhat_b, for standardized centered means.
- Lower: average_j abs(F_bj - .025 F_b0) / Zhat_b for lower CDF columns.
- Upper: average_j abs(F_bj - .975 F_b0) / Zhat_b for upper CDF columns, including
  the deliberately wrong endpoints when present. This does not replace their
  actual CDF or use it as a fitting anchor.

Normalize each envelope times pilot quadrature weights separately. Its weighted
mean and centered covariance define one Gaussian component. Apply the existing
proposal-only effective-weight shrinkage (pseudo-count d+2 toward the initial
central covariance), existing eigenvalue bounds [1e-6,36], then covariance
inflation 1.5. The three resulting components have mass .3 each; retain the
original defensive mean/covariance and mass .1. An identically zero envelope
retains that index's current central component, explicitly recorded; nonfinite
or nonpositive pilot mass fails, with no zero-likelihood substitution. No EM,
mode search, favorable restart, posterior jitter or weight clipping is added.

The fixed initial central covariance is used in both rounds' shrinkage, so an
uncertain first update cannot become its own regularization reference. Effective
weight counts measure concentration, not independent observations. All component
locations, weighted centered covariance, effective counts, entropy domains,
input/response hashes and original support are retained for replay/validation.

After both rounds, retain the existing 2,048-point zero-mean Hermite fit with
ridge 1e-6. The preceding 16,384-point coefficient refit is replaced by proposal
fitting, not added to it. No integration-coefficient refit occurs. Conditional
on independent adaptation/fit, the controls still integrate to zero. The paired
plain estimator under this same fitted proposal is diagnostic only, never an
after-the-fact fallback. This explicitly frozen package can fail; we will not
attribute success solely to one internal change without an additional study.

## Controls, independence and bounds

`config/coarse-control-v4.json` fixes root 2026111901. Pilot domains are appended
[4,round], pointwise controls [2], coarse evaluation [0], correction [1]. Each
of 1,024 trials refits both proposal rounds and controls independently. Retain
all seven existing target definitions and their gates unchanged. Add target 7:
.9 N(0,I) + .1 N((8,8,0,0),diag(.25,.25,1,1)), starting from the same fixed
.9 N(0,I)+.1 N(0,9I) proposal as targets 5–6. Moments and convolved Student-t(20)
CDF endpoints have independent known answers. This stronger displacement/narrowness
is chosen before draws; it is not evidence of achieved empirical concentration.
All target components satisfy the Gaussian defensive second-moment condition.

Run 32 separate initial-proposal diagnostic trials for target 7, entropy
[root,9,7,trial], 64 replicates of 1,024 points, before the candidate trials.
Report their mass concentration and whether the observed maximum reaches the
prior NFL hierarchy's 0.103866 replicate share. This is a descriptive stress
check, not a selector, estimator, or new acceptance gate. Missing that regime
limits any certification claim; it cannot be described as tested robustness.
These additional analytic-only evaluations never enter the NFL work budget.

The original five controls keep alpha .01/35 marginal and .01/5 joint; targets
5–6 keep .01/14 and .01/2; target 7 has its own declared family .01/7 and .01.
All eight cases must pass. Retain the original 90% precision fraction, .9 lower
coverage bound, 0.01 SD / 0.001 CDF tolerances, positivity and wrong-vector gates.
These are finite approximate coverage tests, not universal nominal calibration.
All 8,192 requested trials remain in the denominator, including failures.

Per archived case: 16,384 proposal-fit + 2,048 control-fit + 65,536 coarse
evaluation + 2,048 coarse correction + 2,048 fine correction + 1 offset =
88,065 target evaluations. Retain caps 90,000 evaluations, 1,800 seconds/case,
7,200 seconds across the unchanged five archived cases. Complete both full
known-answer executions and byte-compare manifests/objects. Do not stop after
the first failed control, enlarge nets, drop stress cases or retry favorable seeds.

## Decision and failure analysis

Test weighted moments independently, signed means, separate prior normalization,
zero envelopes, support restoration, conditional zero-mean controls, independent
domains, exact work and corruption. Compare tail CDFs by reversing the convolution
integration rather than reusing the generator. Validate saved adapted geometry
against the original input geometry and declared layout; old seven-case evidence
must not authorize an eight-case study.

Report full coverage/precision, point gaps versus numerical allowances, bias,
retained failed-confidence trials, proposal displacement/weight concentration,
and isolated wrong-endpoint detection. Distinguish pilot concentration from final
replicate concentration. A component estimated from a few dominant weights is a
diagnostic concern, not evidence it found the complete target.

Only a complete passing new certificate and reproduction of all 144 conditional
controls can authorize the unchanged five-case NFL pilot. Otherwise prove the
saved failed certificate blocks before NFL access and diagnose every failure.
Keep all consumed results, no fitting/gate change after inspection. If rejected,
record the concrete reason and the next bounded hypothesis; do not automatically
continue tuning this family. NFL numerical success would still precede the
unfinished 192-fit player-calibration study and observational admission. Defense,
qualification and cross-position comparability remain required product work.

## Analytic diagnostic addendum (before complete case results)

With the frozen candidate already executing, add a deterministic diagnostic for
targets 5–7 only. This is not an alternative estimator, acceptance test, or new
randomized study. No candidate draw, fitting parameter, prior or gate changes.
For X normal and L=a'X, use the normal conditional moments of X given L and
one-dimensional quadrature to calculate each pilot envelope's population mass,
mean and covariance. Split at the absolute-value cusp. Report integration error,
the population-moment Gaussian geometry (same eigenvalue bounds/inflation, no
finite-pilot shrinkage), and density ratios at the two analytic component centers.

Compare learned geometry with those population moments to separate finite-pilot
error from moment-family limitations. These center probes are not variance bounds
or evidence of adequate precision; no Monte Carlo results for an oracle proposal
will be generated or selected. Tests independently check normal absolute/linear/
quadratic moments. All candidate outcomes, including failed intervals, remain in
their original denominator. This diagnostic does not consume new NFL outcomes.

### Diagnostic clarification from source review

Before the tail cases finish, source review identifies a scope distinction: the
analytic calculation uses the **unperturbed fine target**, whereas proposal fitting
uses the coarse target multiplied by `1 + .001 sin(sum(x))`. Therefore these are
fine-target envelope moments, not the exact population limit of the implemented
pilot. Keep that distinction explicit in every comparison; mean/covariance gaps
also include the surrogate perturbation and finite-pilot covariance shrinkage.

For each of these single-prior analytic cases, the normalized envelope is tilted
by a factor between `1-epsilon` and `1+epsilon`. If its fine-target envelope mean
and covariance are mu and C, the Euclidean mean displacement is at most
`epsilon * sqrt(trace(C)) / (1-epsilon)`, by centering the normalized expectation
and applying Cauchy–Schwarz. Report this deterministic bound with epsilon=.001;
it is not a covariance bound, a precision allowance or an admission criterion.
Verify the bound against independently known sine-tilted normal means. Do not
subtract it from observed errors or treat it as numerical quadrature uncertainty.
The numerical candidate, source fingerprint, draws and gates stay unchanged.
