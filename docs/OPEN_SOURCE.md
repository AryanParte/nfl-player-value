# Open-source audit and reuse decisions

Read-only audit completed October 18, 2026: repository metadata, actual source, documentation, manifests, and license files were inspected for the projects below. The research audit did not install or execute these repositories. Inspection is not a claim of compatibility with every 2026 input or a substitute for project-specific tests.

## Preferred building blocks

| Project | Audit findings | Proposed use |
| --- | --- | --- |
| [nflreadpy](https://github.com/nflverse/nflreadpy) | MIT; active October 2026; Python, Polars, Requests, Pydantic. Inspected loaders and integration tests; many test fixtures use historical seasons. | Python data access, wrapped in our own immutable provenance and 2026 coverage checks. Participation loader restrictions reinforce that current live all-22 coverage is unavailable. |
| [nflfastR](https://github.com/nflverse/nflfastR) / [fastrmodels](https://github.com/nflverse/fastrmodels) | MIT license files verified; maintained R outcome-model and statistics ecosystem. Inspected EP calculation and player-stat code. | Consume versioned published EPA initially. Record upstream model provenance; an R runtime need not be in the first Python pipeline. Outcome-model validation does not validate our allocation to players. |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | BSD-3-Clause; active; inspected ridge implementations and solver/convergence tests. NumPy/SciPy stack. | Transparent sparse regularized baseline and reproducible comparisons. No built-in NFL attribution validity. |
| [PyMC](https://github.com/pymc-devs/pymc) | Apache-2.0 with incorporated license notices; inspected dependency manifest and sampler implementation. Audited current branch required Python 3.12+ and tightly bounded PyTensor/ArviZ versions. | Candidate hierarchical modeling after a baseline; pin a compatible stable dependency set and measure runtime. Do not blindly install repository HEAD. |
| [ArviZ](https://github.com/arviz-devs/arviz) | Apache-2.0; inspected modular package/migration structure and tests. Active ecosystem changes require compatibility checks. | Posterior diagnostics and uncertainty analysis when the Bayesian stage is justified. Diagnostics do not establish causal identification. |
| [Recharts](https://github.com/recharts/recharts) | MIT; React/TypeScript; inspected error-bar implementation and tests. Audited HEAD was a canary version. | Stable pinned release for original leaderboard/history/uncertainty views, including asymmetric intervals. |

The audited commits included `nflreadpy@e7e87b2`, `nflfastR@701bbf3`, `fastrmodels@75c7b68`, `scikit-learn@d1b6d43`, `pymc@91e6da3`, `arviz@7d8d555`, and `recharts@b81ad8e`. These identify the research inspection, not the final dependency lock. Production versions require installation and smoke tests before adoption.

## Research references with substantial adaptation required

| Project | Actual limitations found | Decision |
| --- | --- | --- |
| [ryurko/nflWAR](https://github.com/ryurko/nflWAR) | Last pushed 2018; R/lme4; original 2009–17 data and legacy nflscrapR ingestion. DESCRIPTION contained a license placeholder, with no usable code license identified. Source includes individual points-above-average effects, but context choices can control player-created outcomes. | Use the [published methodology](https://arxiv.org/html/1802.00998v2) as research; independently implement the approved formulation. Do not copy unlicensed source. |
| [sabinanalytics/jqas-football-pm-public](https://github.com/sabinanalytics/jqas-football-pm-public) | Last pushed 2020; RStan/Matrix; private Oracle/PFF dependencies, exactly-22-player preparation, and a referenced missing fit script. No license identified. | Study participation-based hierarchical plus-minus; independent implementation and the information-loss experiment are still required. |
| [sabinanalytics/football-plus-minus](https://github.com/sabinanalytics/football-plus-minus) | Historical 2008–19 work; no license identified; documented descriptive/predictive and run/pass confounding issues. | Research comparison only. |
| [ryurko/nfl-ghosts](https://github.com/ryurko/nfl-ghosts) | GPL-3.0; R/Python conditional-density tracking work, leave-one-week-out code; tracking data not included and competition terms apply. | Later tracking research. Not a public live 2026 feed or a complete player-value engine. Review derivative distribution obligations before any code reuse. |
| [nflplotR](https://github.com/nflverse/nflplotR) | MIT; maintained R graphics tooling. Image rights are separate. | Optional offline research figures; not an additional frontend runtime. |

## Approaches not adopted

- [nfl_data_py](https://github.com/nflverse/nfl_data_py) is deprecated/archived in favor of nflreadpy. New ingestion should not depend on it.
- [elifloss/nfl-war-dashboard](https://github.com/elifloss/nfl-war-dashboard) has an MIT license but its inspected implementation uses fixed position weights, weighted standardized statistics, a percentile replacement rule, and hardcoded historical seasons. Its Streamlit/older-data stack and metric do not implement this project's CAVAA estimand.
- [alannguyen67/nfl-qb-intelligence](https://github.com/alannguyen67/nfl-qb-intelligence) has a dashboard example but no identified reuse license, manually weighted ratings, recency modifiers, and historical 2024–25 inputs. It is not an attribution implementation to adopt.
- [getstrained/intro-strain](https://github.com/getstrained/intro-strain) offers historical tracking/pressure research with private matchup dependencies and no identified reuse license. It is not a production value model.
- [edwinbudding/WAR_Project](https://github.com/edwinbudding/WAR_Project) relies on premium PFF inputs, fixed activity weights, local paths, and no identified reuse license. It does not remove our data or validation problem.

Open code is not automatically licensed code, and an open implementation may still require inaccessible data. Do not copy unsupported weighting systems simply because they produce a leaderboard.

## Existing project patterns to reuse independently

The user's [NFL Opponent Intelligence repository](https://github.com/AryanParte/nfl-opponent-intelligence) demonstrates content-addressed snapshots, source metadata, atomic publication, offline replay, explicit exclusions, and tested data contracts. These engineering patterns fit this project. Its audited ingestion was constrained to 2024 and its analytics were not an individual-player attribution model, so it is not a drop-in implementation.

Keep this repository, local clone, environments, branches, caches, and automation independent. Do not modify the existing project or its schedule. The new project still needs 2026 contracts, first-unit membership, attribution models, defensive experiments, weekly ranking history, and its own product interface.
