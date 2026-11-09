# Continuous-variance recovery decision — November 9, 2026

**No scoring module is admitted.** The continuous-variance candidate and its
team-only control are implemented, but neither meets the frozen numerical
accuracy requirements on the archived NFL data. An independent offline rebuild
produces identical manifest, model and result bytes. Reproducibility does not
make those estimates numerically trustworthy or scientifically validated.

This closes a bounded diagnostic unit, not the requested scoring milestone or
full uncertainty-calibration campaign. [PR #22](https://github.com/AryanParte/nfl-player-value/pull/22)
is stacked on the still-open PR #21; neither was merged by the agent.

## What changed and what stayed fixed

The [original preregistration](CONTINUOUS_VARIANCE.md) replaces the parent's
five-point precision grid with independent continuous log-normal priors. This
addresses an observed limitation: the old grid excluded some variance scales
used in the failed calibration controls. It retains the additive design,
persistent QB plus tied QB-year effects, team-year and game effects, noise prior,
all source rows and three positional benchmarks. It does not add an interaction
model or separate innovation variance to chase coverage.

After the first numerical failure, a [preregistered proposal repair](CONTINUOUS_NUMERICS.md)
changed where integration points are sampled: stratified prior/Student-t
proposals with exact importance corrections. The posterior, prior sensitivities,
95% interval definition and accuracy gates stayed fixed. Safeguarded mixture-CDF
root solving and bounded spawned workers reduce computation without replacing
the statistical target. Independent scalar quadrature and CDF-root references
protect that distinction.

Both full-study attempts and their performance iterations were interrupted;
their checkpoints remain diagnostic evidence, never inputs chosen for a favorable
rerun. The [scope stop](CONTINUOUS_DIAGNOSTIC_STOP.md) was committed before the
remaining off-grid/fixed-year fits: finish indices 0–7 of each generator, retain
all 64 requested trials in its denominator, and explicitly leave calibration
unfinished. This followed real-data numerical failures and measured runtime,
not a selection of successful simulated outcomes. The final two builds each
recomputed all 24 diagnostic fits. Earlier inspected draws are consumed evidence.

## Numerical result on real data

The final proposal evaluates 4,096 nodes per independent scramble. The frozen
minimum effective sample size is 128; maximum mean disagreement is 0.01 posterior
SD and interval-endpoint disagreement is 0.02 SD. Both independent-scramble and
nested-resolution checks must pass. These control integration error, not whether
an NFL contribution is causal or its interval has nominal repeated-sampling coverage.

| Candidate | Minimum ESS | Independent mean / endpoint difference (SD) | Nested mean / endpoint difference (SD) | Numerical decision |
| --- | ---: | --- | --- | --- |
| Evolving QB | 76.17 | 0.03775 / 0.03968 | 0.02741 / 0.03559 | Fails |
| Team control | 205.80 | 0.00631 / 0.00555 | 0.01169 / 0.01119 | Fails nested mean check |

The two QB prior-mean sensitivities also fail. Their apparent maximum mean shifts
of approximately 0.37/0.39 EP cannot be used as evidence of prior robustness.
The original Gaussian proposal failed too; this is not a comparison in which a
passing alternative was withheld. `predict_frozen` rejects numerically invalid
models. Every stored player estimate remains explicitly invalid, uncalibrated
and unadmitted; no ranking or frontend score is generated.

The [importance-geometry audit](audits/2026-11-09-importance-geometry.json) identifies
a concrete numerical problem. Three optimizer starts reach essentially the same
mode, but one integration point receives about 8.44% of a scramble's normalized
weight. It lies far out along the offense-precision direction: very high precision
means almost zero team-effect variance. QB/defense directions remain narrower.
The local elliptical proposals do not cover these different tail shapes reliably.
This is evidence of importance-weight concentration, not proof of a unique mode
or statistical rejection of the continuous model. The next unit must solve this
numerical issue before interpreting interval coverage or changing the variance prior.

## Diagnostic simulations, with failures and omissions visible

Each scenario requested 64 fits; only its first eight were attempted under the
documented execution cap. All 17 failed attempts returned numerical diagnostics,
not process exceptions. The 168 unattempted fits are separate from those failures.

| Generator | Requested | Attempted | Numerically valid | Failed | Unattempted | Coverage bounds over all requested trials |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Continuous prior | 64 | 8 | 4 | 4 | 56 | 6.11%–99.86% |
| Off-grid continuous hierarchy | 64 | 8 | 3 | 5 | 56 | 4.44%–99.75% |
| Fixed year changes | 64 | 8 | 0 | 8 | 56 | 0%–100% |

These bounds treat every failed/unattempted interval as unknown, not as a miss or
a success. The success-only coverage is 97.81% (Monte Carlo SE 0.84 percentage
points, four replicates) and 94.74% (SE 2.68 points, three replicates). These are
selected conditional summaries, **not calibration estimates for the complete
study**; the nominal-shortfall flag is not an admission rule. No fixed-year
coverage summary is available. Treating the seven successful fits as the whole
experiment would hide the principal failure. All admission flags remain false.

## Season accounting and the observational estimand

The unchanged archive contains 48,776 verified 2024–26 training dropbacks across
666 games. Only 57 QBs / 122 archived 2026 games / 8,996 dropbacks contribute to
2026 totals. The archive ends November 7 at 20:41:17 Eastern, partway through Week
9; it is not November 9 coverage. No later game was downloaded and Week 10 remains
sealed. Historical plays improve estimation and add zero current-season points.

First-unit weights are rederived from exact archived depth/roster evidence and
checked against the parent. Equal-player and opportunity-weighted sensitivities
remain distinct. Qualification never filters the benchmark: 23 QB denominators
retain their narrow proof; 34 remain unresolved. All 122 archived completed games
are retained, including negative contributions. Maximum play reconstruction
error is 1.78e-15 EP; maximum game-to-player total error is 2.22e-16 EP.

These arithmetic checks do not validate attribution. The current additive
contrast allocates an estimated season-level QB effect across observed dropbacks;
its per-game ledger is opportunity-weighted accounting, not an independently
measured game-performance effect. Team/context terms and unexplained outcomes
remain separate. QB/team allocation still depends on exchangeability, shrinkage
and observed design support. Recovering a unique causal effect is not imposed as
a requirement for a clearly conditional observational metric. Numerical accuracy,
appropriately scoped uncertainty checks, declared prior/allocation sensitivity
and fresh predictive evidence remain necessary. No admission rule was relaxed
after viewing these results.

## Defense, product and deployment

The required historical information-loss experiment and Defense Explorer remain
intact. The [November 9 source-metadata audit](audits/2026-11-09-defense-availability.json)
finds 46 assets in nflverse's public `pbp_participation` release, with season files
through 2025 and none named for 2026. This supports an explicit gap in that feed;
it does not establish absence from every provider. No game outcomes were accessed
for this check. The prior 895-defender diagnosis still has residualized rank
856 with rich participation and 193 after aggregation. There is no new defensive
CAVAA or admission, and no artificial rescaling into a unified ranking.

All 17 position/contribution modules remain unavailable for ranking. Explorer
availability/explanations are implemented; admitted scores and ranked history
are unfinished. PRs #18/#19 are owner-merged. November 9 API inspection reports
`has_pages: false` and no Explorer refresh run among all 47 returned workflow
runs. Browser authentication was not rechecked. Deployment preparation is merged
code, not an activated website, and remains independent of the development
automation. No deployment access issue stopped this modeling work.

## Reproduction and verification

The [compact result audit](audits/2026-11-09-continuous-variance.json) records the
producer, environment, plan, final per-trial checks and parent source references.

| Artifact | SHA-256 / revision |
| --- | --- |
| Producer commit | `099cce5fbff08c13e33322b707b7c80aa402d74c` |
| Diagnostic plan | `7583950357a0e4d13ec80c24c12ba8ecfeea3b8e7c56d187f29aaf18cda44000` |
| Manifest | `ad45a2cbf0889d4ebebd13cb17dba54a420881453beb9058f44cb0f5dda2cab1` |
| Models | `1096cdc8553e98088306114b37cd467797bee10ecbe00ad96c0f419a2d37c889` |
| Results | `9a188b103bda99a717eae544918caa0155a75c2c0084e3358d0028c1d916898f` |

With the original raw, offensive-input and multi-season stores available:

```sh
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m nfl_value.continuous_cli --workers 4 --output-store data/derived/continuous-variance-diagnostic build --plan config/continuous-variance-diagnostic-v1.json
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m nfl_value.continuous_cli --workers 4 --output-store data/derived/continuous-variance-diagnostic replay ad45a2cbf0889d4ebebd13cb17dba54a420881453beb9058f44cb0f5dda2cab1
```

Actual verification was a second full diagnostic **build**, not a third expensive
CLI replay: the rebuild denied Python Internet sockets/DNS in the parent and
spawned workers, retained local process IPC, replayed original source stores,
recomputed both real fits and all 24 attempts, and produced byte-identical
manifest/models/results. Numerical replay tolerances remain 1e-9 absolute and
1e-8 relative; they were not needed to explain differences between these builds.
Large research/source stores remain local and are not yet covered by deployed
durable retention. A fresh clone needs those immutable inputs before reproducing.

`make check` passes 396 Python tests and 27 frontend contracts, Ruff/adopted
formatting, TypeScript/build, compile and whitespace checks. New regressions use
independent density/quadrature/root references; preserve signed nonduplicated
season totals and benchmark/qualification separation; detect modified data and
replay artifacts; retain failed/unattempted denominators; and compare serial with
spawned execution. Hosted CI is reported in the learning log with its exact head.
No local browser rerun or new live deployment verification is claimed.

## Next concrete milestone

First preregister a small numerical-reference pilot for the weak nuisance-variance
tails, with explicit runtime/node limits and agreement criteria against an
independent integration method. Keep this target posterior and all failed evidence
fixed while diagnosing integration; do not select a more favorable prior or
wider interval. Only launch another full calibration study after that pilot
passes on the frozen real design and difficult synthetic cases. The consumed
diagnostic outcomes cannot become its fresh confirmatory evidence.

Then complete fresh calibration, the sealed prospective comparison and the
observational-attribution/admission review. The deliverable remains a reproducible,
defensibly validated partial contribution module feeding the dashboard, followed
by broader defensive/cross-position coverage. This run did not reach that milestone.
