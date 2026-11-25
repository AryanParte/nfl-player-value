# Allocation and discovery decision — November 24, 2026

**Reject progression to full numerical certification. No CAVAA module is admitted.**
The candidate passes nine of ten small feasibility screens; the curved case
passes precision in 28/32 trials, below the unchanged 90% requirement. This is a
substantial numerical recovery, not a usable MVP ranking or player calibration.

The [design](ALLOCATION_DISCOVERY_DESIGN.md) was committed at **13703f1** before
producer **1e2a39b** and all study draws. It retains the protected proposal and
all precision/coverage rules, trades optimizer starts for more search candidates,
and uses an independent ratio-residual pilot to allocate a fixed integration budget.
Allocation here means computer samples, not expected-point attribution to players.

## Complete evidence and comparisons

Both offline executions finish all **576 requested trials**: 320 candidate,
128 new-search/equal-allocation and 128 previous-search/equal-allocation diagnostics.
Every trial retains raw integrals and completes its confidence calculation.
No failed or unattempted trial is removed. The second execution is reproducibility
evidence, not another 576 independent scientific trials.

| Candidate case | Precision passes / 32 | Joint coverage / 32 | Small screen |
| --- | ---: | ---: | --- |
| 0 | 32 | 30 | Pass |
| 1 | 32 | 26 | Pass, not a calibration certificate |
| 2 | 32 | 31 | Pass |
| 3: broad nonmodal tail | 31 | 31 | Pass |
| 4: curved target | 28 | 31 | **Fail** |
| 5: broad tail | 31 | 30 | Pass |
| 6: displaced mode | 32 | 31 | Pass |
| 7: remote mode | 31 | 31 | Pass |
| 8: opposite displacement | 32 | 29 | Pass |
| 9: correlated displacement | 32 | 29 | Pass |

Case 1's 26/32 joint coverage has a severe-undercoverage p-value of 0.00460,
above this small screen's frozen 0.001 cutoff. Passing that screen does **not**
establish 95% coverage. Keep this concern in the fresh full-coverage study; do
not widen intervals or reinterpret a feasibility pass as calibrated uncertainty.

| Case | Candidate precision | Same fit, equal allocation | Previous search, equal allocation |
| --- | ---: | ---: | ---: |
| 3 | 31/32 | 32/32 | 32/32 |
| 6 | 32/32 | 17/32 | 19/32 |
| 7 | 31/32 | 23/32 | 18/32 |
| 9 | 32/32 | 28/32 | 28/32 |

Candidate/equal arms have identical geometry, control fitting and allocation-pilot
evidence, with independent evaluation draws. The comparison supports improved
integration precision for cases 6, 7 and 9, without a universal improvement claim.
Previous-search comparisons share fitting entropy but intentionally change geometry.
They cannot isolate allocation or be called identical-fit comparisons.

The remote candidate finds both modes in 31/32 trials; one discovery miss remains.
The previous-search arm finds both in 24/32. This is the direct discovery
comparison, not a comparison with yesterday's different random draws.
Its previous-search diagnostic has 25/32 joint coverage versus 31/32 candidate
and 32/32 equal-arm coverage. Preserve all these outcomes; a diagnostic arm or
discovered-mode subgroup is not an alternative admission population.

Improved pass counts do not imply uniformly smaller errors. Across **all 32**
remote trials, candidate second-mean RMSE is 0.05282 SD versus 0.03029 for the
identical-fit equal arm; second upper-CDF RMSE is 0.004420 versus 0.001329.
The one missed-mode trial remains in both denominators. Allocation can reduce
typical variation while a rare failure dominates mean squared error. The audit
retains every functional's error and the descriptive discovery groups.

## Remaining failure and decision

All four curved-case precision failures occur at **contrast 1's upper endpoint**,
in trials 5, 12, 21 and 28. Each individual point discrepancy and numerical error
allowance is below .001, but their required sum exceeds it: respectively
0.00125070, 0.00100777, 0.00113406 and 0.00106707. All mean checks pass.
That is insufficient endpoint precision, not evidence for relaxing the sum rule.

Post-result diagnostics use saved arrays only, without new draws or refitting:

- For the curved target, observed component residual variance loss is 0.563–0.913
  times the pilot's inverse-count prediction (median 0.769). This does not support
  a blanket claim that the pilot understated total evaluation variance.
- In the four failed trials, the chosen allocation also reduces the pilot's
  predicted worst functional variance versus equal allocation (ratios
  0.911, 0.807, 0.868, 0.849). A sum-versus-maximum objective mismatch alone is
  not established as the cause. These are predictions, not counterfactual
  evaluations at another allocation.
- For the failing endpoint, controlled/plain coarse residual variance has median
  ratio 0.867, ranging 0.636–1.318. Polynomial controls provide limited improvement
  here and sometimes increase variance. The paired correction's share of the
  sum of coarse and correction residual variances is only 0.00565%–0.02625%
  (median 0.01042%). This is a variance diagnostic, not a realized error split.

The last calculation uses `var(X[:,5] - .975*X[:,0], ddof=1)` separately for
saved `coarse`, `plain_coarse`, and `correction` arrays. Ratio-of-variance and
correction-share quantiles use all 32 trials. The known .975 is diagnostic only;
allocation continues to use its independent estimated pilot anchors.
Component-level pilot/predicted/observed variances remain in the
[machine-readable audit](audits/2026-11-24-allocation-discovery.json).

**Next bounded hypothesis:** freeze one endpoint-focused control comparison,
using analytically centered smooth CDF controls, independent fitting, the unchanged
candidate comparator, and fresh known-answer geometry checks before new results.
Prove the controls' zero-integral identity and signed accounting first. Keep
search/allocation settings fixed for that comparison and retain every old case
as a regression check. This is a proposed numerical variance-reduction direction,
not an adopted fix, a reason to add arbitrary complexity, or permission to optimize
on consumed outcomes. Its cost and decision rules must be frozen before draws.

No automatic sample increase, plain/diagnostic fallback, changed prior, wider
interval or relaxed gate. Full numerical coverage, unchanged archived NFL comparison,
the unfinished 192-fit player-calibration study and observational admission remain
required. No new NFL outcomes or sealed Week 10 evidence were used.

## Reproduction and limits

Plan SHA-256: `d0adbccfbbd77616e291045df541cad157ef7020d15284b804af0ac0128568fe`.
Numerical kernel: `5b7b910cd86b4c306de4ae5200abebb05b32ca1733caab4548da5fb15c1b2c15`.
Manifest: `a99b4289cf5791daa2db0c41a7d6edc4e26bd9a546bb817d2c4ed4c00970802f`.
Trial-loop totals are 798.31 and 796.81 seconds; these exclude preparation,
post-study validation, storage/replay analysis, tests and reporting overhead.
The [execution receipt](audits/2026-11-24-allocation-executions.json) binds logs,
reconstruction, unchanged original player artifacts and the actual archive gate.
All 18 objects and the manifest match byte-for-byte. The actual saved report
is rejected before any archived NFL input is loaded. Candidate calls range
83,286–84,003, below the frozen 90,000 cap. Previous-setting calls range
82,726–83,631 including their unused diagnostic pilot; actual work is not equal
between search settings. There are no budget failures or omitted trials.

Build from producer **1e2a39b** with retained parent archives and its recorded
environment; a different Git revision changes manifest identity even if numerical
bytes agree. Use this PR's reporting revision for analysis:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/allocation-discovery-preflight-v1.json --store data/derived/allocation-discovery-preflight build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --plan config/allocation-discovery-preflight-v1.json --store data/derived/allocation-discovery-preflight-offline build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python scripts/analyze_mode_preflight.py data/derived/allocation-discovery-preflight a99b4289cf5791daa2db0c41a7d6edc4e26bd9a546bb817d2c4ed4c00970802f --reconstruction data/derived/allocation-discovery-preflight-offline
```

Research stores remain local; durable remote retention is unverified. Exact
replay is not calibration. The 57-QB/122-game archive still ends November 7 evening;
no current leaderboard, qualification completion or defensive admission is claimed.
No new dependency, service, purchase, automation change or other-repository edit.
