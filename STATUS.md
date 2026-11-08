# Project status

Updated: November 7, 2026, America/New_York.

## Current scoring milestone

The November 7 MVP target was missed. The owner requested an execution reset:
scoring is the critical path, optional infrastructure is paused, and each run must
complete substantial implementation/experiments/diagnosis/verification/decision.
There is no measured completion percentage. Use the six evidence-based
[milestones](docs/MILESTONES.md), not an unmeasured “60% remaining” claim.

On `codex/qb-model-recovery`, the [bounded QB recovery study](docs/QB_RECOVERY_RESULTS.md)
now produces cumulative first-unit and sensitivity research contrasts for **57 QBs,
122 completed 2026 games and 8,996 dropbacks**. All negative values and completed
games remain. Attribution, benchmark and unexplained components conserve EPA.

**Decision: no admission.** Learned variance components improve fixed-signal
calibration to 94.50%/93.79%, but matched-hierarchy coverage is 87.09%; fresh
failure-analysis draws give 88.32%, versus 95.00% with known synthetic variances.
The 2024 final-test and 2026 transfer predictive intervals both cross zero.
QB/team allocation remains consequentially assumption-dependent: a witness that preserves every play prediction changes a season contrast by 80.16 EP, and variance sensitivities
move contrasts by up to 13.97 EP. Full details and exact hashes are in the
[research audit](docs/audits/2026-11-07-qb-recovery.json). None is a ranked MVP score.

Twenty-three QB participation denominators satisfy the existing narrow proof;
34 remain unresolved. Qualification is separate from model/benchmark membership.
All 17 modules remain unadmitted. The defensive information-loss experiment and
Defense Explorer remain required and delivered; unsupported value remains null.

Next: preregister and complete a bounded multi-season QB/team-season recovery unit
using historical transitions and variance-component uncertainty, plus the same
identifiability/variance diagnosis on the existing defensive designs. Do not tune
on the now-consumed 2024 or archived 2026 tests. A positive contribution module
still needs calibrated, stable first-unit estimates and justified admission.

## Deployment and execution state

PRs #18 and #19 were merged by the owner; canonical main is `1ee2486` and its
hosted matrix/dashboard CI passed. The Explorer release/retention/refresh workflow
is merged code, not an activated website. Current inspection found no production
run, a signed-out browser, and “Site not found” at the Pages URL. Authenticated
Pages configuration and a manual bootstrap remain blocked by access. The
[production runbook](docs/PRODUCTION_REFRESH.md) already supplies the steps;
this did not block independent model work. An Explorer deployment would still
not be an admitted CAVAA leaderboard.

The existing daily automation prompt and repository instructions now prioritize
model milestones and substantial coherent runs. Its identity, ACTIVE status,
target chat and **7:30 PM America/New_York** recurrence remain unchanged. The
other NFL project and its automation were not touched. No purchases or new runtime
dependencies. The current PR's verification is recorded separately from main CI.

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

The recovery unit passes `make check`: 373 Python tests, 27 frontend contracts,
Ruff/adopted formatting, TypeScript, production build, compile and whitespace.
The full real-source recovery and variance control replay with HTTP forbidden.
Earlier production browser rehearsals remain documented in their dated audit;
this model-only run does not represent them as a new hosted deployment check.
Hosted CI for the new PR is reported separately. Existing coverage remains
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
