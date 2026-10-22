"""FTN historical identity/lineup checks, independently implemented.

These are rostered player IDs on a play, not assignments, player quality, or
proof of a defender's position. Preserve bad rows in raw data and count issues.
"""

from collections import Counter
import re


PARTICIPATION_COLUMNS = {
    "nflverse_game_id", "play_id", "possession_team", "offense_players",
    "defense_players", "players_on_play", "n_offense", "n_defense",
}
GSIS = re.compile(r"00-\d{7}")


def participation_key(row: dict, season: int) -> tuple[str, int]:
    game = row["nflverse_game_id"]
    if not re.fullmatch(rf"{season}_\d{{2}}_[A-Z]{{2,3}}_[A-Z]{{2,3}}", game):
        raise ValueError("invalid participation game ID or season")
    _, week, away, home = game.split("_")
    if not 1 <= int(week) <= 22 or away == home:
        raise ValueError("invalid participation game week/teams")
    if row["possession_team"] not in {away, home}:
        raise ValueError("participation possession is not a game team")
    if not re.fullmatch(r"\d+", row["play_id"]):
        raise ValueError("invalid participation play ID")
    return game, int(row["play_id"])


def inspect_lineup(row: dict) -> tuple[dict[str, list[str]], list[str]]:
    issues = []
    lineups = {}
    for field in ("offense_players", "defense_players", "players_on_play"):
        ids = row[field].split(";")
        lineups[field] = sorted(ids)
        if any(not GSIS.fullmatch(player) for player in ids):
            issues.append(f"{field}:noncanonical_or_missing_id")
        if len(ids) != len(set(ids)):
            issues.append(f"{field}:duplicate_id")
        expected = 22 if field == "players_on_play" else 11
        if len(ids) != expected:
            issues.append(f"{field}:not_{expected}_players")
    for side in ("offense", "defense"):
        if row[f"n_{side}"] != "11":
            issues.append(f"n_{side}:not_11")
    offense, defense = (set(lineups[f"{side}_players"]) for side in ("offense", "defense"))
    if offense & defense:
        issues.append("offense_defense_overlap")
    if offense | defense != set(lineups["players_on_play"]):
        issues.append("players_on_play:union_mismatch")
    return lineups, sorted(issues)


def audit_participation_rows(rows, *, season: int) -> dict:
    count = 0
    seen = set()
    games = {}
    reasons = Counter()
    for row in rows:
        count += 1
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"ragged participation row {count}")
        key = participation_key(row, season)
        if key in seen:
            raise ValueError("duplicate participation game/play key")
        seen.add(key)
        _, issues = inspect_lineup(row)
        reasons.update(issues)
        game = games.setdefault(key[0], {"rows": 0, "valid_lineup_rows": 0})
        game["rows"] += 1
        game["valid_lineup_rows"] += not issues
    if not count:
        raise ValueError("empty participation source")
    return {
        "rows": count, "valid_lineup_rows": sum(g["valid_lineup_rows"] for g in games.values()),
        "lineup_issue_counts": dict(sorted(reasons.items())), "games": dict(sorted(games.items())),
        "ranking_ready": False,
        "limitations": [
            "Historical FTN participation, released after the postseason; not live 2026 availability.",
            "Lineup validation checks IDs and counts, not correctness of football assignments or roles.",
            "Special-teams and postseason rows remain archived; research cohort selection requires PBP and schedules.",
            "No individual contribution is allocated by this audit.",
        ],
    }
