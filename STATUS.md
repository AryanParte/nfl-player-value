# Project status

Updated: November 7, 2026, America/New_York.

## Current unit

The [independent Explorer production workflow](docs/PRODUCTION_REFRESH.md) is
implemented on `codex/explorer-production-refresh`, stacked on pending PR #18
(`codex/explorer-launch-package`, `6d370bf`). Canonical main remains `72a2c7d`.
PR #18's hosted matrix/dashboard CI passed; no review feedback or unfinished local
changes were present at the start. No prerequisite has been merged by an agent.

The read-only build job restores the previous retained candidate, captures all
four sources, checks readiness, builds and replays the launch package, and tests
its actual site on desktop/mobile Chromium. The publisher receives the independent
archive pin and exact producer revision. It creates a new draft release, verifies
an independent download/replay before exposing the archive, and rechecks freshness
immediately before a Pages request. Existing public releases are never overwritten.
Failed prepublication steps preserve the last deployed website. No new Python/npm
dependency or paid service is introduced; the Codex development timer is unchanged.

A real **local bootstrap rehearsal** captured 122 completed games / 14,960 scoped
plays / 562 players at November 7, 20:41:17 America/New_York
(`2026-11-08T01:41:17.891273+00:00`). Week 9 remains partial. The package is
39,278,287 bytes, SHA-256
`0b04b9015ccf1140edbb338e858b2ef535a70e47a8a6f6e57db3328b29520199`,
produced by `d6d4688291298f81c7fcf150377e4de1f7830759`.
This rehearsal used an explicitly initialized local bootstrap state: no remote
previous-release command, upload, download or Pages deployment occurred. The
production transport boundaries were tested with fake GitHub calls and real
synthetic archive replay. The public release listing was empty when inspected.
The 23-member archive restored successfully, with a fresh publication check at
20:44:06 Eastern. The actual restored site passed desktop/mobile Chromium at a
project subpath without intercepting data requests. All 122 November 6 games are
still present, and the canonical staged Week 6 pointer is unchanged. See the
[audit](docs/audits/2026-11-07-production-refresh.json) and
[learning report](docs/learning/2026-11-07.md).

**The November 7 unified-MVP objective remains unmet.** All 17 modules are still
not admitted, CAVAA and defensive snaps remain null, and no real ranking is
published. The production workflow is reviewable code, not an activated service.
It requires owner merges, Pages configuration and a successful hosted trial.
Current-time data readiness does not establish attribution, calibration or
cross-position comparability. Historical model experiments remain frozen at their
original cohorts; refreshing the Explorer does not refresh those models.

The required defensive information-loss experiment and Defense Explorer are
implemented. The stronger-signal uncertainty experiments still fail severely,
and observed QB-change diagnostics do not establish an attribution increment.
No benchmark, penalty, qualification, uncertainty or admission rule changed to
meet the calendar deadline. Research details remain in the measured evidence below.

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
23:50:38.680415 UTC; this is an archived snapshot, not November 6 live coverage or
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

357 Python tests, 27 frontend contracts, Ruff, TypeScript/format/build, compile
and whitespace checks pass locally, along with all 12 existing Chromium scenarios
and two actual-release browser checks. Thirteen new Python regressions cover the
production boundaries. actionlint 1.7.12 passes without ShellCheck integration.
Hosted Python 3.11/3.12/3.13 and dashboard results for the pushed commit are
reported on the PR. No hosted production result is inferred from these checks.
The old coverage percentage remains informational, not today's measurement.

## Next highest-priority unit

Review/merge PR #18 and the stacked production workflow through the owner's
normal process, configure this repository's Pages source/environment, then run
one manual bootstrap from main. Verify the actual remote release download/replay,
public content hash, desktop/mobile rendering and failure preservation. The
connector cannot upload binary assets, dispatch a new workflow or inspect/configure
Pages settings; this run does not claim that those hosted operations succeeded.
The checked-in main-only workflow supplies the reviewed execution path after merge.

Use the production runbook for retries and retained drafts. Do not weaken freshness
or completion gates to activate it. Scheduled refresh is Tuesday/Friday at 16:17
UTC and is independent of both Codex development automations. Public GitHub hosting
is the intended zero-cost route; no purchases/upgrades have been made or authorized.

## Unfinished release gates

Actual hosted retention/deployment and independent refresh have not yet been
verified. Preserve all original/corrected release packages; their current/prior
Explorer closures do not retain every research store. The 128 MiB archive bound
requires a reviewed growth strategy if exceeded. Administrative deletion and
out-of-band deployment remain outside the workflow's guarantees.

Calibrated player uncertainty, general exposure/stints, defensible attribution,
cross-position admission and ranked/history views remain incomplete. Defense
requires permitted workload sources, live-like missingness, verified roles,
additional seasons and absence/uncertainty evidence. Do not convert event counts
into scores or tune on the already observed evaluation outcomes. An exploratory
website does not satisfy the original MVP-ranking objective.
