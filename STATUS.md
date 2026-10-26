# Project status

Updated: October 25, 2026, America/New_York.

## Current unit

The additional manual CI/reliability unit is implemented on
`codex/ci-regression-reliability`, from owner-merged PR #8 / main `5080d15`.
Main CI was green and there were no open PRs or unfinished changes at inspection.
The unit adds pinned Ruff/coverage checks, retained CI/browser diagnostics,
13 meaningful replay/export/archive regressions, stricter numerical and manifest
validation, and a manual dependency audit. Installer/build-tool advisory matches
were resolved with pip 26.2.2 and setuptools 84.1.0. See [CI](docs/CI.md) and the
appended [learning report](docs/learning/2026-10-25.md). No schedule was changed.

The required **Defense Explorer foundation and first React/TypeScript dashboard**
are implemented. The Python exporter rebuilds scoped observed evidence from the
archived 2026 inputs; the browser verifies the hash and strict data contract before
showing players, filters, chart coverage, team EPA and provenance. See the
[contract](docs/DEFENSE_EXPLORER.md), [audit](docs/audits/2026-10-25-defense-explorer.json)
and [learning report](docs/learning/2026-10-25.md).

PR #8 is now merged by the owner. This manual unit targets main with no stacked
dependency. Agents still must not merge this work or enable auto-merge.

## Measured evidence

The saved 2026 view has 93 completed games, 11,441 included pass/run plays, 32
teams and 518 players through Week 6. Its fixed cutoff is October 22 at
23:50:38.680415 UTC; this is an archived snapshot, not October 25 live coverage.
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

199 Python tests, 13 frontend contracts, TypeScript/format/build checks and eight
Chromium scenarios pass locally. Combined Python coverage is 90.15%; it remains
informational and does not establish attribution. The manual dependency audits
report no known vulnerabilities with the new installer/build pins. Hosted CI
results for this branch will be reported separately; local success is not hosted
verification. During the earlier Explorer unit, the real snapshot built and exactly replayed
offline with network construction/connections blocked. Desktop/mobile inspection
finds no page errors, failed responses or document overflow. See the audit for
recorded inputs and the learning report for failures fixed during verification.

## Next highest-priority unit — October 26

Finish position/roster-stint evidence and correct `SeasonExposure`'s observed-by
completion timestamp handling before benchmark contrasts or qualification. Do not
infer missed-game denominators from positive appearances. Test the first-unit,
equal-player and opportunity-weighted contrasts on the bounded historical plan,
with joint player/benchmark uncertainty and qualification sensitivity. Keep the
October 28–30 freeze and November 7 launch target explicit; additional complexity
must not displace admission decisions or publication work.

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
