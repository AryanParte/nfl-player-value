"""Paired historical research inputs; no player effects or CAVAA estimates."""

from collections import Counter, defaultdict
import csv
from datetime import datetime
import gzip
import io
import json
from math import fsum, isfinite
import re

from nfl_value.ingestion import SnapshotStore, json_bytes, replay, sha256
from nfl_value.participation import PARTICIPATION_COLUMNS, inspect_lineup, participation_key
from nfl_value.preplay import CONTEXT, parse_context as _context
from nfl_value.schedules import CLOCK_COLUMNS, CLOCK_COMPLETION, LEGACY_COMPLETION, reconcile_game_coverage
from nfl_value.source_audit import aware_time


FLAGS = ("qb_kneel", "qb_spike", "two_point_attempt")
PBP_COLUMNS = {
    "game_id", "play_id", "season_type", "play_type", "play_type_nfl", "posteam", "defteam", "epa",
    "home_team", "away_team", "total_home_score", "total_away_score", *CONTEXT, *FLAGS,
}


def _rows(raw: bytes, columns: set[str], *, compressed: bool = True):
    # Only read already-replayed sources: expansion, row widths, keys audited.
    handle = gzip.GzipFile(fileobj=io.BytesIO(raw)) if compressed else io.BytesIO(raw)
    with io.TextIOWrapper(handle, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not columns <= set(reader.fieldnames or []):
            raise ValueError(f"defensive inputs require columns: {sorted(columns - set(reader.fieldnames or []))}")
        for row in reader:
            yield {key: row[key] for key in columns}


def paired_cohort(pbp_rows, participation_rows, *, season: int, completed_games: list[dict]) -> tuple[dict, dict, dict]:
    """Use only whole games with valid lineups/context on every candidate play.

    Candidate: completed REG pass/run, excluding kneels, spikes and two-point
    attempts. A bad candidate blocks its entire game in BOTH views. Audits retain
    all losses; complete-case selection can bias the subsequent experiment.
    """
    games = {game["game_id"]: game for game in completed_games}
    if len(games) != len(completed_games):
        raise ValueError("duplicate completed game")
    participation = {}
    for row in participation_rows:
        key = participation_key(row, season)
        if key in participation:
            raise ValueError("duplicate participation game/play key")
        participation[key] = row
    seen = set()
    excluded = Counter()
    rejected = Counter()
    counts = {game_id: {"candidate_plays": 0, "matched_plays": 0, "rejected": Counter()} for game_id in games}
    accepted = []
    for row in pbp_rows:
        game_id = row["game_id"]
        key = game_id, int(row["play_id"])
        if key in seen:
            raise ValueError("duplicate PBP game/play key")
        seen.add(key)
        if row["season_type"] != "REG":
            excluded["postseason"] += 1
            continue
        if game_id not in games:
            excluded["game_not_reconciled_complete"] += 1
            continue
        if row["play_type"] not in {"pass", "run"}:
            excluded["not_pass_or_run"] += 1
            continue
        if any(row[flag] == "1" for flag in FLAGS):
            excluded["kneel_spike_or_two_point"] += 1
            continue
        game_counts = counts[game_id]
        game_counts["candidate_plays"] += 1
        reasons = []
        if any(row[flag] != "0" for flag in FLAGS):
            reasons.append("unknown_exclusion_flag")
        game = games[game_id]
        if {row["posteam"], row["defteam"]} != {game["away_team"], game["home_team"]}:
            reasons.append("pbp_team_mismatch")
        try:
            context = _context(row)
            epa = float(row["epa"])
            if not isfinite(epa):
                raise ValueError("nonfinite EPA")
        except ValueError:
            reasons.append("missing_or_invalid_context_or_epa")
        part = participation.get(key)
        if part is None:
            reasons.append("missing_participation")
        else:
            lineups, lineup_issues = inspect_lineup(part)
            reasons.extend(lineup_issues)
            if part["possession_team"] != row["posteam"]:
                reasons.append("possession_team_mismatch")
        if reasons:
            rejected.update(reasons)
            game_counts["rejected"].update(reasons)
            continue
        game_counts["matched_plays"] += 1
        accepted.append({
            "game_id": game_id, "play_id": key[1], "week": game["week"],
            "scheduled_kickoff": game["scheduled_kickoff"], "offense_team": row["posteam"],
            "defense_team": row["defteam"], "defense_epa": -epa, "context": context,
            "offense_players": lineups["offense_players"], "defense_players": lineups["defense_players"],
        })
    observed_sides = defaultdict(set)
    for play in accepted:
        observed_sides[play["game_id"]].add(play["defense_team"])
    complete_ids = sorted(game_id for game_id, item in counts.items()
                          if item["candidate_plays"] > 0 and item["candidate_plays"] == item["matched_plays"]
                          and observed_sides[game_id] == {games[game_id]["away_team"], games[game_id]["home_team"]})
    complete_set = set(complete_ids)
    plays = sorted((p for p in accepted if p["game_id"] in complete_set), key=lambda p: (p["game_id"], p["play_id"]))
    cohort_hash = sha256(json_bytes([[p["game_id"], p["play_id"]] for p in plays]))
    common = {"schema_version": 1, "season": season, "cohort_sha256": cohort_hash,
              "cohort_plays": len(plays), "game_ids": complete_ids, "ranking_ready": False}
    grouped = defaultdict(list)
    for play in plays:
        grouped[(play["game_id"], play["defense_team"])].append(play)
    team_games = []
    for (game_id, team), group in sorted(grouped.items()):
        n = len(group)
        players = Counter(player for play in group for player in play["defense_players"])
        team_games.append({
            "game_id": game_id, "week": group[0]["week"], "scheduled_kickoff": group[0]["scheduled_kickoff"],
            "defense_team": team, "offense_team": group[0]["offense_team"], "opportunities": n,
            "defense_epa_total": fsum(p["defense_epa"] for p in group),
            "defense_epa_mean": fsum(p["defense_epa"] for p in group) / n,
            "context_mean": {name: fsum(p["context"][name] for p in group) / n for name in CONTEXT},
            "defender_workloads": [{"player_id": player, "appearances": appearances, "fraction": appearances / n}
                                   for player, appearances in sorted(players.items())],
        })
    audit = {
        "pbp_rows": len(seen), "participation_rows": len(participation),
        "participation_without_pbp": [{"game_id": k[0], "play_id": k[1]} for k in sorted(participation.keys() - seen)],
        "pbp_without_participation_rows": len(seen - participation.keys()),
        "excluded_pbp_counts": dict(sorted(excluded.items())), "rejection_counts": dict(sorted(rejected.items())),
        "candidate_plays": sum(c["candidate_plays"] for c in counts.values()),
        "matched_plays_before_whole_game_gate": len(accepted),
        "matched_plays_removed_by_whole_game_gate": len(accepted) - len(plays),
        "paired_plays": len(plays), "paired_games": len(complete_ids),
        "games": {gid: {**c, "rejected": dict(sorted(c["rejected"].items())), "paired": gid in complete_set,
                        "exclusion_reason": None if gid in complete_set else (
                            "no_candidate_plays" if not c["candidate_plays"] else
                            "invalid_or_unmatched_candidate_plays" if c["candidate_plays"] != c["matched_plays"] else
                            "missing_defensive_side")}
                  for gid, c in sorted(counts.items())},
    }
    return {**common, "view": "rich_play_lineups", "plays": plays}, {**common, "view": "degraded_team_games", "team_games": team_games}, audit


def build_defense_inputs(store: SnapshotStore, *, schedules: str, pbp: str, participation: str, cutoff: datetime, code_revision: str, report_version: int = 2) -> tuple[dict, dict, dict]:
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision) or cutoff.utcoffset() is None:
        raise ValueError("full code revision and timezone-aware cutoff required")
    if type(report_version) is not int or report_version not in {1, 2}:
        raise ValueError("unsupported defensive input version")
    ids = {"schedules": schedules, "pbp": pbp, "participation": participation}
    receipts = {kind: replay(store, rid) for kind, rid in ids.items()}
    if any(r["source"]["kind"] != kind for kind, r in receipts.items()):
        raise ValueError("receipt source kind disagrees with requested input")
    seasons = {r["source"]["season"] for r in receipts.values()}
    if len(seasons) != 1:
        raise ValueError("input receipts must describe one season")
    if any(aware_time(t) > cutoff for r in receipts.values() for t in r["retrieval"].values()):
        raise ValueError("input receipt was retrieved after cutoff")
    raw_pbp = store.read(receipts["pbp"]["objects"]["raw"])
    coverage = reconcile_game_coverage(
        receipts["schedules"]["audit"]["games"], _rows(raw_pbp, PBP_COLUMNS | (CLOCK_COLUMNS if report_version == 2 else set())), cutoff=cutoff,
        observed_at=max(aware_time(receipts[k]["retrieval"]["data"]) for k in ("schedules", "pbp")),
        policy_version=CLOCK_COMPLETION if report_version == 2 else LEGACY_COMPLETION,
    )
    season = seasons.pop()
    rich, degraded, audit = paired_cohort(
        _rows(raw_pbp, PBP_COLUMNS),
        _rows(store.read(receipts["participation"]["objects"]["raw"]), PARTICIPATION_COLUMNS, compressed=False),
        season=season, completed_games=coverage["matched_games"],
    )
    report = {
        "report_version": report_version, "code_revision": code_revision, "season": season,
        "cutoff": cutoff.isoformat(), "source_receipts": ids, "game_coverage": coverage,
        "policy": "complete-game-reg-pass-run-v1", "join_audit": audit,
        "attribution": "FTN Data via nflverse; PBP and schedules via nflverse",
        "derived_participation_license": "CC-BY-SA-4.0",
        "license_url": receipts["participation"]["source"]["license_url"],
        "historical_availability": "retrospectively_retrieved_postseason_participation",
        "experiment_run": False, "ranking_ready": False,
        "limitations": [
            "No fitted effects, causal attribution or cross-position comparability is established.",
            "Complete-case game selection may bias results; audit excluded games before fitting.",
            "Degraded fractions measure accepted pass/run appearances, not official defensive snaps or pass-rush opportunities.",
            "This controlled reduction does not establish permitted live-2026 workload availability or emulate all its missingness.",
            "Preplay context and aggregate game outcomes describe observed exposure; they are not pregame prediction features.",
            "No player positions, coverage assignments, pressure adjustment or target deterrence are inferred.",
        ],
    }
    # Carry source terms into each independently reusable derivative.
    for view in (rich, degraded):
        view["provenance"] = {key: report[key] for key in ("source_receipts", "code_revision", "cutoff", "policy", "attribution", "derived_participation_license", "license_url")}
        if report_version == 2:
            view["provenance"]["completion_policy"] = CLOCK_COMPLETION
    return report, rich, degraded


def save_defense_inputs(derived: SnapshotStore, report: dict, rich: dict, degraded: dict) -> tuple[str, dict]:
    saved = {**report, "objects": {"rich": derived.put(json_bytes(rich)), "degraded": derived.put(json_bytes(degraded))}}
    return derived.put(json_bytes(saved), manifest=True), saved


def replay_defense_inputs(raw: SnapshotStore, derived: SnapshotStore, report_id: str) -> dict:
    saved = json.loads(derived.read(report_id, manifest=True))
    if saved["report_version"] not in {1, 2}:
        raise ValueError("unsupported defensive input version")
    report, rich, degraded = build_defense_inputs(raw, **saved["source_receipts"], cutoff=aware_time(saved["cutoff"]), code_revision=saved["code_revision"], report_version=saved["report_version"])
    objects = {}
    for name, view in (("rich", rich), ("degraded", degraded)):
        body = derived.read(saved["objects"][name])
        if body != json_bytes(view):
            raise ValueError("defensive input object replay differs; use recorded code revision")
        objects[name] = sha256(body)
    if {**report, "objects": objects} != saved:
        raise ValueError("defensive input report replay differs; use recorded code revision")
    return saved
