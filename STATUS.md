# Project status

Updated for the November 25, 2026 run (America/New_York).

## Current scoring milestone

The November 7 target was missed. **No CAVAA module or MVP ranking is admitted.**
All 17 registry modules remain unavailable. Scoring remains critical; optional
infrastructure is paused. No unmeasured completion percentage is justified.
See the concrete [M1–M6 backlog](docs/MILESTONES.md).

The [endpoint-control unit](docs/ENDPOINT_CONTROL_RESULTS.md) implements and tests
an analytically centered control, diagnoses a floating-point cancellation defect,
then freezes and evaluates one arithmetic repair. All 768 original and 896 repaired
arm-trials finish; independent builds reproduce every object/manifest exactly.
Both numerical candidates are rejected for progression. The first version's correlated-mixture case passes joint
numerical coverage in only 2/32 trials, despite finding both modes in every trial.
Direct subtraction of near-one CDFs creates tiny quantized features and enormous
coefficients; independent high-precision/zero-integral checks verify the defect.

The stable increment repair passes those checks and the correlated-case screen:
32/32 precision and 30/32 joint coverage under newly frozen randomizations. It
passes 13/14 small screens, but a fresh stronger-curvature case passes precision
in only 23/32. All its means pass; nine endpoint discrepancy-plus-allowance sums
exceed .001, reaching .00130947. Coefficient norms remain modest, and coarse
integration dominates endpoint variance. This is a remaining precision failure,
not grounds to widen intervals, relax gates or silently raise work limits.

Next freeze a bounded work/precision/convergence comparison of the unchanged
repaired coarse integrator, with fixed alternatives, work caps, fresh randomizations
and representative known answers. Quantify whether additional coarse computation
is useful before adopting it; no automatic top-ups or diagnostic winner selection.
Keep consumed cases as regressions. Full numerical coverage, archived comparison,
unfinished 192-fit player calibration and observational admission remain required.
The small severe-undercoverage screens are not certification of 95% coverage.
Remote mode misses remain, and some mean/endpoint RMSEs worsen versus polynomial
controls despite improved precision counts; see the complete matched comparisons.

Original model/prediction hashes are verified unchanged: 57 QBs / 122 archived
completed 2026 games / 8,996 dropbacks, 37 first-unit members, 57 sensitivity members
and 38 negative first-unit estimates. Training uses 48,776 dropbacks across 2024–26
without adding historical-season points. The archive ends November 7 at 20:41:17
Eastern; evidence cutoff is 2026-11-08T02:47:32.067979Z. This is not November 25 live
coverage. Cumulative nonduplicated accounting, all three benchmarks and negative
values remain intact. No new NFL outcomes were read; Week 10 stays sealed.

## Other product milestones

M3 remains 23/57 proven narrow QB participation denominators. Thirty-two lack
full-team-game participation and two lack one-team windows. Missing evidence is
not ineligibility; qualification remains independent of benchmark membership.

M4 retains the required defensive information-loss experiment and Defense Explorer:
131 games / 15,803 plays / 895 defenders; residualized rank 856 versus 193 after
aggregation. November 25 metadata has no 2026-named asset among 46 in the checked
participation release. That is one feed's metadata, not universal absence or
verified game coverage. Permitted lineups, roles, calibrated uncertainty and
cross-position comparability remain unfinished. No defensive score is invented.

M5 includes React/TypeScript availability, explanations and provenance. No admitted
leaderboard or ranked history exists. A scoped intermediate QB module does not
replace the cross-position objective; unsupported contributions remain unavailable.

## Deployment and execution state

The owner merged #37 during this run; its final PR CI passed. Origin main is 9c8d2fd;
[PR #38](https://github.com/AryanParte/nfl-player-value/pull/38) now targets main.
It initially stacked on #37; no agent merge, rebase or history rewrite occurred.

The latest returned [production run 45520666532](https://github.com/AryanParte/nfl-player-value/actions/runs/45520666532)
remains the November 24 failure: `no retained Explorer; first manual run requires bootstrap`.
November 25 repository metadata still reports no Pages site. The connector lacks
dispatch/Pages configuration; no new bootstrap was attempted. Browser sign-in was
last checked November 24, not reverified today. Authenticated bootstrap, remote
retention/replay and live verification remain blocked. See the
[runbook](docs/PRODUCTION_REFRESH.md). Explorer deployment would not be an admitted
CAVAA leaderboard and does not block modeling.

Before repaired-study draws, local make check passes 560 Python tests, 27 frontend
contracts, Ruff/format, TypeScript/build, compilation and whitespace. Both numerical
producer CI runs pass all four jobs, including Python 3.11–3.13 and dashboard/browser:
[original](https://github.com/AryanParte/nfl-player-value/actions/runs/45724338274),
[repair](https://github.com/AryanParte/nfl-player-value/actions/runs/45727731668).
Final reporting-head CI is inspected separately in the PR. Numerical source remains
unchanged after the respective frozen producer starts its study. See the
[learning report](docs/learning/2026-11-25.md).

Software verification, numerical coverage and player validation remain distinct.
Raw research stores and required parents remain local; replay is not durable remote
retention. No new dependency, service cost, purchase, schedule change or other-repository
edit. The 7:30 PM America/New_York automation is unchanged.

## Earlier measured evidence (unchanged archives)

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

The earlier recovery unit passed `make check`: 373 Python tests, 27 frontend contracts,
Ruff/adopted formatting, TypeScript, production build, compile and whitespace.
The full real-source recovery and variance control replay with HTTP forbidden.
Earlier production browser rehearsals remain documented in their dated audit;
this model-only run does not represent them as a new hosted deployment check.
Hosted CI for that earlier PR is recorded in its learning report. Existing coverage remains
informational, not a fresh coverage measurement.

## Next highest-priority unit

Complete the model-centered M1/M2 unit described above, with the mandatory M4
recovery diagnosis included. Do not allow deployment access to displace this work.
Reserve fresh evaluation evidence and record a decision after meaningful trials,
not merely another isolated component or unsuccessful fit.

The bounded operational action remains authenticated Pages setup and one manual
Explorer bootstrap from main, followed by actual remote download/replay and
live-site verification. PRs #18/#19 no longer await merge. Preserve freshness,
completion and last-valid-publication safeguards. Weekly production refresh is
Tuesday/Friday at 16:17 UTC, independently of development. No paid service is
required or approved; the current access limitation is explicit in M6.

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
