# Project status

Updated: October 26, 2026, America/New_York.

## Current unit

The weekly position/team evidence unit is implemented on
`codex/position-exposure-evidence`, from owner-merged PR #9 / main `61dcead`.
Main CI was green, with no open PRs, reviews to address or unfinished local work.
The new source adapter archives weekly rosters separately from annual rosters;
the offline join records exact player/team/week matches, unresolved identities,
literal statuses and missing workloads. `SeasonExposure` now distinguishes a
completion retrieval bound from an exact finish. See the
[contract](docs/ROSTER_INPUTS.md), [audit](docs/audits/2026-10-26-roster-evidence.json)
and [learning report](docs/learning/2026-10-26.md).

The preceding manual CI/reliability work is merged. Its Python matrix, Ruff,
coverage diagnostics, frontend/browser checks and optional dependency audit remain
intact. This unit adds no dependencies, services or schedules.

The required **Defense Explorer foundation and first React/TypeScript dashboard**
are implemented. The Python exporter rebuilds scoped observed evidence from the
archived 2026 inputs; the browser verifies the hash and strict data contract before
showing players, filters, chart coverage, team EPA and provenance. See the
[contract](docs/DEFENSE_EXPLORER.md), [audit](docs/audits/2026-10-25-defense-explorer.json)
and [learning report](docs/learning/2026-10-25.md).

This unit targets main with no stacked dependency. Agents must not merge this
work or enable auto-merge.

## Measured evidence

The new join exactly replays with network calls blocked. The 2025 archive has
46,849 weekly rows (44,697 regular season); 5,323 of 5,347 observed offensive
player-game rows have a directly interpretable source position. The 2026 archive
has 17,606 weekly rows; 1,814 of 1,819 offensive player-game rows resolve. The
remaining 24/5 use broad position labels and stay unresolved. No matched
team-game is missing all roster rows, which does **not** certify complete stints.
29 historical roster rows have missing GSIS IDs and remain unlinked.

All weekly roster evidence was retrieved retrospectively. Its October 26 evidence
cutoff does not advance either archived game cohort: 2025 retains 272 games /
32,813 plays, and 2026 retains the 93-game / 11,441-play Week 6 snapshot below.
Unobserved offensive workloads stay null, and every denominator/admission gate
remains false. No completed-game inventory was refreshed in this unit.

The saved 2026 view has 93 completed games, 11,441 included pass/run plays, 32
teams and 518 players through Week 6. Its fixed cutoff is October 22 at
23:50:38.680415 UTC; this is an archived snapshot, not October 26 live coverage.
Recorded credits total 425 sacks and 130 interceptions. Four additional flagged
sacks remain unallocated. There are 92 players without a verified chart role,
one unresolved roster name and ten blocked defensive team-game-role cells:
six IDL, two CB and two S. The separate LS issue is outside the defensive view.
All 186 chart team-games use retrospectively retrieved evidence.

These are event/chart observations, not individual value estimates. No snap
fractions, games-played denominators or pressure rates are inferred. Every player
has null CAVAA and snaps; team EPA is kept separate and negative team outcomes
remain visible. Qualification and the first-unit/equal-player/opportunity-weighted
contrasts are not calculated here. No position is admitted to the MVP leaderboard.

The October 24 bounded historical experiment remains unchanged: 243 games /
29,297 plays, no reliable defender increment over team/context prediction, and
residualized defender rank falling from 922 to 301 across 951 columns after
aggregation. See [the prior audit](docs/audits/2026-10-24-defensive-model.json).
The richer model is not ground truth, and the degraded historical view is not
verified live-feed coverage.

217 Python tests, 13 frontend contracts, Ruff, TypeScript/format/build, compile and
whitespace checks pass locally. The existing eight Chromium scenarios were not
rerun locally for this Python-only unit; the unchanged hosted dashboard job runs
them. Hosted results for this branch are reported separately. The October 25
coverage baseline was 90.15% and remains informational; it is not today's
measurement or evidence of attribution. During the earlier Explorer unit, the
real snapshot built and exactly replayed
offline with network construction/connections blocked. Desktop/mobile inspection
finds no page errors, failed responses or document overflow. See the audit for
recorded inputs and the learning report for failures fixed during verification.

## Next highest-priority unit — October 27

Implement and test the first-unit, equal-player and opportunity-weighted contrasts
for directly supported offensive role evidence. Resolve a documented exposure
policy using the weekly/status and pregame evidence; explicitly block ambiguous
trades, gaps, injuries and unverified missed-game denominators. Do not silently
fill them or let leaderboard qualification define the benchmark. Complete the
bounded qualification/uncertainty tests and admission decisions in the October
28–30 freeze window. Prioritize that experiment and its decision over further
generic data/CI framework work; November 7 remains the launch target.

Defensive follow-up still requires a permitted live workload source, actual
live-like missingness, verified positions, additional seasons, absence cases and
player uncertainty. Do not convert the Explorer's event counts into scores.

## Unfinished release gates

The local exploratory website is usable, but no 2026 CAVAA score is published and
no position has passed attribution/comparability admission. Supported offensive
contrasts, joint intervals, qualification tests, ranked/history views, durable
off-machine snapshot retention, deployment and independent production refresh
remain unfinished. Source receipts and generated exports are local and ignored
by Git; a hash alone cannot restore missing bytes. The current public-data rights
review does not admit a PFR workload dependency.

An exploratory site without admitted CAVAA does not fulfill the MVP-ranking
objective. November 7 remains the target and that scientific release risk remains
open. Today's run changes no schedule, purchases nothing, and does not modify NFL
Opponent Intelligence. Production refresh remains independent of Codex.
