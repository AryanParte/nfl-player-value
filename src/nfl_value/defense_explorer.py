"""Observed defensive evidence for a dashboard, never a player-value ranking."""

from collections import Counter, defaultdict
from math import fsum
import json
import os
from pathlib import Path
import re
import tempfile

from nfl_value.first_unit import DEFENSE_ROLES
from nfl_value.ingestion import SnapshotStore, json_bytes, replay
from nfl_value.offensive_inputs import replay_offensive_inputs
from nfl_value.pregame_inputs import _rows, build_inputs
from nfl_value.source_audit import aware_time


EVENT_COLUMNS = {"game_id", "play_id", "sack", "interception", "sack_player_id", "half_sack_1_player_id",
                 "half_sack_2_player_id", "interception_player_id"}
MISSING = {"", "NA"}
UNAVAILABLE = {
    "cavaa": "Individual defensive attribution and cross-position comparability have not passed admission.",
    "defensive_snaps": "No verified, permitted live defensive workload feed is integrated.",
    "pressure_rate": "Pressure observations and a verified pass-rush denominator are unavailable.",
    "coverage_deterrence": "Targets avoided, coverage assignments and off-ball effects are unmeasured.",
    "qualification": "Chart membership and event appearances do not establish games played or snap eligibility.",
    "player_uncertainty": "No admitted individual estimate exists for an uncertainty interval.",
}


def canonical(value):
    return isinstance(value, str) and re.fullmatch(r"00-\d{7}", value) is not None


def event_credits(row, event_kind):
    """All-or-nothing credit per event; malformed half sacks cannot create full sacks."""
    out, issues = {"sacks": {}, "interceptions": {}}, []
    if row["sack"] == row["interception"] == "1":
        return out, ["sack_and_interception_conflict"]
    for metric, flag, fields in (
        ("sacks", "sack", ("sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id")),
        ("interceptions", "interception", ("interception_player_id",)),
    ):
        values = [row[k] for k in fields]
        if row[flag] not in {"0", "1"}:
            issues.append("unknown_" + flag + "_flag")
        elif row[flag] == "0":
            if any(v not in MISSING for v in values):
                issues.append("unexpected_" + flag + "_identity")
        elif event_kind != ("sack" if flag == "sack" else "pass"):
            issues.append("inconsistent_" + flag + "_event")
        elif metric == "interceptions":
            if canonical(values[0]):
                out[metric][values[0]] = 1
            else:
                issues.append("unresolved_interception_identity")
        else:
            solo, half1, half2 = values
            if canonical(solo) and half1 in MISSING and half2 in MISSING:
                out[metric][solo] = 1.0
            elif solo in MISSING and canonical(half1) and canonical(half2) and half1 != half2:
                out[metric] = {half1: 0.5, half2: 0.5}
            else:
                issues.append("unresolved_sack_credit")
    return out, issues


def observed_explorer(ledger, game_coverage, first_unit, event_rows, roster_rows):
    """Consume a replayed ledger and same-source event records; preserve all team outcomes."""
    if not game_coverage["coverage_complete"] or not game_coverage["matched_games"] or not first_unit:
        raise ValueError("reconciled games and chart coverage diagnostics required")
    games = {g["game_id"]: g for g in game_coverage["matched_games"]}
    if len(games) != len(game_coverage["matched_games"]):
        raise ValueError("duplicate completed game")
    plays = {(p["game_id"], p["play_id"]): p for p in ledger["plays"]}
    if len(plays) != len(ledger["plays"]) or not plays:
        raise ValueError("nonempty unique play cohort required")
    team_plays, players, chart_espn = defaultdict(list), {}, defaultdict(set)
    per_game_teams = defaultdict(set)

    def entry(player, gid, team):
        if not canonical(player) or gid not in games or team not in {games[gid]["away_team"], games[gid]["home_team"]}:
            raise ValueError("invalid observed identity/game/team")
        per_game_teams[(player, gid)].add(team)
        if len(per_game_teams[(player, gid)]) != 1:
            raise ValueError("player assigned to both teams in one game")
        item = players.setdefault(player, {})
        game = games[gid]
        opponent = game["away_team"] if game["home_team"] == team else game["home_team"]
        return item.setdefault(gid, {"game_id": gid, "week": game["week"], "team": team, "opponent": opponent,
                                    "chart_roles": [], "sack_credits": 0.0, "interceptions": 0})

    for p in plays.values():
        if p["game_id"] not in games:
            raise ValueError("ledger includes unreconciled game")
        game = games[p["game_id"]]
        if {p["offense_team"], p["defense_team"]} != {game["away_team"], game["home_team"]}:
            raise ValueError("ledger teams disagree with completed game")
        team_plays[(p["game_id"], p["defense_team"])].append(p)

    issues = [i for i in first_unit["issues"] if i["role"] in DEFENSE_ROLES]
    blocked = {(i["game_id"], i["team_id"], i["role"]) for i in issues}
    valid_cells = set()
    for a in first_unit["assignments"]:
        key = (a["game_id"], a["team_id"], a["role"])
        if a["role"] not in DEFENSE_ROLES or key in blocked:
            continue
        row = entry(a["player_id"], a["game_id"], a["team_id"])
        if a["role"] not in row["chart_roles"]:
            row["chart_roles"].append(a["role"])
        chart_espn[a["player_id"]].add(a["espn_id"])
        valid_cells.add(key)

    seen, linked, event_issues = set(), set(), []
    known = Counter(sacks=0, interceptions=0)
    allocated = Counter(sacks=0.0, interceptions=0)
    unknown = Counter(sacks=0, interceptions=0)
    for row in event_rows:
        key = (row["game_id"], int(row["play_id"]))
        if key in seen:
            raise ValueError("duplicate PBP event key")
        seen.add(key)
        if key not in plays:
            continue
        linked.add(key)
        p = plays[key]
        credit, reasons = event_credits(row, p["event_kind"])
        for metric, flag in (("sacks", "sack"), ("interceptions", "interception")):
            known[metric] += row[flag] == "1"
            unknown[metric] += row[flag] not in {"0", "1"}
            for player, value in credit[metric].items():
                target = entry(player, key[0], p["defense_team"])
                target["sack_credits" if metric == "sacks" else "interceptions"] += value
                allocated[metric] += value
        if reasons:
            event_issues.append({"game_id": key[0], "play_id": key[1], "reasons": reasons})
    if linked != plays.keys():
        raise ValueError("event rows do not cover the exact ledger cohort")

    identities, espn_players = defaultdict(list), defaultdict(set)
    for row in roster_rows:
        if canonical(row["gsis_id"]):
            identities[row["gsis_id"]].append(row)
            espn_players[row["espn_id"]].add(row["gsis_id"])
    output, name_issues = [], []
    for player, entries in sorted(players.items()):
        candidates = identities[player]
        names = {r["full_name"].strip() for r in candidates if r["full_name"].strip() not in MISSING}
        espns = {r["espn_id"] for r in candidates if re.fullmatch(r"[1-9]\d*", r["espn_id"])}
        name = next(iter(names)) if len(names) == 1 and len(espns) == 1 and espn_players[next(iter(espns))] == {player} and (not chart_espn[player] or chart_espn[player] == espns) else None
        if name is None:
            name_issues.append({"player_id": player, "reason": "missing_or_ambiguous_roster_name_identity"})
        rows = sorted(entries.values(), key=lambda r: (r["week"], r["game_id"]))
        output.append({"player_id": player, "name": name, "teams": sorted({r["team"] for r in rows}),
                       "roles": sorted({role for r in rows for role in r["chart_roles"]}),
                       "chart_games": sum(bool(r["chart_roles"]) for r in rows),
                       "event_games": sum(r["sack_credits"] > 0 or r["interceptions"] > 0 for r in rows),
                       "sack_credits": fsum(r["sack_credits"] for r in rows), "interceptions": sum(r["interceptions"] for r in rows),
                       "cavaa": None, "defensive_snaps": None, "games": rows})
    contexts = []
    for gid, game in sorted(games.items()):
        for team, opponent in ((game["home_team"], game["away_team"]), (game["away_team"], game["home_team"])):
            rows = team_plays[(gid, team)]
            available = [p for p in rows if p["offense_epa"] is not None]
            total = -fsum(p["offense_epa"] for p in rows) if rows and len(available) == len(rows) else None
            contexts.append({"game_id": gid, "week": game["week"], "team": team, "opponent": opponent,
                             "included_plays": len(rows), "epa_observed_plays": len(available), "defense_epa": total})
    coverage = {"completed_games": len(games), "through_week": max(g["week"] for g in games.values()),
                "included_plays": len(plays), "players": len(output), "expected_role_cells": 2*len(games),
                "role_cells": [{"role": role, "complete_cells": sum(k[2] == role for k in valid_cells),
                                "blocked_cells": len({k for k in blocked if k[2] == role})} for role in DEFENSE_ROLES]}
    return {"coverage": coverage, "players": output, "team_games": sorted(contexts, key=lambda r: (r["game_id"], r["team"])),
            "unavailable": UNAVAILABLE,
            "audit": {"chart_issues": issues, "name_issues": name_issues, "event_issues": event_issues,
                      "flagged_events": dict(known), "allocated_credits": dict(allocated),
                      "unallocated_flagged_events": {k: known[k]-allocated[k] for k in known}, "unknown_event_flags": dict(unknown)}}


def build_explorer(raw, inputs, *, offensive_report, depth_charts, rosters, code_revision):
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("full committed code revision required")
    report = replay_offensive_inputs(raw, inputs, offensive_report)
    ledger = json.loads(inputs.read(report["objects"]["ledger"]))
    cutoff = aware_time(report["cutoff"])
    ids = {**report["source_receipts"], "depth_charts": depth_charts, "rosters": rosters}
    receipts = {kind: replay(raw, rid) for kind, rid in ids.items()}
    if any(r["source"]["kind"] != kind or r["source"]["season"] != report["season"] for kind, r in receipts.items()):
        raise ValueError("source kind/season mismatch")
    if any(aware_time(t) > cutoff for r in receipts.values() for t in r["retrieval"].values()):
        raise ValueError("source retrieved after the fixed outcome cutoff")
    chart = build_inputs(raw, schedules=ids["schedules"], pbp=ids["pbp"], depth_charts=depth_charts, cutoff=cutoff, code_revision=code_revision)
    if chart["game_coverage"] != report["game_coverage"]:
        raise ValueError("chart and outcome cohorts disagree")
    data = observed_explorer(ledger, report["game_coverage"], chart["first_unit"],
        _rows(raw.read(receipts["pbp"]["objects"]["raw"]), EVENT_COLUMNS),
        _rows(raw.read(receipts["rosters"]["objects"]["raw"]), {"gsis_id", "espn_id", "full_name"}))
    return {"schema_version": 1, "kind": "defense_explorer", "data_mode": "observed", "ranking_ready": False,
            "season": report["season"], "cutoff": report["cutoff"], "code_revision": code_revision,
            "provenance": {"offensive_report": offensive_report, "source_receipts": ids,
                "sources": [{"kind": kind, "fetched_at": r["retrieval"]["data"], "updated_at": r["asset"]["updated_at"],
                             "source_url": r["asset"]["browser_download_url"],
                             **{k: r["source"][k] for k in ("license_id", "license_url", "attribution")}} for kind, r in sorted(receipts.items())],
                "opportunity_policy": ledger["opportunity_policy"], "chart_policy": chart["first_unit"]["policy_version"],
                "retrospective_chart_team_games": chart["historical_availability"]["team_games_using_retrospectively_retrieved_depth"],
                "name_policy": "Unique GSIS/ESPN roster name only; roster team and position do not establish historical roles or stints."},
            "scope": "Recorded sacks/interceptions on included completed REG pass/run plays, plus valid pregame first-unit chart members. Not a complete roster or official full-season totals.",
            **data}


def save_explorer(store, payload):
    obj = store.put(json_bytes(payload))
    report = {"report_version": 1, "object": obj, "code_revision": payload["code_revision"], "ranking_ready": False,
              "offensive_report": payload["provenance"]["offensive_report"],
              "depth_charts": payload["provenance"]["source_receipts"]["depth_charts"],
              "rosters": payload["provenance"]["source_receipts"]["rosters"]}
    return store.put(json_bytes(report), manifest=True), report


def replay_explorer(raw, inputs, store, report_id):
    report = json.loads(store.read(report_id, manifest=True))
    if report["report_version"] != 1 or report["ranking_ready"] is not False:
        raise ValueError("unsupported explorer report")
    payload = build_explorer(raw, inputs, **{k: report[k] for k in ("offensive_report", "depth_charts", "rosters", "code_revision")})
    if json_bytes(payload) != store.read(report["object"]):
        raise ValueError("explorer replay differs; use recorded code revision")
    return report, payload


def export_explorer(store, report_id, destination):
    """Publish a verified immutable object before atomically advancing its local pointer."""
    report = json.loads(store.read(report_id, manifest=True))
    body = store.read(report["object"])
    payload = json.loads(body)
    if report["report_version"] != 1 or payload["schema_version"] != 1 or payload["kind"] != "defense_explorer" or payload["ranking_ready"] is not False:
        raise ValueError("unsupported explorer export")
    if any(p["cavaa"] is not None or p["defensive_snaps"] is not None for p in payload["players"]):
        raise ValueError("unadmitted values cannot be exported")
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("export directory cannot be a symbolic link")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / (report["object"] + ".json")
    if target.is_symlink():
        raise ValueError("export object cannot be a symbolic link")
    if target.exists():
        if target.read_bytes() != body:
            raise ValueError("existing immutable export disagrees")
    else:
        _publish_bytes(target, body, replace=False)
    pointer = {"schema_version": 1, "snapshot_id": report["object"]}
    _publish_bytes(destination / "latest.json", json_bytes(pointer), replace=True)
    return pointer


def _publish_bytes(path, body, *, replace):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
