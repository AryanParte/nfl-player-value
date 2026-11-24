# Tail-mixture preflight — November 22, 2026

**Reject this candidate before full numerical certification. No CAVAA module is
admitted.** Design `a3dd981` precedes producer `273e9ac` and all new draws.
[PR #35](https://github.com/AryanParte/nfl-player-value/pull/35) targets main
directly after the owner merged #33 and #34.

All 320 candidate and 128 mode-only diagnostic trials were attempted. All 448
retain raw integrals; 446 confidence constructions finish. Both failed confidence
sets remain counted, and their defined point estimates remain in error summaries.
Two complete offline builds reproduce all 14 objects and one manifest exactly.
Replaying the same seeds does not create another 448 independent trials.

## Candidate decision

Every case requests 32 trials. Precision includes both actual discrepancy and
numerical error allowance, at unchanged .01 SD for means / .001 CDF for endpoints.
Six of ten small feasibility screens pass. These screens neither establish a
population success probability nor replace the full coverage lower-bound gate.

| Case | Complete confidence sets | Precision | Joint numerical coverage | Screen |
| --- | ---: | ---: | ---: | --- |
| 0 | 32 | 100% | 96.875% | Pass |
| 1 | 32 | 100% | 93.750% | Pass |
| 2 | 32 | 100% | 100% | Pass |
| 3: weak broad displaced component | 32 | 93.750% | 90.625% | Pass |
| 4: curved | 32 | 90.625% | 93.750% | Pass |
| 5: broad tail | 32 | 93.750% | 100% | Pass |
| 6: displaced narrow component | 32 | 31.250% | 96.875% | Fail |
| 7: remote narrow component | 30 | 34.375% | 78.125% | Fail |
| 8: geometry extension | 32 | 37.500% | 100% | Fail |
| 9: rotated geometry | 32 | 68.750% | 87.500% | Fail |

## What the matched diagnostic explains

The diagnostic independently recomputes the same initial mode fit for each
matched trial; all saved initial geometries agree exactly. Evaluation randomness
is separate. The comparison is conditional on these known targets and this
bounded algorithm, not a causal football result or permission to select an arm.

| Case | Tail candidate precise / 32 | Mode-only precise / 32 |
| --- | ---: | ---: |
| 3 | 30 | 0 |
| 5 | 30 | 29 |
| 6 | 10 | 31 |
| 7 | 11 | 23 |

**Broad nonmodal mass improves.** Case 3 still finds only one density peak in all
32 trials, but the adapted mixture clears precision in 30. All mean checks pass;
the other two failures are endpoint discrepancy plus allowance. This resolves
the specific mode-only failure on that case, not the complete numerical problem.
Some lower-endpoint point errors worsen even while the overall screen improves.

**More accurate means do not guarantee endpoint precision.** Case 6 finds both
modes in every trial. Mean RMSE for the first standardized contrast improves
from .0005840 to .00005267 SD, yet first upper-endpoint RMSE rises from .0001754
to .0003244 CDF. All individual point errors remain within their tolerances, but
22/32 trials fail the combined endpoint check. Its median maximum combined error
is .0010995 CDF versus the unchanged .001 limit. An interval width or objective
improvement cannot be substituted for the required functional precision.

**Remote discovery and post-discovery integration both remain problems.**
Case 7 finds both modes in 23 trials. Mode-only passes precision in all 23;
adaptation passes in ten. Among nine one-mode trials, adaptation passes once
and mode-only never does. These conditional groups explain outcomes and may not
be selected as validation populations. Two candidate intervals fail with
`positive bounded normalizing mass required`. All 32 point estimates are
defined; second-contrast RMSE is .2303 SD versus .1390 for mode-only, including
both failed intervals. Rare poor draws are not removed. The severe joint
undercoverage test also fails (.0008685 < .001).

Cases 8 and 9 additionally fail combined endpoint precision in 20 and ten trials.
Case 8 has one mean-allowance failure; case 9's mean checks all pass. This is not
evidence that every failed point estimate is biased outside tolerance. See the
[complete failure-inclusive audit](audits/2026-11-22-tail-mixture.json) for raw
point errors, numerical allowances, paired diagnostics, discovery groups, pilot
mass, concentration, objectives, work and all denominators.

The density-fitting objective is not the endpoint-integration objective. Its
algorithmic rationale comes from [Cappé et al.'s mixture importance adaptation](https://arxiv.org/html/0710.4242);
neither that paper nor a monotone fitted objective certifies these finite
regularized QMC results. Regularization can decrease the fitted objective; those
steps are retained. Effective weight counts are concentration diagnostics, not
independent observations. Center density probes are not global variance bounds.

## Decision and next hypothesis

Stop this frozen candidate; do not increase EM steps, adjust covariance bounds,
choose only successful searches, select the mode-only/plain diagnostic, widen
intervals or retune consumed draws. No new football outcomes or Week 10 evidence
were read. The actual saved preflight report rejects before archived NFL inputs.

The next bounded hypothesis should preserve discovered-mode proposal coverage
while adding broad/endpoint-tail sampling. A fixed protective mixture offers a
possible pointwise density guarantee relative to its mode-only part; that algebra
would not guarantee controlled-estimator variance, numerical coverage or successful
global discovery. Freeze the method, work allocation, all retained cases and
decision rules before fresh trials. This is a hypothesis, not an implemented fix.
Full certification, the unchanged archived pilot, unfinished 192-fit player
calibration and observational admission remain required.

## Verification and reproduction

Final local `make check` passes 537 Python tests and 27 frontend contracts,
Ruff/adopted formatting, TypeScript/build, compilation and whitespace.
Producer [CI 45062740010](https://github.com/AryanParte/nfl-player-value/actions/runs/45062740010)
passes all four jobs: Python 3.11–3.13 and dashboard/browser checks. Final reporting
head CI is inspected separately in the PR.

Independent finite-sum updates, Gaussian moments, duplicate mass conservation,
collinear/concentrated pilots, signed raw estimates, separate entropy domains and
corrupted-stage rejection pass. A new corruption test initially failed because
a zero-count work category was accepted. The validator was fixed and the full
suite rerun before study draws. No numerical rule was changed after results.
The existing preflight engine is extended for the new frozen plan; older plans
retain their own hashes and require their recorded producer revision for replay.

| Binding | Value |
| --- | --- |
| Producer | `273e9ac4847b6008be2d5ac3ad9e05654758f29b` |
| Canonical JSON plan SHA-256 | `3443c16fa5d36f25772a0ab5642c1ba7032c25a7693d0a7c736ade8eb56e6aa1` |
| Numerical source SHA-256 | `a0588b36f713632e0e6acaadd0b396f2530d45790adb93e522fa89bc6be2aecf` |
| Manifest | `849bcc3300e7efed79a911a4605bc1cf9e4be0ffb119763fe2900d4097d7586f` |

At the producer revision, in the recorded environment with the immutable parent
stores named by the plan present:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/tail-mixture-preflight-v1.json --store data/derived/tail-mixture-preflight build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/tail-mixture-preflight-v1.json --store data/derived/tail-mixture-preflight-offline build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python scripts/analyze_mode_preflight.py data/derived/tail-mixture-preflight 849bcc3300e7efed79a911a4605bc1cf9e4be0ffb119763fe2900d4097d7586f --reconstruction data/derived/tail-mixture-preflight-offline
```

Offline builds disable socket/DNS access. Complete reconstruction compares actual
object bytes, not just summaries. Source/environment mismatch is rejected;
cross-platform byte identity is not claimed. Candidate target work ranges
80,683–81,737, including every search, derivative, pilot and evaluation, below
90,000. The worst-case design bound remains 89,447. Measured case loops take
307.32/307.37 seconds, excluding preparation, validation, storage and other
overhead; these are not total development or production runtimes. EM arithmetic
also costs time and is not hidden behind a claim of equal total computational work.

The [execution audit](audits/2026-11-22-tail-executions.json) records source/log
bindings, unchanged original model/prediction hashes and the actual NFL gate
proof. Raw research stores remain local and ignored by Git; a fresh clone alone
lacks the required parent stores. Durable remote retention is
unverified. No service, dependency, purchase or automation change was introduced.
The football archive still ends November 7 evening, not November 22.
