"""Versioned weekly position/team evidence joined to an archived game cohort.

This is evidence for later exposure reconciliation, not a completed denominator.
It neither allocates EPA nor changes the existing offensive ledger or benchmark.
"""

from collections import Counter, defaultdict
from datetime import datetime
import json
import re

from nfl_value.benchmarks import _aware, _count, validate_player_id
from nfl_value.ingestion import SnapshotStore, json_bytes, replay, sha256
from nfl_value.offensive_inputs import COUNT_NAMES, replay_offensive_inputs
from nfl_value.pregame_inputs import _rows, _team_games
from nfl_value.source_audit import aware_time
from nfl_value.weekly_rosters import MISSING, WEEKLY_ROSTER_COLUMNS, normalize_weekly_rosters


POLICY = "weekly-roster-evidence-v1"


def join_roster_evidence(
    rows,
    *,
    season: int,
    team_games,
    season_teams: list[str],
    workloads: list[dict],
    retrieved_at: datetime,
) -> tuple[dict, dict]:
    """Join on GSIS/team/season/week, never backfill from a later week or name.

    Keep one row for each listed player/team/completed game, including those with
    no offensive actor observation. Missing workloads are null, not zero snaps or
    a missed game. Bye weeks generate no game. Status remains uninterpreted.
    """
    _aware(retrieved_at, "retrieved_at")
    team_games = tuple(team_games)
    observations = normalize_weekly_rosters(rows, season=season)
    by_team_week, games = {}, {}
    for game in team_games:
        if int(game.game_id[:4]) != season or game.team_id not in season_teams:
            raise ValueError("completed game outside roster season/team universe")
        key = (game.team_id, int(game.game_id.split("_")[1]))
        if key in by_team_week:
            raise ValueError("duplicate completed team/week")
        by_team_week[key] = game
        games[(game.game_id, game.team_id)] = game
    by_player_week, by_secondary, coverage = defaultdict(list), defaultdict(set), Counter()
    keys = set()
    for index, row in enumerate(observations):
        if row["game_type"] != "REG":
            continue
        if row["team"] not in season_teams:
            raise ValueError("weekly roster team outside schedule universe; review mapping")
        if row["espn_id"] not in MISSING:
            by_secondary[(row["espn_id"], row["week"])].add(row["source_gsis_id"])
        game = by_team_week.get((row["team"], row["week"]))
        if game:
            coverage[(game.game_id, game.team_id)] += 1
        if row["player_id"] is not None:
            by_player_week[(row["player_id"], row["week"])].append(index)
            if game:
                keys.add((row["player_id"], game.game_id, game.team_id))
    workload_by_key, actor_teams = {}, defaultdict(set)
    for item in workloads:
        validate_player_id(item["player_id"])
        key = (item["player_id"], item["game_id"], item["team"])
        if key in workload_by_key:
            raise ValueError("duplicate offensive player/game/team workload")
        if (item["game_id"], item["team"]) not in games:
            raise ValueError("offensive workload outside completed team games")
        for scope in ("observed", "context_outcome_complete"):
            if set(item[scope]) != set(COUNT_NAMES):
                raise ValueError("unexpected offensive opportunity units")
            for name in COUNT_NAMES:
                _count(item[scope][name], name)
        if any(item["context_outcome_complete"][n] > item["observed"][n] for n in COUNT_NAMES):
            raise ValueError("complete opportunities exceed observed opportunities")
        if not item["observed"]["on_ball_plays"]:
            raise ValueError("observed actor workload must include a positive on-ball count")
        workload_by_key[key] = item
        actor_teams[(item["player_id"], item["game_id"])].add(item["team"])
        keys.add(key)
    evidence = []
    for player, game_id, team in sorted(keys):
        game = games[(game_id, team)]
        week = int(game_id.split("_")[1])
        indices = by_player_week[(player, week)]
        issues, role = [], None
        if not indices:
            issues.append("missing_roster_record")
        elif len(indices) != 1:
            issues.append("ambiguous_player_week")
        else:
            row = observations[indices[0]]
            if row["team"] != team:
                issues.append("roster_team_mismatch")
            if row["espn_id"] not in MISSING and len(by_secondary[(row["espn_id"], week)]) > 1:
                issues.append("conflicting_secondary_identity")
            issues.extend(row["issues"])
            if not issues:
                role = row["source_position_role"]
        if len(actor_teams[(player, game_id)]) > 1:
            issues.append("offensive_player_game_team_conflict")
            role = None
        workload = workload_by_key.get((player, game_id, team))
        evidence.append(
            {
                "player_id": player,
                "game_id": game_id,
                "team": team,
                "week": week,
                "roster_observation_indices": indices,
                "source_position_role": role,
                "observed_offensive_participation": workload is not None,
                "offensive_opportunities": {
                    s: workload[s] for s in ("observed", "context_outcome_complete")
                }
                if workload
                else None,
                "roster_retrieved_before_kickoff": retrieved_at < game.kickoff,
                "issues": sorted(issues),
            }
        )
    actor_rows = [r for r in evidence if r["observed_offensive_participation"]]
    coverage_rows = [
        {"game_id": game_id, "team": team, "listed_rows": coverage[(game_id, team)]}
        for game_id, team in sorted(games)
    ]
    payload = {
        "schema_version": 1,
        "policy": POLICY,
        "roster_observations": observations,
        "player_games": evidence,
        "team_game_roster_coverage": coverage_rows,
        "qualification_denominator_complete": False,
        "roster_stints_verified": False,
        "ranking_ready": False,
    }
    audit = {
        "weekly_observations": len(observations),
        "completed_team_games": len(games),
        "team_games_without_roster_rows": sum(not r["listed_rows"] for r in coverage_rows),
        "player_game_rows": len(evidence),
        "observed_offensive_player_games": len(actor_rows),
        "observed_offensive_players": len({r["player_id"] for r in actor_rows}),
        "actor_rows_with_resolved_role": sum(
            r["source_position_role"] is not None for r in actor_rows
        ),
        "actor_role_counts": dict(
            sorted(
                Counter(
                    r["source_position_role"] for r in actor_rows if r["source_position_role"]
                ).items()
            )
        ),
        "actor_issue_counts": dict(
            sorted(Counter(i for r in actor_rows for i in r["issues"]).items())
        ),
        "all_player_game_issue_counts": dict(
            sorted(Counter(i for r in evidence for i in r["issues"]).items())
        ),
        "player_games_without_observed_offensive_participation": len(evidence) - len(actor_rows),
        "team_games_with_roster_retrieved_before_kickoff": sum(
            retrieved_at < g.kickoff for g in team_games
        ),
        "team_games_with_retrospective_roster_retrieval": sum(
            retrieved_at >= g.kickoff for g in team_games
        ),
    }
    return payload, audit


def build_roster_inputs(
    raw: SnapshotStore,
    offensive: SnapshotStore,
    *,
    weekly_rosters: str,
    offensive_report_id: str,
    evidence_cutoff: datetime,
    code_revision: str,
) -> tuple[dict, dict]:
    """Rebuild both dependencies before joining; keep their cutoffs distinct."""
    _aware(evidence_cutoff, "evidence_cutoff")
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("full code revision required")
    receipt = replay(raw, weekly_rosters)
    if receipt["source"]["kind"] != "weekly_rosters":
        raise ValueError("expected weekly_rosters source kind")
    upstream = replay_offensive_inputs(raw, offensive, offensive_report_id)
    if receipt["source"]["season"] != upstream["season"]:
        raise ValueError("roster and offensive evidence must describe the same season")
    if aware_time(upstream["cutoff"]) > evidence_cutoff or any(
        aware_time(t) > evidence_cutoff for t in receipt["retrieval"].values()
    ):
        raise ValueError("input evidence is later than evidence cutoff")
    ledger = json.loads(offensive.read(upstream["objects"]["ledger"]))
    schedule = replay(raw, upstream["source_receipts"]["schedules"])
    evidence, audit = join_roster_evidence(
        _rows(raw.read(receipt["objects"]["raw"]), WEEKLY_ROSTER_COLUMNS),
        season=upstream["season"],
        team_games=_team_games(upstream["game_coverage"]),
        season_teams=schedule["audit"]["teams"],
        workloads=ledger["observed_player_games"],
        retrieved_at=aware_time(receipt["retrieval"]["data"]),
    )
    report = {
        "report_version": 1,
        "policy": POLICY,
        "code_revision": code_revision,
        "season": upstream["season"],
        "evidence_cutoff": evidence_cutoff.isoformat(),
        "game_cohort_cutoff": upstream["cutoff"],
        "offensive_report_id": offensive_report_id,
        "weekly_rosters": weekly_rosters,
        "game_coverage_complete": upstream["game_coverage"]["coverage_complete"],
        "source_attribution": {
            **upstream["source_attribution"],
            "weekly_rosters": {
                k: receipt["source"][k] for k in ("license_id", "license_url", "attribution")
            },
        },
        "audit": audit,
        "ranking_ready": False,
        "limitations": [
            "Source positions are retrospective weekly labels, not verified roles on every play.",
            "Weekly status/roster listing does not establish transaction time, exact stints or a missed-game denominator.",
            "No forward/backward filling across gaps, byes, trades, position changes or missing identities.",
            "No observed offensive workload means unknown participation, not zero snaps, zero value or a missed game.",
            "Released/reserve/practice-squad labels are preserved; their exposure rules require separate review.",
            "No benchmark, qualification, attribution or position-admission decision is made by this evidence join.",
            "New roster retrieval does not update the archived game's cutoff or establish historical availability.",
        ],
    }
    evidence["provenance"] = {
        k: report[k]
        for k in (
            "policy",
            "code_revision",
            "season",
            "evidence_cutoff",
            "game_cohort_cutoff",
            "offensive_report_id",
            "weekly_rosters",
            "source_attribution",
        )
    }
    return report, evidence


def save_roster_inputs(derived: SnapshotStore, report: dict, evidence: dict) -> tuple[str, dict]:
    saved = {**report, "objects": {"evidence": derived.put(json_bytes(evidence))}}
    return derived.put(json_bytes(saved), manifest=True), saved


def replay_roster_inputs(
    raw: SnapshotStore, offensive: SnapshotStore, derived: SnapshotStore, report_id: str
) -> dict:
    saved = json.loads(derived.read(report_id, manifest=True))
    if type(saved["report_version"]) is not int or saved["report_version"] != 1:
        raise ValueError("unsupported roster input report version")
    report, evidence = build_roster_inputs(
        raw,
        offensive,
        weekly_rosters=saved["weekly_rosters"],
        offensive_report_id=saved["offensive_report_id"],
        evidence_cutoff=aware_time(saved["evidence_cutoff"]),
        code_revision=saved["code_revision"],
    )
    body = derived.read(saved["objects"]["evidence"])
    if body != json_bytes(evidence) or {**report, "objects": {"evidence": sha256(body)}} != saved:
        raise ValueError("roster input replay differs; use recorded code revision")
    return saved
