# Weekly position and team evidence

The versioned `weekly-roster-evidence-v1` join connects public weekly roster
observations to the archived offensive ledger's completed-game cohort. It is a
prerequisite for positional modeling and exposure reconciliation, not a CAVAA
estimate, completed eligibility denominator or position-admission decision.

## Source and interpretation

The annual `rosters` release contains the latest player record for the season.
The distinct [`weekly_rosters` release](https://github.com/nflverse/nflverse-data/releases/tag/weekly_rosters)
retains weekly observations. The [official nflreadr loader](https://nflreadr.nflverse.com/reference/load_rosters_weekly.html)
documents coverage back to 2002. This implementation registers its own source kind
and schema; annual roster receipts and their existing replay remain unchanged.
Source bytes, release metadata, hashes, retrieval times and the CC-BY-4.0 license
are retained by the existing ingestion store. Software licensing is separate.

The [upstream dictionary](https://github.com/nflverse/nflreadr/blob/main/data-raw/dictionary_rosters.csv)
describes primary position and status but warns that `depth_chart_position` is
not always accurate. Only primary QB/RB/WR/TE/K/P/LS labels currently have direct
role mappings. Broad OL/DL/DB/LB labels stay unresolved; a listed linebacker may
be an edge player. A punter appearing as an offensive actor stays a punter rather
than being relabeled a quarterback because he threw a pass.

The source includes active, inactive, reserve, practice-squad, released and other
statuses. They are preserved literally. Neither an ACT label nor row existence
proves participation or that the player was under contract at kickoff. The data
does not provide exact signing/release timestamps. Weekly evidence alone cannot
certify nonoverlapping roster stints or count all missed games.

## Deterministic join

- Join canonical GSIS ID, team, season and exact regular-season week. No name or
  ESPN fallback, alias guessing, forward fill or backward fill.
- Retain missing/noncanonical identities in the observation table. Duplicate
  source keys, malformed schemas/seasons/weeks and unknown schedule-team mappings
  fail. Multiple rows per player/week, inconsistent secondary identities and
  team conflicts remain explicit unresolved evidence.
- Produce one evidence row per listed player/team/completed game, plus observed
  offensive actors lacking a roster match. Byes produce no game. Trade rows do
  not append both teams' entire seasons; missing weeks are not filled.
- Carry existing observed and context-complete opportunity counts unchanged.
  A scramble remains one union opportunity. No EPA is allocated here. A missing
  workload is `null`, not zero snaps, zero contribution or a missed game.
- Store the offensive report hash, roster receipt hash, producer revision, policy
  version and attribution. Keep the archived **game-cohort cutoff** separate from
  the new **evidence cutoff**. Count retrospective retrieval explicitly.

`source_position_role` means a directly interpretable source label with an
unambiguous join. It is not verified positioning on every play. All evidence
bundles retain `roster_stints_verified=false`,
`qualification_denominator_complete=false` and `ranking_ready=false`.

## Build and exactly replay

Commit source changes first so the receipt/report identifies executable code.
Capture is the only online step; build and replay read archived bytes only.

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.ingest_cli capture weekly_rosters --season 2026
PYTHONPATH=src .venv/bin/python -m nfl_value.roster_cli build \
  --weekly-rosters ROSTER_RECEIPT_SHA256 \
  --offensive-report-id OFFENSIVE_REPORT_SHA256 \
  --evidence-cutoff TIME_AFTER_ALL_INPUT_RETRIEVALS
PYTHONPATH=src .venv/bin/python -m nfl_value.roster_cli replay ROSTER_REPORT_SHA256
```

Replay first reproduces source audits and the whole offensive input chain, then
rebuilds the join and compares exact payload/report bytes. Correctly hashed but
altered roles, changed report flags and corrupt dependencies fail verification.
Raw/derived artifacts stay outside Git; committed audits record identifiers and
aggregate findings. These hashes require retained bytes to reproduce results.

## Completion time correction

`CompletedTeamGame.completion_time_kind` defaults to `observed_by`. The same
retrieval may bound the completion of six earlier games; it cannot establish that
those games overlapped. `SeasonExposure` still rejects duplicate games, equal
kickoffs, bounds later than the cutoff, and overlap established by an explicitly
`exact` finish. It does not invent a three-hour final-whistle time. Nonoverlapping
membership must still be reconciled upstream before declaring completeness.
Existing saved schedule/offensive reports are unchanged and replay with their
recorded semantics.

## Next acceptance requirements

Use the literal weekly evidence and pregame depth charts to review roster-status
and transaction policies. Identify ambiguous same-week trades, release/injury
cases, missing weeks and position changes before constructing a `SeasonExposure`.
Keep every admitted missed-game exposure in G, keep participation distinct from
roster presence, and keep benchmark membership independent of qualification.

Historical fits must explicitly acknowledge retrospective roster evidence and
must never use a later week's position to fill an earlier gap. Primary/sensitivity
contrasts, joint uncertainty and the 0.75x/1x/1.25x qualification experiment remain
separate work. Broad defensive roles still require verified role/workload evidence;
this join does not turn Defense Explorer observations into comparable MVP scores.
