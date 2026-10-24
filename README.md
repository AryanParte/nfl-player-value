# NFL Player Value

An independent research and software project for estimating **Context-Adjusted Value Above Average (CAVAA)**: a player's cumulative expected-point contribution beyond an ordinary first-unit player at the same position, under comparable observed circumstances.

The target is a usable 2026 season-to-date leaderboard and interactive website by **November 7, 2026**. Week 10 rankings follow completion of those games and availability of the required data; November 7 is not a promise of Week 10 results.

## Current status

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
historical diagnostic, not verified live-2026 attribution. **No real CAVAA ranking
is produced yet.** Roster/stint and position verification, broader defensive
validation, Defense Explorer, player uncertainty and the dashboard remain open. The 2026 first-unit chart audit still has 11 blocked IDL/CB/S/LS
issues. Synthetic tests are not football findings. See [offensive inputs](docs/OFFENSIVE_INPUTS.md)
and [defensive inputs](docs/DEFENSE_INPUTS.md).

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
| [Evaluation](docs/EVALUATION.md) | Predictive and attribution checks, sensitivity, and admission criteria |
| [Defense experiment](docs/DEFENSE_EXPERIMENT.md) | Required defensive research design and explorer scope |
| [Defensive inputs](docs/DEFENSE_INPUTS.md) | FTN provenance, whole-game cohort policy, paired views and offline replay |
| [Offensive inputs](docs/OFFENSIVE_INPUTS.md) | Unique play outcomes, actor links, opportunity unions and missingness |
| [Defensive model comparison](docs/DEFENSE_MODEL.md) | Frozen paired-view fits, aggregation/rank loss, selection audit and numerical replay |
| [Baseline experiment](docs/BASELINE.md) | Frozen splits, regularized fitting, role ablation, outcome accounting and numerical replay |
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

## Run the checks

Use Python 3.11–3.13. Ingestion/contracts use the standard library; modeling uses
the pinned NumPy/SciPy extra. Keep the environment inside this repository.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[model]'
make check PYTHON=.venv/bin/python
```

This runs 171 offline tests, compiles the Python sources, and checks whitespace.
Tests cover the data/benchmark/qualification contracts, locking, known-effect and
collinearity simulations, leakage, numerical solving and accounting. Real historical
evaluation is separate from synthetic CI evidence; see the [offensive audit](docs/audits/2026-10-23-offensive-baseline.json)
and [defensive audit](docs/audits/2026-10-24-defensive-model.json).

## Delivery and cost constraints

The canonical repository is [AryanParte/nfl-player-value](https://github.com/AryanParte/nfl-player-value). Development uses feature branches and reviewable pull requests; automated development must not merge into `main`.

The planned product uses offline Python computation and a React/TypeScript static dashboard consuming immutable JSON snapshots. No application server or database is required initially. Public data and free hosting are the default; no paid datasets, services, or purchases are authorized. Recurring operating cost must remain below $100/month, preferably near zero.

The authorized daily development schedule is **7:30 PM America/New_York**, independent of the existing NFL Opponent Intelligence project. Production data refreshes must run independently of that development automation. See the [daily workflow](docs/DAILY_WORKFLOW.md) and [project status](STATUS.md).
