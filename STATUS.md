# Project status

Updated: November 10, 2026, America/New_York.

## Current scoring milestone

The November 7 MVP target was missed. Scoring remains the critical path and
optional infrastructure is paused. There is no measured completion percentage.
Use the six evidence-based [milestones](docs/MILESTONES.md).

The [numerical-reference unit](docs/VARIANCE_REFERENCE_RESULTS.md) implements a
more stable sampler for the existing continuous-variance QB model, an independent
adaptive reference, exact node reuse and complete error diagnostics within fixed
work limits. It retains **57 QBs / 122 archived 2026 games / 8,996 dropbacks**;
48,776 historical/current dropbacks inform estimation. The archive ends November 7
at 20:41:17 Eastern, not November 10 live coverage. All three benchmarks, negative
contributions, season-only accounting and separate qualification remain intact.

**Decision: no admission.** All five original sampler checks pass, including both
real QB prior sensitivities. The primary QB minimum effective sample size rises
from 76.17 to 1,077.07; independent mean disagreement falls from 0.03775 to 0.00696
posterior SD. Every original reference exhausts 90,000 solves. Two independent
builds reproduce the manifest, models and results byte-for-byte, including failures.
The exact-reuse follow-up retains complete reference estimates; both real models
still fail. The QB primary mean discrepancy plus estimated error is 0.02449 SD
(limit 0.01), and endpoint-CDF discrepancy plus estimated error is 0.03256
(limit 0.001). The team control also remains nonconverged. Raw numerical agreement
without an accurate reference is insufficient. All five follow-up references fail;
none is omitted. The follow-up also reproduces
byte-for-byte offline, with model/result bytes unchanged from the original pilot.
The linked result/audit records every case and exact evidence.

This is a numerical pilot, not fresh calibration. Its three synthetic draws were
already consumed. The earlier 192-fit calibration remains unfinished and Week 10
remains sealed/uninspected. QB/team allocation remains assumption-dependent. All
17 modules remain unadmitted; no research estimate is presented as an MVP score.

Next: preregister and validate a more efficient independent reference, with
unchanged posterior/accuracy rules. The measured all-axis subdivision cost makes
dimension-adaptive refinement a bounded next candidate; prove its error behavior
on known targets before reusing these consumed stress cases. Do not launch another
full calibration campaign until numerical reliability passes. Then complete fresh
calibration, prospective evaluation and the observational admission review.

## Other product milestones

Twenty-three QB participation denominators satisfy the existing narrow proof;
34 remain unresolved, not automatically ineligible. Qualification stays independent
of benchmark/model populations. Exact stints and missed-game evidence remain open.

The required defensive experiment and Defense Explorer remain intact. The same
131 games / 15,803 plays / 895 defenders show residualized rank falling from 856
to 193 after aggregation. These are diagnostics, not defensive CAVAA. November 10
metadata still finds no 2026-named participation asset among 46 in the checked
release; that is not absence across every provider. Live workloads, defensive
uncertainty and cross-position comparability remain unfinished.

The dashboard exposes data limitations and module availability. It has no admitted
CAVAA leaderboard or ranked history. Its next scoring input must be the first
validated contribution module with benchmarks, uncertainty and scope preserved.

## Deployment and execution state

PRs #18/#19/#20 were owner-merged; inspected main remains `6eb68ed`. The Explorer
workflow is merged preparation, not an activated website. November 10 API reports
`has_pages: false`; the browser visibly shows Sign in and No releases published.
Local `gh` is absent; the connector cannot configure Pages or dispatch the workflow.
No settings changed. Authenticated Pages/bootstrap and remote retention/replay
remain unfinished, as described in the [runbook](docs/PRODUCTION_REFRESH.md).
This did not block modeling. Explorer deployment would not admit CAVAA scores.

[PR #23](https://github.com/AryanParte/nfl-player-value/pull/23) is stacked on PR #22,
which depends on PR #21. Local `make check` passes 404 Python tests, 27 frontend
contracts, Ruff/adopted formatting, TypeScript/build, compile and whitespace.
Hosted Python 3.11/3.12/3.13 and dashboard/Chromium checks pass on the producing
source. See the [learning report](docs/learning/2026-11-10.md) for exact CI evidence,
review focus and scientific limits. Tests passing is separate from model admission.

No automation settings, other repository, dependency or paid service changed.
The existing **7:30 PM America/New_York** development recurrence is preserved;
production refresh remains independent. No merge, force-push or main implementation
push was performed.

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
