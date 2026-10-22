# Historical defensive experiment inputs

The dedicated adapter captures FTN participation for 2023–2025. The first live
row-level audit is for 2025; the other seasons still need their own coverage audit.
The [nflreadr declaration](https://github.com/nflverse/nflreadr/blob/main/R/load_participation.R)
attributes these data to **FTN Data via nflverse** under
[CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
It describes release after the postseason. There is no verified live 2026
participation feed. Pre-2023 NGS sources need separate review and an adapter.

The raw receipt archives exact bytes, GitHub's published SHA-256, release metadata,
retrieval times, the legal text and the source's declaration. Participation uses
receipt version 2; existing version 1 receipts remain replayable unchanged. The
software's MIT license does not replace source-data terms. Each derived view
carries attribution, the CC-BY-SA identifier/link, source receipts, code revision,
cutoff and transformation policy. Do not publish FTN-derived tables under an
unqualified software-only license. Raw and derived data stay outside Git.

## Fixed cohort policy

`complete-game-reg-pass-run-v1` is a deliberately conservative research input rule:

1. Reconcile regular-season games using terminal PBP markers and schedule scores.
2. Consider PBP `play_type=pass|run`. Exclude explicit kneels, spikes and two-point
   attempts. No-play penalties and special teams are outside this estimand. Sacks
   and scrambles occur once in the source play stream; no extra event rows are added.
3. Require finite EPA and preplay down, distance, field position, clock, quarter
   and offense-relative score differential. Reject unknown exclusion flags.
4. Join on canonical nflverse game ID and integer play ID. Require possession/team
   agreement, 11 distinct canonical GSIS IDs per side, no side overlap, agreement
   with both count fields and the 22-player union. IDs are syntactically checked;
   a separate roster crosswalk and position/assignment validation remain necessary.
5. Include a game in **both** paired views only when every candidate play passes
   and both defensive sides have observations. Preserve every rejected reason,
   missing join, excluded game and removed-play count in the audit.

The complete-game policy prevents incomplete lineup coverage from masquerading as
a full game's workload. It can create selection bias: compare excluded games,
teams and game states before fitting. A later sensitivity policy must be versioned
and reported, never silently relaxed to improve coefficients or recover a favorite
player. Excluding a 12-player row does not prove that the source is wrong; illegal
personnel can occur in football. This policy models ordinary 11-versus-11 exposure.

## What the two views mean

The rich view has one row per accepted play with both lineups and preplay context.
Its outcome is `defense_epa = -epa`: positive values mean the offense lost expected
points. This is a **team outcome**, not an individual defender's score or CAVAA.

The degraded view has one row per defensive team-game: outcome sum/mean,
opportunity count, mean context, and defender appearance counts/fractions. It
contains no play IDs, per-play lineups, offense player IDs, pressure, time to throw,
routes or coverage labels. A defender on 30 of 60 accepted plays gets a 0.5
fraction. These are fractions of eligible pass/run plays, **not official total
defensive snaps or pass-rush opportunities**. Both views share a hash of identical
game/play keys and retain identical outcomes; team outcomes are not distributed
among players at this stage.

This is a controlled aggregation experiment input, not a demonstrated replica of
live 2026 data. Permitted live workload sources, event coverage and their actual
missingness remain dependencies. Do not use historical availability to imply live
availability. The experiment must add a source-matched degradation and assess
selection bias before any defensive admission decision.

No postplay pressure or time-to-throw adjustment is used. Even preplay state can
reflect earlier player-created value; fixed observed-context contrasts do not
identify the total causal effect of a replacement. Aggregated context/workload
describes realized games, so it cannot be treated as known pregame forecasting
input. Split by whole games/chronological cutoffs; never randomly split teammate
rows or use future seasons for training.

## Reproduce

Run from the canonical repository with the development lease held and source code
committed. Capture requires network access; build and replay require only local
archived objects. Substitute the exact receipt IDs and an aware cutoff at or after
all source retrievals:

```sh
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture participation --season 2025
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture pbp --season 2025
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture schedules --season 2025
PYTHONPATH=src python3 -m nfl_value.defense_cli build \
  --participation PARTICIPATION_RECEIPT --pbp PBP_RECEIPT \
  --schedules SCHEDULE_RECEIPT --cutoff ISO_TIMESTAMP
PYTHONPATH=src python3 -m nfl_value.defense_cli replay REPORT_ID
```

Defaults are `data/raw/source-snapshots` and `data/derived/defense-inputs`.
The report references content-addressed rich and degraded JSON objects. Offline
replay revalidates source receipts and regenerates both objects and the report;
it checks exact bytes without updating a latest pointer. A successful CLI exit
means a reproducible diagnostic, even when coverage is empty or blocked. Every
report retains `experiment_run=false` and `ranking_ready=false`. Durable remote
retention and model fitting remain separate work.
