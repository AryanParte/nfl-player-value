# Data sources and provenance

Research audit date: **October 18, 2026**. Availability findings are observations at that date, not continuing guarantees. The production pipeline must verify every selected release, schema, game set, and license. Some row-level checks below were made on October 17 and may lag subsequent source updates.

**October 19 implementation audit:** real PBP, season-roster, and depth-chart
snapshots were archived with exact published/observed hashes and replayed offline.
The [machine-readable audit](audits/2026-10-19-sources.json) contains source asset
identities, timestamps, code revision and coverage. PBP contains 16,212 rows and
92 games with end markers, not a certified complete Week 6 release. Rosters contain
3,043 rows, including one missing GSIS ID. Across 246 depth-chart timestamps,
673,227 rows include 25,063 missing-ID rows and 1,019 legacy-format-ID rows.
These are row counts across repeated snapshots, not counts of distinct players.
See [INGESTION.md](INGESTION.md) for why these sources are not yet ranking-ready.

## Public-source launch plan

| Source | Historical/current availability observed | Intended use and limitation |
| --- | --- | --- |
| nflverse play-by-play | Since 1999; a 2026 release asset was present | EPA and game/play context. A present file does not establish complete or corrected game coverage. |
| Rosters and player identifiers | 2026 assets present; historical fields vary | Stable IDs, team stints, and roles; audit merges and position changes. |
| Depth charts | Historical loader support; 2026 timestamped snapshots present | Pregame first-unit membership. Since 2025, timestamps replace a simple week index; reconstruct as-of membership. |
| Snap counts | Since 2012; 2026 game-level records present | Offensive, defensive, and special-teams workload. These are not play-level lineups. |
| Participation | Since 2016; 2023 onward FTN releases are post-season | Historical rich-lineup experiment. No public 2026 live all-22 participation feed was verified. |
| FTN charting subset | Since 2022; 2026 records present, generally delayed | Selected play context and charted events. Does not supply complete individual blocking, rushing, or coverage assignments. |
| Next Gen Stats aggregates | Since 2016; current-season aggregates present | Selected passing/rushing/receiving context with qualification thresholds. Not raw tracking; absent rows are not zero. |
| PFR advanced statistics via nflverse | Since 2018; current-season assets present | Potential event/context analysis only after upstream use rights are resolved. |
| Injury reports | 2026 data present in the audit | Availability/context. Schema and coverage differ from older documentation; do not invent severity. |
| Derived player/team statistics | Current nflverse releases | Convenience aggregates from the same underlying plays, not independent evidence. |

Primary references: [nflverse update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html), [depth-chart loader](https://nflreadr.nflverse.com/reference/load_depth_charts.html), [participation loader](https://nflreadr.nflverse.com/reference/load_participation.html), [FTN loader](https://nflreadr.nflverse.com/reference/load_ftn_charting.html), and [FTN dictionary](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html).

## Why per-game freshness is necessary

The October 17 checks found FTN charting and snap counts covering 80 games: the first five weeks plus one Week 6 game. PFR passing and defensive advanced-stat samples covered 79 games through Week 5. Injury data contained 1,787 rows through Week 6, but Week 6 records represented 28 teams. Those findings cannot be treated as a complete Week 6 snapshot.

Next Gen Stats files included week `0` season summaries as well as weekly rows. Do not add the summaries to the weekly observations. Player qualification filters create selective missingness.

On October 18, depth-chart CSV and Parquet assets were current while another format was stale. Select and version an explicit asset; do not assume every format in one release has identical freshness. Updated metadata does not establish that row-level gaps found the previous day were repaired.

The live pipeline will replace this research audit with machine-readable coverage evidence. Required checks include completed-game joins, duplicate keys, player-ID joins, expected team/role cells, source cutoffs, excluded rows, and required-field missingness.

## Rights and permitted use

Software licenses and data licenses are separate. An MIT-licensed loader does not grant unrestricted public redistribution of the data it downloads. Retain source-specific license text/version and attribution with each manifest; distinguish local modeling, stored raw data, derived statistics, and public display.

The audited FTN subset and participation documentation specify **CC BY-SA 4.0** and attribution such as **“FTN Data via nflverse.”** Confirm the applicable terms for each asset and resulting distribution before publication. Do not assume this governs unrelated commercial FTN feeds.

PFR-derived data remain an unresolved public-product dependency because [Sports Reference's data-use policy](https://www.sports-reference.com/data_use.html) applies upstream. A wrapper's availability or license does not settle permission for a public leaderboard. Exclude any required product feature that lacks a permitted source or an approved alternative.

Logos and headshots have independent rights. A plotting package license does not license every image it can retrieve.

## Commercial and competition data

Commercial FTN, PFF, SIS, and licensed tracking data may support better attribution, but consumer subscriptions do not automatically permit API ingestion, derived rankings, or redistribution. None is a launch prerequisite and **no purchase is authorized**. Obtain explicit approval and appropriate contractual rights before introducing a paid dependency. See [FTN data offerings](https://ftnfantasy.com/stats/sports-data) and [PFF WAR](https://www.pff.com/war) for context, not permission to reproduce their data or scores.

[NFL Big Data Bowl](https://operations.nfl.com/programs-initiatives/innovation/big-data-bowl) datasets support historical tracking research under their own terms. They are not a continuous live 2026 tracking feed.

## Reproducibility requirements

Preserve exact input bytes or a permitted immutable reconstruction path, content hashes, retrieval and source timestamps, data dictionary/schema, game coverage, licensing references, and transformation version. Use the same manifest for modeling, explanations, and publication. Never rewrite a historical ranking silently after upstream corrections; publish a linked corrected version.
