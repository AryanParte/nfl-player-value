"""Offline, versioned candidate inputs. No fitted effects or rankings."""

from datetime import datetime
import csv
import gzip
import io
import json
import re

from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.first_unit import require_role_assignments, select_first_units
from nfl_value.ingestion import SnapshotStore, replay
from nfl_value.schedules import reconcile_game_coverage
from nfl_value.source_audit import aware_time


def _rows(raw: bytes, required: set[str]):
    # Call only after replay has bounded the gzip expansion and validated CSV.
    reader = csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8-sig", newline=""), strict=True)
    if not required <= set(reader.fieldnames or []):
        raise ValueError(f"normalization requires columns: {sorted(required - set(reader.fieldnames or []))}")
    yield from reader


def _team_games(coverage: dict) -> list[CompletedTeamGame]:
    return [
        CompletedTeamGame(g["game_id"], g[side], aware_time(g["scheduled_kickoff"]), aware_time(g["completion_observed_by"]), "REG")
        for g in coverage["matched_games"] for side in ("away_team", "home_team")
    ]


def build_inputs(store: SnapshotStore, *, schedules: str, pbp: str, depth_charts: str, cutoff: datetime, code_revision: str) -> dict:
    """Verify every receipt first; derive deterministic diagnostic inputs locally."""
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("code_revision must be a full Git SHA")
    if cutoff.utcoffset() is None:
        raise ValueError("cutoff must be timezone-aware")
    receipt_ids = {"schedules": schedules, "pbp": pbp, "depth_charts": depth_charts}
    receipts = {kind: replay(store, rid) for kind, rid in receipt_ids.items()}
    if any(r["source"]["kind"] != kind for kind, r in receipts.items()):
        raise ValueError("receipt source kind disagrees with requested input")
    seasons = {r["source"]["season"] for r in receipts.values()}
    if len(seasons) != 1:
        raise ValueError("all input receipts must describe one season")
    if any(aware_time(t) > cutoff for r in receipts.values() for t in r["retrieval"].values()):
        raise ValueError("input receipt was retrieved after cutoff")
    observed_at = max(aware_time(receipts[k]["retrieval"]["data"]) for k in ("schedules", "pbp"))
    games = reconcile_game_coverage(
        receipts["schedules"]["audit"]["games"],
        _rows(store.read(receipts["pbp"]["objects"]["raw"]), {"home_team", "away_team", "total_home_score", "total_away_score"}),
        cutoff=cutoff, observed_at=observed_at,
    )
    team_games = _team_games(games)
    first_unit = select_first_units(
        _rows(store.read(receipts["depth_charts"]["objects"]["raw"]), {"pos_grp"}), team_games,
    ) if team_games else None
    depth_observed = aware_time(receipts["depth_charts"]["retrieval"]["data"])
    return {
        "report_version": 1, "code_revision": code_revision, "season": seasons.pop(),
        "cutoff": cutoff.isoformat(), "source_receipts": receipt_ids,
        "season_team_ids": receipts["schedules"]["audit"]["teams"],
        "game_coverage": games, "first_unit": first_unit,
        "historical_availability": {
            "team_games_with_depth_retrieved_before_kickoff": sum(depth_observed < g.kickoff for g in team_games),
            "team_games_using_retrospectively_retrieved_depth": sum(depth_observed >= g.kickoff for g in team_games),
        },
        "ranking_ready": False,
        "limitations": [
            "Completion uses terminal PBP markers plus schedule agreement, not an independent live final-status feed.",
            "Scheduled kickoff is conservative selection context, not verified actual kickoff.",
            "Historical depth row times may contain later corrections; this does not prove vintage pregame availability.",
            "Chart roles do not establish participation, roster stints, eligibility denominators or defensive assignments on plays.",
            "Defensive roles are formation proxies; nickel is included as an additional chart role and duplicate CB identities are counted once.",
            "Fullback and holder are not silently assigned to running back or punter benchmarks.",
            "No individual attribution, cross-position comparability or CAVAA ranking has been validated.",
        ],
    }


def require_benchmark_inputs(report: dict, role: str, *, allow_retrospective: bool = False):
    """Guard the whole universe before handing candidate inputs to modeling.

    Explicit retrospective use permits research on later-retrieved chart records;
    it does not validate historical availability, eligibility, or contribution.
    """
    if type(allow_retrospective) is not bool:
        raise ValueError("allow_retrospective must be an explicit boolean")
    if not report["game_coverage"]["coverage_complete"] or report["first_unit"] is None:
        raise ValueError("incomplete schedule/PBP game coverage")
    games = _team_games(report["game_coverage"])
    if {g.team_id for g in games} != set(report["season_team_ids"]):
        raise ValueError("completed games do not yet cover the season team universe")
    if report["historical_availability"]["team_games_using_retrospectively_retrieved_depth"] and not allow_retrospective:
        raise ValueError("retrospective depth evidence must be explicitly acknowledged")
    assignments = require_role_assignments(report["first_unit"], role)
    if {(a.team_id, a.game_id) for a in assignments} != {(g.team_id, g.game_id) for g in games}:
        raise ValueError("incomplete first-unit team-game cells")
    return tuple(games), assignments


def replay_inputs(raw_store: SnapshotStore, derived_store: SnapshotStore, report_id: str) -> dict:
    saved = json.loads(derived_store.read(report_id, manifest=True))
    if saved["report_version"] != 1:
        raise ValueError("unsupported pregame input report version")
    reproduced = build_inputs(raw_store, **saved["source_receipts"], cutoff=aware_time(saved["cutoff"]), code_revision=saved["code_revision"])
    if reproduced != saved:
        raise ValueError("input replay differs; use the recorded code revision")
    return reproduced
