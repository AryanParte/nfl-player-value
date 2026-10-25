# Observed Defense Explorer

The first React/TypeScript dashboard renders recorded defensive events, chart
membership, team EPA and data coverage from a reproducible Python export. It
implements the required exploratory defensive product while individual defensive
attribution remains unsupported. **It supplies no CAVAA score, player interval,
eligibility decision or MVP ranking.** The first-unit CAVAA benchmark and its two
sensitivity benchmarks remain unchanged.

## Meaning of an observation

Use the reconciled completed regular-season pass/run cohort from
[offensive inputs](OFFENSIVE_INPUTS.md). Its exclusions include no-plays, kneels,
spikes, conversions and special teams. These are scoped observations, not official
full-season sack/interception totals. No scoring formula combines the counts.

- A solo sack credits one valid recorded GSIS identity with 1; a split sack
  credits two distinct valid identities with 0.5 each. Mixed, missing, duplicated
  or contradictory identities withhold the entire event's credit. One sack
  never becomes two sacks. An interception credits its initial recorded
  interceptor; a lateral recipient is not a second interception.
- A player enters the population through a valid defensive first-unit chart
  cell or a valid event identity. This is not a complete NFL defensive roster.
  IDL/EDGE/LB/CB/S labels come only from those charts. Event-only players can have
  an unverified role. Whole conflicted team-game-role cells are withheld.
- Names require a unique roster GSIS/ESPN association consistent with chart
  identity evidence. Ambiguous names stay missing. Roster team or position does
  not establish historical stints, games played or play-by-play assignments.
- A chart-listed game is not a played game. A recorded event game is a lower
  bound on appearances, not a workload denominator. Zero counts mean no valid
  credit in the included records; they do not mean zero defensive value or
  confirmed absence. The UI recomputes counts when filtering by observed team.
- Team defensive EPA is the negative sum of offensive EPA over included plays.
  Negative outcomes remain negative. A missing EPA observation makes that
  team-game's total unavailable. Team EPA is never allocated to the selected
  player, and a selected player need not have played every included snap.

Player counts are deterministic recorded observations, not noisy CAVAA estimates
with confidence intervals. Measurement gaps and unresolved identities are shown
as coverage limitations; statistical intervals cannot repair absent measurements.

The definitions of the recorded actor fields were checked against the primary
[nflverse PBP dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv).
The public [snap-count loader](https://nflreadr.nflverse.com/reference/load_snap_counts.html)
identifies PFR as the upstream source. This unit does not introduce that unresolved
public-product dependency. Snaps, pressure rates, target deterrence, assignments,
run fits and off-ball effects remain unavailable. No historical fraction is
presented as live 2026 workload coverage.

## Export and browser contract

`nfl_value.explorer_cli` replays the outcome report and all four raw receipts:
PBP, schedule, depth charts and roster. It rejects source-kind/season mismatches
and retrievals after the fixed outcome cutoff. Formation-aware chart selection
uses the same completed-game cohort; retrospective retrieval is disclosed.

The immutable payload carries source-receipt hashes, source update/retrieval
timestamps, source-specific attribution and license references, code revision,
opportunity/chart policies, per-game evidence, coverage and unresolved-record
diagnostics. It has `schema_version=1`, `ranking_ready=false`, and null CAVAA/snaps.
Derived observations use the recorded ordinary nflverse CC-BY-4.0 inputs; this
export contains no FTN participation/model output. Software and data rights
remain distinct. Preserve attribution with redistributed derivatives.

Replay reconstructs the exact JSON bytes from archived inputs. Export first
writes an immutable hash-named object, then atomically replaces `latest.json`.
Prior objects survive. A failed pointer replacement leaves the previous pointer
intact. This local operation is a building block, not a deployed publication job.

The browser resolves only a same-origin, validated hash filename. It verifies
SHA-256 before parsing a strict Zod schema and checks game/player totals,
event-credit conservation, source chronology and team-game coverage. Numeric
CAVAA/snaps, ranking readiness, mismatched totals or corrupted bytes withhold the
entire view. A missing snapshot offers retry without synthetic fallback data.
The 5 MiB payload limit bounds the supported contract, though the current fetch
buffers the response before enforcing it; use trusted static hosting and no
user-supplied snapshot URLs. The hash checks byte consistency, not authenticity
against a compromised publisher.

## Reproduce a saved snapshot

From a clean, committed Python source revision at the repository root:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.explorer_cli build \
  --offensive-report OFFENSIVE_REPORT_ID \
  --depth-charts DEPTH_RECEIPT_ID \
  --rosters ROSTER_RECEIPT_ID
PYTHONPATH=src .venv/bin/python -m nfl_value.explorer_cli replay EXPLORER_REPORT_ID
PYTHONPATH=src .venv/bin/python -m nfl_value.explorer_cli export EXPLORER_REPORT_ID
```

Default stores are `data/raw/source-snapshots`, `data/derived/offensive-inputs`
and `data/derived/defense-explorer`; export defaults to `web/public/data`.
All are independent of the other NFL project. Source bytes and generated data
remain outside Git. Receipt hashes alone cannot restore unavailable source bytes;
durable off-machine retention is still required before release.

See [frontend instructions](../web/README.md) for local rendering and verification.
The release still needs a supported CAVAA module, benchmark/qualification and
uncertainty evaluation, ranking/history views, durable publication, independent
weekly refresh and deployment. An observed explorer does not complete the
universal MVP-ranking objective.
