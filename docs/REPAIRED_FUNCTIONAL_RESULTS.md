# Repaired-target functional study — November 15

The bounded study is complete: **all five known-answer controls pass for the
single frozen equal-work alternative; only one of five archived NFL comparisons
passes**. The QB and three stress cases remain uncertified because numerical
error is too large. All point discrepancies meet their tolerances, so these
failures do not establish primary-estimate bias. No contribution module is
admitted. See [PR #29](https://github.com/AryanParte/nfl-player-value/pull/29).

This November 15 run was finalized November 16 after an interrupted browser
access check. Offline experiments completed in the background. The reporting
date does not advance the archived football evidence cutoff.

## Frozen sequence and implementation

- `4f8209c` freezes the [two-level study](REPAIRED_FUNCTIONAL.md) before results.
- `6259786` implements independent coarse and paired fine-minus-coarse integrals,
  combines unnormalized vectors, and uses the existing Fieller/Student confidence
  construction. It retains all five archived cases and all functional limits.
- `fcb765b` records the [restoration correction](REPAIRED_FUNCTIONAL_CORRECTION.md)
  before corrected results. Independent replay of all five trial-zero density
  fits proves their complete sampling distributions are reproduced with each
  synthetic target's own policy. The [audit](audits/2026-11-15-proposal-restoration.json)
  records both correct and incorrect component hashes.
- `e2544ca` fixes that deterministic mismatch, hashes the complete sampling
  distributions, retains raw completed work before confidence failures, and checks
  the executing source fingerprint at both start and final serialization.

The restoration correction changes no seed, sample size, known answer, posterior,
accuracy limit or admission rule. Corrected trials reuse the declared seeds to implement the original
design; they are not described as a newly independent confirmation experiment.
Two separately executed network-disabled builds test deterministic reconstruction.

## Preserved original attempt

All 5,120 trials complete. Four controls pass; the two-dimensional control fails
one upper-endpoint marginal-coverage test: **91.6016%**, one-sided undercoverage
p-value **3.0064e-6**, below the unchanged multiplicity-adjusted 0.0002857143 limit.
Its joint coverage is 93.75% and its precision fraction is 100%; neither overrides
the failed marginal test. All incorrect endpoints are rejected in every control.

| Control | Joint coverage | Precision fraction | Decision |
| --- | ---: | ---: | --- |
| Two-dimensional mixture | 93.7500% | 100% | Fail |
| Three-dimensional mixture | 94.4336% | 100% | Pass |
| Four-dimensional mixture | 96.6797% | 100% | Pass |
| Four-dimensional tail mixture | 95.3125% | 99.9023% | Pass |
| Bounded curved target | 94.3359% | 100% | Pass |

The incorrect prior proposal center violates the frozen distribution. Its density
still enters importance weights consistently, so this is not evidence that the
football posterior itself changed. Nor does identifying the defect prove that
corrected coverage must pass. The failed attempt authorizes no NFL evaluation.

Report: `ef9037e672999ea4d2170ae95a91ee048f26a45ff987b1c9986f6c39c31d2544`.
Study: `8aa325d1361b4b059ca003f975c5cc07fccef65e43c2a0df7de3eb34c10b1d1a`.
Producing revision: `6259786df3e69a1118218dbcf51820994c641747`.
The immutable store is `data/derived/repaired-functional-controls`. Replay of this
failed version requires its producing source; the corrected executable deliberately
rejects its obsolete source fingerprint. No original artifact is overwritten.

## Corrected-design failure diagnosis

The exact proposal correction does **not** remove the first control's failure:
its upper-endpoint marginal coverage is 92.1875% (p=7.6164e-5). All 5,120 trials
complete and all incorrect endpoints are rejected. The other four controls pass.

| Control | Joint coverage | Precision fraction | Decision |
| --- | ---: | ---: | --- |
| Two-dimensional mixture | 94.5313% | 100% | Fail |
| Three-dimensional mixture | 95.5078% | 100% | Pass |
| Four-dimensional mixture | 95.0195% | 100% | Pass |
| Four-dimensional tail mixture | 94.8242% | 99.9023% | Pass |
| Bounded curved target | 94.5313% | 100% | Pass |

Report: `7932f0fc67c47218947387958e21e3f500e9129e95069339364de899c1bf0771`.
Study: `93bd2ac7f3219d2e4be6be808f81e147270eab5a20360c230edc18fc0afaab6e`.
Producing revision: `e2544caf0630633ea29ec337b3b18d0d8acd0014`.
The complete independently executed network-disabled reconstruction has identical
manifest bytes and all six object hashes (five checkpoints and the study).
Original and reconstruction stores are `data/derived/repaired-functional-corrected`
and `data/derived/repaired-functional-corrected-offline`. Replay requires the
producing statistical source, not an edited kernel with a different fingerprint.

The [separately frozen diagnosis/allocation](REPAIRED_ALLOCATION.md) precedes the
following calculations and any fresh allocation results.

For the failed endpoint, an independently computed sine moment is
0.006208927189093265; original-coordinate 128- and 256-node-per-axis quadrature
agree to about 8e-17. The influence quantity `numerator - .975 * mass` isolates
normalization covariance without substituting a player-uncertainty interval.

| Level | Centered Student coverage | Pooled replicate skewness | Excess kurtosis | Mean estimated / empirical trial variance |
| --- | ---: | ---: | ---: | ---: |
| Coarse | 91.9922% | -1.6588 | 5.2618 | 0.8598 |
| Correction | 95.0195% | -0.0463 | -0.0923 | 1.0195 |
| Combined | 92.1875% | -1.6543 | 5.2455 | 0.8582 |

The coarse level accounts for 99.9026% of the separate empirical variances.
These consumed-draw diagnostics implicate skewed coarse errors and the
finite-replicate confidence approximation; they do not prove universal bias in
the variance estimator. Increasing the fine correction budget would target the
smaller component. One predeclared alternative instead uses 64 independent nets
with half as many points in each, keeping total points unchanged. It uses fresh
randomizations and the same precision/coverage gates. No intervals are multiplied,
no player interval changes, and no NFL case runs unless every control passes.

The diagnostic equations and the single allocation alternative were committed
at `6d06059` before those calculations and new results; the alternative runner
was committed at `3774295` before both independently executed builds. Version 2
uses 64 replicates × 1,024 coarse / 32 correction points, compared with version 1's
32 × 2,048 / 64. Both retain 65,536 coarse plus 2,048 paired correction points.
The experiment-schema label remains `repaired-functional-controls-v1`; the exact
allocation is distinguished by the embedded plan version and its content hash.

All five 64-replicate controls complete and pass in both independent builds.
The formerly failing marginal covers 95.1172%, with p=0.58837. The same frozen
decomposition on this consumed first-control output finds a combined estimated/
empirical variance ratio of 1.0401, versus 0.8582 previously. Its coarse empirical
trial variance increases from 1.104e-9 to 1.498e-9. More independent replicates
improve this measured coverage while sacrificing precision; they do not make
integration more accurate for free. Comparisons use different preregistered
numerical draws and are descriptive. See the
[decomposition](audits/2026-11-15-allocation-errors.json).

| Control | Joint coverage | Precision fraction | Decision |
| --- | ---: | ---: | --- |
| Two-dimensional mixture | 94.6289% | 100% | Pass |
| Three-dimensional mixture | 95.2148% | 100% | Pass |
| Four-dimensional mixture | 95.6055% | 100% | Pass |
| Four-dimensional tail mixture | 93.7500% | 99.1211% | Pass |
| Bounded curved target | 95.9961% | 100% | Pass |

All 5,120 requested trials complete and all deliberately incorrect endpoints are
rejected. These are passes against the frozen finite-sample coverage/precision
rules, not exact 95% coverage for every possible target. In particular, the tail
control's measured coverage remains below 95%.

## Completed controls and storage failure

Both numerical builds at 3774295 finish all five controls, then exit with
“stored object exceeds size limit” while saving the combined study. Doubling
replicate count also doubled retained raw vectors. Separate checkpoints fit the
existing 128 MiB object bound; the aggregate does not. This is an artifact failure,
not another statistical trial or a successful one-shot run.

The separately [frozen storage recovery](REPAIRED_STORAGE_RECOVERY.md) keeps that
bound and stores a small index pointing to independently hashed case objects.
Loading rebuilds the logical study and verifies its whole-study hash, ordering,
uniqueness and original numerical decisions. Recovery proves all statistical
source unchanged from 3774295, except the two save/load functions, and records
the original numerical producer separately from packaging revision 558c878.
No numerical trial, limit or decision changes to recover these outputs.

Both separately computed checkpoint sets match byte for byte. Both staged
recoveries have identical manifests and all **11** stored object hashes. The
updated one-shot controls CLI was not re-executed after the storage repair;
this is two independent numerical executions followed by two verified recoveries.

Recovered report: 9563320e56ac493885a0154551754157db8916ca4e8e7069c8ddc9d6b440a700.
Recovery receipt: 6abfdad60a19dcb37c49d257f7a82bfc4d3507751035342c54b51fa30ad33048.
Stores: data/derived/repaired-functional-allocation and
data/derived/repaired-functional-allocation-offline. These local stores are
immutable research evidence, not durable remote retention.

## Archived NFL comparison and decision

The recovered all-control pass authorizes exactly the five frozen archived cases.
Every case completes with 2,049 fine and 67,584 coarse evaluations, including the
offset evaluation. No case times out. The original pass takes about 3,406 seconds
in total and its independent offline repeat about 3,405, inside the 7,200-second
cap; every case also meets the 1,800-second cap. All original primary QMC flags
remain valid. Comparison uses simultaneous numerical-error limits, not simply
the distance between point estimates.

| Case / prior | Maximum mean discrepancy + numerical error (posterior SD) | Maximum endpoint discrepancy + numerical error (CDF) | Decision |
| --- | ---: | ---: | --- |
| Real QB / primary | 0.015977 | 0.001242 | Fail |
| Real QB / lower precision prior | 0.014764 | 0.001120 | Fail |
| Real QB / higher precision prior | 0.017348 | 0.001385 | Fail |
| Real team control | 0.002215 | 0.000220 | Pass |
| Prior stress | 0.004392 | 0.001168 | Fail |
| Hierarchy stress | 0.033895 | 0.001720 | Fail |
| Fixed-year stress | 0.028953 | 0.002462 | Fail |

Limits remain **0.01 posterior SD** and **0.001 CDF**. The three real-QB prior
rows are sensitivities within one case, not three independent case passes.
All point discrepancies meet the limits; no numerical confidence set excludes
the allowed agreement region. For the primary QB's worst mean, point discrepancy
is 0.005955 SD and numerical error is 0.010022 SD. Uncertainty prevents certifying
agreement. It does not establish model bias or justify altering football priors,
widening player intervals or relaxing admission gates.

The frozen separate-level influence diagnostic uses numerator minus ratio times
mass at the combined estimate. Across all cases/settings, the largest correction
to coarse influence-standard-error ratio is **1.36e-9**. The largest correction
to a normalized point estimate is **1.26e-12 posterior SD / 6.22e-14 CDF**.
These observed first-order diagnostics locate imprecision in coarse integration;
they are not new acceptance rules or proof that correction is unnecessary in
all tails. The repaired solver remains necessary for the earlier conditioning
failure. Increasing fine-evaluation work alone would not address this result.

Report: fc9b04f4012293f7ed3c4f1584550c9cc12a9e901d59e0f6c49ceea496e6d4ab.
Study: 834c581fe8927db3ac61022b48027ffaee61facfe93954e19378a462e52add25.
Producing source: 558c8789721cdb081c3101c6a9df2f281a740973.
Stores: data/derived/repaired-functional-nfl and
data/derived/repaired-functional-nfl-offline. Independent network-disabled
reconstruction matches the manifest and all **six** objects exactly. The
[audit](audits/2026-11-15-repaired-functional.json) contains all decisions, timings,
source binding, raw-object references, diagnostic equations and replay receipts.

The bounded alternative family stops here. The next concrete numerical candidate
is an independently fitted, zero-mean control variate for the coarse integral,
with analytically known component expectations. Freeze fitting separation,
fresh numerical draws, fixed work and coverage/precision rules before evaluation.
This is a proposed next experiment, not an adopted model or demonstrated pass.
Retain all five consumed NFL cases and their sensitivity settings. A numerical
pass would still precede the unfinished 192-fit player calibration, prospective
evidence and observational admission. No new primary sampling, favorable seed or
unplanned further replicate increase is authorized by this unit.

## Verification and limits

A regression test first fails on the incorrect NFL-centered restoration and then
passes on the corrected zero-centered synthetic policy. Analytical tests protect
large surrogate errors, signed numerators, normalization order, independent levels,
paired coordinates, zero corrections and Student-t functionals. Artifact tests
reject changed source, altered raw levels, false decisions, missing cases and
incomplete evaluation counts. Ordinary CI requires no live NFL download.

At 558c878, local make check passes 465 Python tests, 27 frontend contracts,
Ruff/format, TypeScript/build, syntax and whitespace. Hosted
[run 43780721311](https://github.com/AryanParte/nfl-player-value/actions/runs/43780721311)
passes Python 3.11–3.13 and the dashboard job, including 12 Chromium scenarios.
Storage tests reject corrupt/missing cases, duplicate or reordered indexes, logical
hash drift and computational changes disguised as packaging recovery. Final
reporting-head CI is inspected separately. Software checks and exact replay
cannot replace scientific calibration.

The primary model/prediction objects, 57-QB / 122-game archived season, first-unit
and both sensitivities, negative contributions and every archived game remain
unchanged. The archive ends November 7 evening, not November 15. Week 10 is sealed.
The 192-fit calibration, observational allocation, 34 unresolved QB denominators,
defensive admission and a scored leaderboard remain unfinished.

November 15 metadata still finds no 2026-named asset among 46 in the checked
`nflverse/nflverse-data` participation release; this is not all-provider absence
or a game-level coverage audit. November 15 repository metadata reports no Pages
site; local gh is unavailable. A browser access check hung and was interrupted
before returning authenticated state; no settings change or deployment was
performed. Defense Explorer and independent refresh remain intact.
No new dependency, recurring cost, schedule change, merge or other-repository edit.
