# Frozen failure trace — November 13

The original paired study retains one failed density trial: `continuous_prior_0`,
trial zero, with a non-positive-definite conditional factorization. The archived
density report is `d29590d4c9adb157b9343720c28614da9918fb5571ea927cb880aa4bf4421b30`.

Reproduce exactly that failed fit once under the same 90,000-evaluation / 900-second
limits, wrapping the conditional evaluator only to record the first failing
coordinates, finite precision range, matrix eigenvalues and response hash. Keep
the exception; do not substitute a likelihood, clip a tail, add diagonal jitter,
change seeds, repair a prior or rerun the scientific trial as a success. No
additional holdout, football contrast, calibration or admission is authorized by
this diagnostic. It is post-result failure analysis, not fresh validation.

Retain the point and matrix diagnostics in a content-addressed object linked to
the original report and producing code revision. If the error cannot be
reproduced, report that fact. This trace may identify a numerical-conditioning
problem but cannot establish a correct replacement kernel without independent
known-answer validation and a separately declared equivalence study.
