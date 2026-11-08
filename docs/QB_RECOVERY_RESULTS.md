# QB recovery decision — November 7, 2026

**Decision: do not admit the QB dropback module.** This run implemented and ran a
bounded model recovery study, not another infrastructure milestone. It produced
reproducible cumulative 2026 research contrasts for 57 QBs in all 122 completed
games / 244 team games (8,996 roster-verified dropbacks). A usable CAVAA ranking
remains unfinished. [The audit](audits/2026-11-07-qb-recovery.json) records exact
sources, revisions, plans, results and verification; [the preregistration](QB_RECOVERY.md)
separates the initial experiment from its subsequent diagnostic control.

## What changed scientifically

The old all-role model conditioned on realized target availability and used a
strong shared player penalty. Target availability can reflect QB-created sacks
and throwaways, making it inappropriate as a QB hardship control. The new module
uses preplay context plus separate QB, offensive-team, defensive-team and game
effects. Restricted likelihood (REML) estimates their variance components from
training observations. No receiver IDs, target-observation flags, pressure or
other postplay outcomes are context controls. Designed runs and non-QB dropbacks
remain outside this module, with explicit exclusion counts.

Four declared alternatives were evaluated: team/context, a deliberately confounded
QB proxy without offensive-team effects, the primary joint model, and a fixed
strong-shrinkage control on the same design. Neither the QB proxy nor a favorable
predictive result can establish individual attribution. No real-season candidate
was selected or tuned on the newly revealed tests.

## Prediction did not establish an increment

Differences below are joint-model RMSE minus team-model RMSE, in EPA per play;
negative favors the joint model. Intervals resample games, not individual plays.

| Held-out window | Games / dropbacks | Difference | Paired 95% interval |
| --- | ---: | ---: | --- |
| 2024 weeks 11–14; fit through 10 | 56 / 4,258 | −0.000308 | [−0.001041, 0.000385] |
| 2024 weeks 15–18; refit through 14 | 64 / 4,759 | −0.000171 | [−0.000992, 0.000631] |
| Archived 2026 weeks 7+; fit through 6 | 29 / 1,994 | −0.000115 | [−0.002394, 0.002418] |

All intervals cross zero. The fixed-shrinkage and QB-proxy alternatives also fail
to show a reliable advantage. This does not show that QBs have no value: team
indicators already absorb much of the QB/team signal. It does mean this experiment
has not supplied the declared predictive evidence for separating them.
The 2024 windows are retrospective development evidence, and the 2026 sources were
already used in Explorer. Neither is described as a prospective historical-vintage
test. All three windows are now consumed and cannot become tuning targets.

## Calibration improved, but remains insufficient

Each row uses 128 fresh known-effect simulations on the actual 2026 design,
reestimating the primary variance components every time. These are tests of model
assumptions, not measured NFL coverage. Monte Carlo error uses independent trials,
not the correlated player cells within each trial.

| Truth scenario | REML conditional coverage (MC SE) | Fixed-shrinkage coverage |
| --- | ---: | ---: |
| Gaussian effects from declared hierarchy | 87.09% (1.22 pp) | 29.13% |
| Fixed QB/team signals, independent errors | 94.50% (0.48 pp) | 0.00% |
| Fixed signals, half the error variance shared within game | 93.79% (0.96 pp) | 0.00% |

All fits converged. The hierarchy scenario still triggers the frozen severe
undercoverage flag. Fixed-signal performance is a substantial improvement over
the old strong-shrinkage behavior, but two improved scenarios cannot establish
general 95% calibration. Boundary variance estimates were common: for example,
the offensive-team variance reached its lower boundary in 31/128 hierarchy trials.

A separately preregistered failure-analysis control used **128 new draws**:
conditional empirical Bayes covered 88.32% (MC SE 0.89 pp), while an oracle given
the simulation's true variances covered 95.00% (0.23 pp). The oracle changes both
shrinkage and covariance; it does not isolate interval-width estimation alone.
The result supports variance estimation/boundary behavior as a material cause,
and checks the simulation's algebraic target. Real variances are unknown. No
oracle interval, fitted width multiplier or relaxed gate is used for real players.
The second empirical-Bayes run narrowly avoids the severe-failure flag; that flag
is a rejection diagnostic, **not** a certificate of 95% coverage.

## What the season ledger does and does not identify

All 57 observed QBs receive research contrasts against the complete first-unit
benchmark and both sensitivities, including one-opportunity players. The first-unit
range is −49.09 to +32.19 EP, with 36 negative estimates. Changing to equal-player
or opportunity-weighted averages changes an individual total by up to 4.85 or
2.10 EP. These ranges are research diagnostics, not a public ranking.

Every completed game remains in the ledger. The season-constant coefficient is a
season estimate fitted from all those games, not a current-form estimate applied
backward. Per-game allocations are opportunity counts times that season contrast;
they are **not** recovered game-specific skill changes. Context, team, game,
benchmark and unexplained outcomes stay separate. Rebasing the QB component
against the benchmark conserves observed EPA to less than 9e−16 per play. This
module cannot be added to an overlapping full-play receiving/other-actor score.

The unrestricted design has rank 194 across 260 columns; all 57 first-unit
contrasts project into its null space. A concrete ARI example increases both
observed QB coefficients by 0.25 EP/dropback and decreases its offensive-team
coefficient by 0.25: every play prediction is unchanged, but a season contrast
changes by **80.16 EP**. This is an algebraic identification example, not a confidence
interval or an assertion about those players. Halving/doubling the fitted QB
variance also changes real contrasts by up to 13.97/12.30 EP. The season fit places
offensive-team variance at its lower bound, making its allocation close to the
explicitly confounded QB-proxy control.

For an observational hierarchical estimand, a null direction alone is not a demand
for impossible causal identification or grounds to reject every random-effects
model. Such models require exchangeability/variance assumptions that select an
allocation. Here, inconclusive prediction, undercoverage and consequential
allocation sensitivity together leave those assumptions insufficiently supported.
We did not change admission requirements after observing these failures.

The existing narrow full-QB participation diagnostic proves denominators for 23/57;
all 23 pass the three provisional opportunity grids. For 32 others, participation
is not positively observed in every team game; two lack a single-team window.
These are missing-evidence reasons, not proof of ineligibility. None qualifies for
the main leaderboard because attribution/comparability remain unvalidated. The
partial dropback module does not replace the existing full-QB threshold definition,
and qualification never removes a benchmark member or a modeling observation.

## Next decision, not another penalty search

The next bounded scoring unit should test whether **historical QB/team transitions
supply enough independent information**, then fit a multi-season QB/team-season
candidate with uncertainty over variance components. Freeze the historical folds,
assumptions, alternative and calibration tests before fitting; reserve a genuinely
uninspected future 2026 game window for final evidence. Use the current results as
development/failure evidence only. Compare with the team baseline, retain the
explicit QB-proxy control, and include fixed-signal and hierarchy calibration.
If transitions still cannot support the first-unit contrast, document the missing
information instead of forcing positive admission. Complexity must earn its place
through calibrated, stable estimates, not an improved test score alone.

In that unit, apply the existing-design variance/identifiability diagnosis to the
required rich/degraded defensive workstream. The historical information-loss
experiment and Defense Explorer remain delivered; no defensive player value is
admitted. The six [product milestones](MILESTONES.md) remain the backlog, and the
cross-position objective remains unchanged.

## Reproduction and operational state

The canonical clone retains the exact source/derived objects. The original fit is
`f53411d6685ddc9eced484db196fca69dc4aef2f0524273c736f933ec3eb254c`; the diagnostic
control is `4b1fe26e4b42fa940e5a2c0da0041d6d107874dee7b3bd891addcdd9b0b89308`.
Use the pinned NumPy/SciPy environment and recorded code revisions:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.qb_recovery_cli replay f53411d6685ddc9eced484db196fca69dc4aef2f0524273c736f933ec3eb254c
PYTHONPATH=src .venv/bin/python -m nfl_value.qb_variance_control --parent-report f53411d6685ddc9eced484db196fca69dc4aef2f0524273c736f933ec3eb254c --replay 4b1fe26e4b42fa940e5a2c0da0041d6d107874dee7b3bd891addcdd9b0b89308
```

The control command also fully replays the parent study. Source hashes, numerical
outputs, optimizer results and simulation outputs are compared; HTTP is blocked
in the recorded local replay. A fresh mutable download is not a substitute for
these archived bytes. Research stores remain local; durable off-machine retention
of these new research objects is still unfinished. The separate production
Explorer retention implementation does not automatically cover them.

PRs #18/#19 are owner-merged and their merged main CI passed. No production refresh
run was observed; Pages returns “Site not found,” and the browser is signed out.
The connector has no new-workflow dispatch/Pages configuration capability. There
is no observed release failure to repair yet; authenticated Pages setup and one
manual bootstrap remain necessary. This access blocker did not stop modeling.
The existing development automation's prompt now emphasizes the scoring critical
path, substantive units and milestone evidence; its identity, ACTIVE status and
7:30 PM America/New_York recurrence were preserved exactly. No new runtime package,
paid service, other repository change or scheduling change was introduced.
