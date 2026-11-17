# Coarse control-variate study — November 16, 2026

The frozen candidate passes every known-answer numerical-coverage gate. This
permits the archived comparison; it does not establish player calibration or
admit CAVAA. The five archived NFL comparisons are pending at this checkpoint.

## Design and implementation

[Design d60052d](COARSE_CONTROL_VARIATES.md) precedes implementation and all new
draws. Its single candidate fits zero-mean Gaussian controls on 4,096 independent
training points, then evaluates 64 independent randomized nets. The exact repaired
minus coarse correction remains. All football models, priors, benchmarks,
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

Pending at this checkpoint. The current certificate authorizes recomputing the
144 conditional controls and evaluating all five frozen NFL cases, including
all three QB prior settings. Every case retains the unchanged 90,000 evaluation,
1,800-second case and 7,200-second total caps. The candidate requests 73,729
evaluations per case, including its fitting sample and fine offset.

No new player calibration, retrospective cohort extension, participation claim,
defensive score, ranked publication or deployment follows from the controls.
Week 10 remains sealed. All 17 contribution modules remain unadmitted.
