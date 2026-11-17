# Project status

Updated: November 16, 2026, America/New_York.

## Current scoring milestone

The November 7 target was missed. There is no admitted MVP ranking or measured
completion percentage. Scoring remains the critical path; optional infrastructure
is paused. Track implementation, evidence and blockers separately in
[M1–M6](docs/MILESTONES.md).

The [coarse control-variate study](docs/COARSE_CONTROL_RESULTS.md) implements one
candidate frozen in d60052d: independently fitted zero-mean Gaussian controls,
separate fitting/evaluation draws, unchanged posterior and numerical limits.
All five known-answer gates pass on 5,120 complete trials. Joint coverage ranges
from 94.9219% to 96.1914%; every deliberately incorrect endpoint is rejected.
Two complete network-disabled executions reproduce the same manifest and all 11
objects. This is numerical-error evidence on the controls, not player calibration.

The archived real-QB comparison fails at **0.013312 posterior SD / 0.001137 CDF**
including numerical error, against **0.01 / 0.001** limits. Its paired plain
calculation is nearly identical and slightly better. Improvement over yesterday's
seed cannot be credited to the new method. All five cases complete within their
original budgets; only the team control passes. Both full offline executions match the manifest and all six objects.
The [NFL audit](docs/audits/2026-11-16-coarse-nfl.json) retains every failed comparison.

Known-target adjusted/plain empirical variance ranges from 0.442 to 1.778 despite
smaller regression residuals. The QB's conditional variance changes are modest
and insufficient for certification. No primary estimate, player interval, prior,
benchmark, admission rule or sealed Week 10 outcome changed. All 17 modules remain
unadmitted; the original 192-fit player calibration remains unfinished.

The unchanged archive has 57 QBs / 122 completed 2026 games / 8,996 dropbacks,
37 first-unit members, 57 sensitivity members and 38 negative first-unit estimates.
Training uses 48,776 dropbacks across 2024–26 without adding historical points.
The cohort ends November 7 at 20:41:17 Eastern; evidence cutoff remains
2026-11-08T02:47:32.067979Z. This is not November 16 live coverage.
Original model/prediction objects and nonduplicated season accounting remain intact.

Decision: reject this pointwise-fitted candidate for numerical certification.
Next freeze a bounded candidate fitting coefficients to independent
integration-replicate means, addressing the measured mismatch between pointwise
regression and randomized integration. It needs a fresh frozen design, matching
training/evaluation net sizes, bounded work and known-answer validation; it is
not an adopted method. Do not select the paired plain calculation after results,
retry favorable seeds, widen player intervals or add fine work to fix coarse error.
Numerical certification still precedes fresh calibration and observational admission.

## Other product milestones

Twenty-three narrow QB participation denominators remain proven; 34 are unresolved,
not automatically ineligible (32 lack full-team-game participation evidence; two
lack one-team windows). Resolve stint/missed-game evidence without changing
benchmark membership or the model observation population.

The required defensive information-loss experiment and Defense Explorer remain:
131 games / 15,803 plays / 895 defenders, residualized rank 856 versus 193 after
aggregation. The November 16 metadata check finds no 2026-named asset among 46 in
the checked participation release. This is not all-provider absence or a game-level
coverage audit. Live lineups, defensive uncertainty and cross-position comparability
remain unfinished. No event-count CAVAA is invented.

The React/TypeScript dashboard has explanation/provenance and availability views,
but no admitted leaderboard or ranked history. Its next scored input must be a
validated contribution module with scope, uncertainty and sensitivities preserved.

## Deployment and execution state

Inspected main remains 0a586a1. PR #29 is open; [PR #30](https://github.com/AryanParte/nfl-player-value/pull/30)
is explicitly stacked on it. No agent merge or history rewrite occurred. Pending
review did not block the new numerical implementation and experiments.

November 16 repository metadata still reports no Pages site. The last inspected
Explorer failure remains [43515405405](https://github.com/AryanParte/nfl-player-value/actions/runs/43515405405),
which requires the first manual bootstrap. This model unit made no new deployment
attempt or settings change. Authenticated Pages/bootstrap, actual remote retention/
replay and live-site verification remain open; see the [runbook](docs/PRODUCTION_REFRESH.md).
An Explorer deployment would still not be an admitted CAVAA leaderboard.

Local make check passes 477 Python tests and 27 frontend contracts for the final
changes, plus Ruff/format, TypeScript/build, syntax and whitespace. Hosted
[run 43999147468](https://github.com/AryanParte/nfl-player-value/actions/runs/43999147468)
passes Python 3.11–3.13 and dashboard checks, including 12 Chromium scenarios.
Final reporting-head CI is inspected separately. The
[learning report](docs/learning/2026-11-16.md) explains the numerical/scientific
limits and review focus. Exact replay and software checks are not attribution.

No new dependency, purchase, paid service, main push, other-repository edit or
7:30 PM America/New_York automation change. Added recurring service cost is zero.
Production refresh remains independent. Local immutable research/replay stores
are not durable remote research retention.

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
