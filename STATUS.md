# Project status

Updated: November 13, 2026, America/New_York.

## Current scoring milestone

The November 7 target was missed. There is no usable admitted MVP ranking or
measured completion percentage. Scoring remains the critical path; optional
infrastructure is paused. Track implementation, evidence and blockers separately
in [M1–M6](docs/MILESTONES.md).

The [density-stabilization unit](docs/DENSITY_HOLDOUT_RESULTS.md) implements and
evaluates one frozen alternative, independent paired density holdouts, five
known-answer coverage controls and the gated archived numerical pilot. All 5,120
control trials complete: joint coverage is 94.43–96.39%, precision is 100%, and
all deliberately wrong endpoints are rejected. All 160 known-target density
pairs and 19/20 archived pairs finish; one factorization failure remains recorded.
Stabilization improves every real-QB held-out log score, but individual proposals
still differ sharply in quality. This is numerical evidence, not player calibration.

The real QB reference still fails: worst discrepancy plus numerical error is
0.014228 posterior SD / 0.001308 CDF against unchanged 0.01 / 0.001 limits.
Reference error is much smaller than in the previous run; remaining point
discrepancies now matter, but no real-QB confidence set establishes an error
outside tolerance. The team control passes. A separate frozen trace reproduces
the prior-stress factorization failure: a 9.66e-24 precision is lost at matrix
roundoff scale. No jitter, zero-likelihood substitution or altered prior repairs
that failed trial. Full case decisions and replay evidence are in the results.

The same 57 QBs / 122 completed archived 2026 games / 8,996 dropbacks retain
first-unit/equal-player/opportunity-weighted contrasts, 38 negative first-unit
estimates and nonduplicated season accounting. Training totals 48,776 dropbacks
across 2024–26 without adding historical points. The game cohort ends November 7
at 20:41:17 Eastern; the evidence cutoff is 2026-11-08T02:47:32.067979Z. This is
not November 13 live coverage. No new calibration or sealed Week 10 outcomes enter
this study. The 192-fit calibration remains unfinished. All 17 modules remain
unadmitted, with unsupported contributions unavailable.

Next: freeze a target-preserving conditional-solver repair/equivalence study using
exact alias/weak-precision controls and an independent reference. Resolve the
roundoff failure before another proposal search. Then diagnose remaining
primary/reference disagreement with separately declared independent randomizations
and work limits. Do not automatically enlarge primary samples, choose favorable
pilots, change priors or relax accuracy limits. Numerical reliability precedes
fresh calibration, prospective prediction and observational admission.

## Other product milestones

Twenty-three narrow QB participation denominators remain proven; 34 are unresolved,
not automatically ineligible (32 lack full-team-game participation evidence; two
lack one-team windows). Stint/missed-game evidence remains open. Eligibility is
independent of benchmark membership and the model's observation population.

The required defensive information-loss experiment and Defense Explorer remain
intact: 131 games / 15,803 plays / 895 defenders, residualized rank 856 versus 193
after aggregation. November 13 metadata still has no 2026-named asset among 46
in the checked participation release. This is not all-provider absence or a
snap-count audit. Live lineups, defensive uncertainty and cross-position
comparability remain unfinished. Event counts are not invented CAVAA scores.

The React/TypeScript dashboard has explanation/provenance and availability views,
but no admitted leaderboard or ranked history. Its next scored input must be a
defensibly validated contribution module with scope and uncertainty preserved.

## Deployment and execution state

PRs #18–#26 are merged; inspected main is e28bdb2 and its CI passes. November 13
rechecks still show no Pages site, a signed-out in-app browser, and scheduled
Explorer run 42908770888 blocked before capture/publication by the initial-retention
safeguard. The connector lacks Pages configuration/dispatch. See the
[runbook](docs/PRODUCTION_REFRESH.md). No settings, schedules or release changed.
This operational blocker did not prevent model work; an Explorer deployment would
still not constitute an admitted CAVAA leaderboard.

[PR #27](https://github.com/AryanParte/nfl-player-value/pull/27) targets current main.
Local make check passes 441 Python tests and 27 frontend contracts plus lint,
formatting, TypeScript/build, syntax and whitespace. Hosted Python 3.11/3.12/3.13
and dashboard/Chromium pass on pilot source f3e854c; final-head CI is reported in
the PR. The [learning report](docs/learning/2026-11-13.md) leads with milestone
outcomes, numerical failures and next actions rather than activity counts.

No dependency, purchase, paid service, agent merge, other-repository edit or
7:30 PM America/New_York automation change. Production refresh remains independent
of development. Local immutable research/replay stores are not yet durable remote
research retention. Software checks and exact replay do not establish attribution.

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
