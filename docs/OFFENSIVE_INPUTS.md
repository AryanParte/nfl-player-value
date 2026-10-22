# Observed offensive play ledger

The offline normalizer prepares a transparent baseline's observations. It does
not fit a model, allocate EPA to players, verify roster positions, or qualify a
leaderboard. It uses recorded source versions and a corrected
[completed-game evidence rule](PREGAME_INPUTS.md).

## One outcome, several observed actors

Each completed REG pass/run play appears once, keyed by game ID and play ID, with
one offense EPA outcome and observed preplay context. A passer and a receiver can
both appear as actor links; neither receives a copy of full-play EPA. Player-game
workloads contain counts only. Model components and an unallocated shared term
must subsequently reconcile with the single outcome.

The [nflverse PBP dictionary](https://github.com/nflverse/nflreadr/blob/main/data-raw/dictionary_pbp.csv)
defines dropbacks to include attempts, sacks and scrambles, and the receiver ID
as the recorded target. We independently implement those field contracts; no
source implementation is copied. In the audited data, sacks carry a passer ID
and scrambles carry a rusher ID. We check flag consistency rather than infer a
player from a name or the team's most frequent quarterback.

| Observed event | Actor treatment |
| --- | --- |
| Pass | Recorded passer is the dropback actor; record a target when supplied |
| Sack | Recorded passer is the dropback actor; no receiving target inferred |
| Scramble | Recorded rusher fills both dropback and rush links, counted once in their union |
| Non-dropback run | Record the rusher; roster evidence must distinguish QB, RB or another position |
| Aborted play | Preserve observed team EPA/context; actor links remain unallocated pending review |
| Conflicting/unknown flags or identities | Keep the play with explicit issues and no guessed links |

A receiver throwing a trick pass is not thereby assigned the roster position QB.
A QB rushing on a non-dropback play can enter the intended QB opportunity union
only after position and identity verification. No position multiplier is used.

The initial scope excludes kneels, spikes, two-point attempts, `no_play` penalties
and special teams. Penalties embedded in valid pass/run EPA remain part of that
team outcome. This is a restricted pass/run estimand, not every form of player
value. Football-specific treatment of omitted plays must be resolved before any
full-player claim. Negative performances are retained; there is no recency decay.

## Counts, missingness and denominators

Per player-game, record dropbacks, rushes, targets, dropback-or-rush plays,
carry-or-target plays, and unique on-ball plays. These are **set unions**, not
sums of overlapping event counts. One scramble has one dropback, one rush, and
one combined dropback-or-rush opportunity. A self-target likewise remains one
unique on-ball play. Do not add overlapping columns into a season denominator.

`observed` workloads count valid actor links. `context_outcome_complete` workloads
additionally require finite EPA and valid context. Here “outcome” means the team
EPA response, not the receiving target. An unknown actor does not make valid
team EPA disappear. Missing EPA remains null, with an explicit missing count;
`observed_offense_epa_sum` sums only supplied outcomes and is not player CAVAA.

No recorded target can represent a throwaway or an unavailable identity. Record
`none_recorded` and its count; do not invent an unnamed receiver or claim zero
receiving value. Actor issues and player IDs appearing on both teams in one game
are recorded for resolution. Sparse participants stay in the data; leaderboard
qualification does not define this observation population or the benchmark.

Observed player games are only a lower bound on appearances. They cannot establish
games missed, non-ball participation, signing/trade dates, or the available-game
denominator. The output explicitly retains `player_positions_verified=false`,
`roster_stints_verified=false`, and `qualification_denominator_complete=false`.
Do not feed these counts into the three-game/positional gates as if those missing
contracts had been established. The first-unit benchmark remains separate.

## Reproduction and next model boundary

With the repository lease held and source code committed:

```sh
PYTHONPATH=src python3 -m nfl_value.offensive_cli build \
  --schedules SCHEDULE_RECEIPT --pbp PBP_RECEIPT --cutoff AWARE_ISO_TIMESTAMP
PYTHONPATH=src python3 -m nfl_value.offensive_cli replay REPORT_ID
```

Raw receipts default to `data/raw/source-snapshots`; immutable reports/ledger
objects use `data/derived/offensive-inputs`. Both are ignored by Git. Build and
replay are offline, identify exact source receipts and executing code, and do not
advance a latest pointer. New pregame/defensive reports also use completion v2;
their old reports replay unchanged. A successful diagnostic can contain missing
games or unresolved actors. Every output keeps `ranking_ready=false`.

Next fit a context-only baseline and regularized joint actor model on chronological
game splits, retaining unallocated/team components. Resolve identity/position and
roster-stint evidence before positional contrasts or qualification. Report actor
coverage sensitivity rather than silently dropping aborted or difficult plays.
This ledger provides no pressure adjustment, coaching score, causal effect,
uncertainty interval, or evidence of cross-position comparability.
