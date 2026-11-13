# Project status

Updated: November 12, 2026, America/New_York.

## Current scoring milestone

The November 7 MVP target was missed. Scoring remains the critical path; optional
infrastructure is paused. There is no measured completion percentage. Track the
six [milestones](docs/MILESTONES.md), separating implementation from evidence.

The additional manual [replicated randomized-reference unit](docs/RANDOMIZED_REFERENCE_RESULTS.md)
implements numerical-error coverage controls, density-only sampling adaptation,
verified control certificates and archived model evaluation. Both initial proposals
fail; the first adapted study also fails its tail coverage gate. A separately
frozen, more informative confirmation retains the identical proposal and all
limits: its four known-answer gates pass with 94.34–95.31% measured joint coverage
and 99.12–100% precision. Earlier failures remain unchanged and independently replay.

This does not clear the scoring gate. The real QB reference fails at worst
0.030273 posterior SD / 0.001951 CDF discrepancy plus numerical error, above the
unchanged 0.01 / 0.001 limits. The team-only control passes. In the real QB case,
reference uncertainty dominates the failure; no confidence set establishes a
beyond-tolerance disagreement with the primary calculation. Known-answer coverage
is not guaranteed precision for the NFL target or player-uncertainty calibration.
All five cases finish: one passes and four fail. The independent offline rebuild
has identical manifest/model/result bytes. No contribution module is admitted.

The same 57 QBs / 122 archived completed 2026 games / 8,996 dropbacks retain
first-unit/equal-player/opportunity-weighted contrasts, negative values and
nonduplicated season-only accounting. Training across 2024–26 totals 48,776
dropbacks, without adding historical points. Coverage ends November 7 at 20:41:17
Eastern, not November 12 live coverage. The 192-fit calibration remains unfinished;
no fresh calibration or Week 10 outcomes are used. QB/team allocation continues
to depend on explicit hierarchical assumptions. Full case outcomes, provenance,
offline reconstruction and the failure decomposition are in the linked results.

Next: freeze a density-only holdout study of proposal instability/poor importance
overlap, comparing the current fit with one justified stabilized proposal. The
QB density pilot has only 187.6 effective samples from 4,096 points and a selected
mixture fit that hits covariance floors. The hierarchy stress pilot has only
5.8 effective samples and all three fitting starts reach their iteration cap.
These are warning signs, not a proven cause. Measure held-out precision before
another NFL comparison. Preserve the posterior, functional limits and failures;
do not automatically escalate primary samples. Numerical reliability must precede fresh calibration, prospective
prediction and observational admission. No score is published to satisfy a date.

## Other product milestones

Twenty-three narrow QB participation denominators remain proven; 34 are unresolved,
not automatically ineligible. Exact stint/missed-game evidence remains open.
Eligibility stays independent of the model and benchmark populations.

The required defensive information-loss experiment and Defense Explorer remain
intact: same 131 games / 15,803 plays / 895 defenders, residualized rank 856 versus
193 after aggregation. November 12 metadata has no 2026-named asset among 46 in
the checked participation release; this is not absence across every provider or
a game-level snap-count audit. Live lineup/role evidence, defensive uncertainty
and cross-position comparability remain unfinished. All 17 modules stay unadmitted.

The dashboard has explanation/provenance and availability views, but no admitted
MVP leaderboard or ranked history. Its next input must be a defensibly validated
contribution module with scope, benchmarks and uncertainty preserved.

## Deployment and execution state

PRs #18–#25 are merged; inspected main is `55e8f02` and its CI passed. The earlier
November 12 deployment audit found that the latest
scheduled [Explorer run](https://github.com/AryanParte/nfl-player-value/actions/runs/42908770888)
still fails at the first-bootstrap safeguard: no retained Explorer exists.
Offline gates passed; capture/publishing were skipped. The API reports no Pages
site; the connector lacks settings/dispatch and local `gh` is absent. See the
[runbook](docs/PRODUCTION_REFRESH.md). No bypass or settings change occurred.
Explorer-only deployment would not admit an MVP leaderboard.

[PR #26](https://github.com/AryanParte/nfl-player-value/pull/26) targets current main.
Local checks pass 432 Python tests and 27 frontend contracts, Ruff/adopted
formatting, TypeScript/build, syntax and whitespace. Hosted Python 3.11/3.12/3.13
and dashboard/Chromium pass on the producing pilot source; final-head status is
reported in the PR. The [learning report](docs/learning/2026-11-12.md) distinguishes
this additional manual unit from the earlier daily run. Passing software tests
is separate from statistical validation.

No new dependency, paid service, automation change, agent merge or other-repository edit.
The daily **7:30 PM America/New_York** identity/schedule is preserved; weekly
production refresh remains independent. Research stores remain locally retained;
byte-identical local replay does not establish durable remote storage.

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
