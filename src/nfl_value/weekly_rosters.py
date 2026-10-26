"""Literal weekly roster observations, not transactions or game participation."""

from collections import Counter
import re


WEEKLY_ROSTER_COLUMNS = {
    "season",
    "week",
    "game_type",
    "team",
    "gsis_id",
    "espn_id",
    "position",
    "depth_chart_position",
    "status",
    "status_description_abbr",
}
MISSING = {"", "NA"}
# Primary NFL position labels with a direct, reviewed interpretation. Broad OL,
# DL, DB and LB labels do not establish formation-specific model roles. The
# upstream dictionary explicitly warns that depth_chart_position is unreliable.
DIRECT_ROLES = frozenset({"QB", "RB", "WR", "TE", "K", "P", "LS"})


def normalize_weekly_rosters(rows, *, season: int) -> list[dict]:
    """Retain missing identities/opaque statuses, reject structural corruption.

    No ESPN/name fallback, team aliasing, role imputation or status-based dropping.
    Distinct rows sharing a GSIS/week remain for the downstream ambiguity audit.
    """
    seen, observations = set(), []
    for row in rows:
        if not WEEKLY_ROSTER_COLUMNS <= row.keys():
            raise ValueError("missing weekly roster columns")
        if None in row or any(v is None for v in row.values()):
            raise ValueError("ragged weekly roster row")
        if not re.fullmatch(r"\d{4}", row["season"]) or int(row["season"]) != season:
            raise ValueError("weekly roster includes a different or invalid season")
        if not re.fullmatch(r"[1-9]\d?", row["week"]):
            raise ValueError("invalid weekly roster week")
        week = int(row["week"])
        if row["game_type"] not in {"REG", "WC", "DIV", "CON", "SB"}:
            raise ValueError("unreviewed weekly roster game type")
        last_regular_week = 18 if season >= 2021 else 17
        if row["game_type"] == "REG" and week > last_regular_week:
            raise ValueError("invalid regular-season roster week")
        playoff_offset = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}.get(row["game_type"])
        if playoff_offset and week != last_regular_week + playoff_offset:
            raise ValueError("postseason roster week disagrees with game type")
        if not re.fullmatch(r"[A-Z]{2,3}", row["team"]):
            raise ValueError("invalid weekly roster team")
        key = tuple(row[k] for k in ("season", "week", "game_type", "team", "gsis_id", "espn_id"))
        if key in seen:
            raise ValueError("duplicate weekly roster source key")
        seen.add(key)
        issues = []
        gsis = row["gsis_id"]
        if gsis in MISSING:
            issues.append("missing_gsis_id")
        elif not re.fullmatch(r"00-\d{7}", gsis):
            issues.append("noncanonical_gsis_id")
        role = row["position"] if row["position"] in DIRECT_ROLES else None
        if role is None:
            issues.append("primary_position_unreviewed")
        if row["status"] in MISSING:
            issues.append("missing_roster_status")
        observations.append(
            {
                "season": season,
                "week": week,
                "game_type": row["game_type"],
                "team": row["team"],
                "player_id": gsis if re.fullmatch(r"00-\d{7}", gsis) else None,
                "source_gsis_id": gsis,
                "espn_id": row["espn_id"],
                "primary_position": row["position"],
                "depth_chart_position": row["depth_chart_position"],
                "source_position_role": role,
                "status": row["status"],
                "status_description_abbr": row["status_description_abbr"],
                "issues": sorted(issues),
            }
        )
    if not observations:
        raise ValueError("empty weekly roster source")
    return sorted(
        observations,
        key=lambda r: (r["game_type"], r["week"], r["team"], r["source_gsis_id"], r["espn_id"]),
    )


def audit_weekly_rosters(rows, *, season: int) -> dict:
    observations = normalize_weekly_rosters(rows, season=season)
    return {
        "rows": len(observations),
        "weeks": dict(
            sorted(Counter(str(r["week"]) for r in observations).items(), key=lambda x: int(x[0]))
        ),
        "game_types": dict(sorted(Counter(r["game_type"] for r in observations).items())),
        "teams": sorted({r["team"] for r in observations}),
        "positions": dict(sorted(Counter(r["primary_position"] for r in observations).items())),
        "statuses": dict(sorted(Counter(r["status"] for r in observations).items())),
        "issue_counts": dict(sorted(Counter(i for r in observations for i in r["issues"]).items())),
        "ranking_ready": False,
        "limitations": [
            "Weekly rows include inactive/reserve/released players; listing does not prove roster tenure or participation.",
            "Week labels are not transaction timestamps or evidence of historical pregame availability.",
            "Broad position labels and unreviewed statuses remain literal; depth_chart_position is not authoritative.",
        ],
    }
