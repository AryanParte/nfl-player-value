# Numerical-reference pilot — November 10

**No CAVAA admission.** This unit improves integration of the existing continuous
QB model and adds an independent numerical reference. It does not change the
scientific prior, context variables, benchmark, interval definition or admission
rules. Both complete five-case versions reproduce byte-for-byte in independent
offline builds. All sampler checks pass, but **all five independent references
fail in both versions**. No case is omitted and no new calibration is performed.

The statistical target remains a partial, observational QB dropback contribution.
Training uses 48,776 dropbacks across 2024–26. Only 57 QBs / 122 archived 2026 games /
8,996 dropbacks add season points. The archive ends November 7 at 20:41:17 Eastern,
not November 10 live coverage. Historical observations add zero current-season
points. First-unit, equal-player and opportunity-weighted contrasts retain their
joint player/benchmark covariance. Qualification never selects the fit or benchmark.

## Frozen sequence and implementation

1. Commit `c1c35b6` freezes the [five cases and resource/decision rules](VARIANCE_REFERENCE.md).
   The model and November 9 posterior target stay fixed. Axis conditional-density
   tables construct a full-support proposal; exact joint-density corrections
   preserve dependence. These curves are not posterior marginals.
2. Known-answer tests expose corners in the table inverse CDF and poor scaling
   of near-zero centered integrals. The [smooth-reference repair](VARIANCE_REFERENCE_SMOOTH.md)
   is documented before NFL results. A smooth Student-t transform and exact
   mass-offset identities change coordinates/conditioning, not the posterior or gates.
3. Producing revision `1b5b7452116c7063464765a8b1f3d9c29860dc7e` runs the full uncached
   pilot twice, one rebuild with Python Internet sockets/DNS forbidden. Every case
   is attempted; all five pass QMC checks and exhaust the reference solve budget.
4. Inspection finds repeated exact rule nodes: 155 requests for 57 distinct nodes
   per four-dimensional region, or 91 for 33 in three dimensions. The original
   plan permits exact reuse. The [bounded cache and complete-subdivision policy](VARIANCE_REFERENCE_REUSE.md)
   is frozen and tested before its NFL follow-up. Producing revision
   `f496ffdb27ecca9744eabd7ed36db69396713943` keeps the same five cases and limits.

The last change retains a complete reference estimate and its estimated error
within the remaining solve budget. It never treats nonconvergence as success.
Cross-region cache hits can leave unused budget; no adaptive spending chases a
passing result. The original failures and producing code remain preserved.

## Original numerical evidence

All five QMC checks pass. The table reports the primary prior; the real QB's two
prior sensitivities also pass. Minimum ESS across its three priors is 1,068.52.
Mean and endpoint discrepancies are measured in posterior standard deviations.

| Case | Nodes per scramble | Minimum ESS | Independent mean / endpoint discrepancy | Nested mean / endpoint discrepancy |
| --- | ---: | ---: | ---: | ---: |
| Real evolving QB | 2,048 | 1,077.07 | 0.006958 / 0.009711 | 0.003125 / 0.006419 |
| Real team control | 1,024 | 814.42 | 0.002963 / 0.004020 | 0.001138 / 0.002552 |
| Consumed continuous-prior draw 0 | 2,048 | 1,621.54 | 0.002005 / 0.016690 | 0.001946 / 0.011257 |
| Consumed continuous-hierarchy draw 0 | 2,048 | 611.15 | 0.005802 / 0.010810 | 0.006111 / 0.010918 |
| Consumed fixed-year-change draw 0 | 2,048 | 819.71 | 0.008754 / 0.008174 | 0.002696 / 0.003749 |

The unchanged QMC requirements are ESS ≥128, both mean discrepancies ≤0.01 and
both endpoint discrepancies ≤0.02. November 9's real primary minimum ESS was 76.17
and independent mean discrepancy 0.03775. That is a measured improvement in
sampling stability, not proof of accurate integration or correct player attribution.

All five original independent references exhaust 90,000 actual target solves.
They do not return completed reference-error estimates. Ordinary-build case times
are 785.1 / 173.9 / 635.1 / 633.2 / 628.3 seconds, totaling 2,855.5 seconds after
source reconstruction. No case is omitted or reclassified as a pass. Both builds
have identical manifest/model/result bytes, including these failures.

The independent reference must converge, have verified positive mass, and meet
mean discrepancy plus propagated estimated error ≤0.01 posterior SD and endpoint
CDF discrepancy plus propagated estimated error ≤0.001. This is additional to
the existing QMC endpoint-SD gate. The cubature error is estimated, not rigorous.
It uses a different integration method but shares the tested conditional-model
algebra; it is not independent football evidence.

## Exact-reuse follow-up: completed, not numerically certified

The complete follow-up and independent offline rebuild have identical manifests,
models and results. Their model/result bytes also equal the uncached version:
exact work reuse changes reference evidence and computing cost, not estimated
player values or intervals. All five QMC diagnostic histories are identical.

| Case | Actual target solves | Complete subdivisions | Mean discrepancy + estimated error (SD) | Endpoint-CDF discrepancy + estimated error | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Real evolving QB, primary prior | 89,599 | 92 | 0.024490 | 0.032561 | Failed |
| Real team control | 53,941 | 192 | 0.003514 | 0.004769 | Failed |
| Consumed continuous-prior draw 0 | 89,646 | 92 | 0.115005 | 0.211181 | Failed |
| Consumed continuous-hierarchy draw 0 | 89,744 | 92 | 0.034479 | 0.052320 | Failed |
| Consumed fixed-year-change draw 0 | 89,600 | 92 | 0.358873 | 0.632446 | Failed |

Every reference returns `not_converged`. All four-dimensional cases reach their
92-subdivision ceiling derived from the original solve budget; the team control
reaches the original 192-subdivision cap. None hits the time limit. The QB's minus/
plus log(4) prior sensitivities also fail: mean/error diagnostics 0.023479/0.025945
SD and CDF/error diagnostics 0.032407/0.032857. No sensitivity is dropped.

For the real QB reference, 228,315 requested nodes use 83,961 distinct solves and
144,354 cache hits; setup/QMC bring the case to 89,599 total solves. The team
reference uses 139,867 requests / 50,721 distinct solves / 89,146 hits. The cache
retains at most 1,024 entries. These exact counts verify the observed repeated-work
mechanism. Wall times are 369.6 / 48.8 / 287.0 / 286.0 / 284.2 seconds, totaling
1,275.7 seconds (21.3 minutes) after source reconstruction. These are measured
execution times, not a controlled hardware-performance benchmark.

The QB raw discrepancies (0.007780 SD / 0.000837 CDF) are within the standalone
limits, but propagated reference error is not. Other cases also have raw
disagreement: the fixed-year case is 0.022995 SD / 0.001864 CDF. A stable sampler
and a low raw difference in one case cannot certify every interval. The reference
itself remains insufficiently resolved; these results cannot identify which
approximation is closer to the true integral or reject the scientific prior.

**Decision and next action:** retain the improved sampler as research code; do
not launch a fresh full calibration campaign or publish scores yet. Preregister
an efficient independent reference under the same target and accuracy rules.
Dimension-adaptive subdivision is a bounded candidate justified by the measured
cost of splitting every dimension at once. Validate known-answer error behavior
first, then all five consumed numerical stress cases. Do not simply discard error
terms, accept nonconvergence, inflate intervals or change priors to produce a pass.
Fresh calibration, prospective prediction and observational admission follow only
after numerical reliability. The defensive workstream remains mandatory.

## Scoring and statistical limits

The research output preserves 38 negative player estimates. Maximum per-play
accounting error is 8.88e-16 EP. The first-unit player total matches the play ledger;
game-ledger totals match the season contrast. A constant season effect allocated
over opportunities is not a separately observed weekly performance score.
These checks prevent duplicated points; they do not identify QB/cast causality.

The three synthetic cases are already consumed draws from November 9. They are
numerical stress tests, not new calibration evidence. The prior 192-fit campaign
remains unfinished, and no coverage percentage from this pilot can clear it.
2026 Week 10 remains sealed and uninspected. QB/team allocation still depends on
hierarchical assumptions and coarse team-season context. No credible claim of
pure QB skill, complete offensive value or cross-position comparability follows.

## Reproduction and verification

Uncached report: `25be7d6692ce1504f4f5511a6c2bd141fb64ff982abae0e968ef00c5bb4d6a29`.
Models: `969823d70ceabc6cb5c7dec3e7065a1e23ff547c6275e9322fad71f04d320c51`.
Results: `b55976166828f825cd9343e30dc3a2a08e306e3b4136f755dc40ff80addd64c9`.
Stores: `data/derived/variance-reference` and `variance-reference-offline`.
Cached report: `98ceb32af881404c22a1221b27012da7ef427e4c218d1808b4a83ccc7d0b77c4`;
stores `data/derived/variance-reference-cached` and `variance-reference-cached-offline`.
Model/result identifiers are identical to the uncached version above.
The [compact audit](audits/2026-11-10-variance-reference.json) records both versions.

From the canonical clone and producing code, with the saved parent/source stores:

```sh
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv/bin/python -m nfl_value.reference_cli \
  --output-store data/derived/variance-reference-cached \
  build --plan config/variance-reference-cached-v1.json
```

`replay REPORT_ID` recomputes all cases and compares manifest/model/results,
checking hashes, plan, NumPy/SciPy versions and fixed tolerances. An independent
build has separate output storage. Exact local reproduction is not a guarantee
across platforms or future dependencies, nor durable off-machine retention.
Timing metadata is excluded from numerical hashes; actual time-limit failures
can still cause nonidentical cases and must be reported as incomplete verification.

Final local `make check` passes 404 Python tests, 27 frontend contracts,
Ruff/adopted formatting, TypeScript/build, compile and whitespace checks. Analytic
tests include correlated mixing, exact CDF/density/moment checks, scalar quadrature,
wrong-endpoint rejection, cache equivalence and retained nonconvergence under a
solve cap. Accounting/provenance tests retain all cases and reject altered inputs,
corrupted artifacts and missing replay cases. Hosted
[CI 42895375490](https://github.com/AryanParte/nfl-player-value/actions/runs/42895375490)
passes Python 3.11/3.12/3.13 and dashboard/Chromium on the cached producing revision.
No live NFL download is required in ordinary CI; no new package or recurring fee.
