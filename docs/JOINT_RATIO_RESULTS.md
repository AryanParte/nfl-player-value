# Joint ratio-control decision — November 18, 2026

**Reject this candidate for numerical certification. No CAVAA module is admitted.**
All seven targets complete 1,024 trials each. The original five pass, but both
new analytic tail targets fail precision. The frozen gate blocks archived NFL
evaluation; it is unattempted, not an additional failed football fit. An actual
gate check rejects the saved certificate before accessing NFL inputs.

The [design](JOINT_RATIO_DESIGN.md) was committed as 4d5f6bb before implementation
or fresh draws. Source e363a2e fits two existing zero-mean composite directions
to N-rZ, then restores the shared denominator adjustment. It changes numerical
integration only. Primary model/prediction objects, priors, cumulative first-unit
CAVAA, both benchmark sensitivities, negative contributions, eligibility and
sealed Week 10 are unchanged. Numerical coverage is not player calibration.

## Complete known-answer results

Each row has 1,024 completed trials, no omitted failures. Precision requires the
original mean/endpoint limits in at least 90% of trials. Coverage tests use the
preregistered original and added-stress families; none was changed after results.

| Target | Joint coverage | Precision fraction | Paired plain precision | Gate |
| --- | ---: | ---: | ---: | --- |
| 0: two-dimensional mixture | 95.1172% | 100% | 100% | Pass |
| 1: three-dimensional mixture | 95.2148% | 100% | 100% | Pass |
| 2: four-dimensional mixture | 95.3125% | 100% | 100% | Pass |
| 3: original tail mixture | 95.7031% | 97.1680% | 99.2188% | Pass |
| 4: curved density | 95.8008% | 99.8047% | 100% | Pass |
| 5: broad-tail mixture | 96.0938% | 6.0547% | 4.8828% | **Fail** |
| 6: displaced-mass mixture | 95.8984% | 0% | 0% | **Fail** |

These finite coverage tests pass; that does not prove exact or universal 95%
coverage. The smallest observed marginal coverage is 93.2617% (target 4), whose
undercoverage p-value .00855 does not cross its frozen family threshold. The
paired plain calculation is diagnostic, never a fallback selected after results.

Both full offline executions reproduce the manifest and all **15 objects** byte
for byte. They are two executions of the same 7,168 trials, not 14,336 independent
trials. The [audit](audits/2026-11-18-joint-ratio-controls.json) retains all decisions,
paired bias/error summaries, training/evaluation influence diagnostics, precision
decompositions and provenance. The [execution record](audits/2026-11-18-joint-ratio-executions.json)
retains logs, timing, source fingerprints and the blocked NFL gate.

## Failure analysis

| Added target | Mean combined-error failures | Endpoint combined-error failures | Mean point-only failures | Endpoint point-only failures |
| --- | ---: | ---: | ---: | ---: |
| Broad tail | 0/1,024 | 962/1,024 | 0/1,024 | 2/1,024 |
| Displaced mass | 1,024/1,024 | 1,024/1,024 | 734/1,024 | 811/1,024 |

For the broad tail, the median maximum endpoint discrepancy plus numerical error
is .001267, against .001. Its median error allowance alone is .000954. Most point
estimates are close, but the reference cannot reliably establish the required
precision. No interval excludes the tolerance region. This is not evidence that
the unchanged primary football estimate is biased.

The displaced case has much larger error: median maxima .0900 SD / .01353 CDF.
Both the point estimates and error allowances are inadequate. Five mean and eight
endpoint confidence sets exclude their respective tolerance regions; these are
known-answer numerical failures, not an NFL attribution result. The plain
reference also has zero precision passes, so controls are not the sole problem.

The two-direction fit repairs the algebraic objective mismatch but does not
guarantee held-out variance reduction. Curved-target mean empirical variance is
1.1475 and 1.1353 times the paired plain variance. For displaced mass, every one
of the seven measured variances worsens (1.0261–1.1628 times plain). On broad-tail
CDFs, variance ratios .9680/.9687/.9902/1.0133 show only small gains or loss.
Training improvements therefore cannot be used as validation evidence.

The largest replicate mass shares are 1.5898% and 2.3205% for the added targets,
versus 1.5625% for perfectly equal mass across 64 replicates. Neither reaches the
previous NFL hierarchy case's 10.3866%. These controls do **not** certify that
stronger concentration regime. They fail precision even at smaller mass shares,
showing why a mass-only diagnostic cannot establish accuracy of every functional.
Both analytic mixtures have finite importance moments; infinite variance is not
the explanation for these failures.

The original deliberately wrong joint endpoint sets are rejected in all trials.
Self-review identified a limitation in interpreting that gate: a whole vector can
fail because of a mean or a different endpoint. A separate diagnostic now tests
whether the two altered endpoint confidence intervals themselves exclude the
tolerance region, using the original joint critical value. It cannot borrow a
nuisance failure. The original gate is unchanged; the diagnostic is not a new
acceptance rule. Its per-target counts are retained in the audit. Both wrong endpoints are
individually excluded in all trials for targets 0–5, but only 421/1,024 for
target 6; at least one is excluded in every trial. Reporting joint rejection as
proof of detecting both endpoints would overstate this evidence.

## Decision and next scoring action

Do not tune these coefficients, choose favorable seeds, drop a tail case, widen
intervals, relax precision, or select plain results from this consumed study.
The coefficient-only repair is insufficient at the fixed work budget. Further
sample-count growth alone is not the next proposed action.

Next freeze one bounded proposal-level alternative that allocates integration
effort to the required standardized means and endpoint probabilities as well as
normalizing mass. This is a hypothesis motivated by the measured functional
precision failure, not an adopted model or claimed fix. Define support, fitting
and independent validation, all benchmark/prior contrasts, work limits and a
stop rule before new draws. Retain the original and tail controls, and explicitly
address the still-untested stronger concentration. Only a passing numerical
certificate can enable the unchanged archived pilot and unfinished 192-fit
player-calibration study. The next product milestone remains a defensibly
validated contribution module, not another numerical component alone.

## Reproduction and software verification

Numerical producer: `e363a2eeaab1c0203e71d2326567dd35becc6db5`.
Plan hash: `6300d5ab107a1044afc156f7bbc066c546a22c57bb19e5e1c8043311e90ad8b5`.
Kernel hash: `952226898867036fe94b78e4e621b3c6c509950715b9c9b09f88e49bab0d4d5b`.
Report: `0302e878d5b0204c418d09375ecd278ef2bf46b30aac51be17812c49a7ef7fbd`.

With the archived parent stores and recorded Python/NumPy/SciPy environment,
run from the repository root under the development lease:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  .venv/bin/python -m nfl_value.coarse_control_cli \
  --plan config/coarse-control-v3.json \
  --output-store data/derived/joint-ratio-controls --offline replay \
  0302e878d5b0204c418d09375ecd278ef2bf46b30aac51be17812c49a7ef7fbd
```

The original independent executions instead used `known` into two new stores,
both started from e363a2e. Raw stores are ignored locally; the public audit is not
a substitute for their unverified durable remote retention. Package-source or
environment changes deliberately invalidate the certificate. Later diagnostics
change scripts/tests/documentation only; numerical source remains identical.

Verification covers independent analytical covariance answers, signed and
collinear controls, prior-specific masses, entropy/work accounting, corrupt
artifacts, all-seven-case storage, and independently integrated tail CDFs.
Ordinary CI remains offline. Review [PR #32](https://github.com/AryanParte/nfl-player-value/pull/32),
the full result audit and [learning report](learning/2026-11-18.md).
