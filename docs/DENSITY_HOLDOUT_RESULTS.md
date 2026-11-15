# Density stabilization and numerical coverage — November 13

Covariance stabilization improves average proposal overlap on the archived QB
and difficult consumed stress targets, but does not deliver an admitted CAVAA
module. All five known-answer coverage controls pass. The archived QB reference
still fails its unchanged accuracy limits, and a retained stress failure exposes
an ill-conditioned conditional solve. Better sampling is not calibrated football
attribution. See [PR #27](https://github.com/AryanParte/nfl-player-value/pull/27)
and the [audit](audits/2026-11-13-density-holdout.json).

## Frozen sequence and scope

- `aefe914` freezes the paired study and one covariance alternative before results.
- `addf315` corrects a mathematical tail flaw before any study trial: the proposed
  quadratic curved target has infinite Gaussian importance-weight variance.
  The [amendment](DENSITY_HOLDOUT_TAIL_AMENDMENT.md) uses a bounded-sine transform
  with the same independently known latent functionals and finite variance.
  No empirical result motivates that correction; the original plan is retained.
- `7f92146` implements the study. The exact archived posterior, first-unit and both
  sensitivity benchmarks, qualifications, source cohort and accuracy limits stay
  fixed. The five pilot cases are already consumed numerical diagnostics, not
  fresh football validation or new calibration draws.
- The [compatibility correction](DENSITY_HOLDOUT.md) binds two exact archived
  primary-runner extensions instead of rejecting equivalent reference policies.
  Before the functional pilot, all five targets' known answers and both trial-zero
  geometries match the saved control bytes under the full archived policy.
  Missing/changed extensions, other keys and altered model parameters still fail.

No favorable pilot is selected: known coverage and the archived reference always
use their declared density trial zero. All failed cases remain in denominators.
No further confirmation audit, retry seed, interval inflation or gate relaxation
is used to obtain these results.

## Known-answer numerical-error coverage

Each control has 32 independent paired density fits, followed by exactly 1,024
reference trials on the preselected stabilized geometry. Each reference trial
contains 32 independent scrambled nets of 2,048 points. All 5,120 trials finish;
every trial meets the 0.01 posterior-SD mean / 0.001 endpoint-CDF precision limits
and rejects deliberately incorrect endpoints. All seven marginal undercoverage
tests and the joint test pass their frozen multiplicity-adjusted thresholds.

| Control | Joint coverage | One-sided 95% lower bound | Precision | Decision |
| --- | ---: | ---: | ---: | --- |
| Two-dimensional mixture | 94.43% | 93.11% | 100% | Pass |
| Three-dimensional mixture | 94.63% | 93.32% | 100% | Pass |
| Four-dimensional mixture | 96.29% | 95.16% | 100% | Pass |
| Four-dimensional tail mixture | 94.73% | 93.43% | 100% | Pass |
| Bounded curved four-dimensional target | 96.39% | 95.27% | 100% | Pass |

This is empirical coverage conditional on the functions/proposals tested, not a
universal guarantee for NFL targets or for the larger family of player contrasts.
The same Fieller implementation propagates numerator/normalization covariance.
Known-answer coverage permits the archived numerical pilot only; it does not
validate player uncertainty, identify QB/team attribution or admit a position.

Stabilization is not uniformly beneficial. The simplest control's mean held-out
log-score gain is -0.00466 (descriptive 95% interval -0.00688 to -0.00245), while
the four-dimensional mixture improves by 0.07286 (0.04548 to 0.10024). The other
known-target log-score intervals include zero. All 160 density trials finish.

## Archived density diagnosis

Positive held-out log-score gain favors the stabilized proposal. Negative log-C2
ratio favors its estimated normalized second moment. These intervals describe
variation across four pilot fits, including holdout noise; they are not admission
tests or guarantees about effective independent sample size.

| Target | Complete / requested | Mean held-out gain (descriptive 95% interval) | Mean log-C2 ratio (descriptive 95% interval) |
| --- | ---: | --- | --- |
| Real QB | 4/4 | 0.3185 (0.0147, 0.6222) | -1.3815 (-3.0331, 0.2702) |
| Real team control | 4/4 | 0.0286 (-0.0274, 0.0847) | -0.1643 (-0.5011, 0.1726) |
| Consumed prior stress | 3/4 | 0.1662 (-0.0662, 0.3986) | -1.8687 (-2.1494, -1.5880) |
| Consumed hierarchy stress | 4/4 | 0.6646 (-0.0437, 1.3730) | -3.2503 (-6.0171, -0.4834) |
| Consumed fixed-year stress | 4/4 | 0.3299 (0.0277, 0.6321) | -2.3542 (-4.1747, -0.5338) |

The prior-stress summaries describe its three completed pairs, not a successful
four-pair study. Its failed trial zero is retained with its exception. There are
19 completed, one failed and zero unattempted archived density trials.

Every real-QB fit improves held-out log score despite reduced training fit. Two
selected baseline fits hit covariance floors; all four stabilized selected fits
avoid that clipping. This supports pilot overfitting as one problem, but does not
show that stabilization fixes every poor-overlap case. Real-QB stabilized C2
estimates range from 1.97 to 32.22; hierarchy estimates range from 1.89 to 353.82.
The fixed-year target has one estimate above 20,000. Finite-sample C2 values are
diagnostics, not certified bounds or independent sample counts. Full geometries,
failed starts, raw holdout moments and training-point hashes remain archived.

## Archived numerical pilot

All five primary-QMC checks pass. All five reference cases are attempted within
their declared work limits: one passes, three complete but fail accuracy, and one
fails during proposal construction. No time/solve cap causes a stop.

| Case | Worst mean discrepancy + error (SD) | Worst endpoint discrepancy + error (CDF) | Decision |
| --- | ---: | ---: | --- |
| Real QB, across all three prior settings | 0.014228 | 0.001308 | Fail |
| Real team control | 0.002051 | 0.000200 | Pass |
| Consumed prior stress | Unavailable | Unavailable | Conditional factorization fails |
| Consumed hierarchy stress | 0.051716 | 0.002632 | Fail |
| Consumed fixed-year stress | 0.081790 | 0.004670 | Fail |

The limits remain 0.01 SD and 0.001 CDF. The largest real-QB mean check comprises
0.011703 SD point discrepancy plus 0.002525 SD numerical error. Yesterday's worst
check was 0.005394 plus 0.024879 = 0.030273 SD. Thus reference uncertainty is much
smaller, but the new point discrepancy is larger. No real-QB numerical confidence
set lies entirely outside its tolerance; this does not establish primary bias or
justify choosing whichever answer looks preferable. Primary stability across its
two randomizations is not the same as independent accuracy. Hierarchy/fixed-year
failures remain dominated by reference imprecision. Their improved-looking
aggregate density metrics cannot override the numerical failures.

The pilot report is `00e774dff2fedec35cb7d3326e0df34c76bf57e892eb31979ad138f88774d761`,
produced by `f3e854c9e9c4c295e943266e6fbac5f75b0757e3`. Its ordinary and
network-disabled builds have identical manifest, model and prediction bytes.
Models, estimates, intervals, benchmarks and season ledgers also match the prior
pilot after excluding only validity flags. Every completed archived season game
and signed contribution remains; no historical training point enters the 2026
scoring total. There is still no admitted score or completed player calibration.

The next concrete unit is a frozen target-preserving conditional-factorization
repair/equivalence study, including exact-alias and weak-precision known answers.
After that repair, diagnose remaining primary/reference disagreement under new
declared randomizations and budgets. Do not automatically increase primary nets,
pick a favorable density pilot, change a prior or relax a limit. Numerical
reliability must precede fresh calibration and observational admission.

## Conditional factorization failure

The [separately frozen trace](DENSITY_FAILURE_TRACE.md) reproduces the prior-stress
trial-zero exception after 2,345 conditional evaluations. Its log-precision vector
is approximately (0.303, -52.994, 15.755, 9.500) for QB/offense/defense/game.
The offense precision is 9.66e-24. The assembled 525-dimensional matrix has maximum
eigenvalue 6.96e6 and minimum -1.79e-10, while machine epsilon times its spectral
norm is 1.54e-9. Two computed eigenvalues are nonpositive. This is evidence of
loss of numerical definiteness at extreme conditioning; it is not evidence of a
negative modeled variance or an invalid football outcome.

A simple analogue is an intercept and identical random-effect column: in exact
arithmetic, `[[n,n],[n,n+lambda]]` is positive definite for lambda>0, but a tiny
lambda can disappear when added in floating point. Adding arbitrary diagonal
jitter changes the conditional posterior and cannot count as an exact repair.
The trace records the coordinates, matrix/response hashes and exception, then
rethrows it. It neither substitutes zero likelihood nor replaces the failed trial.
The current kernel therefore still needs a numerically stable, target-preserving
factorization with independent known-answer/equivalence checks.

## Verification, provenance and remaining decision

Known controls: `fa15a47bfca458c0f666c7db5a475b3f4a169408e0e18e0ad6c1095464f08bd8`.
Archived density: `d29590d4c9adb157b9343720c28614da9918fb5571ea927cb880aa4bf4421b30`.
Both use source `7f921462b00f91f03ded4f80e0fa0b7f9cdaa3b6`; independent builds with
sockets and DNS blocked have identical manifest and study bytes. The trace is
`368eb66e0b2aa55b1978df999ae83f66fc8f054b9e194ed2b9e19f55e189aaf0`, produced by
`49a0d056a382ee4636af5c02a7c376b6282c3c98`. The audit records object hashes,
source manifests, all coverage decisions, density summaries and failure analysis.

The four legacy proposal-geometry hashes also reproduce exactly. Regression
checks cover independent covariance algebra, dominant-weight/rank-deficient
pilots, analytical density ratios, the curved inverse/Jacobian and scalar endpoint
answers, signed Student-t functionals with supplied proposals, policy compatibility,
failure denominators and corrupted evidence/certificate rejection. No fresh live
NFL download is required by ordinary CI. The full study is separate from CI.

Local `make check` passes 441 Python tests and 27 frontend contracts, Ruff/adopted
formatting, TypeScript/build, compilation and whitespace. Hosted Python
3.11/3.12/3.13 and dashboard/Chromium pass on the
[pilot source](https://github.com/AryanParte/nfl-player-value/actions/runs/43503025511).
The PR is authoritative for final-head CI; local/source checks are not substitutes.

Research stores remain local and ignored; byte-identical replay does not establish
durable remote research retention. No dependency, purchase, paid service, deployment,
schedule or other-repository change occurs. Defense Explorer and the all-position
objective remain required; unsupported contributions stay unavailable. No new
calibration or sealed Week 10 outcome enters this unit.

Replay the fixed studies from the stable clone and retained input stores:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.density_cli --output-store data/derived/density-controls replay fa15a47bfca458c0f666c7db5a475b3f4a169408e0e18e0ad6c1095464f08bd8
PYTHONPATH=src .venv/bin/python -m nfl_value.density_cli --output-store data/derived/density-holdout replay d29590d4c9adb157b9343720c28614da9918fb5571ea927cb880aa4bf4421b30
PYTHONPATH=src .venv/bin/python -m nfl_value.density_cli --output-store data/derived/density-reference replay 00e774dff2fedec35cb7d3326e0df34c76bf57e892eb31979ad138f88774d761
PYTHONPATH=src .venv/bin/python scripts/trace_density_failure.py
```

Use the archived producing revision/environment to reproduce manifest IDs; later
commits record different source identities. The replay command compares scientific
objects, while independent builds also verify original manifest bytes. Runtime
measurements stay outside deterministic scientific objects.
