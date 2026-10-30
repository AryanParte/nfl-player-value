# Bounded observed-lineup transition audit

Plan `95d1379` was committed before implementation and new case results. This is
a retrospective diagnostic of the existing outcome model, not an injury study, causal replacement
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

## October 29 results

Producer `815f5bf` ran the frozen plan without a new source capture. The
[audit](audits/2026-10-29-transitions.json) records the full report hash, source
cutoffs, complete subgroup summaries, all 13 QB-change cases and object hashes
for every panel/case/exclusion. The 2026 archive still ends at Week 6, with an
October 22 23:50:38.680415 UTC game-cohort cutoff; its October 26 roster evidence
does not turn this into a live October 29 ranking or historically available data.

| Measure | 2025 weeks 15–18 | Archived 2026 weeks 1–6 |
| --- | ---: | ---: |
| Completed games / team-games | 64 / 128 | 93 / 186 |
| Eligible team-games | 104 | 157 |
| Adjacent pairs / accepted / excluded | 96 / 61 / 35 | 154 / 112 / 42 |
| QB-change pairs / offense teams | 8 / 7 | 5 / 4 |
| QB changes with zero prior-leader recorded dropbacks | 7 | 3 |
| QB changes with both identities observed in training | 4 | 2 |
| Retained-QB high-target-mix pairs / teams | 5 / 4 | 9 / 9 |

Endpoint failure reasons can overlap. Historical panels have 18 actor/event
issues, eight insufficient leader shares, one ambiguous QB leader and one
unresolved dropback position/identity. Current panels have 25 actor/event issues
and five insufficient leader shares. These exclusions select a cleaner subset;
they do not certify that the missing cases are comparable or unimportant.

Values below are **joint minus observed-role mean absolute error** when explaining
the change in team mean offensive EPA per play. Negative favors joint. These
small differences are not individual value or changes in win probability.

| Prespecified group | 2025 difference | 2026 difference |
| --- | ---: | ---: |
| All accepted pairs | -0.000033 | +0.000548 |
| QB changed | +0.002540 | +0.004489 |
| QB retained | -0.000421 | +0.000363 |
| QB retained, target-mix distance ≥0.5 | +0.000365 | -0.000491 |

The changed-QB mean absolute errors are 0.24854 versus 0.24600 historically and
0.37482 versus 0.37033 in 2026 (joint versus role). Leaving out one offense team
moves the paired difference across [0.000786, 0.004278] and
[-0.000470, 0.009560]. These are sensitivity ranges, not confidence intervals or
independent samples. The high-target-mix ranges cross zero in both windows.
No retained-QB case has an unknown target mix in these actual inputs; the empty
group still reports null metrics, and its behavior is tested synthetically.

The seven changed-QB comparisons lacking training support remain null, never
zero-effect backups. All prior leaders have a weekly roster record in these
13 cases, but that record does not prove availability, injury status or snaps.
The largest component reconstruction error is 1.20e-15 EPA per play. Arithmetic
conservation, weak change prediction and sparse substitutions do not establish
causal attribution or repair the prior calibration failures. No position is
admitted and the first-unit CAVAA benchmark remains unchanged.

## Run and reproduce

Use the existing pinned model environment from the repository root:

```sh
PYTHONPATH=src python -m nfl_value.transition_cli build \
  --baseline-report 1fd9e2479c71ff06590a96e7b512fb291f80ad35bc10867d81814af7452660de \
  --historical-roster-report be0547bd656d1925343bbd2ac5a2c14e6db44a4d53c47621fab0d4c874ea7ee7 \
  --transfer-roster-report 1e15bbad312a88685b9fa74164b6b8eecc677c49f07029528048413b3c35ea3b \
  --plan config/transitions-v1.json
PYTHONPATH=src python -m nfl_value.transition_cli replay \
  54afb613475b4aa2736e6995ea7427e9aa765bd982c62d822276e83aecc729be
```

Commit source/package edits before building; the manifest records the actual
producer. Default output is `data/derived/transitions`, alongside the existing
raw/offensive/roster/baseline stores. Store overrides precede `build` or `replay`.
The existing immutable experiment writer uses `objects.models` for complete
team-game panels and `objects.predictions` for cases/exclusions; those keys do
not mean this audit fits a new model. Replay verifies and rebuilds all upstream
sources/models, identities, partitions, summaries and numerical components.
Both full build and replay ran with HTTP opens and socket connections blocked.

Self-review added a guard against omitted completed games in a saved evaluation
partition: an omitted middle game is not a bye. Its regression rejects the
omission even when saved prediction rows otherwise match. Rebuilding after this
guard leaves both real diagnostic objects byte-identical. The 15 new tests also
cover outcome-independent selection, no skipping bad endpoints, unknown targets,
non-QB tricks, untrained actors, negative accounting and rehashed tampering.
Source bytes and full derived objects remain local/ignored; durable retention
and an independently scheduled production publisher are still required.
