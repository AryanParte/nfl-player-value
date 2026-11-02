# November 2, 2026 module decision

Decision: **no current contribution module is admitted to a 2026 CAVAA ranking**.
This records the overdue October 30 freeze on its actual decision date; it does
not claim development or approval occurred on October 30–November 1. The source
checkout is owner-merged PR #13, main `e186c81`. No later implementation or open
PR was present at inspection. This is a release decision based on bounded
evidence, not a claim that NFL player value can never be estimated.

## Reviewed evidence

- October 23 [offensive baseline](../audits/2026-10-23-offensive-baseline.json):
  limited actor-identity increment over observed-role prediction, with shared
  team/context components and unresolved identification.
- October 24 [defensive information loss](../audits/2026-10-24-defensive-model.json):
  neither selected defender model passes its declared incremental-prediction
  criterion. Residualized defender rank falls from 922 to 301 across 951 columns.
  The richer historical model is not ground truth or a live-2026 attribution feed.
- October 25 [Defense Explorer](../audits/2026-10-25-defense-explorer.json) and
  October 26 [roster joins](../audits/2026-10-26-roster-evidence.json): observed
  events and exact-week positions do not establish all workloads, roster stints,
  missed-game denominators, off-ball contributions or permitted live tracking.
- October 27 [contrast experiment](../audits/2026-10-27-positional-contrasts.json):
  approved benchmark contrasts and arithmetic work on selected observed exposure,
  but general denominators and later historical RB/WR/TE benchmark cells remain
  incomplete. Largest archived 2026 penalty range is 87.14 EP versus 0.54 EP across
  benchmarks at the primary penalty. These are sensitivity diagnostics, not CI.
- October 28 [calibration](../audits/2026-10-28-calibration.json): near-95% coverage
  under the model's prior coexists with below-2% coverage under declared stronger
  effects. That is a failed general interval claim in simulations, not a measured
  actual-player error rate. Widening a sampling interval does not remove bias.
- October 29 [transitions](../audits/2026-10-29-transitions.json): eight/five QB
  changes in 2025/2026, only four/two supported predecessor contrasts, and no
  improved mean change error over the role model in those groups. Recorded target
  mix does not identify supporting-cast quality or a causal substitution.

## Decisions by module

| Modules / roles | Decision and principal reasons |
| --- | --- |
| Observed QB components / QB | Not admitted: incomplete contribution/context identification, selected exposure, retrospective benchmark evidence, failed interval stress tests and unproved cross-position comparison |
| On-ball RB / RB | Not admitted: carries/targets omit blocking and off-ball value; same attribution, exposure, benchmark and uncertainty limits |
| Targeted receiving / WR, TE | Not admitted: recorded targets are partial and endogenous; no full receiving contribution, general denominator or calibrated uncertainty |
| Blocking / OT, OG, C | Not evaluated as an individual model; no implemented blocking allocation, validated benchmark contrast, workload policy or uncertainty evidence |
| Defense / IDL, EDGE, LB, CB, S | Not admitted: historical prediction criterion not passed, no verified live role/workload attribution, positional first-unit contrasts or player uncertainty; Explorer event counts remain separate |
| Specialists / K, P, LS, KR, PR | Not evaluated as individual models; task-specific contribution, opportunity/eligibility, benchmark and comparison validation are unimplemented |

Passing arithmetic reconstruction is recorded separately from correct attribution.
Sufficient participation cannot override any failed or untested module gate. No
favorable subgroup, experimental label, zero-filled score or arbitrary position
multiplier authorizes a ranking. Benchmark membership remains independent of
qualification, and cumulative season value must preserve negative/earlier games.

## Release consequence and reopening

The current release scope can present observed data, coverage, research findings
and explicit unavailability. A November 7 site without admitted scores does not
fulfill the requested unified MVP leaderboard. No scientific gate is waived to
meet the date. Source retention, current-source refresh, website deployment and
production failure recovery also remain incomplete.

A positive decision requires a new reviewed registry/contract version, a precise
contribution scope, permitted source coverage, verified general denominators,
the first-unit and both sensitivity populations, shared-value accounting,
credible attribution and uncertainty evidence, and comparison with other admitted
modules. New validation must disclose previously examined outcomes. The current
version cannot be unlocked by flipping a Boolean or meeting a snap threshold.
Preserve this dated decision and its referenced audit bytes; issue a new record
when evidence or policy changes. The executable registry is a prerequisite guard,
not the entire future publication validator or an independent scientific proof.
