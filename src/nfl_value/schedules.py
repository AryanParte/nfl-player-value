"""Schedule inventory and conservative, cross-file completion evidence.

Scores alone never establish final status. A terminal PBP END_GAME marker and
matching schedule scores establish that completion was observed by retrieval,
not the exact final-whistle time. This is not an independent NFL status feed.
"""

from collections import Counter
from datetime import date, datetime, timezone
import re
from zoneinfo import ZoneInfo


SCHEDULE_COLUMNS = {
    "game_id", "season", "game_type", "week", "gameday", "gametime",
    "away_team", "home_team", "away_score", "home_score",
}
EASTERN = ZoneInfo("America/New_York")
MISSING = {"", "NA"}
LEGACY_COMPLETION = "terminal-marker-schedule-v1"
CLOCK_COMPLETION = "clock-marker-schedule-v2"
CLOCK_COLUMNS = {"qtr", "quarter_seconds_remaining"}


def _integer(value: str, name: str, minimum: int = 0) -> int:
    if not re.fullmatch(r"\d+", value) or int(value) < minimum:
        raise ValueError(f"invalid {name}: {value!r}")
    return int(value)


def audit_schedule_rows(rows, *, season: int) -> dict:
    """Archive all seasons; normalize only the explicitly requested season."""
    count = 0
    seen = set()
    games = {}
    for row in rows:
        count += 1
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"ragged schedule row {count}")
        game_id = row["game_id"]
        if game_id in seen:
            raise ValueError("duplicate schedule game ID")
        seen.add(game_id)
        if _integer(row["season"], "season") != season:
            continue
        week = _integer(row["week"], "week", 1)
        teams = (row["away_team"], row["home_team"])
        if any(not re.fullmatch(r"[A-Z]{2,3}", t) for t in teams) or teams[0] == teams[1]:
            raise ValueError("invalid schedule teams")
        if game_id != f"{season}_{week:02d}_{teams[0]}_{teams[1]}":
            raise ValueError("schedule game ID disagrees with season/week/teams")
        kind = row["game_type"]
        if kind not in {"REG", "WC", "DIV", "CON", "SB"}:
            raise ValueError("unsupported schedule game type")
        if kind == "REG" and week > (18 if season >= 2021 else 17):
            raise ValueError("regular-season week exceeds season length")
        day = date.fromisoformat(row["gameday"])
        if day.year not in {season, season + 1}:
            raise ValueError("game date outside season years")
        kickoff = None
        if row["gametime"] not in MISSING:
            if not re.fullmatch(r"\d{2}:\d{2}", row["gametime"]):
                raise ValueError("invalid schedule gametime")
            kickoff = datetime.fromisoformat(f"{day}T{row['gametime']}").replace(tzinfo=EASTERN).astimezone(timezone.utc).isoformat()
        scores = [None if row[f"{side}_score"] in MISSING else _integer(row[f"{side}_score"], "score") for side in ("away", "home")]
        if (scores[0] is None) != (scores[1] is None):
            raise ValueError("schedule has only one team's score")
        games[game_id] = {
            "week": week, "season_type": kind, "gameday": day.isoformat(),
            "scheduled_kickoff": kickoff, "away_team": teams[0], "home_team": teams[1],
            "away_score": scores[0], "home_score": scores[1],
        }
    if not games:
        raise ValueError("schedule has no games for requested season")
    return {
        "rows": count, "selected_rows": len(games), "other_season_rows": count - len(games),
        "games": dict(sorted(games.items())),
        "teams": sorted({g[s] for g in games.values() for s in ("away_team", "home_team")}),
        "game_types": dict(sorted(Counter(g["season_type"] for g in games.values()).items())),
        "ranking_ready": False,
        "limitations": [
            "Schedule scores are not an explicit final-status flag.",
            "Eastern scheduled kickoff is not an observed actual kickoff.",
            "The all-season archive is preserved; only the requested season is normalized.",
        ],
    }


def _event_clock(row: dict) -> tuple[int, int]:
    quarter = _integer(row["qtr"], "quarter", 1)
    seconds = _integer(row["quarter_seconds_remaining"], "quarter clock")
    if quarter > 5 or seconds > 900:
        raise ValueError("invalid regular-season event clock")
    return quarter, -seconds


def _clock_completion_issue(item: dict) -> str | None:
    if len(item["markers"]) != 1:
        return "missing_or_duplicate_end_marker"
    marker_id, marker = item["markers"][0]
    try:
        end = _event_clock(marker)
        if end[0] < 4 or (end[0] == 4 and end[1] != 0):
            return "invalid_end_marker_clock"
        for play, row in item["rows"]:
            # COMMENT is descriptive metadata, not a timed football event.
            # It can lack a clock; no other event is excused for missing time.
            if row["play_type_nfl"] == "COMMENT":
                continue
            current = _event_clock(row)
            if current > end:
                return "event_after_end_marker_clock"
            if play > marker_id and current == end:
                return "ambiguous_event_at_end_marker_clock"
    except (ValueError, KeyError):
        return "missing_or_invalid_event_clock"
    return None


def reconcile_game_coverage(schedule_games: dict, pbp_rows, *, cutoff: datetime, observed_at: datetime,
                            policy_version: str = LEGACY_COMPLETION) -> dict:
    """Report every due game, including missing/incomplete games, without dropout.

    The caller must replay both receipts and set observed_at to their latest
    retrieval. Never use this observation to claim a historical publication was
    available before then. Future/TBD games and postseason are not MVP games.

    The default preserves legacy callers. New report builders explicitly select
    CLOCK_COMPLETION. Numeric IDs identify plays; they need not order events.
    """
    if policy_version not in {LEGACY_COMPLETION, CLOCK_COMPLETION}:
        raise ValueError("unsupported completion policy")
    for value in (cutoff, observed_at):
        if value.utcoffset() is None:
            raise ValueError("cutoff and observation time must be timezone-aware")
    if observed_at > cutoff:
        raise ValueError("source observations are later than cutoff")
    if not schedule_games:
        raise ValueError("schedule inventory must not be empty")
    evidence = {}
    for row in pbp_rows:
        if row["season_type"] != "REG":
            continue
        game_id = row["game_id"]
        if game_id not in schedule_games or schedule_games[game_id]["season_type"] != "REG":
            raise ValueError("regular-season PBP references an unexpected schedule game")
        item = evidence.setdefault(game_id, {"last_play": -1, "markers": [], "rows": []})
        play = _integer(row["play_id"], "play ID")
        item["last_play"] = max(item["last_play"], play)
        if policy_version == CLOCK_COMPLETION:
            item["rows"].append((play, {key: row.get(key, "") for key in CLOCK_COLUMNS | {"play_type_nfl"}}))
        if row["play_type_nfl"] == "END_GAME":
            item["markers"].append((play, row))
    matched, unresolved, future, excluded = [], [], [], []
    for game_id, game in sorted(schedule_games.items()):
        if game["season_type"] != "REG":
            excluded.append(game_id)
            continue
        kickoff = datetime.fromisoformat(game["scheduled_kickoff"]) if game["scheduled_kickoff"] else None
        if kickoff is None:
            if date.fromisoformat(game["gameday"]) <= cutoff.astimezone(EASTERN).date() or game_id in evidence:
                unresolved.append({"game_id": game_id, "reason": "missing_kickoff"})
            else:
                future.append(game_id)
            continue
        if kickoff >= cutoff:
            if game_id in evidence:
                raise ValueError("PBP exists for a game not started by cutoff")
            future.append(game_id)
            continue
        item = evidence.get(game_id)
        reason = None
        if not item:
            reason = "missing_pbp"
        elif policy_version == CLOCK_COMPLETION and (clock_issue := _clock_completion_issue(item)):
            reason = clock_issue
        elif policy_version == LEGACY_COMPLETION and (len(item["markers"]) != 1 or item["markers"][0][0] != item["last_play"]):
            reason = "missing_or_nonterminal_end_marker"
        elif game["home_score"] is None:
            reason = "missing_schedule_scores"
        else:
            marker = item["markers"][0][1]
            for side in ("home", "away"):
                if marker[f"{side}_team"] != game[f"{side}_team"]:
                    raise ValueError("PBP final-marker teams disagree with schedule")
                score = marker[f"total_{side}_score"]
                if score in MISSING or _integer(score, "final PBP score") != game[f"{side}_score"]:
                    reason = "score_disagreement"
        if reason:
            unresolved.append({"game_id": game_id, "reason": reason})
        elif kickoff >= observed_at:
            raise ValueError("completion evidence predates scheduled kickoff")
        else:
            matched.append({"game_id": game_id, **game, "completion_observed_by": observed_at.isoformat()})
    return {
        "policy_version": policy_version,
        "coverage_complete": bool(matched) and not unresolved,
        "matched_games": matched, "unresolved_games": unresolved,
        "not_due_game_ids": future, "excluded_postseason_game_ids": excluded,
        "completion_time_kind": "observed_complete_by_retrieval_not_final_whistle",
    }
