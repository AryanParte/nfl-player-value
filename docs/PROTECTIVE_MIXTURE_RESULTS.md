# Protective-mixture preflight — November 23, 2026

**Reject progression to full numerical certification. No CAVAA module is
admitted.** The [design](PROTECTIVE_MIXTURE_DESIGN.md), commit `0b85e56`, precedes
producer `1bc5718` and all new draws. [PR #36](https://github.com/AryanParte/nfl-player-value/pull/36)
is stacked on open #35, `codex/tail-mixture-preflight` at d46a2d9.

All **576 requested trials** were attempted: 320 candidate, 128 mode-only and
128 tail-only diagnostics. Every trial retains raw integrals. There are 574
complete confidence constructions; the candidate and mode-only remote cases each
have one failure. Those failures stay in denominators and their defined point
estimates stay in error summaries. Two complete offline builds reproduce all
18 objects and one manifest byte-for-byte. Replay is not another statistical sample.

## What changed and what the evidence supports

The candidate samples from exactly half the original mode proposal plus half the
adapted tail proposal. The original defensive component retains total mass .1.
All eight ordered strata, full mixture weights and signed integrals remain. No
football prior, likelihood, benchmark, qualification or accounting policy changes.

The pointwise density bound passes independent tests. It does **not** guarantee
finite control-variate precision or numerical-error coverage. Fixed sample counts
are now split across eight strata; the control basis has 120 columns in four
dimensions, with duplicate columns handled by the unchanged SVD ridge. Observed
numerical ranks range from 35 to 89; this expected redundancy is not itself a
solver failure. The candidate's whole pipeline, including allocation and control
fitting, is tested together. No experiment here isolates either mechanism causally.

All candidate screens retain the previous .01 SD mean and .001 CDF endpoint
limits, including discrepancy plus numerical allowance. Every case has 32 trials.

| Case | Complete confidence sets | Precise | Joint numerical coverage | Screen |
| --- | ---: | ---: | ---: | --- |
| 0 | 32 | 32/32 | 28/32 | Pass |
| 1 | 32 | 32/32 | 31/32 | Pass |
| 2 | 32 | 32/32 | 32/32 | Pass |
| 3: weak broad displaced component | 32 | 32/32 | 29/32 | Pass |
| 4: curved | 32 | 29/32 | 32/32 | Pass |
| 5: broad tail | 32 | 32/32 | 29/32 | Pass |
| 6: displaced narrow component | 32 | 21/32 | 31/32 | Fail |
| 7: remote narrow component | 31 | 16/32 | 21/32 | Fail |
| 8: changed remote direction/weight | 32 | 22/32 | 31/32 | Fail |
| 9: correlated displaced component | 32 | 27/32 | 32/32 | Fail |

Six small feasibility screens pass; four fail. A passing screen only avoids the
frozen severe-undercoverage rejection and meets this sample's precision fraction.
For example, 28/32 joint coverage in case 0 is not evidence that nominal 95%
coverage has been established. These screens cannot replace the larger full
coverage study, authorize NFL inputs or validate player attribution.

## Matched failure analysis

Both diagnostics reproduce the candidate's original mode fits exactly. The tail
diagnostic also reproduces its entire adaptation. All evaluation randomness is
separate. Neither diagnostic nor the paired plain estimator is selectable.

| Case | Protected precision | Mode-only precision | Tail-only precision |
| --- | ---: | ---: | ---: |
| 3 | 32/32 | 0/32 | 30/32 |
| 5 | 32/32 | 28/32 | 32/32 |
| 6 | 21/32 | 32/32 | 11/32 |
| 7 | 16/32 | 20/32 | 5/32 |

**Broad nonmodal mass:** case 3 retains the improvement over mode-only and passes
all precision checks. This does not require finding another density mode: all
32 fits still discover one mode. The first mean RMSE is about .0000424 SD,
versus .00686 SD for mode-only. Different evaluation draws mean individual trial
differences include integration noise; they are not exact counterfactual errors.

**Post-discovery endpoint precision:** every case 6 fit finds both modes. All
individual mean and endpoint point errors and all individual numerical allowances
are within their limits, yet their sum fails for endpoints in 11/32 trials.
The median maximum combined endpoint error is .0009098 CDF; its maximum is
.0013288. First-mean RMSE improves from .0005498 SD (mode-only) to .0000625 SD,
while first upper-endpoint RMSE worsens from .0001429 to .0001967 CDF. Protection
recovers precision relative to tail-only, but not relative to mode-only.

The controlled candidate passes 21/32 here versus 17/32 for its paired plain
estimator. Across these 32 complete pairs, empirical controlled/plain variance
ratios for the four endpoints are about .825, .557, .919 and .263. The controls
help on these summaries but still leave too much endpoint error. Disabling them
or claiming the density floor has solved the problem would not be supported.

**Remote discovery and outliers:** case 7 discovers two modes in 20 trials and
one in 12. Among two-mode trials, protected precision passes 15, mode-only 20 and
tail-only four. Among one-mode trials the counts are one, zero and one. These
are descriptive groups, not eligibility rules or selectable validation subsets.
Global discovery and integration after discovery both remain unresolved.

All three arms have only 21/32 joint coverage, with severe-undercoverage p-value
2.36e-7 against the unchanged .001 screen. Candidate and mode-only each have one
`positive bounded normalizing mass required` confidence failure, at different
trials. All 32 point estimates remain defined. Candidate second-mean RMSE is
.3035 SD, versus .2315 mode-only and .1634 tail-only; the second upper-endpoint
RMSE is also worse (.0703 versus .0151/.0132 CDF). Better precision counts do not
erase worse outlier errors. A mixture density floor is not a guarantee for these
normalized, controlled, finite-randomization estimates.

**Geometry extensions:** case 8 has two one-mode fits and 30 two-mode fits;
10 endpoint combined checks fail. Case 9 always finds two modes and fails five
endpoint combined checks. Neither has a mean precision failure. This rules out
describing the whole candidate failure as only missing remote modes.

## Decision and next bounded action

Reject this candidate. Do not adopt the diagnostic winner per case, select
successful searches, retune the half mixture, enlarge samples automatically,
change football priors, widen intervals or relax accuracy requirements.

Next freeze a study that distinguishes **where the component-level ratio residual
variance is spent** from **whether global discovery succeeds**, then tests one
justified allocation/discovery alternative within a declared total work budget.
Use independent pilot information, never known-answer errors or evaluation draws,
to set any allocation. Preserve all retained stress cases, fresh random domains,
an unchanged comparator and failure-inclusive decision rules. This is a research
direction, not a validated fix; do not rerun this completed fixed-mixture study
or claim that a variance-based allocation is automatically optimal for QMC.

Full numerical certification, unchanged archived comparison, unfinished 192-fit
player calibration and observational admission still precede a scoring module.
The archive remains 57 QBs / 122 games / 8,996 dropbacks through November 7 evening.
No new NFL outcomes or sealed Week 10 data were read. First-unit and both
sensitivity comparisons, negative contributions and cumulative accounting remain.
Participation, defensive attribution/comparability and scored history remain open.

## Verification and reproduction

Local make check passes 543 Python tests, 27 frontend contracts, Ruff/format,
TypeScript/build, compilation and whitespace. Producer
[CI 45287372251](https://github.com/AryanParte/nfl-player-value/actions/runs/45287372251)
passes all four jobs: Python 3.11–3.13 and dashboard/browser. Final reporting-head
CI is inspected separately in the PR. No numerical implementation changed after
the study started.

Independent tests cover Gaussian density sums, second-moment inequalities,
zero-mean controls under duplicate strata, a signed polynomial with known integral
-2, work conservation, matched fit domains, corrupted child geometry and mixture
mass, and rejection before NFL access. These are software and arithmetic checks,
separate from the measured numerical-error coverage above.

| Binding | Value |
| --- | --- |
| Producer | `1bc5718b9dd595c9a46667ee14c1b45387711967` |
| Canonical plan SHA-256 | `168ffd8a171a516b9d8d0094f882d11c78060e74663237814a712d1ff9d70b5c` |
| Numerical source SHA-256 | `da647619e4018fee0f2a7ef4c8f214f27244ff205a7a0aebe8f572c466fba445` |
| Manifest/report | `4163d5718c8c79c78372243273ea3cc82600d7824238f4a28e5941ae2bbcb9fc` |

At the recorded producer and environment, with the immutable parent stores named
by the plan present:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/protective-mixture-preflight-v1.json --store data/derived/protective-mixture-preflight build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/protective-mixture-preflight-v1.json --store data/derived/protective-mixture-preflight-offline build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python scripts/analyze_mode_preflight.py data/derived/protective-mixture-preflight 4163d5718c8c79c78372243273ea3cc82600d7824238f4a28e5941ae2bbcb9fc --reconstruction data/derived/protective-mixture-preflight-offline
```

Sockets/DNS are disabled during both builds. The [analysis audit](audits/2026-11-23-protective-mixture.json)
compares every saved object and manifest; cross-platform byte identity is not
claimed. The [execution audit](audits/2026-11-23-protective-executions.json) binds
logs/source, verifies original model/prediction hashes, and verifies the actual
saved report rejects before NFL input access. Candidate work is 80,668–81,722
target evaluations per trial, below 90,000. Case-loop totals are 975.66/974.44
seconds, excluding preparation, validation, storage and other overhead. These are
not production or whole-development runtimes. Eight-stratum/control arithmetic
costs more despite unchanged target-call bounds.

Raw stores and required parents remain local and ignored; a fresh clone alone is
insufficient. Durable remote retention remains unverified. No dependency or
recurring service cost was added. [Operational evidence](audits/2026-11-23-operations.json)
still shows no Pages site and a production failure requiring first manual
bootstrap. Deployment would be an Explorer, not admitted CAVAA. No purchase,
automation, other-repository change or agent merge occurred.
