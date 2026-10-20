"""Positional comparison contracts; these functions do not fit player effects.

Each prediction must evaluate a candidate in the SAME focal-player context and
on the SAME expected-points scale. Average these predictions, not covariates or
unadjusted player statistics. Call separately for each role and focal context.

The caller supplies an authoritative completed-game inventory and the latest
available pregame first-unit assignments. Missing cells fail closed. Membership
comes from depth charts, never outcome-based selection or leaderboard eligibility.
"""

from dataclasses import dataclass
from datetime import datetime
from math import fsum, isfinite
from numbers import Real
import re
from typing import Literal, Sequence


ROLE_CODES = frozenset(
    {"QB", "RB", "WR", "TE", "OT", "OG", "C", "IDL", "EDGE", "LB", "CB", "S", "K", "P", "LS", "KR", "PR"}
)


def validate_player_id(player_id: str) -> None:
    """Require a canonical nflverse GSIS player identifier, never a display name."""
    if not isinstance(player_id, str) or not re.fullmatch(r"00-\d{7}", player_id):
        raise ValueError("player_id must be a canonical GSIS ID: 00-#######")


def validate_role(role: str) -> None:
    if role not in ROLE_CODES:
        raise ValueError(f"unsupported or ambiguous role: {role!r}")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _team(team_id: str) -> None:
    if not isinstance(team_id, str) or not re.fullmatch(r"[A-Z]{2,3}", team_id):
        raise ValueError("team_id must be a canonical uppercase team abbreviation")


def _count(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


@dataclass(frozen=True)
class CompletedTeamGame:
    """One completed regular-season team game from the authoritative schedule.

    The season-specific schedule remains authoritative for whether an otherwise
    valid week exists (for example, older seasons with only 17 regular weeks).
    completed_at is a conservative known-complete-by bound when an exact finish
    time is unavailable. The ingestion report must identify that time semantics;
    never backdate the bound to an invented final-whistle time.
    """

    game_id: str
    team_id: str
    kickoff: datetime
    completed_at: datetime
    season_type: Literal["REG"]

    def __post_init__(self) -> None:
        if not isinstance(self.game_id, str) or not re.fullmatch(
            r"\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}", self.game_id
        ):
            raise ValueError("game_id must use the nflverse season_week_away_home form")
        if self.season_type != "REG":
            raise ValueError("the season MVP window accepts regular-season (REG) games only")
        week = int(self.game_id.split("_")[1])
        if not 1 <= week <= 18:
            raise ValueError("regular-season game week must be between 1 and 18")
        _team(self.team_id)
        teams = self.game_id.split("_")[2:]
        if self.team_id not in teams or teams[0] == teams[1]:
            raise ValueError("team_id must be one of the game's two distinct teams")
        _aware(self.kickoff, "kickoff")
        _aware(self.completed_at, "completed_at")
        if self.completed_at <= self.kickoff:
            raise ValueError("completed_at must be after kickoff")


@dataclass(frozen=True)
class PlayerPrediction:
    """One candidate's model expectation in the focal context.

    opportunities is observed season exposure in the declared role. Positive
    exposure defines the equal-player sensitivity population and supplies weights
    for the opportunity-weighted sensitivity. Zero is valid for first-unit
    predictions. Qualification is absent: low-volume participants remain included.
    """

    player_id: str
    role: str
    expected_points: float
    opportunities: int

    def __post_init__(self) -> None:
        validate_player_id(self.player_id)
        validate_role(self.role)
        if isinstance(self.expected_points, bool) or not isinstance(self.expected_points, Real) or not isfinite(self.expected_points):
            raise ValueError("expected_points must be finite")
        _count(self.opportunities, "opportunities")


@dataclass(frozen=True)
class FirstUnitAssignment:
    player_id: str
    role: str
    team_id: str
    game_id: str
    snapshot_at: datetime

    def __post_init__(self) -> None:
        validate_player_id(self.player_id)
        validate_role(self.role)
        _team(self.team_id)
        _aware(self.snapshot_at, "snapshot_at")


@dataclass(frozen=True)
class BenchmarkEstimate:
    name: str
    role: str
    expected_points: float
    player_weights: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class BenchmarkSet:
    first_unit: BenchmarkEstimate
    equal_player: BenchmarkEstimate
    opportunity_weighted: BenchmarkEstimate


def calculate_benchmarks(
    *,
    role: str,
    predictions: Sequence[PlayerPrediction],
    assignments: Sequence[FirstUnitAssignment],
    team_games: Sequence[CompletedTeamGame],
    expected_team_ids: Sequence[str],
    cutoff: datetime,
) -> BenchmarkSet:
    """Calculate the approved primary benchmark and both required sensitivities.

    First-unit weighting: each team gets equal total weight; divide its weight
    equally among its completed games, then among first-unit players in the role
    for each game. Byes create no game. All supplied games must finish by cutoff.

    The schedule inventory must include every completed team game in the chosen
    season-to-date window. We check its declared team coverage and every supplied
    team-game role cell; detecting a game omitted from the authoritative source
    requires the caller's ingestion completeness checks. Assignments must be the
    latest actually available pregame records, not retrospective corrections.
    """
    validate_role(role)
    _aware(cutoff, "cutoff")
    if not predictions:
        raise ValueError("the positional prediction population must not be empty")
    by_player = {p.player_id: p for p in predictions}
    if len(by_player) != len(predictions):
        raise ValueError("duplicate player predictions")
    if any(p.role != role for p in predictions) or any(a.role != role for a in assignments):
        raise ValueError("one role per benchmark invocation is required")
    if not expected_team_ids or len(set(expected_team_ids)) != len(expected_team_ids):
        raise ValueError("expected_team_ids must be nonempty and unique")
    for team_id in expected_team_ids:
        _team(team_id)
    games = {(g.team_id, g.game_id): g for g in team_games}
    if not games or len(games) != len(team_games):
        raise ValueError("team-game inventory must be nonempty and unique")
    if {g.team_id for g in team_games} != set(expected_team_ids):
        raise ValueError("missing or unexpected teams in completed-game inventory")
    if len({g.game_id.split("_")[0] for g in team_games}) != 1:
        raise ValueError("a benchmark window must contain one season")
    if any(g.completed_at > cutoff for g in team_games):
        raise ValueError("game was not completed by cutoff")
    cells: dict[tuple[str, str], set[str]] = {key: set() for key in games}
    player_game_teams: dict[tuple[str, str], str] = {}
    for assignment in assignments:
        key = (assignment.team_id, assignment.game_id)
        if key not in games:
            raise ValueError("assignment references an unexpected team-game")
        if assignment.snapshot_at >= games[key].kickoff:
            raise ValueError("first-unit snapshot must be strictly before kickoff")
        if assignment.player_id not in by_player:
            raise ValueError("first-unit player has no model prediction")
        if assignment.player_id in cells[key]:
            raise ValueError("duplicate first-unit assignment")
        player_game = (assignment.player_id, assignment.game_id)
        if player_game in player_game_teams:
            raise ValueError("a player cannot represent two teams in the same game")
        player_game_teams[player_game] = assignment.team_id
        cells[key].add(assignment.player_id)
    if any(not players for players in cells.values()):
        raise ValueError("missing first-unit coverage for a required team-game/role cell")

    games_per_team = {
        team_id: sum(g.team_id == team_id for g in team_games)
        for team_id in expected_team_ids
    }
    weight_parts: dict[str, list[float]] = {}
    for (team_id, _), players in cells.items():
        weight = 1 / (len(expected_team_ids) * games_per_team[team_id] * len(players))
        for player_id in players:
            weight_parts.setdefault(player_id, []).append(weight)
    first_weights = {player_id: fsum(parts) for player_id, parts in weight_parts.items()}
    total_opportunities = sum(p.opportunities for p in predictions)
    if total_opportunities == 0:
        raise ValueError("opportunity-weighted benchmark needs positive total exposure")
    # Never-observed roster entries must not change the equal-player average.
    # A first-unit player with zero role opportunities can still enter primary.
    observed_players = [p.player_id for p in predictions if p.opportunities > 0]
    equal_weights = {player_id: 1 / len(observed_players) for player_id in observed_players}
    opportunity_weights = {
        p.player_id: p.opportunities / total_opportunities for p in predictions
    }

    def estimate(name: str, weights: dict[str, float]) -> BenchmarkEstimate:
        ordered = tuple(sorted(weights.items()))
        expected_points = fsum(by_player[player].expected_points * weight for player, weight in ordered)
        return BenchmarkEstimate(name, role, expected_points, ordered)

    return BenchmarkSet(
        estimate("first_unit", first_weights),
        estimate("equal_player", equal_weights),
        estimate("opportunity_weighted", opportunity_weights),
    )
