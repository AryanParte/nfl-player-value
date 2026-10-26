"""Audit archived CSV bytes. These reports do not certify ranking eligibility."""

from collections import Counter
import csv
from datetime import datetime
import gzip
import hashlib
import io
from math import isfinite
import re

from nfl_value.sources import SourceSpec
from nfl_value.schedules import SCHEDULE_COLUMNS, audit_schedule_rows
from nfl_value.participation import PARTICIPATION_COLUMNS, audit_participation_rows
from nfl_value.weekly_rosters import WEEKLY_ROSTER_COLUMNS, audit_weekly_rosters


MAX_DECODED_BYTES = 512 * 1024 * 1024
MISSING = {"", "NA"}
REQUIRED = {
    "pbp": {"game_id", "play_id", "season", "season_type", "week", "play_type_nfl", "epa"},
    "rosters": {"season", "team", "gsis_id", "espn_id", "position", "week"},
    "depth_charts": {"dt", "team", "gsis_id", "espn_id", "pos_grp_id", "pos_slot", "pos_rank", "pos_abb"},
    "schedules": SCHEDULE_COLUMNS,
    "participation": PARTICIPATION_COLUMNS,
    "weekly_rosters": WEEKLY_ROSTER_COLUMNS,
}


def aware_time(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return result


def integer(value: str, name: str, minimum: int = 0) -> int:
    if not re.fullmatch(r"\d+", value) or int(value) < minimum:
        raise ValueError(f"invalid {name}: {value!r}")
    return int(value)


def audit_csv(raw: bytes, spec: SourceSpec, *, observed_at: str) -> dict:
    """Keep missing IDs visible and reject malformed/duplicate source keys.

    END_GAME is source evidence, not an exact completion timestamp. An
    independent schedule/final-status reconciliation is required before use.
    Roster rows are current season roster records, not historical team stints.
    Depth timestamps reflect source loading, not independently verified events.
    """
    observed = aware_time(observed_at)
    if spec.filename.endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as handle:
            decoded = handle.read(MAX_DECODED_BYTES + 1)
    else:
        decoded = raw
    if len(decoded) > MAX_DECODED_BYTES:
        raise ValueError("decoded source exceeds size limit")
    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(decoded), encoding="utf-8-sig", newline=""), strict=True)
    columns = reader.fieldnames
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("missing or duplicate CSV column names")
    missing = REQUIRED[spec.kind] - set(columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if spec.kind == "weekly_rosters":
        return {
            "schema_version": spec.schema_version, "columns": columns,
            "decoded_bytes": len(decoded), "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            **audit_weekly_rosters(reader, season=spec.season),
        }
    if spec.kind == "participation":
        return {
            "schema_version": spec.schema_version, "columns": columns,
            "decoded_bytes": len(decoded), "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            **audit_participation_rows(reader, season=spec.season),
        }
    if spec.kind == "schedules":
        return {
            "schema_version": spec.schema_version,
            "columns": columns,
            "decoded_bytes": len(decoded),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            **audit_schedule_rows(reader, season=spec.season),
        }
    count = 0
    seen = set()
    missing_fields = Counter()
    invalid_fields = Counter()
    teams = set()
    roles = Counter()
    weeks = Counter()
    games = {}
    timestamps = set()
    for row in reader:
        count += 1
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"ragged CSV row {count}")
        if spec.kind in {"pbp", "rosters"}:
            if integer(row["season"], "season") != spec.season:
                raise ValueError("source includes a different season")
            week = integer(row["week"], "week", 1)
            weeks[str(week)] += 1
        if spec.kind == "pbp":
            game_id = row["game_id"]
            if not re.fullmatch(r"\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}", game_id):
                raise ValueError("invalid nflverse game ID")
            parts = game_id.split("_")
            if int(parts[0]) != spec.season or int(parts[1]) != week or parts[2] == parts[3]:
                raise ValueError("game ID disagrees with season/week/teams")
            if row["season_type"] not in {"REG", "POST"}:
                raise ValueError("unrecognized PBP season type")
            if row["season_type"] == "REG" and week > 18:
                raise ValueError("invalid regular-season week")
            key = (game_id, integer(row["play_id"], "play_id"))
            game = games.setdefault(game_id, {"week": week, "season_type": row["season_type"], "rows": 0, "end_game_markers": 0})
            if game["season_type"] != row["season_type"]:
                raise ValueError("inconsistent game season type")
            game["rows"] += 1
            game["end_game_markers"] += row["play_type_nfl"] == "END_GAME"
            missing_fields["epa"] += row["epa"] in MISSING
            if row["epa"] not in MISSING and not isfinite(float(row["epa"])):
                raise ValueError("nonfinite EPA value")
        else:
            if not re.fullmatch(r"[A-Z]{2,3}", row["team"]):
                raise ValueError("invalid team abbreviation")
            teams.add(row["team"])
            missing_fields["gsis_id"] += row["gsis_id"] in MISSING
            if row["gsis_id"] not in MISSING and not re.fullmatch(r"00-\d{7}", row["gsis_id"]):
                # The upstream depth archive includes legacy-format IDs. Keep
                # raw evidence, but never turn these into valid modeling IDs.
                invalid_fields["noncanonical_gsis_id"] += 1
            if spec.kind == "rosters":
                roles[row["position"]] += 1
                # ESPN identity preserves distinct unmatched GSIS rows.
                key = (row["season"], row["team"], row["gsis_id"], row["espn_id"], str(week))
            else:
                timestamp = aware_time(row["dt"])
                if timestamp > observed:
                    raise ValueError("depth snapshot is later than retrieval")
                timestamps.add(row["dt"])
                roles[row["pos_abb"]] += 1
                slot = integer(row["pos_slot"], "pos_slot", 1)
                rank = integer(row["pos_rank"], "pos_rank", 1)
                key = (timestamp.isoformat(), row["team"], row["pos_grp_id"], slot, rank, row["espn_id"])
        if key in seen:
            raise ValueError(f"duplicate source key at row {count}")
        seen.add(key)
    if not count:
        raise ValueError("empty source data")
    ordered_times = sorted(timestamps, key=aware_time)
    return {
        "schema_version": spec.schema_version,
        "columns": columns,
        "rows": count,
        "decoded_bytes": len(decoded),
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "missing_fields": dict(sorted(missing_fields.items())),
        "invalid_fields": dict(sorted(invalid_fields.items())),
        "weeks": dict(sorted(weeks.items(), key=lambda item: int(item[0]))),
        "teams": sorted(teams),
        "roles": dict(sorted(roles.items())),
        "games": dict(sorted(games.items())),
        "depth_timestamps": {"count": len(timestamps), "first": ordered_times[0] if ordered_times else None, "last": ordered_times[-1] if ordered_times else None},
        "ranking_ready": False,
        "limitations": [
            "Source audit only: no independent completed-game coverage reconciliation.",
            "Roster history, pregame first-unit selection and identifier resolution are not implemented here.",
            "Stored bytes may contain later corrections; retrieval is not a historical as-of reconstruction.",
        ],
    }
