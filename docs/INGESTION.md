# Immutable source snapshots

The source layer captures the exact public nflverse CSV.gz assets for play-by-play,
season rosters, timestamped depth charts, and schedules. It audits their structure
and preserves the bytes for offline replay. The separate [pregame input layer](PREGAME_INPUTS.md)
reconciles schedule/PBP completion evidence and selects first-unit chart members.
Neither layer produces model opportunities, eligibility decisions, or rankings.

## Run and replay

Use the repository root, Python 3.11+, and the development lease described in
[DAILY_WORKFLOW.md](DAILY_WORKFLOW.md). Commit source changes before live capture;
the CLI refuses dirty source/package files and execution from a different checkout
or installed copy, so each receipt can identify its executing Git revision.

```sh
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture pbp --season 2026
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture rosters --season 2026
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture depth_charts --season 2026
PYTHONPATH=src python3 -m nfl_value.ingest_cli capture schedules --season 2026
PYTHONPATH=src python3 -m nfl_value.ingest_cli replay RECEIPT_SHA256
```

The optional `--store PATH` comes before `capture` or `replay`. The default is
`data/raw/source-snapshots`, ignored by Git. Capture is online; replay has no
network calls and needs only the recorded local objects. The receipt identifier
is printed with the audit report. See [the October 19 audit](audits/2026-10-19-sources.json)
for the first three real receipt IDs.

## Exact-byte provenance

For each explicitly selected asset, capture saves:

- The GitHub release metadata bytes, asset ID, exact filename/URL, published
  SHA-256, byte size, and upstream update timestamp.
- Original compressed data bytes plus a decoded-content hash and size.
- Retrieval timestamps, selected HTTP headers, schema/columns, row and coverage
  counts, missing/invalid ID counts, and the executing code commit.
- The source's declared data license, attribution reference, and exact license
  text bytes. This is separate from the repository's MIT software license.

Objects live at `objects/SHA256`; receipts at `manifests/SHA256.json`. Temporary
files are fully written before atomic, non-overwriting publication. Existing
objects are verified before reuse. A receipt is written last; interrupted captures
can leave unreferenced complete objects, but cannot advance a ranking or latest
pointer. There is no garbage collection in this unit.

Replay verifies every object's hash, the selected asset against stored release
metadata, the license record, retrieval chronology, and the regenerated audit.
When schemas or audit policy change, use the receipt's recorded code revision to
reproduce the original interpretation. An upstream correction creates new bytes
and a new receipt; previous receipts remain available.

These development snapshots currently reside in the stable local clone. The
committed audit records their identities, not the raw data itself. Off-machine
backup/release-asset retention is still required before production ranking
publication. Redownloading a mutable source URL is not an archival strategy.

## Failure and quality behavior

Capture rejects missing/ambiguous assets, absent published hashes, unexpected URLs,
size/hash mismatches, malformed CSV, missing required columns, duplicate declared
row keys, invalid seasons/weeks, and future or timezone-free depth timestamps.
Reads are bounded to 128 MiB compressed and 512 MiB decoded. New source columns are
preserved in the schema record; they are not automatically modeling features.

Missing GSIS IDs and noncanonical legacy-format IDs remain visible in the raw
archive and audit. They are not guessed, filled with zero, or accepted by the
canonical player contracts. The normalizer must resolve them using a verified
mapping or identify affected rows/cells as unsupported. Raw preservation and
admission to modeling are separate steps.

PBP `END_GAME` markers are counted as source evidence. They are not independently
verified final status or precise completion timestamps. A remaining game clock of
zero is also not a sufficient completion rule, especially in overtime. A separate
schedule/PBP reconciliation now requires terminal markers and matching scores,
with conservative observed-complete-by timestamps. This is cross-file evidence,
not an independent live status feed; see [the policy](PREGAME_INPUTS.md).

Season-roster rows are not historical roster stints. Depth `dt` values indicate
source loading; the pregame layer handles latest pre-kickoff selection, reviewed
role mappings, freshness and required team-game coverage. Archives can contain
later corrections, so an old row timestamp does not independently prove what was
known at a historical cutoff. Every audit in this unit sets `ranking_ready=false`.

## Why direct release assets

The thin standard-library downloader preserves raw provenance before any dataframe
loader transforms it. It reuses nflverse data and EPA, and does not recreate those
models. CSV.gz allows current ingestion and offline CI without another runtime
dependency. nflreadpy/Polars remain candidates for later normalized-table work.
Historical depth charts before 2025 use a different schema and are rejected until
a separate adapter is implemented. No PFR, commercial, or tracking source is
silently substituted when a selected asset is missing.

Source references: [nflverse releases](https://github.com/nflverse/nflverse-data/releases),
[repository data license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md),
and [depth-chart fields](https://nflreadr.nflverse.com/articles/dictionary_depth_charts.html).
