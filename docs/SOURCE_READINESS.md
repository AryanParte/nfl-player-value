# Source readiness and Explorer refresh candidates

This unit adds an operational gate between archived source receipts and a new
Defense Explorer candidate. It does not admit CAVAA, deploy a website, or advance
any public pointer. A fresh source file is not evidence of valid attribution.

The [November 5 real-source audit](audits/2026-11-05-source-readiness.json)
records 121 completed games, 14,851 scoped plays and 562 players through Week 8,
at November 5, 19:04:28 America/New_York. Candidate
`a1a5fc0401401380e3c11291c96cc197f31e05947c0bd8141df879fe49cb6da8`
replays offline and passes the existing frontend schema. It retains all 93 prior
games, adds 28 and records two changed earlier team-context rows. The staged
website still uses Week 6; the new candidate is unpublished.

The four required sources remain public nflverse schedules, play-by-play, depth
charts and seasonal rosters. The existing capture CLI verifies published hashes,
schemas, licenses and retrieval chronology. Readiness replays those receipts
locally before trusting their metadata or measuring age. A missing receipt is an
explicit blocker; corrupted bytes, incompatible source kinds/seasons, schema drift
and evidence retrieved after the cutoff are errors.

## Frozen operational policy

Policy `explorer-source-readiness-2026-v1` is defined in `readiness.py` and copied
into every report with its own SHA-256. It is limited to the 2026 regular season.
Changing a limit requires a reviewed policy/code revision, not an ad hoc override.

| Input | Maximum retrieval age at cutoff | Maximum upstream asset-update age |
| --- | ---: | ---: |
| Schedule | 6 hours | 2 hours |
| Play-by-play | 6 hours | 96 hours |
| Depth charts | 6 hours | 48 hours |
| Seasonal roster names/IDs | 6 hours | 48 hours |

These are project operating limits, not empirically calibrated player-model
thresholds or an upstream service guarantee. nflverse documents schedule updates
about every five minutes, daily roster/chart updates, and PBP updates after game
days with later corrections. The schedule allowance tolerates short pipeline
delays; 48 hours allows two daily cycles. PBP's longer allowance accommodates
off-days, while exact game reconciliation independently prevents an old file from
omitting a started game. Downloading old bytes again does not reset their recorded
upstream age. An asset timestamp alone still cannot prove every record is current.
[nflverse update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html).

Depth checks additionally require each of the 32 teams to have an embedded chart
timestamp within 48 hours of cutoff. A recently rewritten file containing one
team's old chart cannot pass by relying on another team's latest row. Both chart
and roster source inventories must cover the declared team universe. This does
not certify complete player identities, exact stints, participation or workload.
Historical pregame chart selection and its retrospective labels remain unchanged.

The full schedule must contain 272 regular-season games, each canonical team in
17 games, with no duplicate team-week assignments. Counts alone do not establish
correct scheduling; they detect incomplete or malformed source inventories. A
cancellation or unusual rescheduling can conservatively block v1 and requires
explicit review rather than silently reducing the expected universe.

The existing clock-based terminal-PBP and schedule-score reconciliation runs over
the entire declared inventory. Every game already started by cutoff must reconcile
as complete. A missing feed, in-progress game, unknown due kickoff, score mismatch
or unresolved terminal evidence blocks the whole candidate. Future games and
postseason games remain excluded. This intentionally favors an older complete
view over an unexplained partial update. It is cross-file evidence from nflverse,
not an independent live final-status feed. `through_week` remains the maximum week
represented, not a promise that every game in that week has finished.

## Assess and prepare from committed code

Hold the development lease and run from the canonical repository root. Capture
each required source with `python -m nfl_value.ingest_cli capture SOURCE --season
2026`, retaining its returned receipt ID. Set the cutoff after all metadata/data/
license retrievals; do not claim an earlier historical information set.

```sh
# Substitute the four captured receipt IDs and an explicit timezone-aware cutoff.
PYTHONPATH=src .venv/bin/python -m nfl_value.readiness_cli assess \
  --cutoff 2026-11-05T21:00:00+00:00 \
  --schedules SCHEDULE_RECEIPT --pbp PBP_RECEIPT \
  --depth-charts CHART_RECEIPT --rosters ROSTER_RECEIPT
```

`assess` saves an immutable readiness report under
`data/derived/explorer-candidates/manifests/`. Missing-source/age/coverage blockers
produce structured diagnostics and exit **2**. Malformed input, corruption or IO
failure exits **1**. A successful assessment exits **0**, with
`ready_for_explorer_build=true` and `ranking_ready=false`.

Use `prepare` with the same arguments to build a candidate after the gate passes.
Supply `--previous-explorer REPORT_ID` when comparing with an existing snapshot.
The original October archive's report ID is
`497f59523ffd5f608937d82dda6a5d2abf1a8621d92ba7031df94b3a1f605435`.
Store paths can be overridden through global CLI arguments before the subcommand.

Preparation reuses the offensive ledger and Explorer builders, verifies exact
game-set and source/cutoff agreement, and requires every CAVAA/snap estimate to
remain null. It binds the readiness report/policy, producer revision, all input
receipts, offensive report, Explorer report/object and prior Explorer reference.
The result is an immutable `explorer_refresh_candidate` manifest with
`published=false`. It adds no ranking, benchmark, eligibility or model fit.

A candidate cannot regress the supplied prior cutoff or drop any prior game.
New source corrections may change earlier observed values; original objects remain
intact. The candidate records added game IDs and changed existing team-context
rows. That comparison is deliberately narrow: it does not enumerate player/name
changes or infer whether a difference was caused by a source correction or code.
Future production publication must supply its actual last-good reference; omitting
the optional reference here is not evidence of monotonic production history.

The commands have no destination/publish option and never write `latest.json`.
A blocked preparation saves its diagnostic report without building an Explorer.
A later build failure can leave valid unpublished immutable intermediate objects,
but creates no accepted candidate or pointer change. This is preparation safety,
not an implemented hosted rollback or deployment system.

## Replay versus current freshness

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.readiness_cli replay-readiness REPORT_ID
PYTHONPATH=src .venv/bin/python -m nfl_value.readiness_cli replay-candidate CANDIDATE_ID
```

Replay re-audits archived source bytes and recomputes the decision at its original
cutoff. Candidate replay also rebuilds the actual Explorer and validates its prior
reference. It rejects altered/rehashed policy, result, provenance, coverage and
manifest fields. No download is required and no current clock is substituted into
the recorded computation.

**A successful replay does not renew freshness.** The output explicitly says
`verified_at_original_cutoff_only=true`. A candidate prepared later from an older
declared cutoff is historical evidence, not a claim of readiness now. A future
publisher must perform a new assessment against its actual attempt time and bind
that assessment to the proposed source set; it cannot simply reuse a saved
positive decision. All game corrections need their new receipt IDs and cutoff.

Offline tests use synthetic source bytes through the real capture, replay,
reconciliation and Explorer builders. Ordinary PR CI makes no NFL downloads. The
dated live-source audit is separate from those tests. Snapshot checks establish
reproducibility, not causal attribution or calibrated individual uncertainty.

## Remaining release work

The production weekly refresh still needs a scheduler independent of Codex,
current-time source capture/assessment, retries, persistent storage, an immutable
release index, deployment concurrency, validated browser contracts and atomic
last-good publication. This module does not replace those controls or the
[future ranking gates](CI.md). The [recovery archive](RECOVERY.md) remains a separate
retention boundary; new source/candidate stores are not automatically included in
the old archive. Remote upload is still blocked on authenticated release access.
All 17 player-value modules remain unadmitted; an Explorer candidate is not an MVP
leaderboard and does not remove the November 7 scientific release risk.
