"""Provisional participation rules, separate from fitting and benchmark cohorts.

Rules are product defaults awaiting bounded historical tests at 0.75x/1x/1.25x.
Passing participation alone never validates an individual-value attribution.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from nfl_value.benchmarks import (
    CompletedTeamGame,
    _aware,
    _count,
    validate_player_id,
    validate_role,
)


@dataclass(frozen=True)
class GameExposure:
    game: CompletedTeamGame
    participated: bool
    opportunities: int
    team_unit_snaps: int | None = None

    def __post_init__(self) -> None:
        if type(self.participated) is not bool:
            raise ValueError("participated must be boolean")
        _count(self.opportunities, "opportunities")
        if not self.participated and self.opportunities:
            raise ValueError("missed games must have zero player opportunities")
        if self.team_unit_snaps is not None:
            _count(self.team_unit_snaps, "team_unit_snaps")
            if self.opportunities > self.team_unit_snaps:
                raise ValueError("unique player opportunities cannot exceed team unit snaps")


@dataclass(frozen=True)
class SeasonExposure:
    """Validated supplied exposure; schedule/roster reconciliation stays upstream.

    Include every completed team game during the player's nonoverlapping roster
    stints, including injuries and other missed games; exclude byes. A trade does
    not reset totals or append either team's entire season. The ingestion layer
    must reconcile membership to timestamped stints before declaring completeness.
    QB opportunities are unique dropbacks plus designed non-kneel rushes; count
    scrambles once. RB opportunities are unique carry-or-target plays. WR/TE
    targets qualify the partial on-ball module, not full receiving contributions.
    """

    player_id: str
    role: str
    season: int
    cutoff: datetime
    games: tuple[GameExposure, ...]
    opportunity_unit: str
    denominator_complete: bool

    def __post_init__(self) -> None:
        validate_player_id(self.player_id)
        validate_role(self.role)
        _count(self.season, "season")
        _aware(self.cutoff, "cutoff")
        if type(self.denominator_complete) is not bool:
            raise ValueError("denominator_complete must be boolean")
        if not isinstance(self.games, tuple):
            raise ValueError("games must be an immutable tuple")
        if len({g.game.game_id for g in self.games}) != len(self.games):
            raise ValueError("duplicate game in player season exposure, including traded stints")
        for exposure in self.games:
            if int(exposure.game.game_id.split("_")[0]) != self.season:
                raise ValueError("game belongs to a different season")
            if exposure.game.completed_at > self.cutoff:
                raise ValueError("game was not completed by cutoff")
        ordered = sorted(self.games, key=lambda g: g.game.kickoff)
        if any(a.game.completed_at > b.game.kickoff for a, b in zip(ordered, ordered[1:])):
            raise ValueError("player season cannot contain overlapping team games")


@dataclass(frozen=True)
class ModuleStatus:
    """Evidence gates are independently recorded, not inferred from sample size."""

    source_coverage_complete: bool
    attribution_validated: bool
    comparable_to_main: bool
    scope_label: str

    def __post_init__(self) -> None:
        for value in (self.source_coverage_complete, self.attribution_validated, self.comparable_to_main):
            if type(value) is not bool:
                raise ValueError("module evidence gates must be boolean")
        if not isinstance(self.scope_label, str) or not self.scope_label.strip():
            raise ValueError("an explicit module scope label is required")


@dataclass(frozen=True)
class Qualification:
    participation_qualified: bool
    explorer_qualified: bool
    main_qualified: bool
    games_played: int
    completed_team_games: int
    opportunities: int
    minimum_opportunities: int | None
    team_snap_denominator: int | None
    scope_label: str
    main_exclusion_reasons: tuple[str, ...]
    policy_version: str = "provisional-2026-v1"


# (opportunity unit, absolute floor, opportunities per completed team game,
#  percentage of the corresponding team unit's snaps)
_RULES = {
    "QB": ("modeled_qb_plays", 50, 14, 0),
    "RB": ("carry_or_target_plays", 25, 6, 0),
    "WR": ("targets", 15, 3, 0),
    "TE": ("targets", 10, 2, 0),
    "OT": ("offensive_snaps", 100, 0, 35),
    "OG": ("offensive_snaps", 100, 0, 35),
    "C": ("offensive_snaps", 100, 0, 35),
    "IDL": ("defensive_snaps", 75, 0, 20),
    "EDGE": ("defensive_snaps", 75, 0, 20),
    "LB": ("defensive_snaps", 100, 0, 35),
    "CB": ("defensive_snaps", 100, 0, 35),
    "S": ("defensive_snaps", 100, 0, 35),
}


def qualify(
    exposure: SeasonExposure,
    module: ModuleStatus,
    *,
    historical_threshold_multiplier: Literal[0.75, 1.0, 1.25] = 1.0,
) -> Qualification:
    """Evaluate participation and publication gates without score-based filtering.

    Three games participated is always required. The multiplier is restricted
    to the predeclared historical sensitivity grid, scales opportunity thresholds
    only, and must not be tuned to favorite players. Zero/negative value and wide
    uncertainty are not exclusion rules. Unsupported specialist rules fail closed.
    """
    multipliers = {0.75: (3, 4), 1.0: (1, 1), 1.25: (5, 4)}
    if isinstance(historical_threshold_multiplier, bool) or historical_threshold_multiplier not in multipliers:
        raise ValueError("use only the bounded historical threshold grid: 0.75, 1.0, 1.25")
    games_played = sum(g.participated for g in exposure.games)
    completed_games = len(exposure.games)
    opportunities = sum(g.opportunities for g in exposure.games)
    reasons: list[str] = []
    minimum: int | None = None
    team_snaps: int | None = None
    if not exposure.denominator_complete:
        reasons.append("season_exposure_incomplete")
    if games_played < 3:
        reasons.append("fewer_than_three_games")
    rule = _RULES.get(exposure.role)
    if rule is None:
        reasons.append("position_rule_not_validated")
    else:
        unit, floor, per_game, percentage = rule
        if exposure.opportunity_unit != unit:
            raise ValueError(f"{exposure.role} requires opportunity_unit={unit!r}")
        # Keep percentages as exact hundredths until AFTER historical scaling.
        # Rounding a fractional threshold twice can reject an extra opportunity.
        raw_hundredths = max(floor, per_game * completed_games) * 100
        if percentage:
            if any(g.team_unit_snaps is None for g in exposure.games):
                reasons.append("team_snap_denominator_missing")
            else:
                team_snaps = sum(g.team_unit_snaps for g in exposure.games)  # type: ignore[arg-type]
                raw_hundredths = max(raw_hundredths, percentage * team_snaps)
        numerator, denominator = multipliers[historical_threshold_multiplier]
        scaled_denominator = 100 * denominator
        minimum = (raw_hundredths * numerator + scaled_denominator - 1) // scaled_denominator
        if opportunities < minimum:
            reasons.append("below_opportunity_threshold")
    participation_qualified = not reasons
    if not module.source_coverage_complete:
        reasons.append("source_coverage_incomplete")
    explorer_qualified = participation_qualified and module.source_coverage_complete
    if not module.attribution_validated:
        reasons.append("attribution_not_validated")
    if not module.comparable_to_main:
        reasons.append("not_comparable_to_main")
    scope_label = module.scope_label
    if exposure.role in {"WR", "TE"} and rule is not None:
        scope_label = f"{scope_label}; targeted receiving only (partial position coverage)"
    return Qualification(
        participation_qualified=participation_qualified,
        explorer_qualified=explorer_qualified,
        main_qualified=not reasons,
        games_played=games_played,
        completed_team_games=completed_games,
        opportunities=opportunities,
        minimum_opportunities=minimum,
        team_snap_denominator=team_snaps,
        scope_label=scope_label,
        main_exclusion_reasons=tuple(reasons),
        policy_version=(
            "provisional-2026-v1" if historical_threshold_multiplier == 1.0
            else f"provisional-2026-v1-historical-{historical_threshold_multiplier}x"
        ),
    )
