# Multi-season recovery decision — November 8, 2026

**The contribution module remains research-only.** Variance integration is
implemented and numerically verified, but the finite grid does not provide
nominal 95% coverage under the declared off-grid cases. Historical links do not
remove consequential QB/team allocation assumptions. There is no new predictive
pass or admitted CAVAA leaderboard. This is a completed recovery experiment and
failure diagnosis, not a completed scoring milestone.

The [original plan](MULTISEASON.md) was committed in `4591cc7` before fitting.
The [additional control](MULTISEASON_CONTROL.md) was committed in `95d9b8c` after
the first results and before its fresh draws. The [audit](audits/2026-11-08-multiseason.json)
contains full model/control reports, source hashes, settings, provenance, numerical
results and the non-admission decision. No consumed predictive test was retuned.

## Implemented scope and actual estimates

Four frozen alternatives use **48,776 verified dropbacks across 666 games**:
20,072 in 2024, 19,708 in 2025 and 8,996 in the archived 2026 cohort. The primary
shares information across years while allowing QB-year and team-year changes.
The constant-QB, team-only and QB-without-offensive-team controls remain explicit.
Game effects are integrated analytically. A finite prior integrates variance and
residual-scale uncertainty; mixture quantiles include shared benchmark covariance.

Only **122 completed 2026 games / 57 QBs** contribute season points. The archive
ends November 7 at 20:41:17 Eastern, includes part of Week 9, and is not live
November 8 coverage. No older-season opportunities enter the total. Every archived
completed game is represented; 12 non-QB dropbacks are explicitly outside this
module, and designed runs/other plays retain their separate scope.

Research first-unit estimates range **−37.44 to +29.89 EP**; 38 are negative.
The player, benchmark, context/team/game and unexplained components reconstruct
outcomes to 8.88e-16 EP. That proves arithmetic, not attribution. The constant-QB
alternative changes a current-season contrast by up to **25.54 EP**; the
confounded QB-proxy control by 4.47 EP. Equal-player and opportunity-weighted
benchmark changes reach **8.81 and 2.99 EP**. They are meaningful sensitivity
results, not permission to choose the benchmark that favors a particular player.

All model/benchmark members remain independent of qualification. The prior narrow
exposure diagnostic still proves denominators for **23/57 QBs**; 34 remain
unresolved, not proven ineligible. General missed games/stints and position
admission are unfinished. No qualification or registry policy changed.

## Calibration and failure diagnosis

Each row uses 128 new draws, fixed before its outcomes. Monte Carlo SE uses
independent replicate coverage fractions, not 7,296 independent player trials.
These are fixed-design simulations, not actual NFL interval-error estimates.

| Generator | Integrated coverage (MCSE) | Modal-cell coverage | Mean integrated width, EP |
| --- | ---: | ---: | ---: |
| Declared finite hierarchy | 95.13% (0.42 pp) | 90.93% | 65.01 |
| Off-grid continuous hierarchy | 90.78% (0.39 pp) | 90.86% | 77.76 |
| Fixed year changes / shared game noise | 92.06% (0.26 pp) | 92.05% | 93.13 |

Integration helps when the generating distribution matches the declared finite
prior, but not generally off-grid. This is a within-experiment comparison;
November 7 used different generators, so its coverage percentages are not a
controlled before/after comparison. Absence of the old severe-undercoverage flag
is **not** a 95% calibration pass. Fixed-year player bias also remains material
(mean absolute player bias 17.28 EP).

In the fixed-year generator, the independent and shared residual variances are
equal, equivalent to a game precision ratio of 1. The finite prior starts at 4,
and the fitted game component puts all mass at that lower edge. This identifies
an explicit support mismatch in addition to coarse spacing; it is not corrected
after inspecting these draws. A future variance candidate must define its support
and accuracy checks before new experiments.

The additional control used a new seed and the same continuous-hierarchy design:

| Fresh control | Coverage (MCSE) | Width, EP | RMSE, EP |
| --- | ---: | ---: | ---: |
| Unchanged integrated candidate | 89.56% (0.40 pp) | 77.29 | 31.29 |
| Known true variance ratios | 94.34% (0.25 pp) | 86.59 | 27.43 |
| Known ratios, but forced shared QB/innovation variance | 96.63% (0.19 pp) | 100.16 | 28.81 |

Known ratios improve paired coverage by **4.78 pp (MCSE 0.34 pp)**. This points to
variance estimation/support as a material problem. It does not prove every gap
is caused by grid resolution. Forcing shared innovation variance while knowing
the other ratios overcovers in this scenario, so that restriction alone does not
explain the observed undercoverage. Do not automatically add another variance
component or use the oracle's wider intervals for real players. The oracle uses
unavailable synthetic knowledge and is not a deployable fix.

Real QB precision puts 99.977% posterior mass on the single grid value 400.
Reweighting that grid's QB prior moves estimates by at most 0.018 EP. This small
number is **conditional on the same coarse support**, not evidence that the
hierarchy is broadly robust. Offensive-team and game components retain substantial
mass at the near-zero-variance edge. No grid was expanded after these results.

## Attribution and required defensive work

Persistent-QB historical links yield 8 QB/team-season components; adding seasonal
innovation produces 94. Full primary design rank is 893 of 1,191 columns. All 57
current first-unit contrasts depend on hierarchical assumptions; a 0.25 EP
QB-year/team shift preserves every fitted play while changing one season contrast
by **80.16 EP**. Even the constant-QB control permits a 76.53 EP witness. Null
directions diagnose allocation assumptions, not an automatic requirement for
causal identification or a standalone reason to reject an observational model.
Here they accompany unresolved calibration and no fresh predictive evidence.

The required defense diagnostic replays the paired 2025 cohort through Week 10:
**131 games / 15,803 plays / 895 defenders**, identical across both views.

| Defensive view | Rows | Residualized defender rank | Mass at strongest shrinkage |
| --- | ---: | ---: | ---: |
| Play lineups | 15,803 | 856 | 60.10% |
| Team-game means | 262 | 193 | 48.44% |

All 895 defender-minus-cohort-mean contrasts have unresolved null projections.
Prediction-preserving directions change contrasts by about 0.25 EP per appearance.
These are diagnostics, **not positional first-unit CAVAA**. The differing
observational units make cross-view marginal likelihood comparisons invalid.
No defensive uncertainty calibration, live workload availability or admission is
claimed. FTN/nflverse participation derivatives retain CC-BY-SA-4.0 attribution
in the audit; code licensing does not replace the data terms.

## Reproduction, verification and next decision

Use the existing pinned model/quality environment. No downloads occur in these
commands; the exact archived raw and derived stores must be available.

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.multiseason_cli build --inputs config/multiseason-inputs-v1.json
PYTHONPATH=src .venv/bin/python -m nfl_value.multiseason_cli replay 2e6708b65c30b2da606859aa14726228238082d887d05d76ed870606ef7180e6
PYTHONPATH=src .venv/bin/python -m nfl_value.multiseason_control build
PYTHONPATH=src .venv/bin/python -m nfl_value.multiseason_control replay dd3a1aa77d45cb1b59949154a63c9fbd954cc9665e10aa897e063eeb599a8a70
```

The primary producer is `015319bc6e404502e73d25beba5ce53eb500ed6e`; control producer
is `169a0bd` (full revision in the audit). Final replay/CI outcomes are recorded
in the [learning report](learning/2026-11-08.md). Source/output hashes and exact
structure plus 1e-9 absolute / 1e-8 relative numerical checks bind replay.
Large common log-likelihood offsets initially failed strict weight normalization;
max-subtraction followed by explicit division fixes roundoff without relaxing the
check. Independent observation-space and augmented-game references verify the
likelihood, means and covariance. Final self-review also added corrupted-model
rejection and timezone-aware training cutoff comparison for future predictions.

Next, preregister **one** bounded continuous-variance integration candidate with
numerical accuracy checks, fresh simulation seeds and explicit prior sensitivity.
Retain the team control and the current frozen models. Do not add independent
innovation variance merely to force coverage; the new control does not establish
that it is the first fix. Keep **2026 Week 10** untouched for the locked prospective
comparison; once complete, use the same rows for every declared alternative.
Prediction still cannot establish correct player attribution. Admit only after
a documented observational-estimand review and defensible uncertainty evidence.

Defense needs credible live workload/position evidence and calibrated allocation,
not a coefficient rescaling. The Explorer continues to show unsupported values
as unavailable. Pages activation is still outstanding, and research archives are
local rather than durably published. Neither is a reason to substitute optional
infrastructure work for the scoring milestone.
