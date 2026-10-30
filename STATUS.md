# Project status

Updated: October 29, 2026, America/New_York.

## Current unit

The bounded observed QB/target-mix transition audit is implemented on
`codex/observed-lineup-transitions`, from owner-merged PR #12 / main `28d79c8`.
Main CI was green, with no open PRs, reviews to address or unfinished local work.
Plan `95d1379` was committed before implementation/results. The unchanged frozen
baseline is evaluated on adjacent games in its original evaluation partitions;
selection uses observations/identities, never EPA. Every excluded adjacent pair
is retained. The complete baseline/roster/raw chain builds and replays offline.
See the [specification and results](docs/TRANSITIONS.md),
[audit](docs/audits/2026-10-29-transitions.json) and
[learning report](docs/learning/2026-10-29.md).

There are 61/112 accepted pairs in the 2025/2026 windows, including eight/five QB
changes. On changed-QB pairs, joint-model mean absolute change error exceeds the
role baseline by 0.00254/0.00449 EPA per play. Only four/two identity-swap
diagnostics have both actors represented in training; the others remain null.
Small, selected and dependent samples do not establish attribution or causal
absence effects. Target mix measures recorded usage, not cast quality. This
audit supplies bounded evidence for the October 30 decision, not an admission.

**The primary intervals fail the stronger-signal stress tests.** Matched-prior
coverage is 94.85/94.94%, but fixed-signal coverage is only 0.96–1.94% in 2025 and
0.88–1.13% in archived 2026. Those are simulated truths, not measured real-player
errors. Game-cluster sampling variance does not repair shrinkage bias. All 6,144
synthetic-response fits retain the declared settings; no penalty, threshold,
benchmark or admission decision is changed to improve these results.

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

| Season/window | Compared role-players | Complete benchmark roles | Narrow exposure proven | Participation passes at 0.75× / 1× / 1.25× |
| --- | ---: | --- | ---: | --- |
| 2025 Week 6 | 444 | QB/RB/WR/TE | 169 / 444 | 162 / 150 / 139 |
| 2025 Week 10 | 64 | QB | 125 / 490 | 121 / 115 / 108 |
| 2025 Week 14 | 70 | QB | 106 / 536 | 104 / 102 / 98 |
| 2025 Week 18 | 79 | QB | 70 / 575 | 70 / 68 / 67 |
| Archived 2026 Week 3 | 407 | QB/RB/WR/TE | 221 / 407 | 164 / 143 / 112 |
| Archived 2026 Week 6 | 463 | QB/RB/WR/TE | 163 / 463 | 158 / 146 / 130 |

Participation totals include all four roles and remain independent of benchmark
coverage and model admission. None is a qualified main-leaderboard player.
Missing/ambiguous first-unit slots for ARI in `2025_07_GB_ARI` block the complete
RB/WR/TE populations in later historical windows; they are not silently omitted.
The largest 2026 Week 6 primary-setting benchmark difference is 0.54 EP, while the
largest per-player range across the declared penalties is 87.14 EP. This strong
regularization dependence and the selective exposure subset prevent an admission
claim. Conditional intervals now have measured calibration failures under the
declared stronger-signal scenarios. Maximum per-play reconstruction
error across all fits is 1.78e-15 EP, which verifies arithmetic, not attribution.
The first-unit benchmark, penalty 1000 and provisional eligibility rules are
unchanged. The experiment adds no public scores or new live game coverage.

The October 26 roster join exactly replays with network calls blocked. The 2025 archive has
46,849 weekly rows (44,697 regular season); 5,323 of 5,347 observed offensive
player-game rows have a directly interpretable source position. The 2026 archive
has 17,606 weekly rows; 1,814 of 1,819 offensive player-game rows resolve. The
remaining 24/5 use broad position labels and stay unresolved. No matched
team-game is missing all roster rows, which does **not** certify complete stints.
29 historical roster rows have missing GSIS IDs and remain unlinked.

All weekly roster evidence was retrieved retrospectively. Its October 26 evidence
cutoff does not advance either archived game cohort: 2025 retains 272 games /
32,813 plays, and 2026 retains the 93-game / 11,441-play Week 6 snapshot below.
Unobserved offensive workloads stay null, and that upstream roster payload makes
no denominator/admission claims. The new selected exposure diagnostic is separate.
No completed-game inventory was refreshed in this unit.

The saved 2026 view has 93 completed games, 11,441 included pass/run plays, 32
teams and 518 players through Week 6. Its fixed cutoff is October 22 at
23:50:38.680415 UTC; this is an archived snapshot, not October 29 live coverage.
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

265 Python tests, 13 frontend contracts, Ruff, TypeScript/format/build, compile and
whitespace checks pass locally. The existing eight Chromium scenarios were not
rerun locally for this Python-only unit; the unchanged hosted dashboard job runs
them. Hosted results for this branch are reported separately. The October 25
coverage baseline was 90.15% and remains informational; it is not today's
measurement or evidence of attribution. During the earlier Explorer unit, the
real snapshot built and exactly replayed
offline with network construction/connections blocked. Desktop/mobile inspection
finds no page errors, failed responses or document overflow. See the audit for
recorded inputs and the learning report for failures fixed during verification.

## Next highest-priority unit — October 30

Freeze evidence-backed module admission/non-admission decisions and release labels.
Implement the small machine-readable decision contract that future release gates
can enforce; all current score modules remain unadmitted. Preserve the required
first-unit benchmark and sensitivity definitions, cumulative accounting and
provisional participation rules. Do not promote the selected all-games-observed
subset to a general denominator policy, fill historical chart gaps by inference,
or relabel observed transitions as verified injuries/absences. The measured
shrinkage/dependence failures cannot be repaired by choosing a favorable simulated
penalty or merely widening intervals. Avoid another open-ended model rebuild;
then prioritize the November 7 website, durable artifacts and independent
publication/last-good-output work. Explicitly record the unfinished ranking goal.

Defensive follow-up still requires a permitted live workload source, actual
live-like missingness, verified positions, additional seasons, absence cases and
player uncertainty. Do not convert the Explorer's event counts into scores.

## Unfinished release gates

The local exploratory website is usable, but no 2026 CAVAA score is published and
no position has passed attribution/comparability admission. The first offensive
contrast/conditional-interval, calibration, transition and partial qualification
experiments now run, but calibrated player uncertainty, broader exposure,
admission, ranked/history views, durable
off-machine snapshot retention, deployment and independent production refresh
remain unfinished. Source receipts and generated exports are local and ignored
by Git; a hash alone cannot restore missing bytes. The current public-data rights
review does not admit a PFR workload dependency.

An exploratory site without admitted CAVAA does not fulfill the MVP-ranking
objective. November 7 remains the target and that scientific release risk remains
open. Today's run changes no schedule, purchases nothing, and does not modify NFL
Opponent Intelligence. Production refresh remains independent of Codex.
