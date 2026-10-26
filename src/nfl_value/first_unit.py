"""Pregame chart membership, not participation, talent, or contribution scores."""

from collections import defaultdict
from datetime import timedelta

from nfl_value.benchmarks import CompletedTeamGame, FirstUnitAssignment, validate_player_id, validate_role
from nfl_value.source_audit import aware_time, integer


POLICY_VERSION = "espn-formation-slots-2025-v1"
DEFAULT_MAX_AGE = timedelta(hours=72)  # Provisional freshness policy, not a talent threshold.
OFFENSE_ROLES = ("QB", "RB", "WR", "TE", "OT", "OG", "C")
DEFENSE_ROLES = ("IDL", "EDGE", "LB", "CB", "S")
SPECIAL_ROLES = ("K", "P", "LS", "KR", "PR")
ALL_ROLES = OFFENSE_ROLES + DEFENSE_ROLES + SPECIAL_ROLES

# Slot -> (source position, first-unit source rank, model role). WR rank is
# shared across the three formation slots: ranks 1/2/3, NOT rank 1 in each slot.
LAYOUTS = {
    21: {
        1: ("WR", 1, "WR"), 2: ("WR", 2, "WR"), 3: ("LT", 1, "OT"),
        4: ("LG", 1, "OG"), 5: ("C", 1, "C"), 6: ("RG", 1, "OG"),
        7: ("RT", 1, "OT"), 8: ("WR", 3, "WR"), 9: ("QB", 1, "QB"),
        10: ("TE", 1, "TE"), 11: ("RB", 1, "RB"), 12: ("FB", 1, None),
    },
    16: {
        1: ("LDE", 1, "EDGE"), 2: ("LDT", 1, "IDL"), 3: ("RDT", 1, "IDL"),
        4: ("RDE", 1, "EDGE"), 5: ("WLB", 1, "LB"), 6: ("MLB", 1, "LB"),
        7: ("SLB", 1, "LB"), 8: ("LCB", 1, "CB"), 9: ("SS", 1, "S"),
        10: ("FS", 1, "S"), 11: ("RCB", 1, "CB"), 12: ("NB", 1, "CB"),
    },
    15: {
        1: ("LDE", 1, "IDL"), 2: ("NT", 1, "IDL"), 3: ("RDE", 1, "IDL"),
        4: ("WLB", 1, "EDGE"), 5: ("LILB", 1, "LB"), 6: ("RILB", 1, "LB"),
        7: ("SLB", 1, "EDGE"), 8: ("LCB", 1, "CB"), 9: ("SS", 1, "S"),
        10: ("FS", 1, "S"), 11: ("RCB", 1, "CB"), 12: ("NB", 1, "CB"),
    },
    18: {
        1: ("PK", 1, "K"), 2: ("P", 1, "P"), 3: ("H", 1, None),
        4: ("PR", 1, "PR"), 5: ("KR", 1, "KR"), 6: ("LS", 1, "LS"),
    },
}
GROUP_NAMES = {21: "3WR 1TE", 16: "Base 4-3 D", 15: "Base 3-4 D", 18: "Special Teams"}


def select_first_units(rows, team_games: list[CompletedTeamGame], *, requested_roles=ALL_ROLES, max_age=DEFAULT_MAX_AGE) -> dict:
    """Select one latest team snapshot per game, before inspecting its quality.

    Never fill a missing starter with an older snapshot or a lower-ranked player.
    Keep complete cells for diagnosis, but require_role_assignments refuses a
    partial positional population. Trade/stint exposure is a separate contract.
    """
    if not isinstance(max_age, timedelta) or max_age <= timedelta(0):
        raise ValueError("max_age must be a positive timedelta")
    roles = tuple(requested_roles)
    if not roles or len(set(roles)) != len(roles):
        raise ValueError("requested roles must be nonempty and unique")
    for role in roles:
        validate_role(role)
    cells = {(g.team_id, g.game_id): g for g in team_games}
    if not cells or len(cells) != len(team_games):
        raise ValueError("expected team-game cells must be nonempty and unique")
    if len({g.game_id.split('_')[0] for g in team_games}) != 1:
        raise ValueError("first-unit window must contain one season")
    by_team = defaultdict(list)
    for key, game in cells.items():
        by_team[game.team_id].append(key)
    selected = {}
    times = {}
    for row in rows:
        if row["team"] not in by_team:
            continue
        if row["dt"] not in times:
            times[row["dt"]] = aware_time(row["dt"])
        timestamp = times[row["dt"]]
        for key in by_team[row["team"]]:
            if timestamp >= cells[key].kickoff:
                continue
            if key not in selected or timestamp > selected[key][0]:
                selected[key] = (timestamp, [])
            if timestamp == selected[key][0]:
                selected[key][1].append(row)
    assignments, issues, selections = [], [], []

    def issue(key, role, reason, slot=None):
        issues.append({"team_id": key[0], "game_id": key[1], "role": role, "reason": reason, "slot": slot})

    for key, game in sorted(cells.items()):
        if key not in selected:
            for role in roles:
                issue(key, role, "no_pregame_snapshot")
            continue
        timestamp, snapshot = selected[key]
        selections.append({"team_id": key[0], "game_id": key[1], "snapshot_at": timestamp.isoformat(), "age_seconds": (game.kickoff - timestamp).total_seconds()})
        if game.kickoff - timestamp > max_age:
            for role in roles:
                issue(key, role, "stale_snapshot")
            continue
        groups = defaultdict(list)
        for row in snapshot:
            groups[integer(row["pos_grp_id"], "formation", 1)].append(row)
        if set(groups) - LAYOUTS.keys():
            for role in roles:
                issue(key, role, "unreviewed_formation")
            continue
        defense_groups = set(groups) & {15, 16}
        for role in roles:
            if role in OFFENSE_ROLES:
                group = 21
            elif role in SPECIAL_ROLES:
                group = 18
            elif len(defense_groups) != 1:
                issue(key, role, "missing_or_ambiguous_defensive_formation")
                continue
            else:
                group = next(iter(defense_groups))
            group_rows = groups.get(group, [])
            layout = LAYOUTS[group]
            if not group_rows:
                issue(key, role, "missing_formation")
                continue
            if any(r["pos_grp"] != GROUP_NAMES[group] or integer(r["pos_slot"], "slot", 1) not in layout for r in group_rows):
                issue(key, role, "unreviewed_formation_layout")
                continue
            members = []
            for slot, (position, rank, slot_role) in layout.items():
                if slot_role != role:
                    continue
                slot_rows = [r for r in group_rows if integer(r["pos_slot"], "slot", 1) == slot]
                if any(r["pos_abb"] != position for r in slot_rows):
                    issue(key, role, "slot_position_disagreement", slot)
                    continue
                starters = [r for r in slot_rows if integer(r["pos_rank"], "rank", 1) == rank]
                if len(starters) != 1:
                    issue(key, role, "missing_or_ambiguous_first_unit_slot", slot)
                    continue
                starter = starters[0]
                try:
                    validate_player_id(starter["gsis_id"])
                    integer(starter["espn_id"], "ESPN ID", 1)
                except ValueError:
                    issue(key, role, "unresolved_player_identity", slot)
                    continue
                members.append({
                    "player_id": starter["gsis_id"], "espn_id": starter["espn_id"],
                    "role": role, "team_id": key[0], "game_id": key[1],
                    "snapshot_at": timestamp.isoformat(), "formation": group,
                    "slots": [slot], "source_ranks": [rank],
                })
            unique = {}
            for member in members:
                player = member["player_id"]
                if player in unique:
                    # Nickel is an additional chart role, not a twelfth defender
                    # on every play. A CB also listed there gets no extra weight.
                    if role == "CB" and member["slots"] == [12] and unique[player]["espn_id"] == member["espn_id"]:
                        unique[player]["slots"] += member["slots"]
                        unique[player]["source_ranks"] += member["source_ranks"]
                    else:
                        issue(key, role, "same_player_in_multiple_slots")
                else:
                    unique[player] = member
            if not any(i["team_id"] == key[0] and i["game_id"] == key[1] and i["role"] == role for i in issues):
                assignments.extend(unique.values())

    # Do not infer identity joins from names, nor allow one ESPN identity to
    # change GSIS identity across snapshots (or the reverse) without review.
    espn_to_gsis, gsis_to_espn, by_player_game = defaultdict(set), defaultdict(set), defaultdict(list)
    for a in assignments:
        espn_to_gsis[a["espn_id"]].add(a["player_id"])
        gsis_to_espn[a["player_id"]].add(a["espn_id"])
        by_player_game[(a["player_id"], a["game_id"])].append(a)
    for a in assignments:
        if len(espn_to_gsis[a["espn_id"]]) != 1 or len(gsis_to_espn[a["player_id"]]) != 1:
            issue((a["team_id"], a["game_id"]), a["role"], "conflicting_player_identity")
        peers = by_player_game[(a["player_id"], a["game_id"])]
        if len({p["team_id"] for p in peers}) > 1:
            issue((a["team_id"], a["game_id"]), a["role"], "player_on_both_teams")
        for unit in (OFFENSE_ROLES, DEFENSE_ROLES):
            if a["role"] in unit and len({p["role"] for p in peers if p["role"] in unit}) > 1:
                issue((a["team_id"], a["game_id"]), a["role"], "ambiguous_unit_role")
    return {
        "policy_version": POLICY_VERSION, "max_age_seconds": max_age.total_seconds(),
        "requested_roles": sorted(roles), "expected_team_game_cells": len(cells),
        "selections": selections,
        "assignments": sorted(assignments, key=lambda a: (a["game_id"], a["team_id"], a["role"], a["player_id"])),
        "issues": sorted(issues, key=lambda i: (i["game_id"], i["team_id"], i["role"], i["reason"], i["slot"] or 0)),
        "role_coverage_complete": {role: not any(i["role"] == role for i in issues) for role in sorted(roles)},
        "ranking_ready": False,
    }


def require_role_assignments(report: dict, role: str) -> tuple[FirstUnitAssignment, ...]:
    """Reject partial cells before the benchmark can silently renormalize them."""
    if not report["role_coverage_complete"].get(role, False):
        raise ValueError(f"incomplete first-unit coverage for {role}")
    return tuple(FirstUnitAssignment(a["player_id"], role, a["team_id"], a["game_id"], aware_time(a["snapshot_at"])) for a in report["assignments"] if a["role"] == role)
