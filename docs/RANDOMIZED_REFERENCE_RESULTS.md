# Replicated randomized reference — November 12 manual follow-up

This additional user-authorized unit implements and evaluates a numerical
reference for the continuous CAVAA candidate. It does not admit a contribution
module. The reference estimates uncertainty in computing the specified posterior;
that is separate from uncertainty about players, calibration against generated
truth, predictive validation and observational attribution.

## Frozen sequence and actual decisions

The [initial plan](RANDOMIZED_REFERENCE.md), committed as `5e1619c` before its
results, uses 32 independent scrambled Sobol replicates of 2,048 nodes each.
Each replicate retains unnormalized mass and mean/CDF integrals. Pool integrals
before division and use their across-replicate covariance in Student-t/Fieller
sets. Within-net points are dependent and do not supply iid standard errors.
Both numerator and normalizing-mass uncertainty remain in each signed contrast.

The two initial proposals both fail selection. All 1,024 trials finish; no
256-trial confirmation or NFL case follows that failed study. Precision passes
in zero trials for either method across all four fixtures. Some coverage gates
also fail. A single local mode misses important geometry; adding a prior-density
component alone does not solve the precision problem. All failures are retained.

The [density-adaptation plan](RANDOMIZED_REFERENCE_ADAPTATION.md), committed as
`9cc4424` before its results, learns a three-component Gaussian proposal from
4,096 separately randomized, target-density-only pilot points. A prior component
retains full support. Exact mixture-density corrections preserve the original
posterior; this changes where computation is spent, not the football model,
player intervals or benchmark. Known answers, CAVAA functionals and primary-QMC
samples are not used to fit this proposal.

That study finishes all 512 trials and also **fails**. The first three fixtures
pass; the tail fixture has joint coverage 120/128, with one-sided 95% lower bound
0.890057 below the required 0.90. Precision improves to 99.2–100% across fixtures.
No NFL case runs on that authorization. The failed result is not relabeled.

Failure analysis also exposes a weak original study design: at 128 trials, the
lower-bound gate requires at least 122 successes. Even at true joint coverage
0.95, its pass probability is only 0.540714. This does not establish that the
observed failure was random noise. It motivates a more informative fixed study.

The [confirmation plan](RANDOMIZED_REFERENCE_CONFIRMATION.md), committed as
`68a3d9c` before fresh trials, freezes **1,024 trials for every fixture** using
the identical, hash-verified sampling geometries and fresh entropy stage 5.
No geometry change, optional stopping, seed search or follow-on retry is allowed.
All original gates remain; an additional multiplicity-adjusted exact test checks
joint undercoverage at nominal 95%. No numerical or player interval is widened.

## Known-answer coverage result

All 4,096 confirmation trials finish, every deliberately wrong endpoint is
rejected, and all four complete gates pass. The table's intervals are two-sided
exact binomial 95% intervals for measured joint coverage. The prespecified gate
uses its separately recorded one-sided lower bound. A nonsignificant
undercoverage test does not prove exactly 95% coverage.

| Known target | Joint coverage | Binomial 95% interval | Precision pass fraction |
| --- | --- | --- | --- |
| Correlated mixture, 2 dimensions | 966/1,024 = 94.34% | 92.74–95.67% | 100% |
| Correlated mixture, 3 dimensions | 976/1,024 = 95.31% | 93.83–96.52% | 100% |
| Correlated mixture, 4 dimensions | 971/1,024 = 94.82% | 93.28–96.10% | 100% |
| Four-dimensional rare-tail mixture | 970/1,024 = 94.73% | 93.18–96.01% | 99.12% |

This is empirical evidence on four fixed diagnostic functions and fitted
proposals, not a finite-sample guarantee for arbitrary NFL integrands. Each
fixture checks seven mass/mean/CDF quantities. The NFL family is larger and uses
the unchanged Bonferroni multiplicity correction. Fresh randomizations on reused
known functions are not fresh football or uncertainty-calibration evidence.

The two earlier failed studies replay byte-for-byte with networking blocked.
The entire fixed confirmation independently rebuilds offline with identical
manifest and all five object files. Failed trials stay in denominators. Artifact
loading recomputes confidence sets, decisions, fixture answers and dimensions,
and rejects missing/duplicate trials, changed entropy and inconsistent flags.

## Five-case archived result and failure diagnosis

The passing fixed control certificate authorizes the unchanged five-case pilot,
produced at `274be4d91d076d22c1a9715e342a83fe781fec6a`. **One case passes; four
fail. All five finish**, without exhausting a solve/time budget or dropping a
partial replicate. Every primary-QMC stability check passes, but the independent
reference does not certify four of those calculations. The table gives maximum
point discrepancy plus numerical error; the QB row takes the worst over all
three prior settings and 171 benchmark contrasts.

| Case | Mean check, posterior SD | Endpoint-CDF check | Total target evaluations | Decision |
| --- | ---: | ---: | ---: | --- |
| Real QB | 0.030273 | 0.001951 | 75,270 | Fail |
| Real team control | 0.002388 | 0.000162 | 72,852 | Pass |
| Consumed prior draw 0 | 0.013089 | 0.003470 | 75,317 | Fail |
| Consumed hierarchy draw 0 | 0.062177 | 0.003384 | 75,415 | Fail |
| Consumed fixed-year draw 0 | 0.521997 | 0.029502 | 75,271 | Fail |

The limits remain **0.01 SD / 0.001 CDF**. These three consumed synthetic draws
are numerical stress cases, not fresh calibration. No additional primary samples,
changed seeds or looser limits were tried after these results. The fixed-year
failure is severe, not a near-pass. Runtime for the five cases is about 20.4
minutes per build on this machine with the two builds running concurrently;
per-case times are execution metadata in the audit, separate from numerical hashes.

`diagnose_reference` recomputes saved confidence sets and decisions from every
raw replicate before decomposing the failure. Its regression checks corruption,
functional order and the distinction between large point discrepancy and large
numerical error. The declared shift order is primary, negative shift, positive
shift; sorted JSON dictionary order is not the integrand's column order.

At the worst real QB mean check, the point discrepancy is **0.005394 SD** and
numerical error is **0.024879 SD**, totaling 0.030273 SD. All QB point mean/CDF
comparisons themselves fall inside their limits. The fixed-year case instead has
point mean discrepancy as large as 0.053479 SD, but numerical error reaches
0.468518 SD. In every case, no approximate reference confidence set lies wholly
beyond the tolerance region. Thus the failed comparisons are inconclusive; they
neither verify the primary calculation nor establish its bias. The known-answer
study does not guarantee coverage on these different, difficult NFL integrands.

The density-learning evidence suggests a specific efficiency problem:

| Case | Density pilot effective samples / 4,096 | Selected fit hits covariance floor? |
| --- | ---: | --- |
| Real QB | 187.6 | Yes |
| Real team | 595.1 | No |
| Prior stress | 128.9 | Yes |
| Hierarchy stress | 5.8 | Yes; all three starts reach iteration cap |
| Fixed-year stress | 9.5 | Yes |

The collapsed directions have covariance eigenvalues near 1.5e-6 after the
predeclared 1.5 sampling inflation. Fitting a flexible proposal to a few heavily
weighted pilot points can overfit those points and leave poor sampling coverage
elsewhere. These observations motivate that hypothesis; they do not prove the
causal explanation or justify selecting new settings from these NFL outcomes.
Covariance clipping affects only the proposal. Exact target-density corrections
and the prior component preserve full support; this does not repair high variance.
The plan did not require mixture-fit convergence, and a nonconverged proposal
alone does not bias importance integration. Its observed precision still fails.

**Decision:** retain the method's passing known-answer result and team control,
but do not authorize calibration or admit QB CAVAA. Freeze one density-only
holdout comparison of the current versus a justified stabilized proposal, with
independent pilot/validation randomizations and known-answer coverage/precision
checks before another archived pilot. Include a justified curved-density control
if its answers can be independently verified; the present four fixtures do not
cover arbitrary posterior geometry. No broad search over methods, seed retries,
automatic primary-sample escalation, changed football priors or wider intervals.
The 192-fit calibration, prospective prediction and observational admission remain
subsequent, separate milestones.

## Reproducibility and unchanged scoring contract

The ordinary and network-disabled pilot builds produce **identical manifest,
model and prediction bytes**. Report ID:
`eee8529ba317ca804e7702fd43aadd2989f1fac16065a6821774f28f6f5199e0`.
The report retains all replicate integrals, uncertainty sets, prior shifts, work
counts and failure decisions. Model/result bytes differ from the preceding sparse
reference only in numerical-validity flags for the now-passing team control.
Removing only that named field yields exact equality, including all point
estimates, intervals, benchmark weights, qualification and season/play ledgers.

The archive remains 57 QBs / 122 completed 2026 games / 8,996 QB dropbacks, with
48,776 training dropbacks across 2024–26. Historical training adds no 2026 points.
There are 37 first-unit benchmark members and 57 in each sensitivity population;
38 first-unit season estimates are negative. Maximum modeled-play accounting
error remains 8.88e-16 EP. This partial dropback model excludes 12 observed non-QB
dropbacks and does not measure designed rushing; no broader contribution claim is
made. Eligibility remains independent of all benchmark populations.

The game cohort closes at `2026-11-08T01:41:17.891273Z`; evidence closes at
`2026-11-08T02:47:32.067979Z`. No new NFL downloads or Week 10 outcomes are used.
Retrospective roster evidence is not proof of pregame availability. The season
ledger allocates a season-level effect over observed opportunities, not causal
play rewards or a time-varying skill model. QB/team allocation still depends on
explicit hierarchical assumptions and coarse team context.

The required defensive information-loss study and Defense Explorer remain intact;
no defensive admission or cross-position comparability pass is claimed. All 17
modules remain unavailable. Participation, player calibration, fresh prediction,
leaderboard/history and hosted Explorer activation stay on the
[milestone backlog](MILESTONES.md). No automation, service, dependency or other
repository changes. [PR #26](https://github.com/AryanParte/nfl-player-value/pull/26)
contains the implementation, frozen decisions and this report.

## Software verification and remaining limits

Local `make PYTHON=.venv/bin/python check` passes 432 Python tests, 27 frontend
contracts, Ruff/adopted formatting, TypeScript/build, compilation and whitespace.
The [pilot source](https://github.com/AryanParte/nfl-player-value/actions/runs/43343841827)
and [failure-analysis source](https://github.com/AryanParte/nfl-player-value/actions/runs/43346161411)
pass hosted Python 3.11/3.12/3.13 and dashboard/Chromium. Final-head checks are
reported on PR #26. The existing workflows and dependencies are preserved.
Full statistical studies stay outside ordinary offline PR CI.

Exact reconstruction is demonstrated on this machine and pinned numerical
environment, not guaranteed across hardware/BLAS implementations. The archived
pilot is built at the clean producing revision; the later diagnostic adds no new
integration and recomputes all retained numerical evidence. Software verification,
empirical numerical coverage, player calibration and football attribution remain
separate findings. No part of this study constitutes an admitted scoring module.

## Artifact identity

Full raw replicate evidence remains in ignored, content-addressed local stores.
The audit records compact decisions and hashes, not a replacement for those
artifacts. Durable remote retention of these research stores remains unfinished.

| Study | Producing source | Report ID |
| --- | --- | --- |
| Initial proposals | `1171b1db4f7b5afbab758c9f055d00f201650f6a` | `0477148ccfea35276838997962c6a9b78ac4bef8204cbf1cc8b40f932681a6b7` |
| Density adaptation | `954fd05371c20f8e314b5fda7bc8f6ea5beebf52` | `a3ec189abc21fc3d42c1319ab3df74dbcd9ec4f1168a2bb520192c373ecc96cc` |
| Fixed confirmation | `ddf3f032d63027257a1fa0702ed9f88a4bf141c9` | `ec5841475d642c8461b821d0fb3219e21463c6443f3b4a9181693d1ba1bc001f` |

Self-review subsequently binds saved fixture answers to independently recomputed
truth (`274be4d`); this integrity correction changes no numerical study outputs.
The first offline harness failed before computation because it replaced the
socket class before SSL imported it. Importing the CLI first, then blocking
socket creation and DNS, fixes the harness; the successful replay evidence comes
from that corrected harness, not the failed attempt.

## Reproduction

Use the producing source revision and pinned NumPy/SciPy environment. Known-answer
studies require no downloaded NFL data and run outside ordinary fast PR CI:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.randomized_cli build
PYTHONPATH=src .venv/bin/python -m nfl_value.randomized_cli --output-store data/derived/randomized-controls-adaptive build --plan config/randomized-reference-adaptive-v1.json
PYTHONPATH=src .venv/bin/python -m nfl_value.randomized_cli --output-store data/derived/randomized-controls-confirmation build --plan config/randomized-reference-confirmation-v1.json
PYTHONPATH=src .venv/bin/python -m nfl_value.randomized_cli --output-store data/derived/randomized-controls-confirmation replay ec5841475d642c8461b821d0fb3219e21463c6443f3b4a9181693d1ba1bc001f
PYTHONPATH=src .venv/bin/python -m nfl_value.randomized_pilot --controls-store data/derived/randomized-controls-confirmation build ec5841475d642c8461b821d0fb3219e21463c6443f3b4a9181693d1ba1bc001f
```

The archived pilot requires the exact existing raw/input/multiseason/continuous
stores. A failed control certificate is rejected before loading those inputs.
Build commands require a clean committed tree. Later source revisions produce
different manifests even when numerical study bytes match. Keep one BLAS thread
for the bounded pilot, as in the recorded runs.
