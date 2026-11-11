# NFL Player Value

An independent research and software project for estimating **Context-Adjusted Value Above Average (CAVAA)**: a player's cumulative expected-point contribution beyond an ordinary first-unit player at the same position, under comparable observed circumstances.

The **November 7, 2026** MVP target was missed. A defensibly validated season-to-date
leaderboard remains the objective. Completed software and research estimates do
not yet constitute an admitted player-value ranking.

## Current status

As of November 10, the [numerical-reference pilot](docs/VARIANCE_REFERENCE_RESULTS.md)
passes all five original sampler checks, but all five independent reference checks
fail. Exact work reuse retains measurable errors; both real models still fail
the reference requirements. Both versions reproduce byte-for-byte in independent
offline builds. This is numerical research, not fresh uncertainty calibration or
usable MVP scores. The same 57 QBs / 122 archived 2026 games retain all three benchmarks,
signed accounting and separate qualification. The data archive ends November 7.
**All 17 modules remain unadmitted.** Defense Explorer remains required; live
workloads and cross-position attribution are unfinished. Browser sign-in and Pages
activation remain blocked. See the [milestone backlog](docs/MILESTONES.md) and
[latest learning report](docs/learning/2026-11-10.md). Week 10 stays sealed.
The summaries below describe historical snapshots, not current source freshness.

Benchmark/qualification contracts, immutable source capture, pregame first-unit
selection and historical defensive research inputs are implemented. October 22
adds versioned clock-based completion evidence and a unique-play offensive ledger:
11,441 candidate plays from 93 completed 2026 games through Week 6. The corrected
2025 completion rule accepts all 272 REG games; the defensive lineup cohort
retains 243 games and 29,297 plays. Old reports replay under their original rules.

October 23 adds the first [fitted outcome baselines](docs/BASELINE.md) with frozen
chronological evaluation. Actor identity adds only a small gain beyond observed
role information; its 2025 test interval includes zero. This does not validate
individual attribution. October 24 adds the first [defensive model comparison](docs/DEFENSE_MODEL.md):
aggregation reduces residualized defender rank from 922 to 301 across 951 columns;
neither defender model reliably improves its team/context baseline. This is a
historical diagnostic, not verified live-2026 attribution.

October 25 adds the [Defense Explorer](docs/DEFENSE_EXPLORER.md) and an interactive
React/TypeScript dashboard: 518 observed players through Week 6, scoped event
counts, chart-role coverage, signed team EPA, missing measurements and source
cutoffs. [Run the local view](web/README.md). It is not deployed or a value ranking.

October 26 adds [weekly position/team evidence](docs/ROSTER_INPUTS.md): exact-week
source joins, explicit identity/position gaps, both-season offline replay and a
correction to exposure completion-time handling. It resolves source positions for
1,814 of 1,819 observed offensive player-game rows in the archived 2026 cohort;
weekly roster presence does not establish complete stints or missed games.

October 27 adds [positional contrast diagnostics](docs/CONTRASTS.md): the primary
and two sensitivity benchmarks, joint conditional uncertainty, six cumulative
windows and a narrow exposure/qualification study. Strong penalty sensitivity,
missing historical benchmark cells and selective exposure remain explicit.

October 28 adds [known-effect calibration](docs/CALIBRATION.md): 6,144 synthetic
response fits on the archived Week 6 designs, interval/bias diagnostics and exact
alias checks. Near-95% coverage under the model's own prior does not survive the
prespecified stronger-signal tests. This is a documented model limitation, not a
new ranking or a measurement of actual players' errors.

October 29 adds the [observed QB/target-mix transition audit](docs/TRANSITIONS.md):
unchanged model predictions, outcome-independent adjacent-game selection and
replay from verified archives. Sparse QB changes and unsupported comparisons
remain visible; no observed change is labeled a causal injury/absence effect.

November 2 records [formal module decisions](docs/ADMISSION.md) and an executable
admission prerequisite. All 17 role modules remain unadmitted. The registry binds
exact evidence and policy files, preserves participation/benchmark separation and
rejects unsupported score requests; it does not create a production publisher.

November 3 adds [dashboard module availability and static review bundles](docs/STATIC_REVIEW.md).
All 17 modules have inspectable scope, validation gaps and exact evidence links.
The local 1.19 MB archived view rebuilds byte-for-byte and works on desktop/mobile;
the November 2 review date does not change the Week 6 game cutoff. Deployment,
durable off-machine retention and independent refresh remain unfinished.

November 4 adds [verified Explorer recovery archives](docs/RECOVERY.md).
The exact source/derived dependency set, attribution and saved site ZIP can be
restored into a new directory with full offline replay before it becomes visible.
Remote upload remains blocked on release-upload access; local recovery is not yet
durable off-machine retention, a new game snapshot or a published ranking.

November 5 adds [source readiness and unpublished refresh candidates](docs/SOURCE_READINESS.md).
Four fresh sources reconcile 121 completed games through Week 8. The candidate
preserves prior games and records changed team-context rows, with frozen offline
replay and explicit stale-source failures. The staged site remains on Week 6;
no public pointer or player-value admission changed.

November 6 adds [portable Explorer launch packages](docs/LAUNCH_PACKAGE.md).
Isolated website builds preserve the staged site. A package binds the exact
candidate, saved website, fresh packaging check and current/prior replay inputs;
restoration verifies all of them before exposing the recovered directory.
This prepares an exploratory release; upload, deployment and scored rankings
remain unfinished.

November 7 adds the [independent Explorer refresh and publication workflow](docs/PRODUCTION_REFRESH.md).
It captures sources, tests the restored website, rechecks freshness, verifies an
independent release-asset download before exposing the archive, and requests Pages
deployment only after the gates pass. It preserves prior releases and never
publishes CAVAA scores. Activation and hosted end-to-end validation remain pending;
PRs #18 and #19 have since been merged by the owner. Hosted activation remains
unverified; an Explorer release would still not be an admitted CAVAA leaderboard.

**No real CAVAA ranking is produced yet.** Broader stint verification, defensive
validation, calibrated player uncertainty, attribution/admission, ranking/history
views and independent production publication remain open. Unsupported scores stay
missing. Synthetic tests are not football findings.

The all-position objective remains explicit. An unsupported position receives no invented score. A narrower published board must identify its supported scope; it cannot be presented as a validated ranking of every NFL player.

## The approved approach

- Measure cumulative 2026 value in expected points; retain earlier games and negative contributions.
- Use a first-unit positional benchmark, with equal-player and opportunity-weighted benchmarks as sensitivity checks.
- Begin with an additive regularized model; use hierarchical partial pooling and additional complexity only when validation supports them.
- Separate the model's observation population, benchmark population, and leaderboard qualification rules.
- Keep attribution uncertainty distinct from benchmark/model sensitivity and missing-data limitations.
- Maintain a required defensive workstream, including a historical information-loss experiment and a Defense Explorer.
- Compute rankings reproducibly. An LLM does not invent or numerically determine CAVAA scores.

CAVAA is an observational estimate conditional on measured context and opportunities. It is not proof of the outcome of substituting a player in a real game. Targets, pressure, protection, and teammate performance can partly result from the player himself; adjusting for them indiscriminately can remove his contribution.

## Project guide

| Document | Purpose |
| --- | --- |
| [Roadmap](ROADMAP.md) | Dated delivery plan and release gates |
| [Methodology](docs/METHODOLOGY.md) | Estimand, benchmarks, participation, and attribution rules |
| [Architecture](docs/ARCHITECTURE.md) | Offline Python pipeline, versioned outputs, and React dashboard |
| [Data sources](docs/DATA_SOURCES.md) | Coverage, freshness, provenance, and licensing constraints |
| [Ingestion](docs/INGESTION.md) | Exact-byte capture commands, offline replay, and failure behavior |
| [Pregame inputs](docs/PREGAME_INPUTS.md) | Completed-game evidence, formation-aware first-unit selection, and historical availability |
| [Weekly roster evidence](docs/ROSTER_INPUTS.md) | Exact-week position/team joins, missing observations, and remaining stint/eligibility limits |
| [Evaluation](docs/EVALUATION.md) | Predictive and attribution checks, sensitivity, and admission criteria |
| [Defense experiment](docs/DEFENSE_EXPERIMENT.md) | Required defensive research design and explorer scope |
| [Defensive inputs](docs/DEFENSE_INPUTS.md) | FTN provenance, whole-game cohort policy, paired views and offline replay |
| [Offensive inputs](docs/OFFENSIVE_INPUTS.md) | Unique play outcomes, actor links, opportunity unions and missingness |
| [Defense Explorer](docs/DEFENSE_EXPLORER.md) | Observed defensive evidence, immutable export and the initial dashboard |
| [Static review bundles](docs/STATIC_REVIEW.md) | All-position availability, pinned evidence, offline builds and archived-data limits |
| [Explorer recovery](docs/RECOVERY.md) | Exact retained inputs, attribution, verified restoration and remote-storage limits |
| [Source readiness](docs/SOURCE_READINESS.md) | Frozen source-age/coverage checks and unpublished Explorer refresh candidates |
| [Launch package](docs/LAUNCH_PACKAGE.md) | Isolated website builds, candidate-bound archives and verified portable restoration |
| [Production refresh](docs/PRODUCTION_REFRESH.md) | Main-only Explorer workflow, release retention, Pages gates and activation runbook |
| [Defensive model comparison](docs/DEFENSE_MODEL.md) | Frozen paired-view fits, aggregation/rank loss, selection audit and numerical replay |
| [Baseline experiment](docs/BASELINE.md) | Frozen splits, regularized fitting, role ablation, outcome accounting and numerical replay |
| [Positional contrasts](docs/CONTRASTS.md) | Benchmark accounting, joint conditional intervals, prefix isolation and narrow exposure diagnostics |
| [Calibration stress tests](docs/CALIBRATION.md) | Known-truth coverage, shrinkage bias, clustered noise, exact aliases and offline replay |
| [Multi-season recovery decision](docs/MULTISEASON_RESULTS.md) | Variance integration, new calibration/failure controls, historical links and defensive information loss |
| [Open-source audit](docs/OPEN_SOURCE.md) | Dependencies and research implementations considered |
| [Project status](STATUS.md) | Completed work, active limitations, and next task |
| [Daily workflow](docs/DAILY_WORKFLOW.md) | Independent development runs, locking, verification, and PR rules |
| [First learning report](docs/learning/2026-10-18.md) | Foundation decisions, statistical concepts, verification, and remaining work |
| [October 19 learning report](docs/learning/2026-10-19.md) | Live snapshots, source quality, and replay verification |
| [October 20 learning report](docs/learning/2026-10-20.md) | Receiver slot semantics, game completeness, and benchmark coverage |
| [October 21 learning report](docs/learning/2026-10-21.md) | Participation joins, controlled information loss, and selection bias |
| [October 22 learning report](docs/learning/2026-10-22.md) | Event ordering, preserved replay and offensive opportunity accounting |
| [October 23 learning report](docs/learning/2026-10-23.md) | First fitted models, shrinkage, role-selection confounding and held-out results |
| [October 24 learning report](docs/learning/2026-10-24.md) | Defensive information loss, weighted models, rank deficiency and admission limits |
| [October 25 learning report](docs/learning/2026-10-25.md) | Observed versus attributed value, the first dashboard and shared data contracts |
| [October 26 learning report](docs/learning/2026-10-26.md) | Retrospective roster evidence, exposure timing and real offline replay |
| [October 27 learning report](docs/learning/2026-10-27.md) | Positional contrasts, shared uncertainty, shrinkage sensitivity and selective exposure |
| [October 28 learning report](docs/learning/2026-10-28.md) | Prior-dependent coverage, sampling variance versus bias, and attribution stress tests |
| [October 29 learning report](docs/learning/2026-10-29.md) | Observed transitions, missing comparisons, target mix and limits of absence evidence |
| [November 2 learning report](docs/learning/2026-11-02.md) | Module admission, participation independence and evidence-bound release decisions |
| [November 3 learning report](docs/learning/2026-11-03.md) | Honest availability, integrity versus validity, deterministic review artifacts and independent UI failures |

## Run the checks

Use Python 3.11–3.13. Ingestion/contracts use the standard library; modeling uses
the pinned NumPy/SciPy extra. The dashboard requires Node 24. Keep both
environments inside this repository.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade 'pip==26.2.2'
.venv/bin/python -m pip install '.[model,quality]'
npm --prefix web ci --ignore-scripts --no-fund
make check PYTHON=.venv/bin/python
```

This runs the offline Python suite and frontend contract tests, checks Python
lint/adopted formatting and frontend formatting/TypeScript, builds the dashboard,
compiles Python and checks whitespace. See [CI and release gates](docs/CI.md) for
coverage reports, browser diagnostics and the optional manual dependency audit.
The separate [Chromium suite](web/README.md) verifies browser behavior and data/admission labels.
Tests cover the data/benchmark/qualification contracts, locking, known-effect and
collinearity simulations, leakage, numerical solving and accounting. Real historical
evaluation is separate from synthetic CI evidence; see the [offensive audit](docs/audits/2026-10-23-offensive-baseline.json)
and [defensive audit](docs/audits/2026-10-24-defensive-model.json).

## Delivery and cost constraints

The canonical repository is [AryanParte/nfl-player-value](https://github.com/AryanParte/nfl-player-value). Development uses feature branches and reviewable pull requests; automated development must not merge into `main`.

The planned product uses offline Python computation and a React/TypeScript static dashboard consuming immutable JSON snapshots. No application server or database is required initially. Public data and free hosting are the default; no paid datasets, services, or purchases are authorized. Recurring operating cost must remain below $100/month, preferably near zero.

The authorized daily development schedule is **7:30 PM America/New_York**, independent of the existing NFL Opponent Intelligence project. Production data refreshes must run independently of that development automation. See the [daily workflow](docs/DAILY_WORKFLOW.md) and [project status](STATUS.md).
