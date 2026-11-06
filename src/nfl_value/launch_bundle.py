"""Portable Explorer candidate + site + exact replay dependencies, never publish.

Freshness at packaging is frozen evidence, not a transferable publish permission.
Old recovery-v1 archives and review manifests retain their existing contracts.
"""

import os
from pathlib import Path
import re
import shutil
import tempfile

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.readiness import assess_sources
from nfl_value.recovery import (
    ATTRIBUTION,
    STORES,
    RecordingStore,
    _notice,
    _revision,
    verified_closure,
)
from nfl_value.recovery_io import (
    check_index,
    decode_object,
    digest,
    encode_archive,
    file_index,
    read_archive,
)
from nfl_value.refresh_candidate import replay_candidate
from nfl_value.review_bundle import safe_path
from nfl_value.source_audit import aware_time


LAUNCH_STORES = (*STORES, "data/derived/explorer-candidates")
MANIFEST = "launch-manifest.json"
CHECK = "checks/source-readiness.json"
POLICY = "explorer-launch-closure-2026-v1"


def verified_launch_files(
    repository_root, store_root, review_body, review_hash, candidate_id, checked_at, code_revision
):
    """Read only verified dependencies; exclude unrelated files and old archives."""
    stores = [RecordingStore(store_root / name, name) for name in LAUNCH_STORES]
    candidate = replay_candidate(*stores, digest(candidate_id))
    raw, inputs, explorers, candidates = stores
    original = decode_object(candidates.read(candidate["readiness_report"], manifest=True))
    if checked_at < aware_time(candidate["cutoff"]):
        raise ValueError("packaging check cannot precede candidate cutoff")
    readiness = assess_sources(
        raw, original["source_receipts"], cutoff=checked_at, code_revision=_revision(code_revision)
    )
    if not readiness["ready_for_explorer_build"]:
        raise ValueError("sources not ready at packaging check: " + str(readiness["blockers"]))
    view, metadata = verified_closure(repository_root, store_root, review_body, review_hash)
    if (
        metadata["explorer_report"] != candidate["explorer_report"]
        or metadata["explorer_snapshot"] != candidate["explorer_snapshot"]
        or metadata["game_cutoff"] != candidate["cutoff"]
        or metadata["coverage"] != candidate["coverage"]
    ):
        raise ValueError("site review does not match the exact candidate")
    payload = decode_object(explorers.read(candidate["explorer_snapshot"]))
    if {g["game_id"] for g in readiness["game_coverage"]["matched_games"]} != {
        g["game_id"] for g in payload["team_games"]
    }:
        raise ValueError("packaging check changes candidate game coverage")
    source_sets = [payload["provenance"]["source_receipts"]]
    if candidate["previous_explorer"] is not None:
        previous = decode_object(explorers.read(candidate["previous_explorer"], manifest=True))
        prior_data = decode_object(explorers.read(previous["object"]))
        source_sets.append(prior_data["provenance"]["source_receipts"])
    notices = [b"# Launch package source sets\n\n"]
    for i, ids in enumerate(source_sets):
        notices.append(
            f"Source set {i + 1}: {'candidate' if i == 0 else 'prior comparison'}\n\n".encode()
        )
        notices.append(_notice(raw, ids))
    files = {name: body for store in stores for name, body in store.files.items()}
    for name, body in view.items():
        if name != ATTRIBUTION:
            if name in files and files[name] != body:
                raise ValueError("dependency bytes changed during launch packaging")
            files[name] = body
    files[ATTRIBUTION] = b"\n".join(notices)
    files[CHECK] = json_bytes(readiness)
    return files, candidate


def build_launch(
    repository_root, store_root, review_body, review_hash, candidate_id, checked_at, code_revision
):
    files, candidate = verified_launch_files(
        repository_root,
        store_root,
        review_body,
        review_hash,
        candidate_id,
        checked_at,
        code_revision,
    )
    manifest = {
        "schema_version": 1,
        "kind": "explorer_launch_package",
        "policy": POLICY,
        "packager_code_revision": _revision(code_revision),
        "candidate_id": digest(candidate_id),
        "checked_at": checked_at.isoformat(),
        "review_archive_sha256": digest(review_hash),
        "explorer_report": candidate["explorer_report"],
        "game_cutoff": candidate["cutoff"],
        "ranking_ready": False,
        "published": False,
        "files": file_index(files),
    }
    return encode_archive({**files, MANIFEST: json_bytes(manifest)}), manifest


def _launch(body, expected_sha256):
    files = read_archive(body, expected_sha256)
    manifest = decode_object(files.pop(MANIFEST))
    if (
        manifest.keys()
        != {
            "schema_version",
            "kind",
            "policy",
            "packager_code_revision",
            "candidate_id",
            "checked_at",
            "review_archive_sha256",
            "explorer_report",
            "game_cutoff",
            "ranking_ready",
            "published",
            "files",
        }
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["kind"] != "explorer_launch_package"
        or manifest["policy"] != POLICY
        or manifest["ranking_ready"] is not False
        or manifest["published"] is not False
    ):
        raise ValueError("unsupported launch manifest")
    _revision(manifest["packager_code_revision"])
    digest(manifest["candidate_id"])
    digest(manifest["explorer_report"])
    aware_time(manifest["checked_at"])
    aware_time(manifest["game_cutoff"])
    review_name = f"review/{digest(manifest['review_archive_sha256'])}.zip"
    for name in files:
        allowed = name in {ATTRIBUTION, CHECK, review_name} or any(
            re.fullmatch(
                re.escape(store) + r"/(objects/[a-f0-9]{64}|manifests/[a-f0-9]{64}\.json)", name
            )
            for store in LAUNCH_STORES
        )
        if not allowed:
            raise ValueError("unreviewed launch member")
    if not {ATTRIBUTION, CHECK, review_name} <= files.keys():
        raise ValueError("launch requires site, attribution and readiness check")
    check_index(files, manifest["files"])
    return files, manifest


def restore_launch(repository_root, body, expected_sha256, destination):
    """Replay solely from a private staging directory before exposing the restore."""
    files, manifest = _launch(body, expected_sha256)
    destination = Path(destination)
    safe_path(destination.parent, destination.name)
    if destination.exists():
        raise ValueError("restore destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".launch-restore-", dir=destination.parent))
    try:
        for name, content in files.items():
            target = safe_path(staging, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        review_hash = manifest["review_archive_sha256"]
        rebuilt, _ = build_launch(
            repository_root,
            staging,
            files[f"review/{review_hash}.zip"],
            review_hash,
            manifest["candidate_id"],
            aware_time(manifest["checked_at"]),
            manifest["packager_code_revision"],
        )
        if rebuilt != body:
            raise ValueError("launch package differs from exact semantic replay")
        with (staging / MANIFEST).open("xb") as handle:
            handle.write(json_bytes(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists() or destination.is_symlink():
            raise ValueError("restore destination appeared during replay")
        os.rename(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "archive_sha256": sha256(body),
        "destination": str(destination),
        "files_restored": len(files) + 1,
        "candidate_id": manifest["candidate_id"],
        "review_archive_sha256": manifest["review_archive_sha256"],
        "game_cutoff": manifest["game_cutoff"],
        "checked_at": manifest["checked_at"],
        "verified_at_recorded_time_only": True,
        "ranking_ready": False,
        "published": False,
        "semantic_replay_verified": True,
    }
