# CAVAA methodology specification

Approved research direction, October 18, 2026. This is the implementation contract, not a claim that the model has already been fitted or validated.

## Estimand and units

For player `i` and completed games through cutoff `W`, estimate:

```text
CAVAA_i(W) = sum over observed opportunities p of
             [predicted contribution with player i in context p
              - weighted mean prediction with first-unit peers in context p]
```

The unit is **cumulative expected points** during the 2026 regular season. Preseason and postseason games are outside the MVP ledger and its qualification/benchmark windows. Defensive benefit is expressed as points prevented. The benchmark shares the player's modeled role and comparable observed circumstances. In a nonlinear model, average predictions over benchmark players; do not substitute a vector of average features into the model and assume the results are equivalent.

This is an opportunity-conditioned observational contrast. It does not simulate every change in play calling, target selection, teammates, or opponent behavior that a real substitution would cause. On-ball receiving value is not complete receiver value; blocking, decoy routes, target earning, and coverage deterrence require additional evidence.

Every season game remains in the cumulative ledger. Games missed add no opportunities or contribution, with no separate injury penalty. Prior seasons may inform shrinkage but do not add points to the 2026 total. Current skill is a separate possible display; do not retroactively multiply today's skill estimate by all earlier opportunities.

## First-unit positional benchmark

Define role membership using timestamped depth-chart information available **before kickoff**, supported by a documented mapping from source positions to model roles. This is a measurable proxy for ordinary starting-caliber performance, not a claim that depth-chart labels reveal latent talent perfectly.

For each role:

1. Give each team equal weight.
2. Within each team, average across its completed team games at the ranking cutoff.
3. Within each team-game role cell, split weight equally across the pregame first-unit members.
4. Aggregate repeated memberships into player weights and average their partially pooled model predictions in the evaluated context.

A player named first unit for one game therefore does not receive the same season benchmark weight as a sustained first-unit player. An injury replacement can enter this observable cohort; this limitation must be disclosed. A role with several first-unit members does not receive additional team weight merely because of its roster structure.

The expected team-game/role universe must be declared before constructing weights. Missing required cells, stale or post-kickoff membership evidence, unresolved identifiers, and an unsupported role mapping are failures, not permission to silently renormalize a convenient subset. Any narrower benchmark scope must be explicit and versioned. The ingestion stage must validate the as-of evidence; mathematical weights alone do not establish pregame availability.

Three populations are distinct:

| Population | Purpose |
| --- | --- |
| Model observations | All valid measured opportunities, including low-volume players |
| Benchmark cohort | Players weighted by the declared comparison policy |
| Qualified leaderboard | Players satisfying participation, source coverage, and model-admission rules |

Leaderboard qualification never defines who is allowed to inform the model or the benchmark. A first-unit member with zero observed opportunities remains in the primary benchmark when a valid model prediction exists; membership weights reflect the declared pregame role rather than realized usage. Such a prediction may rely heavily on partial pooling and must carry its uncertainty.

## Required benchmark sensitivities

- **Equal-player:** equal weight to each player with at least one valid observed role-specific opportunity in the declared positional population. Include one-opportunity reserves; exclude zero-opportunity predictions from this sensitivity population. Sparse samples are partially pooled rather than treated as precise estimates.
- **Opportunity-weighted:** weight that same positive-opportunity population by valid role-specific opportunities. It describes the player performance encountered on a typical opportunity and can be influenced by who receives playing time.
- **First-unit:** the primary comparison above. It avoids giving every briefly appearing reserve equal benchmark weight while making the first-unit proxy explicit.

Report population definitions with every comparison. Average-starter and replacement-level variants beyond this first-unit proxy are optional research, not the primary metric. If the benchmark rises by `delta` points per opportunity in an additive constant-effect example, a player's cumulative value falls by `opportunities × delta`. High-volume players can therefore change rank substantially even with unchanged player-effect estimates.

Benchmark sensitivity is not a confidence interval. Statistical uncertainty must include uncertainty and covariance in both the evaluated player and benchmark predictions. A benchmark-centered model need not produce cumulative player totals summing to zero when players have different workloads and contexts.

## Provisional participation policy

Require at least **three games with participation** for the main board. Earlier results may appear as provisional. Let `G` be completed available team games, including games the player missed and excluding byes. Trades use nonoverlapping team stints; neither reset the season nor add two teams' full-season denominators. Late signings, trades, position changes, and injury absences require explicit denominator fixtures before live publication.

| Role/module | Provisional opportunity minimum |
| --- | --- |
| QB | `max(50, 14 × G)` unique modeled QB plays |
| RB on-ball | `max(25, 6 × G)` carries and targets |
| WR targeted receiving | `max(15, 3 × G)` targets |
| TE targeted receiving | `max(10, 2 × G)` targets |
| OL, if supported | `max(100, 35% of available team offensive snaps)` |
| IDL / EDGE explorer | `max(75, 20% of available team defensive snaps)` |
| LB / CB / S explorer | `max(100, 35% of available team defensive snaps)` |

QB opportunities combine dropbacks and designed non-kneel rushes; count scrambles once. Receiving qualification only supports the targeted receiving module. Specialist modules need task-specific denominators before admission. Meeting a defensive snap threshold does not qualify a defender for an overall CAVAA score.

The [offensive ledger](OFFENSIVE_INPUTS.md) now implements unique observed actor
counts, including the dropback/rush union. Those event roles are not verified
positional labels, and its observed player games do not yet establish roster-stint
or missed-game denominators. It deliberately does not produce qualification.

These are product-policy hypotheses, not scientifically established cutoffs. Historical tests compare 0.75×, 1×, and 1.25× requirements and select the least restrictive stable policy without tuning to names, desired winners, or positional diversity. Source coverage and attribution admission remain separate gates.

Partial pooling reduces low-sample extremes but does not create missing information. Do not require a positive estimate, a confidence interval excluding zero, or one universal interval-width cutoff to qualify; those rules select favorable outcomes or privilege easily measured positions.

## Attribution and context

Start with regularized additive player effects, role structure, and a declared context model. Allow team/system and unallocated shared components where individual effects are not identifiable. Preserve a reconciliation between the modeled outcome, fitted components, and residual; do not award full play EPA independently to the quarterback, receiver, line, and defenders.

Use reliable preplay situation and chronologically estimated opponent context. Teammate effects should be joint where identifiable; otherwise consider lagged or leave-player-out proxies with sensitivity tests. Team and player effects can be strongly confounded, especially when teammates nearly always play together.

Pressure, sacks, time to throw, separation, YAC, and targets can be consequences of player decisions or skill. They are not automatic hardship adjustments. Do not add overlapping pressure, accuracy, or sack bonuses to a value estimate already accounting for the same outcome. Coaching and injury information cannot justify invented scheme scores or injury-severity penalties.

Nonlinear interactions need an explicit shared-value allocation before individual contrasts can be summed. Shapley-style allocations encode a chosen coalition/counterfactual definition and are not automatically causal. Graph models and tracking methods remain optional research until they improve evidence, not just fit.

The October 23 [diagnostic baseline](BASELINE.md) includes an observed-role
ablation to distinguish actor identity from knowing a target/carry/dropback link
was recorded. Target availability is realized information and can absorb a QB's
avoidance of sacks or throwaways. This ablation is not an approved hardship
adjustment for final CAVAA. Its model coefficients are not positional scores.
October 27 adds the [bounded positional contrast experiment](CONTRASTS.md), which
applies the first-unit and two sensitivity populations to these joint actor
components. It is a retrospective constant season-average fit, not a current-form
estimate. Context/team/shared-role terms and residuals remain outside individual
contrasts. All model/benchmark participants are retained independently of
qualification; cold benchmark parameters carry prior uncertainty.

The contrast layer's conditional Gaussian intervals use the full covariance of
the player-minus-benchmark calculation. They are working-model diagnostics with
an iid residual assumption and plug-in scale, not calibrated football confidence
intervals. Its narrow exposure proof accepts only a consistent single team/role
with positive observed participation in every completed team game in the window.
This selected subset does not resolve general stints, injured/missed games, trades
or late signings. The three-game rule and threshold grid remain provisional,
and every main-admission flag stays false.

## Evidence and release labels

Prediction accuracy supports the outcome model but does not establish correct player attribution. Cross-position admission requires a comparable estimand, benchmark, opportunity definition, accounting policy, and meaningful validation. Unsupported contributions stay unmeasured; missing is not zero. See [evaluation](EVALUATION.md) and the required [defensive experiment](DEFENSE_EXPERIMENT.md).

Research foundations include [nflWAR](https://arxiv.org/html/1802.00998v2), [football adjusted plus-minus](https://ideas.repec.org/a/bpj/jqsprt/v17y2021i4p313-364n4.html), and [causal limitations of feature relevance](https://proceedings.mlr.press/v108/janzing20a.html). These motivate methods and cautions; none validates this project's unbuilt 2026 metric.
