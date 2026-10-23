# Completed-game evidence and first-unit inputs

This unit derives **candidate modeling inputs**, not CAVAA scores, from verified
source receipts. Run it offline. An immutable diagnostic report preserves missing
games, unresolved role cells, source versions, cutoff, policy versions and code
revision. No latest-ranking pointer is changed.

## Schedule and completion policy

The [nflverse schedules release](https://github.com/nflverse/nflverse-data/releases/tag/schedules)
publishes `games.csv.gz`, maintained by Lee Sharpe in `nfldata`. Capture uses the
release's published SHA-256, metadata and the repository's declared CC-BY-4.0
license, with explicit attribution. The MIT license of a loader is not the data
license. Raw bytes include all seasons; the audit normalizes the requested season.
Only regular-season games enter the MVP window.

The [source dictionary](https://github.com/nflverse/nflreadr/blob/main/data-raw/dictionary_schedules.csv)
defines kickoff in Eastern time. `zoneinfo` applies daylight-saving rules, including
January games belonging to the previous season. The runtime must provide the
IANA timezone database (available on our local machine and CI runners). A missing
kickoff for a due game blocks coverage; a future TBD game is listed separately.

The schedule does **not** expose an explicit final-status flag. New input reports
use `clock-marker-schedule-v2`: require a single PBP `END_GAME` record, matching
team identities and final scores, plus compatible quarter/clock evidence. Neither scores alone,
a present file, nor a zero game clock establish completion. An overtime game can
end with time remaining. Every scheduled regular-season game due by the cutoff
is reconciled; missing PBP or unresolved completion remains visible and blocks
the full game universe. There is no silent omission of an inconvenient game.

The end marker must occur in quarter 4 at clock zero, or in overtime (quarter 5,
possibly with time remaining). No timed event can be later than the marker by
quarter and remaining quarter time. A higher-ID event at exactly the same clock
is unresolved, because the ordering is ambiguous. Non-event `COMMENT` records
are the only rows allowed to lack a clock. Other missing/invalid clocks block the
game. A timeout or kneel with a higher numeric ID is accepted when its clock is
strictly earlier than the marker. This is a conservative evidence rule, not a
claim that game clocks uniquely order every event.

Version 1 required the marker to have the highest numeric play ID. The 2025 audit
found two completed games violating that assumption. Old version-1 reports still
replay with their original rule and exclusions; new pregame/defensive reports use
report version 2. Source receipts do not change. A correction is a new report,
never a silent rewrite of the old result.

`completion_observed_by` is the later retrieval of PBP and schedule. It is a
conservative known-complete-by bound, **not an exact final-whistle timestamp**.
When passed to `CompletedTeamGame.completed_at`, it retains that interpretation.
The cutoff cannot predate the input receipts. This deliberately does not claim
that an October download was available for a September live publication.

This is cross-file corroboration, not an independent NFL status feed. Upstream
errors can be correlated, and a schedule can itself be incomplete. Archive its
full inventory and report counts. A live-status feed is a later enhancement;
production must retain last-good output whenever these conservative gates fail.

## First-unit selection

Using the [2025+ depth-chart schema](https://nflreadr.nflverse.com/articles/dictionary_depth_charts.html),
select the latest whole **team snapshot strictly before scheduled kickoff**.
Inspect quality after selecting it: never backfill a missing slot from an older
snapshot or promote a lower-ranked player to make the cohort complete. Snapshot
age must be at most 72 hours. This is a provisional freshness policy for a daily
feed, not an empirically chosen talent or leaderboard threshold; record failures
before changing it.

The reviewed formation layouts are source group 21 (`3WR 1TE`), 16 (`Base 4-3 D`),
15 (`Base 3-4 D`) and 18 (`Special Teams`). Source evidence reveals an important
convention: WR slots 1, 2 and 8 have first-unit **ranks 1, 2 and 3**. Filtering
`pos_rank == 1` would omit two starting receivers. The adapter requires those
specific slots/ranks, retaining all three. A rank-5 receiver in slot 2 does not
substitute for a missing rank-2 row.

The mapping preserves QB, RB, WR, TE, OT, OG and C cells. It treats a 4-3 end as
EDGE, a 3-4 end/nose as IDL, and a 3-4 outside linebacker as EDGE. These defensive
roles are **chart-based proxies**, not demonstrated rushing/coverage assignments.
Each defensive chart includes nickel as an additional CB role; it does not
describe twelve simultaneous defenders. A CB also listed at nickel is counted
once. A player listed in different defensive model roles blocks the affected
cells pending review. Unknown layouts, ambiguous formations and duplicate
offensive starters also block the relevant cells.

Fullback is not silently mixed into RB, and holder is not silently mixed into P.
Specialist memberships do not establish specialist eligibility or attribution.
Canonical GSIS and ESPN identities must be present and consistent. No name-based
joins, legacy-ID guesses, box-score substitutions or outcome-based membership
selection are performed.

`require_benchmark_inputs(report, role)` checks **whole-game coverage**, season
team coverage and every team-game/role cell before returning benchmark inputs.
It rejects a partial positional population even when some cells are usable.
It also requires an explicit `allow_retrospective=True` for research using depth
archives retrieved after kickoff. This acknowledgment does not certify that the
source's historical timestamps exclude later corrections. Current versions can
support retrospective analysis; vintage live-information backtests need stronger
availability evidence. Selection never uses leaderboard qualification or snaps.

Charts do not prove that a player appeared, was active, signed on a given date,
or belonged to a roster for every game. Historical stints, late signings,
missed-game exposure, and snap/opportunity denominators remain separate work.
The required defensive participation experiment also remains separate.

## Reproduce a report

Acquire the development lease before local writes. Commit source changes first
so every receipt/report identifies the code that actually ran. Capture schedules
through the same CLI used for PBP and depth charts:

```sh
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture schedules --season 2026
PYTHONPATH=src python3 -m nfl_value.pregame_cli build \
  --schedules SCHEDULE_RECEIPT --pbp PBP_RECEIPT \
  --depth-charts DEPTH_RECEIPT --cutoff AWARE_ISO_TIMESTAMP
PYTHONPATH=src python3 -m nfl_value.pregame_cli replay REPORT_ID
```

Raw receipts remain in `data/raw/source-snapshots`; reports are content-addressed
under `data/derived/pregame-inputs`. Both are ignored by Git. A checked-in audit
summary identifies the versions and findings. Replay verifies all raw receipts
and regenerates the entire report locally. A successful CLI exit means the
**diagnostic report** was produced/replayed, not that publication is permitted.
Every report retains `ranking_ready=false`. Durable off-machine raw/report
retention and model/position admission remain production requirements.
