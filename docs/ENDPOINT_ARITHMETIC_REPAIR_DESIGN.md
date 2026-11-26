# Frozen endpoint arithmetic repair — November 25

This amendment follows the original endpoint design e2910c5 and producer
55187bd. It is frozen before repair tests or v2 outcome draws. Preserve v1,
including both complete builds and its adverse results, before changing the
numerical source. This is a bounded recovery within the same modeling unit.

## Concrete failure and rationale

While v1's matched comparison is finishing, candidate case 9 has all 32 modes
correctly discovered but only 2/32 simultaneous known-answer coverage. Saved
trial 3 has endpoint directions of order 1e-9, an intercept near 5.612, features
with fitting SD 2.74e-16 and coefficients up to 3.52e13. Subtracting two CDF values
near one rounds the true tiny difference at machine precision. Scaling that
quantized feature to unit variance and then unscaling its coefficient can amplify
absolute rounding into material integral error. This is not evidence to remove a
mode, alter the posterior, increase target samples or widen confidence bounds.

The repair changes floating-point evaluation of the same analytic zero-integral
function. Independently verify the diagnosis with high-precision small-increment
answers, ordinary quadrature and exact constant-direction controls, before any
new scientific draws. Do not claim the diagnosis alone validates the repair.

## Fixed arithmetic repair

Write s=a'a, t=sqrt(1+s), and c_delta=-b*s/[t*(t+1)]. Compute c=b+c_delta and
Delta=a'z-c_delta. This preserves the small centering shift that direct subtraction
of b/t and b can lose. Evaluate Phi(c+Delta)-Phi(c) as a signed increment:

- When |Delta|*(1+|c|+|Delta|) <= 1/8, use eight-point Gauss-Legendre quadrature on
  [0,1] of Delta*phi(c)*exp(-c*Delta*u-Delta^2*u^2/2). This resolves a small increment
  directly, even if adding it to c would round away. The short smooth interval
  makes quadrature error far below double-precision roundoff; verify boundary and
  extreme-tail examples against independent references.
- Otherwise use log-CDF/log-survival values and expm1 for the positive interval
  between the ordered endpoints, then restore its sign. Use the survival side
  when high >= -low and the CDF side otherwise to avoid subtracting near-one values.
- A zero slope produces an exact zero feature. For auxiliary direction regression,
  subtract a response-row anchor before weighted centering, so constant transformed
  responses give exactly zero residuals/slopes. The intercept remains unpenalized.

No near-constant-feature deletion, regularization change, interval change,
statistical model change or outcome-dependent numerical branch is permitted.
The auxiliary probability clip, all targets, integrals, masses and budgets remain
as in v1. This is a target-preserving arithmetic correction, not a replacement
CDF model or an attempt to turn the old failed outcomes into validation.

## New evidence and decision

The exact JSON `config/endpoint-control-preflight-v2.json` fixes seed 2026112502,
32 trials per arm, candidate stage 0 and unchanged polynomial comparator stage 6.
Cases 0–11 are now consumed regressions. Add two fresh geometries, fixed before
results: stronger positive sine curvature 1.1 with new contrasts/noise (12), and
a differently correlated displaced mixture with new weights/contrasts/noise (13).
No new NFL outcomes are used. Both arms have the same geometry fitting and training
coordinates; evaluation remains independent. There are 896 requested arm-trials.

Keep 90,000 evaluations/180 seconds per trial and 3,600 seconds per trial loop;
retain every failed or unattempted trial. Keep the .01/.001 precision tolerances,
90% per-case precision fraction, complete confidence construction and .01 family
severe-undercoverage budget (joint .01/14, marginal .01/98 for the enlarged family).
Two complete offline builds must reproduce every object and manifest. No automatic
sample growth, retries, favorable-seed selection or diagnostic fallback.

V1 remains rejected. Only an all-case v2 pass permits a separately frozen full
numerical-coverage study. Otherwise analyze the saved v2 failures and stop this
specific two-version unit with an explicit next hypothesis; do not keep tuning
new variants in this run. Full numerical coverage, archived NFL comparison,
player calibration and observational admission remain required before scoring.
