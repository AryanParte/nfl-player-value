"""Prefix-only positional cohorts and a deliberately narrow exposure proof."""

from collections import Counter, defaultdict
from dataclasses import asdict

from nfl_value.baseline import actor_features
from nfl_value.benchmarks import FirstUnitAssignment, PlayerPrediction, calculate_benchmarks
from nfl_value.contrast_math import EXPOSURE, SCOPES
from nfl_value.eligibility import GameExposure, ModuleStatus, SeasonExposure, qualify
from nfl_value.source_audit import aware_time


UNITS = {
    "QB": ("modeled_qb_plays", "dropback_or_rush_plays"),
    "RB": ("carry_or_target_plays", "carry_or_target_plays"),
    "WR": ("targets", "targets"),
    "TE": ("targets", "targets"),
}


def make_cohorts(rows, evidence, first_unit, games, *, cutoff):
    """Keep all model actors; only resolved role/component links get contrasts.

    Zero-valued PlayerPrediction placeholders below are used ONLY to obtain
    cohort weights from the established benchmark policy. They are never model
    predictions or serialized scores. Actual contrasts use fitted coefficients.
    """
    game_ids = {g.game_id for g in games}
    roster = {}
    for row in evidence["player_games"]:
        if row["game_id"] not in game_ids:
            continue
        key = (row["player_id"], row["game_id"], row["team"])
        if key in roster:
            raise ValueError("duplicate roster player/game/team")
        roster[key] = row
    counts, opportunities, links = defaultdict(Counter), defaultdict(set), {}
    game_opportunities = defaultdict(set)
    unsupported = Counter()
    for play in rows:
        for feature in actor_features(play):
            component, player = feature.split("/")
            row = roster.get((player, play["game_id"], play["offense_team"]))
            role = row["source_position_role"] if row and not row["issues"] else None
            if role not in SCOPES or component not in SCOPES[role]:
                unsupported["unresolved_position" if role is None else "outside_role_scope"] += 1
                continue
            key = (role, player)
            counts[key][component] += 1
            opportunities[key].add((play["game_id"], play["play_id"]))
            game_opportunities[(role, player, play["game_id"])].add(play["play_id"])
            links[(play["game_id"], play["play_id"], feature)] = role
    candidates = {role: {p for r, p in counts if r == role} for role in SCOPES}
    assignments, failures = defaultdict(list), defaultdict(list)
    for issue in first_unit["issues"]:
        if issue["game_id"] in game_ids and issue["role"] in SCOPES:
            failures[issue["role"]].append(issue)
    for item in first_unit["assignments"]:
        if item["game_id"] not in game_ids or item["role"] not in SCOPES:
            continue
        role, player = item["role"], item["player_id"]
        candidates[role].add(player)
        row = roster.get((player, item["game_id"], item["team_id"]))
        if row is None or row["issues"] or row["source_position_role"] != role:
            failures[role].append(
                {
                    "game_id": item["game_id"],
                    "team_id": item["team_id"],
                    "reason": "first_unit_roster_role_unresolved_or_disagrees",
                }
            )
        assignments[role].append(
            FirstUnitAssignment(
                player, role, item["team_id"], item["game_id"], aware_time(item["snapshot_at"])
            )
        )
    weights, audit = {}, {}
    for role in SCOPES:
        if not failures[role]:
            try:
                benchmarks = calculate_benchmarks(
                    role=role,
                    predictions=[
                        PlayerPrediction(p, role, 0.0, len(opportunities[(role, p)]))
                        for p in sorted(candidates[role])
                    ],
                    assignments=assignments[role],
                    team_games=games,
                    expected_team_ids=sorted({g.team_id for g in games}),
                    cutoff=cutoff,
                )
                weights[role] = {
                    name: dict(getattr(benchmarks, name).player_weights)
                    for name in ("first_unit", "equal_player", "opportunity_weighted")
                }
            except ValueError as exc:
                failures[role].append({"reason": str(exc)})
        audit[role] = {
            "benchmark_ready": role in weights,
            "blocked_reasons": failures[role],
            "candidate_players": len(candidates[role]),
            "observed_players": sum(r == role for r, _ in counts),
            "first_unit_zero_opportunity_players": sorted(
                {a.player_id for a in assignments[role] if not opportunities[(role, a.player_id)]}
            ),
        }
    return {
        "candidates": {r: sorted(p) for r, p in candidates.items()},
        "weights": weights,
        "audit": audit,
        "counts": counts,
        "opportunities": opportunities,
        "game_opportunities": game_opportunities,
        "links": links,
        "roster": roster,
        "unsupported_actor_appearances": dict(unsupported),
    }


def exposure_diagnostic(
    player, role, cohorts, evidence, games, *, season, week, cutoff, multipliers
):
    """Certify only a full single-team window with positive observed participation.

    A roster listing/status alone cannot establish a missed game or stint. This
    intentionally excludes gaps/trades/late entries and reports the selection.
    """
    observations = [
        r
        for r in evidence["roster_observations"]
        if r["player_id"] == player and r["game_type"] == "REG" and r["week"] <= week
    ]
    teams = {r["team"] for r in observations}
    reasons = []
    if len(teams) != 1:
        reasons.append("no_single_team_in_window")
    if not observations or any(
        r["issues"] or r["source_position_role"] != role for r in observations
    ):
        reasons.append("unresolved_or_changing_position")
    player_games = [g for g in games if g.team_id in teams] if len(teams) == 1 else []
    exposures, complete = [], True
    for game in player_games:
        row = cohorts["roster"].get((player, game.game_id, game.team_id))
        if (
            row is None
            or row["issues"]
            or row["source_position_role"] != role
            or row["observed_offensive_participation"] is not True
        ):
            reasons.append("not_positively_observed_in_every_team_game")
            continue
        count = len(cohorts["game_opportunities"][(role, player, game.game_id)])
        complete &= count == row["offensive_opportunities"]["observed"][UNITS[role][1]]
        exposures.append(GameExposure(game, True, count))
    if not player_games:
        reasons.append("no_team_games")
    if reasons:
        return {
            "policy": EXPOSURE,
            "denominator_complete": False,
            "unresolved_reasons": sorted(set(reasons)),
            "qualification_grid": None,
        }
    exposure = SeasonExposure(player, role, season, cutoff, tuple(exposures), UNITS[role][0], True)
    module = ModuleStatus(
        complete, False, False, "conditional additive on-ball contrast diagnostic"
    )
    return {
        "policy": EXPOSURE,
        "denominator_complete": True,
        "unresolved_reasons": [],
        "qualification_grid": {
            str(m): asdict(qualify(exposure, module, historical_threshold_multiplier=m))
            for m in multipliers
        },
    }
