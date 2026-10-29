# Bounded observed-lineup transition audit

Freeze this plan before inspecting new case results. This is a retrospective
diagnostic of the existing outcome model, not an injury study, causal replacement
estimate or CAVAA admission. The [configuration](../config/transitions-v1.json)
defines case selection. No settings are tuned using this audit.

## Inputs and fixed predictions

Use the October 23 frozen baseline report
`1fd9e2479c71ff06590a96e7b512fb291f80ad35bc10867d81814af7452660de` and the
October 26 weekly roster reports recorded in that day's audit. Replay the full
baseline/raw/offensive chain and both roster reports before using their contents.
Roster reports must reference the exact same offensive reports as the baseline.
Keep the baseline's selected penalty 1000, both joint and observed-role models,
feature vocabulary and saved evaluation partitions. No new fitting/selection
procedure is introduced: upstream replay reproduces the existing fits.

The analysis uses only the baseline's historical test (2025 weeks 15–18) and
transfer test (archived 2026 weeks 1–6). Both games in a pair must be in the same
evaluation partition and strictly after every training kickoff. Outcomes in these
windows were previously examined; this is not untouched confirmation or a new
prospective forecast. Source vintages are retrospective, and observed role/target
features are realized information rather than pregame covariates.

## Case selection independent of EPA

Build every completed team-game panel in each evaluation partition, including
panels that fail the following checks. Use direct consecutive completed games
for each team, ordered by kickoff; a bye is allowed, but never skip a bad panel
to join two convenient games. Preserve reasons for excluded adjacent pairs.

Each endpoint must have all its offensive-ledger rows represented in the prepared
model rows, no actor issues/aborted or unclassified events, and an identified
dropback actor for every pass/sack/scramble. Resolve each dropback actor through
that exact game/team's weekly roster evidence. Unresolved position/identity
blocks the endpoint. Resolved non-QB trick-play actors remain in the denominator
but cannot become a QB leader. Require at least ten observed team dropbacks and
one unique QB leading at least 75% of them. These are conservative case-definition
rules, **not leaderboard participation thresholds**. No game is selected by EPA,
player name, model error, official awards or whether the result favors the model.

Compare all eligible pairs and prespecified overlapping subgroups:

- QB changed versus retained, using the observed dominant dropback actor.
- Changed with zero versus positive observed dropbacks by the prior leader in
  the current game. Zero means zero recorded dropbacks in this checked ledger;
  it does not mean zero snaps, confirmed inactivity, injury or a known cause.
- Retained QB with high versus lower change in recorded target mix. For each
  endpoint, normalize counts across all recorded target IDs; total variation is
  half the sum of absolute share changes over the union of IDs. High means at
  least 0.5 (half the probability mass moves). If either game has no recorded
  targets, mix change is null, not zero; report an unknown-mix subgroup.

Target mix is an observed usage proxy, not supporting-cast quality or lineup
presence. Throwaways/unrecorded targets, off-ball routes, protection, coaching,
injury causes and target earning remain unmeasured. Changing QB and target mix
can cause each other; these groups are not independent treatment assignments.

## Measurements and accounting

For each pair, calculate current-minus-previous **mean offensive EPA per modeled
play**, each frozen model's predicted change and its signed/absolute change error.
Compare joint versus observed-role absolute errors on identical pairs; negative
paired difference favors joint. These changes do not award team EPA to the QB.
Also reconcile the joint change into context, offense/defense team, shared
observed-role, dropback/carry/target and residual components. Keep negative values;
the component changes plus residual must reconstruct the observed change.

For changed QBs only, a separate identity-swap diagnostic holds the current
game's observed circumstances fixed on the new leader's dropbacks. It computes
`new_leader_dropbacks * (beta_new_dropback - beta_prior_dropback)` from the frozen
joint model. Require both features to have positive training exposure; otherwise
return null with the untrained identities. This is a predecessor comparison,
not the first-unit CAVAA benchmark or a prediction of a real substitution.
It ignores any change in decisions, targets, rushing, opportunity or opponents'
responses. Known training exposure cannot establish comparability or causality.

Summaries retain counts, distinct teams/games, mean absolute errors and paired
differences. Report the range of mean paired differences when leaving out each
offense team; if fewer than two teams contribute, return null. This is a
sensitivity range, **not a confidence interval**: pairs overlap, opponents are
shared, and case selection is endogenous. No p-value, admission cutoff or
individual-value uncertainty is inferred. Empty groups are explicit, not success.

The first-unit, equal-player and opportunity-weighted CAVAA definitions remain
unchanged. This audit calculates no positional ranking or qualification. Required
defensive work remains separate; QB transition evidence cannot admit defenders,
offensive linemen or a full-value receiving module.

## Replay and decision use

Save immutable JSON with the exact input IDs, complete plan, code/environment,
both source cutoffs, all panels/exclusions/cases and summaries. Rebuild sources,
baseline fits, panel selection and numerical diagnostics offline; verify hashes,
identities and values using the existing replay tolerances. A failed build/replay
cannot replace prior artifacts or a publication pointer. No new dependency,
download, database, deployment or paid service is needed.

Use these bounded observations with the prior calibration/information-loss
failures for the October 30 module decision. Neither a favorable subgroup nor
verified arithmetic repairs unresolved attribution, denominators, observed-role
conditioning or the failed interval stress tests. No admission follows
automatically, and a defensible negative finding is a valid result.
