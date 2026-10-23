# Required defensive workstream

October 19 inventory check: the public participation release contains 2016–2025
assets and no 2026 asset. The 2025 CSV candidate is asset `353763509`, 49,094,943
bytes, updated `2026-02-10T18:54:08Z`, SHA-256
`59069adfee7b0f464befba8a5e8be331e523633cc6a7ab403d37bcbcdfbe66ac`.
This is verified release metadata, not a completed row-level audit or experiment.
The [participation loader documentation](https://nflreadr.nflverse.com/reference/load_participation.html)
specifies post-season availability from 2023 and CC-BY-SA-4.0 attribution to
FTN Data via nflverse. Its source-specific terms override the ordinary archive
license. At that inventory date the dedicated adapter was not yet implemented.

October 20 implementation: formation-aware defensive first-unit chart inputs now
exist. The live 186-team-game audit flags six PHI IDL identity failures and four
DAL CB/S ambiguity issues. Complete EDGE/LB chart cells still do not establish
defensive attribution or play-level participation. The information-loss experiment
has **not run**; its dedicated historical ingestion and join audit are the next
priority, not replaced by depth-chart mapping. See [the input audit](audits/2026-10-20-pregame-inputs.json).

October 21 implementation: the dedicated adapter and [paired-input builder](DEFENSE_INPUTS.md)
now work. The [2025 audit](audits/2026-10-21-defense-inputs.json) archives 45,184
participation rows and retains 29,059 plays from 241 games in both views. It
records all excluded games and deliberately labels reduced fractions as eligible
pass/run appearances, not official defensive snap fractions. The experiment's
**model fitting and comparison have not run**. Before fitting, correct/version the
completion rule's numeric-ID ordering assumption, assess whole-game selection
loss, verify positional identity crosswalks, and audit additional seasons for
held-out-season testing. Resolve a permitted live workload source and reproduce
its actual missingness before interpreting reduced-model results as live-2026
feasibility. Defense Explorer remains required and unimplemented.

October 22 correction: [completion v2](PREGAME_INPUTS.md) validates event clocks
instead of requiring the highest play ID to be the final marker. With identical
2025 receipts and cutoff, all 272 REG games now reconcile and the paired cohort
increases to 243 games / 29,297 plays. All 29 lineup exclusions remain; retained
team coverage ranges from 13 to 17 games. Legacy v1 still replays unchanged. See
[the controlled comparison](audits/2026-10-22-offensive-inputs.json). This resolves
the completion prerequisite, not the model comparison or selection-bias problem.

Defense is part of the product objective and the implementation roadmap. Public live 2026 data do not currently establish the same assignment-level coverage as historical tracking or full participation data. This workstream tests how much that loss prevents individual attribution.

## Research question

Can a model using the information genuinely available during the 2026 season recover useful individual defensive contribution estimates, and can those estimates be compared with admitted offensive CAVAA modules?

The central limitation is identification. Team-game snap counts tell us how much a defender played, not which players shared each snap, whom he covered, whether he drew a double team, or which assignment he executed. Hundreds of player effects can be weakly identified from only a few completed games per team.

## Historical information-loss experiment

1. Select historical seasons with permitted play-level participation and sufficient context. Record actual field coverage and joins; do not assume a source's headline date range guarantees usable coverage.
2. Fit a richer regularized/hierarchical defensive plus-minus model using player participation, opponent and preplay context, and a documented signed EPA target.
3. Degrade the same historical data to a live-2026-like view: player-game defensive snap fractions, permitted events, and opponent/context-adjusted team-game outcomes. Do not leak the rich lineup features into this reduced model.
4. Evaluate both models on chronological held-out games and seasons, including early-season weekly cutoffs.
5. Compare estimates and uncertainty, but treat the rich model as a reference—not ground truth. Add simulations with known effects, actual absence/replacement cases, and strong teammate-collinearity cases.
6. Measure dependence on historical priors, team effects, roster continuity, and benchmark definitions. Document when apparently precise effects are mainly assumptions.
7. Make and record a position/module admission decision before displaying an overall score.

Use the actual coverage of the current public feed as the degradation target. Historical end-of-season participation is not evidence that the same field is available live. Game snap fractions are not reconstructed all-22 lineups.

## Admission decision

An admitted defensive estimate must have a defined comparable counterfactual, an expected-points-prevented interpretation, explicit shared-value accounting, reliable source/identity coverage, and acceptable documented historical behavior. Meeting a minimum snap count or producing a model coefficient is insufficient.

If the reduced model cannot distinguish players beyond team and prior assumptions, keep its output exploratory or withhold individual scores. Do not turn sacks, tackles, pressures, and interceptions into an arbitrary weighted CAVAA composite. The universal leaderboard goal remains unfinished until comparability is supported.

## Defense Explorer

Deliver exploratory pages for IDL, EDGE, LB, CB, and S even if they do not enter the main leaderboard. Include only verified available measures:

- Snap workloads, games, team/opponent context, and observed event counts.
- Pressure or target measures only when the feed's rights, definition, and denominator are verified.
- Source freshness, missing fields, and uncertainty or association-only labels where relevant.
- Explicitly unmeasured effects: target deterrence, double teams, assignments, run fits, explosive-play prevention, and teammate benefits where supporting data are absent.

Pressure divided by all defensive snaps is not a pass-rush pressure rate. A cornerback with few recorded targets is not automatically excellent; missing coverage opportunity and assignment information matters. Missing events are not zero events.

The explorer must not supply decorative scores to fill unsupported leaderboard positions. Its job is to show what is observed and make the remaining attribution problem inspectable.

## Research foundations

[Sabin's football plus-minus work](https://ideas.repec.org/a/bpj/jqsprt/v17y2021i4p313-364n4.html) motivates participation-based models. Its [public research implementation](https://github.com/sabinanalytics/jqas-football-pm-public) includes private-data dependencies and no identified reuse license; implement approved mathematics independently rather than copying code.

[NFL Ghosts](https://arxiv.org/abs/2406.17220) illustrates tracking-based counterfactual research. It is a useful later direction, not a ready live 2026 all-position metric. The [nflverse participation documentation](https://nflreadr.nflverse.com/reference/load_participation.html) defines the critical live-versus-post-season data constraint.
