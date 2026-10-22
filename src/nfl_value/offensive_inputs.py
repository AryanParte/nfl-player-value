"""One offensive outcome per play, observed actor links, no allocated player EPA."""

from collections import Counter, defaultdict
import csv
from datetime import datetime
import gzip
import io
import json
from math import fsum, isfinite
import re

from nfl_value.ingestion import SnapshotStore, json_bytes, replay, sha256
from nfl_value.preplay import CONTEXT, parse_context
from nfl_value.schedules import CLOCK_COLUMNS, CLOCK_COMPLETION, reconcile_game_coverage
from nfl_value.source_audit import aware_time


EXCLUSION_FLAGS = ("qb_kneel", "qb_spike", "two_point_attempt")
EVENT_FLAGS = ("qb_dropback", "qb_scramble", "rush_attempt", "pass_attempt", "sack", "aborted_play")
IDS = ("passer_player_id", "rusher_player_id", "receiver_player_id")
COLUMNS = {
    "game_id", "play_id", "season_type", "play_type", "play_type_nfl", "posteam", "defteam", "epa",
    "home_team", "away_team", "total_home_score", "total_away_score",
    *CONTEXT, *CLOCK_COLUMNS, *EXCLUSION_FLAGS, *EVENT_FLAGS, *IDS,
}
COUNT_NAMES = ("dropbacks", "rushes", "targets", "dropback_or_rush_plays", "carry_or_target_plays", "on_ball_plays")


def _rows(raw: bytes):
    # Caller must replay first to verify hash, expansion bound, widths and keys.
    with io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not COLUMNS <= set(reader.fieldnames or []):
            raise ValueError(f"offensive inputs require columns: {sorted(COLUMNS - set(reader.fieldnames or []))}")
        for row in reader:
            yield {key: row[key] for key in COLUMNS}


def _actors(row: dict) -> tuple[str, dict, list[str]]:
    actors = {"dropback": None, "rusher": None, "target": None}
    issues = []
    ids = {}
    for field in IDS:
        value = row[field]
        ids[field] = value if re.fullmatch(r"00-\d{7}", value) else None
        if value not in {"", "NA"} and ids[field] is None:
            issues.append(f"noncanonical_{field}")
    if any(row[field] not in {"0", "1"} for field in EVENT_FLAGS):
        return "unclassified", actors, issues + ["unknown_event_flag"]
    if row["aborted_play"] == "1":
        return "aborted", actors, issues + ["aborted_actor_requires_review"]
    dropback, scramble, rush, passed, sack = (row[field] == "1" for field in EVENT_FLAGS[:-1])
    if row["play_type"] == "pass" and dropback and passed and not rush and not scramble:
        kind = "sack" if sack else "pass"
        actors["dropback"] = ids["passer_player_id"]
        if actors["dropback"] is None:
            issues.append("missing_dropback_actor")
        if not sack:
            actors["target"] = ids["receiver_player_id"]
        if ids["rusher_player_id"] or (sack and ids["receiver_player_id"]):
            issues.append("unexpected_actor_for_event")
    elif row["play_type"] == "run" and rush and not passed and not sack and dropback == scramble:
        kind = "scramble" if scramble else "non_dropback_run"
        actors["rusher"] = ids["rusher_player_id"]
        if actors["rusher"] is None:
            issues.append("missing_rusher")
        if scramble:
            actors["dropback"] = actors["rusher"]
        if ids["receiver_player_id"] or (ids["passer_player_id"] and ids["passer_player_id"] != actors["rusher"]):
            issues.append("unexpected_actor_for_event")
    else:
        return "unclassified", actors, issues + ["inconsistent_event_flags"]
    return kind, actors, sorted(issues)


def offensive_ledger(rows, *, completed_games: list[dict]) -> tuple[dict, dict]:
    games = {g["game_id"]: g for g in completed_games}
    if len(games) != len(completed_games):
        raise ValueError("duplicate completed game")
    seen, plays = set(), []
    excluded, issues = Counter(), Counter()
    counts = defaultdict(lambda: {"observed": Counter(), "context_outcome_complete": Counter()})
    player_game_teams = defaultdict(set)
    for row in rows:
        key = (row["game_id"], int(row["play_id"]))
        if key in seen:
            raise ValueError("duplicate offensive game/play key")
        seen.add(key)
        if row["season_type"] != "REG":
            excluded["postseason"] += 1
            continue
        if key[0] not in games:
            excluded["game_not_reconciled_complete"] += 1
            continue
        if row["play_type"] not in {"pass", "run"}:
            excluded["outside_pass_run_scope"] += 1
            continue
        if any(row[field] == "1" for field in EXCLUSION_FLAGS):
            excluded["kneel_spike_or_two_point"] += 1
            continue
        game = games[key[0]]
        if {row["posteam"], row["defteam"]} != {game["away_team"], game["home_team"]}:
            raise ValueError("offensive PBP teams disagree with schedule")
        row_issues = []
        context, epa = None, None
        try:
            context = parse_context(row)
        except ValueError:
            row_issues.append("missing_or_invalid_context")
        try:
            epa = float(row["epa"])
            if not isfinite(epa):
                raise ValueError("nonfinite EPA")
        except ValueError:
            epa = None
            row_issues.append("missing_or_invalid_epa")
        kind, actors, actor_issues = _actors(row)
        if any(row[field] != "0" for field in EXCLUSION_FLAGS):
            kind, actors = "unclassified", dict.fromkeys(actors)
            row_issues.append("unknown_exclusion_flag")
        row_issues.extend(actor_issues)
        complete = context is not None and epa is not None and "unknown_exclusion_flag" not in row_issues
        entry = {
            "game_id": key[0], "play_id": key[1], "week": game["week"], "scheduled_kickoff": game["scheduled_kickoff"],
            "offense_team": row["posteam"], "defense_team": row["defteam"], "event_kind": kind,
            "offense_epa": epa, "context": context, "actors": actors,
            "context_outcome_complete": complete, "issues": sorted(row_issues),
            "target_observation": ("recorded" if actors["target"] else "none_recorded" if kind == "pass" else "not_applicable"),
        }
        plays.append(entry)
        issues.update(row_issues)
        # Set unions ensure a scramble or self-target is never a second play.
        membership = {
            "dropbacks": {actors["dropback"]}, "rushes": {actors["rusher"]}, "targets": {actors["target"]},
            "dropback_or_rush_plays": {actors["dropback"], actors["rusher"]},
            "carry_or_target_plays": {actors["rusher"], actors["target"]}, "on_ball_plays": set(actors.values()),
        }
        for unit, players in membership.items():
            for player in players - {None}:
                item = counts[(player, key[0], row["posteam"])]
                item["observed"][unit] += 1
                item["context_outcome_complete"][unit] += complete
                player_game_teams[(player, key[0])].add(row["posteam"])
    plays.sort(key=lambda p: (p["game_id"], p["play_id"]))
    workload = [{"player_id": player, "game_id": game_id, "team": team,
                 **{scope: {name: c[scope][name] for name in COUNT_NAMES} for scope in ("observed", "context_outcome_complete")}}
                for (player, game_id, team), c in sorted(counts.items())]
    conflicts = [{"player_id": p, "game_id": g, "teams": sorted(t)} for (p, g), t in sorted(player_game_teams.items()) if len(t) > 1]
    payload = {
        "schema_version": 1, "opportunity_policy": "observed-offensive-pass-run-v1", "plays": plays,
        "observed_player_games": workload, "roster_stints_verified": False, "qualification_denominator_complete": False,
        "player_positions_verified": False, "ranking_ready": False,
    }
    audit = {
        "pbp_rows": len(seen), "candidate_plays": len(plays), "excluded_pbp_counts": dict(sorted(excluded.items())),
        "issue_counts": dict(sorted(issues.items())), "player_game_team_conflicts": conflicts,
        "event_counts": dict(sorted(Counter(p["event_kind"] for p in plays).items())),
        "context_outcome_complete_plays": sum(p["context_outcome_complete"] for p in plays),
        "plays_with_actor_issues": sum(any(i not in {"missing_or_invalid_context", "missing_or_invalid_epa"} for i in p["issues"]) for p in plays),
        "passes_without_recorded_target": sum(p["target_observation"] == "none_recorded" for p in plays),
        "missing_epa_plays": sum(p["offense_epa"] is None for p in plays),
        "observed_offense_epa_sum": fsum(p["offense_epa"] for p in plays if p["offense_epa"] is not None),
        "observed_player_game_rows": len(workload), "observed_players": len({p["player_id"] for p in workload}),
    }
    return payload, audit


def build_offensive_inputs(store: SnapshotStore, *, schedules: str, pbp: str, cutoff: datetime, code_revision: str) -> tuple[dict, dict]:
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision) or cutoff.utcoffset() is None:
        raise ValueError("full code revision and timezone-aware cutoff required")
    ids = {"schedules": schedules, "pbp": pbp}
    receipts = {kind: replay(store, rid) for kind, rid in ids.items()}
    if any(r["source"]["kind"] != kind for kind, r in receipts.items()):
        raise ValueError("receipt source kind disagrees with requested input")
    seasons = {r["source"]["season"] for r in receipts.values()}
    if len(seasons) != 1:
        raise ValueError("input receipts must describe one season")
    if any(aware_time(t) > cutoff for r in receipts.values() for t in r["retrieval"].values()):
        raise ValueError("input receipt was retrieved after cutoff")
    raw = store.read(receipts["pbp"]["objects"]["raw"])
    coverage = reconcile_game_coverage(receipts["schedules"]["audit"]["games"], _rows(raw), cutoff=cutoff,
                                     observed_at=max(aware_time(r["retrieval"]["data"]) for r in receipts.values()), policy_version=CLOCK_COMPLETION)
    ledger, audit = offensive_ledger(_rows(raw), completed_games=coverage["matched_games"])
    report = {
        "report_version": 1, "code_revision": code_revision, "season": seasons.pop(), "cutoff": cutoff.isoformat(),
        "source_receipts": ids, "game_coverage": coverage, "opportunity_audit": audit,
        "source_attribution": {kind: {field: receipt["source"][field] for field in ("license_id", "license_url", "attribution")}
                               for kind, receipt in receipts.items()},
        "opportunity_policy": ledger["opportunity_policy"], "ranking_ready": False,
        "limitations": [
            "Observed actor links are event roles, not verified roster positions or individual EPA allocations.",
            "A scramble is one dropback-or-rush play; roles must be verified before applying positional qualification.",
            "No recorded target may mean a throwaway or absent identity; missing target information is not zero receiver value.",
            "Aborted or ambiguous actor links stay unallocated while their observed team EPA remains in the ledger.",
            "Kneels, spikes, no-play penalties, conversions and special teams are outside this initial pass/run scope.",
            "Observed player games do not establish missed games, roster stints, late signings, total snaps or eligibility denominators.",
            "Retrospective source versions do not establish vintage availability. No attribution or comparability is validated.",
        ],
    }
    ledger["provenance"] = {k: report[k] for k in ("code_revision", "season", "cutoff", "source_receipts", "source_attribution", "opportunity_policy")}
    ledger["provenance"]["completion_policy"] = CLOCK_COMPLETION
    return report, ledger


def save_offensive_inputs(derived: SnapshotStore, report: dict, ledger: dict) -> tuple[str, dict]:
    saved = {**report, "objects": {"ledger": derived.put(json_bytes(ledger))}}
    return derived.put(json_bytes(saved), manifest=True), saved


def replay_offensive_inputs(raw: SnapshotStore, derived: SnapshotStore, report_id: str) -> dict:
    saved = json.loads(derived.read(report_id, manifest=True))
    if saved["report_version"] != 1:
        raise ValueError("unsupported offensive input report version")
    report, ledger = build_offensive_inputs(raw, **saved["source_receipts"], cutoff=aware_time(saved["cutoff"]), code_revision=saved["code_revision"])
    body = derived.read(saved["objects"]["ledger"])
    if body != json_bytes(ledger) or {**report, "objects": {"ledger": sha256(body)}} != saved:
        raise ValueError("offensive input replay differs; use recorded code revision")
    return saved
