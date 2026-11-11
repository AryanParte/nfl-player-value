# Dimension-adaptive reference — frozen November 11 plan

This plan precedes new numerical results. Stack on PR #23; PRs #21–#23 remain
open, with no review feedback and successful latest hosted CI. This is the next
M1/M2 scoring recovery unit, not optional infrastructure or module admission.

## Diagnosis and unchanged scientific contract

The November 10 reference splits every selected four-dimensional region into 16
children, although most local error can lie along one coordinate. Exact node
reuse removes repeated evaluations but cannot fix wasteful spatial refinement.
The recorded reference failures are retained. Small raw QMC/reference differences
without an accurate reference do not certify integration.

Use the same posterior, preplay variables, full-support smooth Student-t(5)
transform, QMC seeds/powers and first-unit/equal-player/opportunity benchmarks.
No interval inflation, new prior, deleted cases, causal interpretation or admission.
Historical data inform shrinkage; only the archived 2026 opportunities add points.
Qualification remains separate. The five cases in the parent plan are consumed
numerical stress cases; Week 10 stays sealed. No fresh calibration claim follows.

## Algorithm fixed before results

Use the pinned SciPy 1.15.3 Genz–Malik degree-7/degree-5 nodes and weights through
a small checked adapter. Write a separate global controller: select the region
with greatest absolute component error; bisect only its axis with the greatest
absolute fourth-difference indicator across all vector components. At radii
`a=sqrt(9/70)`, `b=sqrt(9/10)`, the indicator is
`abs((f(+b)+f(-b)-2*f(0)) - 7*(f(+a)+f(-a)-2*f(0)))`.
This cancels the second-order term. Ties use the widest coordinate, then its index.
Use all contrasts and prior sensitivities; never select a favorable subset.

Estimate regional error from the absolute high/low-rule difference with a floating
point roundoff floor. Sum nonnegative regional errors globally, and require every
component to meet the original `atol + rtol*abs(estimate)` condition. Keep the
original normalization-error propagation and mean/CDF gates (0.01 posterior SD /
0.001 probability). These remain estimated errors, not rigorous certificates.
Recompute global sums from retained complete leaves to avoid subtraction drift.
Retain the final complete estimate and failure diagnostics at the work limit.

The maximum is 2,048 binary subdivisions, bounded further by **the original
90,000 target solves, 900 seconds per case and 3,600 seconds across five cases**.
A binary subdivision needs two rules, not 16: the changed subdivision count is
not a larger computation budget or a relaxed accuracy gate. Reserve the complete
two-child worst-case node cost before each split. Keep the exact 1,024-node cache.
No hidden fallback, selected rerun or extra budget based on results.

## Verification and decision sequence

1. Check rule moments against independent analytic polynomial integrals through
   the stated degrees, and rule estimates against SciPy's implementation.
2. Test anisotropic smooth targets with analytic integrals in 2–4 dimensions,
   mixed/signed vector components, narrow structure, nonfinite inputs and budget
   exhaustion. Check both achieved accuracy and error behavior, not only status.
3. Reuse the correlated known-mixing target and actual small random-effect target;
   wrong endpoints must fail. Check deterministic replay and explicit rule-shape
   compatibility. Any mathematical/control defect is fixed before NFL evaluation.
4. Run all five frozen cases, retain every outcome and exact artifact hashes, and
   independently rebuild offline. Compare QMC estimates/ledgers with the parent:
   this reference-only change must not change research point estimates.
5. Diagnose failures. A passed reference alone does not prove calibration or
   observational attribution. If all numerical checks pass, preregister a new
   calibration stage before drawing fresh responses. If not, document the precise
   bottleneck and next bounded action; no scores are published.

## Sources and reuse

The axis-bisection strategy is described in the primary
[NAG D01FCF documentation](https://support.nag.com/numeric/nl/nagdoc_26.1/nagdoc_fl26.1/pdf/d01/d01fcf.pdf),
which cites Genz and Malik (1980). No NAG code or commercial package is used.
[SciPy 1.15.3 cubature](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.integrate.cubature.html)
documents its rules and estimated-error interpretation. The existing BSD-licensed,
pinned SciPy supplies nodes/weights; its private rule API is isolated and tested.
No new dependency, fee, deployment service or automation change is required.
