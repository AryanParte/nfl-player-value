# Endpoint controls and arithmetic recovery — November 25

The original endpoint-control implementation is rejected. A separately frozen
arithmetic repair is evaluated in the same unit; see its final decision below.
No CAVAA module or player ranking is admitted by either preflight. These are
numerical-integration experiments, not football attribution validation.

## Preserved original experiment

[Design](ENDPOINT_CONTROL_DESIGN.md) e2910c5 precedes producer 55187bd.
All 768 requested arm-trials complete with raw integrals and confidence sets.
Two offline builds reproduce all 24 objects and the manifest byte-for-byte.
They repeat the same randomizations, not twice the coverage evidence. Candidate
and polynomial arms share proposal geometry/training coordinates and plain pilot
bytes, while control fits/allocations may differ and evaluation draws are separate.

| Case | Candidate precise / 32 | Polynomial precise / 32 | Candidate joint coverage / 32 | Polynomial joint coverage / 32 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 32 | 32 | 31 | 29 |
| 1 | 32 | 32 | 32 | 30 |
| 2 | 32 | 32 | 32 | 31 |
| 3 broad nonmodal | 32 | 32 | 29 | 31 |
| 4 curved | 31 | 26 | 29 | 31 |
| 5 broad tail | 32 | 32 | 30 | 29 |
| 6 displaced | 32 | 32 | 30 | 29 |
| 7 remote | 29 | 30 | 28 | 30 |
| 8 rotated remote | 29 | 31 | 27 | 29 |
| 9 correlated mixture | 15 | 32 | 2 | 32 |
| 10 fresh negative curvature | 31 | 28 | 31 | 30 |
| 11 fresh correlated mixture | 32 | 32 | 32 | 30 |

Eleven of twelve small screens pass, but case 9 fails both precision and severe
undercoverage. All 32 case-9 trials discover both modes, so missed discovery
cannot explain that failure. Other adverse evidence remains visible: case 7 has
25/32 coverage for one marginal quantity, and case 8 has 25/32 for another. A
small-screen pass never certifies nominal coverage.

The case-9 first lower-endpoint RMSE is 0.00126428 versus polynomial 0.000162255;
first/second mean MSE ratios are 142.0 and 160.6. Some other endpoints improve;
the report retains both directions instead of selecting favorable functionals.
The original curved case improves precision 31 versus 26, and fresh curvature
31 versus 28, but that cannot override a failed complete-method screen.

## Failure analysis and arithmetic repair

Saved case-9 trial 3 contains an endpoint direction of order 1e-9, intercept near
5.612, fitting feature SD 2.74e-16 and a coefficient up to 3.52e13. Subtracting two
normal CDF values near one quantizes a mathematically nonzero, tiny difference.
Unit-variance scaling and coefficient unscaling amplify its absolute rounding.
Across case 9, coefficient norms range from 1.20e13 to 1.61e48; large coefficients
alone are not an admission gate or grounds for silently dropping a feature.

The independent regression example uses intercept 5.612 and slope 3e-9. Its
analytically zero control has a normalized 96-node Gaussian-quadrature residual
of -0.3201 with direct subtraction, versus approximately 9.8e-18 with stable
increments. The small-increment calculation also agrees with an 80-digit Hermite
series to relative error below 1e-13. This establishes a numerical defect; it is
not by itself evidence that every repaired statistical interval is calibrated.

[Recovery design](ENDPOINT_ARITHMETIC_REPAIR_DESIGN.md) d61178d freezes the repair
before repaired-study outcomes. Tiny increments are integrated directly; larger
ones use log-CDF/survival differences and expm1. A stable centering shift preserves
small terms, and response-anchored auxiliary regression makes constant directions
exactly zero. Boundary tests additionally required compensation for rounding in
forming the endpoint sum; the test assertion stayed unchanged.

This changes the arithmetic of the same zero-integral function. It does not change
regularization, priors, targets, CAVAA benchmarks, intervals, eligibility, negative
values or sample budgets. Legacy v1 evaluation remains available only to preserve
its failed experiment; no production scoring path adopts it.

## Repaired experiment

Producer 671c349 evaluates the frozen v2 design on 896 requested arm-trials;
all raw integrals and confidence constructions finish. Two complete offline builds
match all 28 objects and the manifest byte-for-byte. All twelve previous cases
are regressions; only cases 12–13 have fresh geometry in this repair study. V2 uses
new randomizations, so comparisons against v1 are not paired coverage tests.

| Case | Candidate precise / 32 | Polynomial precise / 32 | Candidate joint coverage / 32 | Polynomial joint coverage / 32 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 32 | 32 | 30 | 30 |
| 1 | 32 | 32 | 29 | 30 |
| 2 | 32 | 32 | 31 | 32 |
| 3 broad nonmodal | 32 | 32 | 31 | 30 |
| 4 curved | 32 | 28 | 30 | 28 |
| 5 broad tail | 32 | 32 | 31 | 31 |
| 6 displaced | 32 | 32 | 32 | 30 |
| 7 remote | 31 | 32 | 30 | 31 |
| 8 rotated remote | 31 | 31 | 29 | 30 |
| 9 correlated mixture | 32 | 32 | 30 | 30 |
| 10 negative curvature (regression) | 32 | 25 | 31 | 30 |
| 11 correlated mixture (regression) | 32 | 32 | 30 | 30 |
| 12 fresh stronger curvature | 23 | 18 | 30 | 32 |
| 13 fresh correlated mixture | 32 | 32 | 32 | 30 |

Thirteen of fourteen candidate screens pass; case 12 fails precision. The candidate
improves precision versus its matched polynomial method on the old curved case
(32 versus 28), negative curvature (32 versus 25) and stronger curvature (23 versus
18), but still fails the complete-method requirement. The remote case has 31
precision successes versus polynomial 32. No comparator or individual trial is
selected as a replacement result.

Point-error comparisons are not uniformly favorable. On case 12, candidate-to-
polynomial MSE ratios are 1.27/1.49 for the two means and 1.09 for the first lower
endpoint, while the other three endpoint ratios are .69/.88/.77. On rotated
remote case 8, second-mean RMSE is .00021223 versus .00015374 (MSE ratio 1.91).
Case 13's first-mean MSE ratio is 2.51. The broad-tail first upper endpoint and
remote second upper endpoint also worsen (ratios 1.30 and 1.23). All comparisons,
including mass and the remaining functionals, are retained in the linked audit.
These 32-pair diagnostics include fitting/allocations and independent evaluation
randomness; they are not decisive general superiority tests.

Remote cases 7/8 discover both modes in only 30/32 and 31/32 trials; their misses
remain included. Candidate marginal coverage reaches as low as 28/32 despite
small-screen passes. Arithmetic repair does not resolve global mode discovery or
establish nominal numerical coverage.

Case 12 has one discovered mode in every trial and modest coefficient norms
(minimum 7.50, median 8.59, maximum 10.70), unlike the original arithmetic failure.
Every mean check passes (maximum discrepancy plus allowance .006074 SD). No
endpoint point discrepancy or allowance alone exceeds .001; their required sum
fails in nine trials, reaching .00130947. This is insufficient precision under the
fixed work budget, not evidence to remove the uncertainty allowance.

The median controlled/plain coarse endpoint variance ratios are .432, .662, .471
and .655 in stored endpoint order. The paired correction contributes only about
.0080–.0096% at the median and at most .02194% across endpoints/trials. These are
conditional-on-fit residual diagnostics, not a guarantee about ratio confidence
coverage or independent evidence of NFL uncertainty. The remaining error is
dominated by coarse integration, even after a useful variance reduction.

**Decision: reject progression to full numerical certification.** The two-version
unit ends here, as frozen. Next freeze a bounded work/precision/convergence study
of the unchanged repaired coarse integrator, with fixed alternatives and caps,
fresh randomizations, representative known answers and all consumed regressions.
Measure cost/precision before adoption; do not automatically top up failed trials,
select a diagnostic winner, change the prior or relax precision/coverage rules.

The original design's word "stricter" for a larger Bonferroni family needs an
interpretation correction: smaller per-test alpha controls family false flags
but makes an individual undercoverage flag harder to trigger. Low-powered screen
passes do not establish nominal 95% coverage. The frozen tests and results remain
unchanged; full numerical coverage and player validation are still required.

## Reproduction and evidence

- Original audit: [all cases, comparisons and residual diagnostics](audits/2026-11-25-endpoint-v1.json).
- Original [execution receipt](audits/2026-11-25-endpoint-v1-executions.json): manifest
  `d58b6bd9a06d8d5772f0471cf022416545def1e55274f6f8bf0a7bfc757ff298`;
  kernel `19ca09e6932e20f11d018f68b4a8d7aec62346a42d00af368a9c3659abbc08cd`.
- Original trial-loop times: 1,015.11 and 1,010.68 seconds. Preparation, semantic
  replay validation, storage and reporting are additional time.
- Repaired [all-case audit](audits/2026-11-25-endpoint-v2.json) and
  [execution receipt](audits/2026-11-25-endpoint-v2-executions.json): manifest
  `4ada200017eb0d90c0e0be0a6532a4ded10ee67a702406f673678e6e39f205fa`;
  kernel `adc96485a68512b4cc25e5880b31c676637f20e48d70818ac200c37d427ff572`.
  Full semantic validation reconstructs endpoint fitting from saved inputs in
  both stores; all 28 objects and one manifest match. Trial-loop times are
  1,486.06 and 1,483.20 seconds, excluding preparation, validation and reporting.
- Current [operational receipt](audits/2026-11-25-operations.json) records CI,
  deployment/feed checks, unchanged original player artifact hashes and admission.

Use the recorded producer revision and pinned environment for each version.
`mode_preflight_cli --offline build` with the corresponding frozen plan reproduces
its immutable store; `replay REPORT_ID` checks exact reconstruction. Network access
is disabled in offline runs. Full manifests bind code, plan, environment, geometry,
training responses, raw replicates and allocation decisions. Formatting numeric
vectors inline does not change audit JSON values. Raw research objects and required
parents remain local; durable remote retention is still unverified.

Both actual saved reports are rejected by the NFL archive runner before input
access (mocked input access is asserted absent). Original model/prediction objects
retain their recorded hashes. The archive still ends November 7 evening; no new NFL outcomes or sealed Week 10 evidence were
read. Full numerical coverage, archived comparison, player calibration and
observational admission remain necessary before a contribution module or ranking.
