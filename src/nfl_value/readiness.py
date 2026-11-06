"""Frozen operational source gates for 2026 Explorer candidates, not rankings."""

from collections import Counter
from copy import deepcopy
import re

from nfl_value.ingestion import json_bytes, replay, sha256
from nfl_value.pregame_inputs import _rows
from nfl_value.recovery_io import decode_object
from nfl_value.schedules import CLOCK_COLUMNS, CLOCK_COMPLETION, reconcile_game_coverage
from nfl_value.source_audit import aware_time


TEAMS = tuple(
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS".split()
)
POLICY = {
    "version": "explorer-source-readiness-2026-v1",
    "season": 2026,
    "required_sources": {
        "schedules": {"retrieval_hours": 6, "upstream_hours": 2},
        "pbp": {"retrieval_hours": 6, "upstream_hours": 96},
        "depth_charts": {"retrieval_hours": 6, "upstream_hours": 48},
        "rosters": {"retrieval_hours": 6, "upstream_hours": 48},
    },
    "depth_team_snapshot_hours": 48,
    "expected_teams": list(TEAMS),
    "regular_season_games": 272,
    "games_per_team": 17,
    "completion_policy": CLOCK_COMPLETION,
    "pending_started_games": "block_entire_candidate",
}


def _context(cutoff, code_revision):
    if cutoff.utcoffset() is None or not re.fullmatch(r"[a-f0-9]{40}", code_revision):
        raise ValueError("timezone-aware cutoff and full committed revision required")


def _schedule_inventory(games):
    regular = {gid: g for gid, g in games.items() if g["season_type"] == "REG"}
    counts = Counter(g[side] for g in regular.values() for side in ("away_team", "home_team"))
    cells = Counter(
        (g[side], g["week"]) for g in regular.values() for side in ("away_team", "home_team")
    )
    duplicates = [
        {"team": team, "week": week, "games": count}
        for (team, week), count in sorted(cells.items())
        if count > 1
    ]
    return {
        "regular_games": len(regular),
        "team_game_counts": dict(sorted(counts.items())),
        "duplicate_team_weeks": duplicates,
        "complete": len(regular) == POLICY["regular_season_games"]
        and set(counts) == set(TEAMS)
        and all(counts[t] == POLICY["games_per_team"] for t in TEAMS)
        and not duplicates,
    }


def assess_sources(raw, receipt_ids, *, cutoff, code_revision):
    """Replay inputs before measuring readiness. Missing/stale inputs block explicitly.

    Corrupt or invalid inputs raise; they are not ordinary feed latency. Freshness
    is checked at the declared cutoff. Later replay is not a new current check.
    """
    _context(cutoff, code_revision)
    required = POLICY["required_sources"]
    if not isinstance(receipt_ids, dict) or set(receipt_ids) - set(required):
        raise ValueError("only the four reviewed Explorer source kinds are supported")
    receipts, checks, blockers = {}, {}, []

    def block(scope, reason):
        blockers.append({"scope": scope, "reason": reason})

    for kind, limits in required.items():
        rid = receipt_ids.get(kind)
        if rid is None:
            checks[kind] = {"receipt_id": None, "available": False}
            block(kind, "missing_receipt")
            continue
        receipt = replay(raw, rid)
        if receipt["source"]["kind"] != kind or receipt["source"]["season"] != 2026:
            raise ValueError("readiness source kind/season mismatch")
        if any(aware_time(t) > cutoff for t in receipt["retrieval"].values()):
            raise ValueError("source evidence was retrieved after the readiness cutoff")
        fetched, updated = (
            aware_time(value)
            for value in (receipt["retrieval"]["data"], receipt["asset"]["updated_at"])
        )
        retrieval_age, upstream_age = (
            (cutoff - value).total_seconds() for value in (fetched, updated)
        )
        checks[kind] = {
            "receipt_id": rid,
            "available": True,
            "retrieved_at": receipt["retrieval"]["data"],
            "updated_at": receipt["asset"]["updated_at"],
            "retrieval_age_seconds": retrieval_age,
            "upstream_age_seconds": upstream_age,
        }
        if retrieval_age > limits["retrieval_hours"] * 3600:
            block(kind, "retrieval_too_old")
        if upstream_age > limits["upstream_hours"] * 3600:
            block(kind, "upstream_update_too_old")
        if kind in {"depth_charts", "rosters"} and set(receipt["audit"]["teams"]) != set(TEAMS):
            block(kind, "team_universe_incomplete")
        receipts[kind] = receipt

    inventory, coverage = None, None
    if "schedules" in receipts:
        games = receipts["schedules"]["audit"]["games"]
        inventory = _schedule_inventory(games)
        if not inventory["complete"]:
            block("schedules", "regular_season_inventory_incomplete")
        if "pbp" in receipts:
            coverage = reconcile_game_coverage(
                games,
                _rows(
                    raw.read(receipts["pbp"]["objects"]["raw"]),
                    {"home_team", "away_team", "total_home_score", "total_away_score"}
                    | CLOCK_COLUMNS,
                ),
                cutoff=cutoff,
                observed_at=max(
                    aware_time(receipts[k]["retrieval"]["data"]) for k in ("pbp", "schedules")
                ),
                policy_version=CLOCK_COMPLETION,
            )
            if not coverage["coverage_complete"]:
                block("game_coverage", "unresolved_or_no_completed_games")

    latest = {}
    if "depth_charts" in receipts:
        for row in _rows(raw.read(receipts["depth_charts"]["objects"]["raw"]), {"team", "dt"}):
            value = aware_time(row["dt"])
            if row["team"] not in latest or value > latest[row["team"]]:
                latest[row["team"]] = value
        for team in TEAMS:
            if team not in latest:
                block(f"depth_charts:{team}", "missing_team_snapshot")
            elif (cutoff - latest[team]).total_seconds() > POLICY[
                "depth_team_snapshot_hours"
            ] * 3600:
                block(f"depth_charts:{team}", "team_snapshot_too_old")
    return {
        "schema_version": 1,
        "kind": "explorer_source_readiness",
        "season": 2026,
        "code_revision": code_revision,
        "cutoff": cutoff.isoformat(),
        "policy": deepcopy(POLICY),
        "policy_sha256": sha256(json_bytes(POLICY)),
        "source_receipts": {kind: receipt_ids.get(kind) for kind in required},
        "source_checks": checks,
        "schedule_inventory": inventory,
        "game_coverage": coverage,
        "latest_depth_by_team": {team: value.isoformat() for team, value in sorted(latest.items())},
        "blockers": blockers,
        "ready_for_explorer_build": not blockers,
        "ranking_ready": False,
        "limitations": [
            "Operational age limits are project policy, not an upstream SLA or scientific validation.",
            "Completion is reconciled across nflverse files, not independently verified by a live NFL status feed.",
            "All started games must reconcile; a live, postponed or unresolved game conservatively blocks the whole candidate.",
            "Fresh files do not prove complete identities, workload, pregame vintage availability or player attribution.",
            "Readiness is evaluated only at this cutoff; replay later does not renew freshness.",
        ],
    }


def save_readiness(store, report):
    return store.put(json_bytes(report), manifest=True)


def replay_readiness(raw, store, report_id):
    body = store.read(report_id, manifest=True)
    saved = decode_object(body)
    reproduced = assess_sources(
        raw,
        saved["source_receipts"],
        cutoff=aware_time(saved["cutoff"]),
        code_revision=saved["code_revision"],
    )
    if body != json_bytes(reproduced):
        raise ValueError("readiness replay differs; use the recorded code/policy")
    return reproduced
