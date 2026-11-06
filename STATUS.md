# Project status

Updated: November 5, 2026, America/New_York.

## Current unit

The [source-readiness and Explorer candidate unit](docs/SOURCE_READINESS.md) is
implemented on `codex/explorer-source-readiness`, from owner-merged PR #16 / main
`6a60be5`. Main CI was green; there were no open PRs, reviews or unfinished local
changes. A frozen operational policy checks recent retrieval, upstream asset age,
per-team chart recency, the full 272-game / 32-team schedule and clock-based
completed-game reconciliation. Missing/stale inputs block explicitly; malformed
or corrupted inputs error. No player model, benchmark or qualification rule changed.

The new immutable candidate has **121 completed games / 14,851 scoped pass-run
plays / 562 players through Week 8**, at November 5, 19:04:28 America/New_York
(`2026-11-06T00:04:28.116468+00:00`). All four fresh receipts pass at that cutoff,
and all 32 teams have recent embedded chart snapshots. All 93 earlier games are
preserved; 28 games are added and two existing team-context rows changed. The
comparison records those changes while preserving original objects. It is not a
claim that player names/roles or every earlier source field stayed unchanged.

Candidate ID:
`a1a5fc0401401380e3c11291c96cc197f31e05947c0bd8141df879fe49cb6da8`.
The producer is `65e4cda9a945e93bd6b64b46b024984fbf3c05b3`. Full source/candidate
replay passed with Python networking blocked, and the actual payload passes the
existing frontend Zod contract. The old Week 6 receipts remain reproducible but
fail readiness at the new cutoff: 41 operational blockers and 28 unresolved games.
See the [audit](docs/audits/2026-11-05-source-readiness.json) and
[learning report](docs/learning/2026-11-05.md).

The candidate has 553 recorded sack credits and 170 interceptions. Four flagged
sacks remain unallocated, three names unresolved, and 16 defensive chart cells
blocked (eight IDL, four CB, four S). All 242 chart team-games use retrospective
evidence. CAVAA and defensive snaps remain null for every player; all 17 modules
remain **not admitted**. Source readiness is evaluated at the recorded cutoff;
a later replay does not renew freshness or authorize publication now.

**No public pointer changed.** The locally staged website still uses the archived
Week 6 view. Preparation creates unpublished candidates only; it does not deploy,
schedule production refresh, or provide hosted rollback. Source readiness is one
prerequisite, not ranking or publication approval. No new dependency, paid service
or recurring charge was introduced.

**Off-machine retention remains blocked.** The browser is still signed out,
there are no GitHub releases, the connector lacks binary release-asset upload,
and no authenticated upload CLI is available. Yesterday's [recovery archive](docs/RECOVERY.md)
remains verified locally; it covers the old Explorer dependency set only, not this
new candidate or the other research stores. Complete authenticated upload and an
independent download/restore when access becomes available. Continue independent
launch preparation rather than waiting on authentication.

There are 61/112 accepted pairs in the 2025/2026 windows, including eight/five QB
changes. On changed-QB pairs, joint-model mean absolute change error exceeds the
role baseline by 0.00254/0.00449 EPA per play. Only four/two identity-swap
diagnostics have both actors represented in training; the others remain null.
Small, selected and dependent samples do not establish attribution or causal
absence effects. Target mix measures recorded usage, not cast quality. This
audit supplies bounded evidence for the documented decision, not an admission.

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
That earlier exposure unit did not refresh the completed-game inventory.

The previously staged 2026 view has 93 completed games, 11,441 included pass/run
plays, 32 teams and 518 players through Week 6. Its fixed cutoff is October 22 at
23:50:38.680415 UTC; this is an archived snapshot, not November 5 live coverage or
the new unpublished candidate.
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

332 Python tests, 27 frontend contracts, Ruff, TypeScript/format/build, compile and
whitespace checks pass locally. The 18 new Python tests exercise actual synthetic
capture/replay/Explorer chains, not live downloads or invented model behavior.
Existing Python 3.11/3.12/3.13 and dashboard/12 Chromium scenarios remain in hosted
CI; results for the pushed commit are recorded on the PR. The actual new payload
passes the frontend schema. No UI code changed or new manual browser QA is claimed. Coverage
remains informational; the October 25 percentage is not today's measurement.

## Next highest-priority unit — November 6

Prepare the usable exploratory launch: package the reviewed Week 8 candidate with
current source readiness, browser verification and deployment/retention controls.
Recheck freshness at the actual publication attempt; do not promote an old saved
positive decision. Preserve the archived Week 6 view and original/corrected
versions. Weekly production execution must remain independent of Codex and keep
last-good output when sources or validation fail. No scored leaderboard is yet
scientifically admissible.

When authenticated release-upload access is available, retain the prepared
archives in the canonical repository's releases and verify a separate download/
restore against committed digests. The new candidate and other research stores
also need durable retention. No paid infrastructure without owner approval.

No admitted ranking is presently supported. An exploratory release must state
that the unified-MVP objective remains unfinished. Preserve the November 7 target
without retuning on examined outcomes, promoting selected exposure to general
eligibility, or labeling a retrospective Week 6 view as current NFL rankings.

Defensive follow-up still requires a permitted live workload source, actual
live-like missingness, verified positions, additional seasons, absence cases and
player uncertainty. Do not convert the Explorer's event counts into scores.

## Unfinished release gates

The local exploratory website is usable, but no 2026 CAVAA score is published and
no position has passed attribution/comparability admission. The first offensive
contrast/conditional-interval, calibration, transition and partial qualification
experiments now run, and formal non-admission decisions are recorded. Calibrated
player uncertainty, broader exposure, a module that passes admission,
ranked/history views, durable off-machine snapshot retention, deployment and independent production refresh
remain unfinished. Source receipts and generated exports remain local and ignored
by Git; a hash alone cannot restore missing bytes. Source readiness and candidate
preparation now work, but no production publisher or current-time deployment gate
is implemented. The current public-data rights
review does not admit a PFR workload dependency.

An exploratory site without admitted CAVAA does not fulfill the MVP-ranking
objective. November 7 remains the target and that scientific release risk remains
open. Today's run changes no schedule, purchases nothing, and does not modify NFL
Opponent Intelligence. Production refresh remains independent of Codex.
