# Coarse control-variate study — November 16, 2026

The frozen candidate passes every known-answer numerical-coverage gate, but the
archived real-QB comparison fails the unchanged accuracy limits. All five archived
cases complete; only the team control passes. Both complete archives reconstruct
byte-for-byte offline. The pointwise-fitted candidate is rejected for numerical
certification. No contribution module is admitted and player calibration is unfinished.

## Design and implementation

[Design d60052d](COARSE_CONTROL_VARIATES.md) precedes implementation and all new
draws. Its single candidate fits zero-mean Gaussian controls on 4,096 training
points from separate randomized nets, then uses 64 independent evaluation replicates.
Fitting and evaluation are independent; points within a Sobol net are dependent.
The exact repaired-minus-coarse correction remains. All football models, priors, benchmarks,
calibration limits and primary artifacts are unchanged. The paired unadjusted
reference uses the same evaluation points and cannot be selected after results.

The numerical implementation is 6487dca932d541d7e89a6b62d0a6b1bde0978e2b.
Its whole-package fingerprint is
d4e6f465862adbf1d11b1ad812acac1924f5e11ebfff2181105f044207e97aab.
Later diagnostic scripts and documentation do not alter that fingerprint.
Plan hash: 740aca9f2eb5b8d6e9e5cac44dc4fbea50b05a4d431975f2d9791e7850c5216e.

## Completed known-answer evidence

Every target completes its 1,024 requested fresh fitting/evaluation trials. The
complete denominator is 5,120, with no favorable-seed retry or discarded failure.
Every deliberately incorrect endpoint is rejected. All original marginal/joint
coverage and precision gates pass.

| Target | Joint numerical coverage | One-sided 95% lower bound | Precision fraction | Gate |
| --- | ---: | ---: | ---: | --- |
| Two-dimensional mixture | 0.951172 | 0.938600 | 1.000000 | Pass |
| Three-dimensional mixture | 0.953125 | 0.940760 | 1.000000 | Pass |
| Four-dimensional mixture | 0.952148 | 0.939679 | 1.000000 | Pass |
| Tail mixture | 0.949219 | 0.936445 | 0.990234 | Pass |
| Curved target | 0.961914 | 0.950546 | 1.000000 | Pass |

Numerical coverage concerns the error of the integration calculation. These
synthetic targets are not football players or evidence of observational attribution.
The finite trial experiment supports this procedure on the declared targets, not
a universal coverage guarantee.

The [paired audit](audits/2026-11-16-coarse-controls.json) exposes mixed variance
effects despite the passing coverage. Across mass, mean and endpoint functionals,
adjusted/plain empirical variance ranges from 0.442 to 1.778. Both curved-target
means have about 1.777 times the plain variance. Pointwise fitting therefore does
not establish variance reduction for randomized integration. No unadjusted fallback
is substituted. Fit ranks are 23/24, 39/40 or 59/60, consistent with the redundant
mixture basis; the frozen SVD regularization handles this without deleting columns.

Across the same 35 quantities, ratios of mean training residual RMS to mean
response RMS range from 0.176 to 0.628, yet 20 empirical integration-variance
ratios exceed one. These are correlated quantities and descriptive counts, not
35 independent hypothesis tests. The measurements support an objective mismatch:
a smaller pointwise residual can still give worse randomized-net integration.
They do not establish that the basis rank defect causes the observed error.

Two full one-shot executions, with sockets and name resolution disabled, produce
the same report, manifest and all 11 objects. These are repeated reconstructions
of the same declared trials, not 10,240 independent observations. The previous
aggregate-size failure does not recur: per-case objects preserve the 128 MiB bound.
Observed case times total 2,612.7 seconds and 2,607.96 seconds respectively.

Report: 413cd13dffb1a5a3d4f2d9f2659a8f733216dec2a381931dfac8a746caa6244a.
Stores: data/derived/coarse-control-variates and
data/derived/coarse-control-variates-offline. Run the documented analysis script
against both stores to recompute decisions, paired errors and byte equality.

## Archived NFL comparison

The current certificate successfully recomputes the 144 conditional controls
before NFL access. Every archived case retains the unchanged 90,000 evaluation,
1,800-second case and 7,200-second total caps. The candidate requests 73,729
evaluations per case, including its fitting sample and fine offset. All three
QB prior settings and all 171 player/benchmark contrasts remain in the real-QB case.

The completed QB case fails at **0.013312 posterior SD / 0.001137 CDF** including
numerical error, against **0.01 / 0.001** limits. The negative/positive QB
log-precision prior shifts also fail, at 0.012109 / 0.001016 and
0.014676 / 0.001266 respectively.
The paired plain reference uses exactly the same evaluation points and fails at
0.013274 / 0.001136 for the primary setting. A better-looking result than the
previous seed's 0.015977 / 0.001242 therefore cannot be credited to the controls.

For the worst primary QB mean, point discrepancy is 0.005554 SD and simultaneous
numerical error is 0.007758 SD. Both individually meet tolerance, but their sum
does not. Every QB point discrepancy meets tolerance, and no numerical confidence
set excludes the allowed agreement region. This prevents certifying agreement;
it is not evidence that the primary player estimate is biased.

The conditional first-order variance ratio (adjusted/plain) across QB settings
and functionals ranges from 0.855 to 1.092. Unlike the known-answer study's
empirical repeated-trial variance, these are estimates from one fitted control
and its 64 evaluation replicates. They are not player uncertainty or proof of
uniform improvement. The largest correction/coarse influence-standard-error
ratio is 5.33e-10; adding fine work alone would not fix the measured imprecision.
The two QB checkpoint objects match exactly, including all raw vectors and fits.

All requested cases finish: two real-data models and three previously consumed
stress responses using the archived design. The three QB prior settings are
sensitivities within one case, not independent passes. The team control estimates
team performance; it is not an individual-player contribution module.

| Case / setting | Adjusted mean + error (SD) | Adjusted endpoint + error (CDF) | Paired plain mean + error | Paired plain endpoint + error | Adjusted gate |
| --- | ---: | ---: | ---: | ---: | --- |
| QB, primary | 0.013312 | 0.001137 | 0.013274 | 0.001136 | Fail |
| QB, log-precision shift -ln(4) | 0.012109 | 0.001016 | 0.012079 | 0.001016 | Fail |
| QB, log-precision shift +ln(4) | 0.014676 | 0.001266 | 0.014628 | 0.001265 | Fail |
| Team control | 0.002367 | 0.000187 | 0.002144 | 0.000190 | Pass |
| Prior stress | 0.007482 | 0.002068 | 0.007321 | 0.002034 | Fail |
| Hierarchy stress | 0.053498 | 0.002998 | 0.053540 | 0.003022 | Fail |
| Year-change stress | 0.014874 | 0.001107 | 0.014329 | 0.001078 | Fail |

All point discrepancies in every case meet tolerance, and no numerical confidence
set excludes the permitted agreement region. Numerical uncertainty prevents
certification. The paired plain calculation also passes only the team control.
No after-the-fact choice between adjusted and plain results is made.

Across archived cases, estimated adjusted/plain functional variance ranges from
0.708 to 1.742. These are conditional first-order diagnostics, not independent
trial variances or player confidence intervals. The largest correction/coarse
influence-standard-error ratio is 2.30e-9. The tested pointwise objective does not
provide the needed reduction in integration error; the data do not establish a
single cause such as basis rank, nor guarantee another fitting objective will work.

Each case uses exactly 71,680 coarse and 2,049 fine evaluations (73,729 total),
including the training sample. Maximum observed case time is 1,592.0 seconds;
sums of case times are 4,531.4 and 4,531.9 seconds, below 1,800/case and 7,200 total.
The [execution receipts](audits/2026-11-16-coarse-executions.json) preserve both
runs' timings separately from deterministic scientific objects.

Both full network-disabled executions reproduce the same manifest and all six
objects, including every failed comparison. Report:
386f7ac8b89a6873c5ac0e41bf3ca150fcb063bbfd6f665367346c77f4e839fb.
Producing source: 892e567349f370749fe86ce1bdaebe20c70a6eb9. Stores:
data/derived/coarse-control-nfl and data/derived/coarse-control-nfl-offline.
The [complete NFL audit](audits/2026-11-16-coarse-nfl.json) retains all checks,
paired diagnostics, coefficients' provenance, source closure and primary-object
identities. Its original model and prediction objects remain unchanged.

The bounded candidate ends here: do not adopt this pointwise-fitted estimator
for numerical certification or player calibration. The next proposed experiment
fits coefficients to independent integration-replicate means, matching training
and evaluation net sizes and freezing the budget before new results. That
objective targets the observed problem more directly, but it remains an untested
hypothesis. Preserve all five cases, fresh known-answer draws and existing limits.
Do not retry favorable seeds, select the plain comparator, grow the basis blindly,
or add fine work to address coarse imprecision. A numerical pass would still
precede the unfinished 192-fit player calibration and observational admission.

No new player calibration, retrospective cohort extension, participation claim,
defensive score, ranked publication or deployment follows from the controls.
Week 10 remains sealed. All 17 contribution modules remain unadmitted.

## Reproduction

From the canonical clone, retain the development lease before commands that write
to snapshot stores. Use the recorded numerical source and matching Python/NumPy/
SciPy/BLAS environment, with all immutable parent stores present. The source and
environment guards reject drift. These commands recompute the complete studies
and compare their results with the saved manifests; they are expensive research
checks, not ordinary PR CI. Network access is disabled inside each CLI process.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src \
  .venv/bin/python -m nfl_value.coarse_control_cli --offline \
  --output-store data/derived/coarse-control-variates \
  replay 413cd13dffb1a5a3d4f2d9f2659a8f733216dec2a381931dfac8a746caa6244a

OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src \
  .venv/bin/python -m nfl_value.coarse_control_cli --offline \
  --output-store data/derived/coarse-control-nfl \
  --controls-store data/derived/coarse-control-variates \
  replay-archive 386f7ac8b89a6873c5ac0e41bf3ca150fcb063bbfd6f665367346c77f4e839fb
```

The following read-only command regenerates the NFL diagnostic audit and verifies
the already completed separate reconstruction. Substitute the control-store pair
and control report ID to regenerate the known-answer audit. Execution timings and
metadata observations are retained separately in the execution receipts.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src \
  .venv/bin/python scripts/analyze_coarse_controls.py \
  data/derived/coarse-control-nfl \
  386f7ac8b89a6873c5ac0e41bf3ca150fcb063bbfd6f665367346c77f4e839fb \
  --reconstruction data/derived/coarse-control-nfl-offline
```

## Software verification and review

Local `make check` passes 477 Python tests and 27 frontend contracts for the final
changes, plus Ruff/format, TypeScript/build, compilation and whitespace checks. The new
mathematical tests use independent Gaussian quadrature and exact signed integrals,
unequal mixture weights, collinear bases, independent training/evaluation,
immutable fitted coefficients, exact paired plain calculations and complete
work accounting. Negative controlled quantities are retained rather than clipped.

Artifact checks reject altered coefficients, raw levels, confidence bounds,
work counts, source fingerprints, omitted cases and false authorization.
Storage tests preserve the object cap and detect corrupt case objects. Separate
analytical diagnostics distinguish mass variance from normalized-ratio variance,
retain explicit prior-setting order and leave zero-variance comparisons undefined.
Self-review extended the existing fixture-restoration regression to both the old
and new runners: it checks the independent zero-centered, variance-nine fixture
policy rather than the NFL prior. The implementation was already correct, so
this test extension does not change the study or require new numerical draws.
These software tests do not replace the empirical numerical study.

[Hosted run 43999147468](https://github.com/AryanParte/nfl-player-value/actions/runs/43999147468)
passes all four jobs at 892e567: Python 3.11, 3.12, 3.13 and dashboard. The
dashboard log confirms 27 frontend contracts and all 12 Chromium scenarios.
Final reporting-head CI is inspected separately before completing the PR.

Review confirmed that the fixed controls integrate to zero under the full mixture
density; fitting weights correct the equal allocation across unequal-mass
components. Training and evaluation entropy domains are separate. The corrected
conditional solver, posterior, benchmark covariance and original player artifacts
remain unchanged. Known-control coverage does not establish the accuracy of every
NFL tail or simultaneous player contrast, much less causal attribution.

No new dependencies or recurring service costs. The existing CI matrix and
dashboard/browser stack remain intact. The large offline experiments are manual
research runs, not added to every PR check. The work stays on the independent
repository's feature branch under its retained lease. No automation change,
purchase, deployment, main push or agent merge occurred.
