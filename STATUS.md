# Project status

Updated for the November 17, 2026 run, finalized November 18 (America/New_York).
Times and producer revisions are retained in the execution audit.

## Current scoring milestone

The November 7 target was missed. No CAVAA module or MVP ranking is admitted, and
there is no measured completion percentage. Scoring remains the critical path;
optional infrastructure is paused. Track implementation, scientific evidence and
blockers separately in [M1–M6](docs/MILESTONES.md).

The [integration-aware study](docs/INTEGRATION_CONTROL_RESULTS.md) completes the
candidate frozen in 471fe97. All five known-answer gates pass on 5,120 trials:
joint numerical coverage 94.9219%–96.4844%. Two complete offline executions match
the manifest and all 11 objects. A checkpoint-size failure was diagnosed and
repaired without changing numerical calculations or the 128 MiB limit; the whole
study was recomputed under the corrected source fingerprint.

All five archived cases complete within the original work/time caps, using 88,065
evaluations each. Only the team control passes. The primary QB fails at
**0.011896 posterior SD / 0.001095 CDF**, including numerical error, against
**0.01 / 0.001**. Both prior sensitivities and all three stress cases fail. The
paired plain QB result is only slightly worse. Both full independent NFL executions reproduce the manifest and all 11 objects
byte-for-byte, including every failed comparison.

**Decision: reject this candidate for numerical certification.** The failure
analysis identifies a ratio-objective mismatch: reducing numerator variance can
worsen the normalized estimate by disrupting covariance with its shared mass.
For the QB's upper-CDF contrasts, this occurs for 164/171 during fitting and all
171 during evaluation. An independent analytical regression protects the diagnosis.
Mean precision remains insufficient; a separate hierarchy stress case concentrates
10.3866% of mass in one replicate. Fixing cancellation alone is not a complete fix.
No player interval, prior, benchmark, admission rule or sealed Week 10 outcome changed.

Next freeze a bounded joint mass/numerator fit targeting normalized functional
variance, with analytic tail-stress controls, fresh numerical draws and unchanged
original gates. It is not implemented or adopted. Do not select the paired plain
result, retry favorable seeds, widen intervals or treat numerical coverage as
player calibration. The original 192-fit player-calibration study remains unfinished.

The unchanged archive has 57 QBs / 122 completed 2026 games / 8,996 dropbacks,
37 first-unit members, 57 sensitivity members and 38 negative first-unit estimates.
Training uses 48,776 dropbacks across 2024–26 without adding historical points.
The cohort ends November 7 at 20:41:17 Eastern; evidence cutoff remains
2026-11-08T02:47:32.067979Z. This is not November 17 live coverage. Original
model/prediction objects and nonduplicated season accounting remain intact.

## Other product milestones

Twenty-three narrow QB participation denominators remain proven; 34 are unresolved,
not automatically ineligible (32 lack full-team-game participation evidence; two
lack one-team windows). Resolve stint/missed-game evidence independently of
benchmark membership and the model observation population.

The required defensive information-loss experiment and Defense Explorer remain:
131 games / 15,803 plays / 895 defenders; residualized rank 856 versus 193 after
aggregation. The November 17 metadata audit finds no 2026-named asset among 46 in
the checked participation release. This is not all-provider absence or game-level
coverage. Live lineups, defensive uncertainty and comparability remain unfinished.
No event-count CAVAA is invented or unsupported contribution converted to zero.

The React/TypeScript dashboard has explanations, provenance and availability views,
but no admitted leaderboard or ranked history. Its next scored input must retain
validated scope, uncertainty and the three benchmark comparisons.

## Deployment and execution state

Inspected main remains 0a586a1. PRs #29 and #30 are open;
[PR #31](https://github.com/AryanParte/nfl-player-value/pull/31) is explicitly stacked
on #30 at c49fafc. No agent merge or history rewrite occurred. Pending review did
not prevent independent modeling work.

November 17 repository metadata reports no Pages site. The latest returned
scheduled Explorer run remains [43515405405](https://github.com/AryanParte/nfl-player-value/actions/runs/43515405405),
requiring the first manual bootstrap. No deployment or settings change was made.
Authenticated Pages/bootstrap, actual remote retention/replay and live-site
verification remain open; see the [runbook](docs/PRODUCTION_REFRESH.md). An Explorer
deployment would still not be an admitted CAVAA leaderboard.

Final local make check passes 487 Python tests and 27 frontend contracts, plus
Ruff/format, TypeScript/build, syntax and whitespace. Diagnostic source 53a4c71
passes hosted Python 3.11–3.13 and dashboard/browser checks in
[run 44238231094](https://github.com/AryanParte/nfl-player-value/actions/runs/44238231094).
The final reporting-head CI is inspected separately. See the
[learning report](docs/learning/2026-11-17.md) for review focus and limitations.
These are software checks, not scientific admission.

No new dependency, purchase, paid service, main push, other-repository edit or
7:30 PM America/New_York automation change. Added recurring service cost is zero.
Production refresh remains independent. Local immutable study stores are not
durable remote research retention.

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
