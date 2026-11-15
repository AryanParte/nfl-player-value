# Repaired-target functional study — November 15

This study tests numerical accuracy, not scoring admission. The first
implementation exposed a proposal-restoration defect. It is preserved, and the
exact correction is being evaluated under the unchanged frozen rules. The
archived NFL comparison remains gated on all corrected known-answer controls.
No CAVAA score is published by this work. See [PR #29](https://github.com/AryanParte/nfl-player-value/pull/29).

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

No seed, sample size, known answer, posterior, accuracy limit or admission rule
changes. Corrected trials reuse the declared seeds to implement the original
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
its upper-endpoint marginal coverage is 92.1875% (p=7.6164e-5). Other corrected
control results and independent reconstruction are pending completion.
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

## Verification and limits

A regression test first fails on the incorrect NFL-centered restoration and then
passes on the corrected zero-centered synthetic policy. Analytical tests protect
large surrogate errors, signed numerators, normalization order, independent levels,
paired coordinates, zero corrections and Student-t functionals. Artifact tests
reject changed source, altered raw levels, false decisions, missing cases and
incomplete evaluation counts. Ordinary CI requires no live NFL download.

Local corrected-source checks pass 459 Python tests and 27 frontend contracts,
Ruff/format, TypeScript/build, syntax and whitespace. Initial implementation hosted
CI passes Python 3.11–3.13 and 12 Chromium scenarios. Corrected-source hosted CI
is inspected separately. Software verification cannot replace scientific coverage.

The primary model/prediction objects, 57-QB / 122-game archived season, first-unit
and both sensitivities, negative contributions and every archived game remain
unchanged. The archive ends November 7 evening, not November 15. Week 10 is sealed.
The 192-fit calibration, observational allocation, 34 unresolved QB denominators,
defensive admission and a scored leaderboard remain unfinished.

November 15 metadata still finds no 2026-named asset among 46 in the checked
`nflverse/nflverse-data` participation release; this is not all-provider absence
or a game-level coverage audit. The repository still reports no Pages site and
local `gh` remains unavailable. No new deployment or authenticated browser attempt
is claimed. The required Defense Explorer and independent refresh remain intact.
No new dependency, recurring cost, schedule change, merge or other-repository edit.
