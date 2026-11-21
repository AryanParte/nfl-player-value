# Mode-discovery preflight — November 20, finalized November 21

**Reject this candidate for progression to full certification. No scoring module
is admitted.** The [design](MODE_PREFLIGHT_DESIGN.md) was frozen at `e586379`;
numerical implementation `ac85ca6` precedes all study draws. PR #34 is stacked on
open PR #33. Neither has been merged by the agent.

All 320 candidate and 128 oracle-diagnostic trials were attempted. Every trial
retains raw integrals; 447/448 confidence constructions finish. The failed remote
construction remains in the denominator. Two complete offline executions reproduce
all 14 objects and the manifest byte-for-byte. They reuse the frozen seeds and
are not 896 independent statistical trials.

## Complete candidate decision

Every row requests 32 trials. Precision is discrepancy plus numerical allowance
within .01 SD for means and .001 CDF for endpoints. This small feasibility screen
requires >=90% precision and no severe-undercoverage flag; it cannot replace the
full certificate's coverage lower-bound requirement or authorize NFL work.

| Target | Complete confidence sets | Precision | Joint numerical coverage | Screen |
| --- | ---: | ---: | ---: | --- |
| Original 0 | 32 | 100.00% | 96.875% | Pass |
| Original 1 | 32 | 100.00% | 93.750% | Pass |
| Original 2 | 32 | 100.00% | 100.000% | Pass |
| Original 3, weak displaced broad component | 32 | 0.00% | 96.875% | Fail |
| Original 4, curved | 32 | 93.75% | 96.875% | Pass |
| Broad tail 5 | 32 | 90.625% | 100.000% | Pass |
| Displaced mass 6 | 32 | 93.75% | 90.625% | Pass |
| Remote narrow mass 7 | 31 | 68.75% | 75.000% | Fail |
| Geometry extension 8 | 32 | 93.75% | 90.625% | Pass |
| Geometry extension 9 | 32 | 96.875% | 90.625% | Pass |

Eight of ten screens pass; original case 3 regresses and remote case 7 still
fails. Thirty-two trials give coarse estimates: passing a screen does not prove
a population precision probability >=90% or calibrated 95% numerical intervals.
Comparisons with November 19 use different packages, seeds and trial counts;
there is no paired causal estimate of one implementation change.

## What failed and what the additional analysis resolved

**Case 3: finding every density peak does not preserve every important tail.**
All 24 optimizers report usable convergence in all 32 trials, finding one mode.
The median pilot mass is .999511, but mean and endpoint precision fail in every
trial. Median maximum discrepancy plus allowance is .017461 SD / .00528906 CDF,
against .01 / .001. The plain estimator also has 0% precision. Controlled/plain
variances are nearly equal for most functionals; a fitted control is not evidence
of an integration variance reduction.

A post-result analytical diagnostic was declared separately at `635b9ea`, before
its calculation. The fine target's first-coordinate mixture is .95 N(0,1) +
.05 N(4,4), with independent normal remaining coordinates. The density-derivative
ratio has two stationary points, .783323 and 3.715720, where its log is -4.597900
and -.701063. Monotonic-interval root analysis finds only one density mode,
x=.00357102. The code is checked against direct Gaussian derivatives and a
stronger-component control with two modes. Thus an important displaced component
need not create another density peak. More local restarts cannot alone fix this
fine-target geometry. This is floating-point analytical evidence, not interval
arithmetic certification or a theorem about the .001 sine-tilted coarse target.
See [geometry audit](audits/2026-11-20-mode-tail-geometry.json).

**Case 7: mode discovery is still unreliable.** Twenty-two trials find both modes;
all 22 pass precision, with joint coverage in 20. Ten find only the central mode;
none passes precision, four cover jointly, and one confidence construction fails.
These conditional counts explain the observed failure; they cannot define a
selectable validation subset. All 32 trials have defined point estimates, including
the failed confidence construction. The second standardized mean's all-trial
RMSE is .122026 SD. The ten one-mode pilot masses range .899738–2.425729: missed
mass and rare extreme pilot weights both remain visible. The paired plain
reference also has only 68.75% precision. No plain or successful-search fallback
is selected. Isolated wrong-endpoint checks exclude both in 26/32 trials; joint
vector rejection alone would obscure that limitation.

**The oracle diagnostic does not solve functional precision automatically.** It
uses known true Gaussian components, which the real model cannot access. It has
no search cost, no covariance inflation and separate random draws. Its precision
fractions for cases 6–9 are 87.5%, 90.625%, 96.875%, 96.875%; all 128 confidence
constructions finish. Case 6 fails endpoint precision in four trials despite
correct proposal components and tiny mean errors (median total .00006196 SD).
Its median maximum endpoint discrepancy plus allowance is .00084409 CDF, with a
maximum .00108276. Correct component information can still leave numerical work
insufficient on a finite draw. The small screen does not establish the oracle's
population failure probability or a ceiling for all estimators. Oracle results
are never a production candidate or authorization for NFL evaluation.

The complete [failure-inclusive audit](audits/2026-11-20-mode-preflight.json)
retains controlled/plain comparisons, uncertainty versus point-error decompositions,
isolated endpoint checks, fitting work, probe limitations and every denominator.

## Decision and next bounded action

Do not run full certification for this failed candidate, retune consumed seeds,
select only two-mode trials, widen intervals or change football priors. Freeze
one tail-preserving proposal hypothesis that can represent broad nonmodal mass
alongside separated modes. Its preflight must retain original case 3 and the
remote/rotated cases, measure discovery and functional precision separately, and
count all search/fitting/evaluation work. Merely adding local starts is not a
complete remedy. No new alternative has yet been validated.

The actual saved preflight manifest is rejected by the archived NFL runner before
input access (`coarse control study differs from frozen design`). It has a distinct
schema and `numerical_certified=false`; it cannot become a full certificate by
passing a screen. No archived NFL comparison, completed 192-fit player calibration,
new game coverage or position admission follows. Week 10 remains sealed.

## Verification and reproduction

Final local `make check PYTHON=.venv/bin/python` passes 529 Python tests, 27 frontend
contracts, Ruff/adopted formatting, TypeScript/build, compilation and whitespace.
The numerical producer passes hosted Python 3.11–3.13 and dashboard/browser
[CI 44826832617](https://github.com/AryanParte/nfl-player-value/actions/runs/44826832617).
Final reporting/analytical-head CI is inspected separately in the PR. Tests cover
known Gaussian curvature, duplicated-stratum conservation, work/time caps, retained
search failures, signed integrals, independent random domains, reversed endpoint
convolution, corrupted records and preflight non-admission. Review identified and
fixed an incorrect search-response hash before study execution; an unknown arm
now fails explicitly instead of silently selecting the oracle. Those fixes and
their affected checks preceded numerical production.

| Item | Value |
| --- | --- |
| Producer | `ac85ca66bb3a4f82afa43e67a9ebdada7ed65910` |
| Canonical JSON plan SHA-256 | `cbd0c022a598659f408c557079933e1e9e5eb0ca907da779fe60a10bf3d9a433` |
| Numerical package SHA-256 | `d46398aefa3a69b44c4dca7d4631609c2da1f736eaf59e686c067fe4b2ad1caf` |
| Manifest | `9400cb219b91193c3b0c4f39aca058695148d058adfa14234c6adf0ce17a8fd8` |

At the producer revision, with the recorded environment and immutable parent
stores named by the plan available, both empty-store executions used:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --store data/derived/mode-preflight build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.mode_preflight_cli --offline --store data/derived/mode-preflight-offline build
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python scripts/analyze_mode_preflight.py data/derived/mode-preflight 9400cb219b91193c3b0c4f39aca058695148d058adfa14234c6adf0ce17a8fd8 --reconstruction data/derived/mode-preflight-offline
```

`--offline` disables socket/DNS access. The producer also includes `replay` for
independent recomputation in an existing store. Source/environment mismatch is
rejected; cross-platform byte identity is not claimed. The post-result analytic
script was added after the producer and does not change the numerical package.

Candidate trials use 76,577–77,641 target evaluations, including search, numerical
derivatives, Hessians, pilot, control fitting and both correction evaluations,
within 90,000. Oracle trials use 71,680 and are not an equal-work practical method.
Measured case loops take 514.26 / 515.58 seconds (8.57 / 8.59 minutes), excluding
truth/parent preparation, validation, storage and other overhead. They are not
production runtimes or the elapsed duration of this development run. The runner's
time check covers the trial loop; all trials complete well within the declared
work limits. The [execution audit](audits/2026-11-20-mode-executions.json) binds
logs, source, actual gate proof and original model/prediction hashes.

Raw research stores remain local and ignored by Git; committed audits and replay
commands do not establish durable remote retention. The archive still ends
November 7 evening, not November 21. Participation gaps, defensive uncertainty,
cross-position comparability, ranked history and authenticated Explorer deployment
remain open. No new dependency, service, purchase, schedule or other repository
change was introduced.
