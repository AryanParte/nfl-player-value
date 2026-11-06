"""Prepare immutable Explorer candidates after source gates; never publish."""

from nfl_value.defense_explorer import build_explorer, replay_explorer, save_explorer
from nfl_value.ingestion import json_bytes
from nfl_value.offensive_inputs import build_offensive_inputs, save_offensive_inputs
from nfl_value.readiness import assess_sources, replay_readiness, save_readiness
from nfl_value.recovery_io import decode_object
from nfl_value.source_audit import aware_time


def _manifest(
    raw,
    inputs,
    explorers,
    *,
    readiness_id,
    readiness,
    offensive_id,
    explorer_id,
    report,
    data,
    previous_explorer,
):
    if not readiness["ready_for_explorer_build"] or readiness["ranking_ready"] is not False:
        raise ValueError("blocked readiness cannot authorize an Explorer candidate")
    offensive = decode_object(inputs.read(offensive_id, manifest=True))
    if json_bytes(offensive["game_coverage"]) != json_bytes(readiness["game_coverage"]):
        raise ValueError("candidate game coverage differs from readiness")
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or data["kind"] != "defense_explorer"
        or data["data_mode"] != "observed"
        or data["ranking_ready"] is not False
        or data["season"] != 2026
        or data["cutoff"] != readiness["cutoff"]
        or data["code_revision"] != readiness["code_revision"]
        or data["provenance"]["source_receipts"] != readiness["source_receipts"]
        or data["provenance"]["offensive_report"] != offensive_id
        or any(p["cavaa"] is not None or p["defensive_snaps"] is not None for p in data["players"])
    ):
        raise ValueError("candidate provenance or unadmitted-value contract failed")
    expected = {g["game_id"] for g in readiness["game_coverage"]["matched_games"]}
    actual = {g["game_id"] for g in data["team_games"]}
    if actual != expected or data["coverage"]["completed_games"] != len(expected):
        raise ValueError("candidate does not cover the exact completed-game set")
    comparison = None
    if previous_explorer is not None:
        _, previous = replay_explorer(raw, inputs, explorers, previous_explorer)
        if previous["season"] != data["season"] or aware_time(previous["cutoff"]) > aware_time(
            data["cutoff"]
        ):
            raise ValueError("previous Explorer season/cutoff cannot regress")
        if not {g["game_id"] for g in previous["team_games"]} <= actual:
            raise ValueError(
                "candidate drops previously included games; explicit correction review required"
            )
        previous_rows = {(g["game_id"], g["team"]): g for g in previous["team_games"]}
        current_rows = {(g["game_id"], g["team"]): g for g in data["team_games"]}
        comparison = {
            "added_game_ids": sorted(actual - {key[0] for key in previous_rows}),
            "changed_existing_team_games": [
                {"game_id": gid, "team": team}
                for (gid, team), row in sorted(previous_rows.items())
                if json_bytes(current_rows[(gid, team)]) != json_bytes(row)
            ],
            "scope": "Team context rows only; changes can reflect source corrections or code. Player/name changes are not enumerated.",
        }
    return {
        "schema_version": 1,
        "kind": "explorer_refresh_candidate",
        "season": 2026,
        "code_revision": readiness["code_revision"],
        "cutoff": readiness["cutoff"],
        "readiness_report": readiness_id,
        "readiness_policy_sha256": readiness["policy_sha256"],
        "offensive_report": offensive_id,
        "explorer_report": explorer_id,
        "explorer_snapshot": report["object"],
        "previous_explorer": previous_explorer,
        "previous_comparison": comparison,
        "coverage": data["coverage"],
        "ranking_ready": False,
        "published": False,
    }


def prepare_candidate(
    raw,
    inputs,
    explorers,
    candidates,
    receipt_ids,
    *,
    cutoff,
    code_revision,
    previous_explorer=None,
):
    readiness = assess_sources(raw, receipt_ids, cutoff=cutoff, code_revision=code_revision)
    rid = save_readiness(candidates, readiness)
    if not readiness["ready_for_explorer_build"]:
        return rid, readiness, None
    ids = readiness["source_receipts"]
    offensive, ledger = build_offensive_inputs(
        raw, schedules=ids["schedules"], pbp=ids["pbp"], cutoff=cutoff, code_revision=code_revision
    )
    offensive_id, _ = save_offensive_inputs(inputs, offensive, ledger)
    data = build_explorer(
        raw,
        inputs,
        offensive_report=offensive_id,
        depth_charts=ids["depth_charts"],
        rosters=ids["rosters"],
        code_revision=code_revision,
    )
    explorer_id, report = save_explorer(explorers, data)
    manifest = _manifest(
        raw,
        inputs,
        explorers,
        readiness_id=rid,
        readiness=readiness,
        offensive_id=offensive_id,
        explorer_id=explorer_id,
        report=report,
        data=data,
        previous_explorer=previous_explorer,
    )
    return rid, readiness, candidates.put(json_bytes(manifest), manifest=True)


def replay_candidate(raw, inputs, explorers, candidates, candidate_id):
    body = candidates.read(candidate_id, manifest=True)
    saved = decode_object(body)
    readiness = replay_readiness(raw, candidates, saved["readiness_report"])
    report, data = replay_explorer(raw, inputs, explorers, saved["explorer_report"])
    reproduced = _manifest(
        raw,
        inputs,
        explorers,
        readiness_id=saved["readiness_report"],
        readiness=readiness,
        offensive_id=saved["offensive_report"],
        explorer_id=saved["explorer_report"],
        report=report,
        data=data,
        previous_explorer=saved["previous_explorer"],
    )
    if body != json_bytes(reproduced):
        raise ValueError("candidate replay differs; use the recorded code/policy")
    return reproduced
