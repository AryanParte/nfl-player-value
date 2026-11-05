"""Retain and restore the exact public input closure of an archived Explorer.

Version 1 covers the 2026 CC-BY-4.0 Explorer chain, not every research experiment.
Restoration verifies the saved compiler assets; it does not rerun the compiler.
"""

import os
from pathlib import Path
import re
import shutil
import tempfile

from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.recovery_io import (
    check_index,
    decode_object,
    digest,
    encode_archive,
    file_index,
    read_archive,
)
from nfl_value.review_bundle import review_inputs, safe_path


STORES = (
    "data/raw/source-snapshots",
    "data/derived/offensive-inputs",
    "data/derived/defense-explorer",
)
MANIFEST = "recovery-manifest.json"
ATTRIBUTION = "ATTRIBUTION.md"
POLICY = "explorer-2026-cc-by-closure-v1"


class RecordingStore(SnapshotStore):
    """Record only successful reads during the existing full semantic replay."""

    def __init__(self, root, label):
        super().__init__(root)
        self.label = label
        self.files = {}

    def read(self, identifier, *, manifest=False):
        path = self._path(identifier, manifest=manifest)
        safe_path(self.root, str(path.relative_to(self.root)))
        body = super().read(identifier, manifest=manifest)
        name = f"{self.label}/{path.relative_to(self.root).as_posix()}"
        if name in self.files and self.files[name] != body:
            raise ValueError("input changed during dependency recording")
        self.files[name] = body
        return body

    def put(self, body, *, manifest=False):
        raise ValueError("recovery replay must be read-only")


def _revision(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise ValueError("full committed revision required")
    return value


def _review(body, expected_sha256):
    files = read_archive(body, expected_sha256)
    manifest = decode_object(files["review-manifest.json"])
    check_index({k: v for k, v in files.items() if k != "review-manifest.json"}, manifest["files"])
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["kind"] != "archived_exploratory_review"
        or manifest["ranking_ready"] is not False
    ):
        raise ValueError("unsupported review archive")
    _revision(manifest["code_revision"])
    digest(manifest["explorer_report"])
    return files, manifest


def _notice(raw, receipt_ids):
    if set(receipt_ids) != {"pbp", "schedules", "depth_charts", "rosters"}:
        raise ValueError("unsupported recovery source family")
    text = [
        "# Archived NFL Explorer inputs and attribution\n",
        "Raw source bytes are retained unchanged. Derived ledgers and the Explorer",
        "select completed regular-season pass/run observations and transform them",
        "under the recorded code and policies. They are not official player-value rankings.",
        "Data in this archive retain CC-BY-4.0 terms, separately from the repository's",
        "MIT software license. No source endorses this project. Preserve these credits",
        "and the archived license text when redistributing.\n",
    ]
    for kind, rid in sorted(receipt_ids.items()):
        receipt = decode_object(raw.read(rid, manifest=True))
        source = receipt["source"]
        if (
            source["kind"] != kind
            or source["season"] != 2026
            or source["license_id"] != "CC-BY-4.0"
        ):
            raise ValueError("recovery v1 only admits the reviewed 2026 CC-BY-4.0 inputs")
        text.extend(
            [
                f"## {kind}\n",
                source["attribution"],
                f"Source: {receipt['asset']['browser_download_url']}",
                f"License: {source['license_id']} — {source['license_url']}",
                f"Retrieved: {receipt['retrieval']['data']}; upstream update: {receipt['asset']['updated_at']}",
                f"Receipt SHA-256: {rid}",
                f"Raw SHA-256: {receipt['objects']['raw']}",
                f"Archived license: {raw.label}/objects/{receipt['objects']['license']}\n",
            ]
        )
    return ("\n".join(text) + "\n").encode()


def verified_closure(repository_root, store_root, review_body, review_sha256):
    """Recoverable means exact semantic replay, not just successful ZIP reading."""
    view, reviewed = _review(review_body, review_sha256)
    stores = [RecordingStore(store_root / relative, relative) for relative in STORES]
    expected, metadata = review_inputs(
        repository_root, *stores, reviewed["explorer_report"], reviewed["code_revision"]
    )
    if any(view.get(name) != body for name, body in expected.items()):
        raise ValueError("review public objects disagree with restored replay")
    if json_bytes({key: reviewed.get(key) for key in metadata}) != json_bytes(metadata):
        raise ValueError("review provenance, coverage or cutoff disagrees with replay")
    if reviewed.keys() != metadata.keys() | {"toolchain", "files"}:
        raise ValueError("unexpected review manifest fields")
    if (
        not isinstance(reviewed["toolchain"], dict)
        or reviewed["toolchain"].keys() != {"node", "npm", "python"}
        or any(not isinstance(v, str) or not v for v in reviewed["toolchain"].values())
    ):
        raise ValueError("recorded review toolchain required")
    allowed = set(expected) | {"review-manifest.json", "index.html"}
    assets = {k for k in view if re.fullmatch(r"assets/[a-zA-Z0-9_-]+\.(js|css)", k)}
    if (
        set(view) != allowed | assets
        or not any(k.endswith(".js") for k in assets)
        or not any(k.endswith(".css") for k in assets)
    ):
        raise ValueError("unexpected or incomplete public review files")
    notice = _notice(stores[0], metadata["source_receipts"])
    files = {name: body for store in stores for name, body in store.files.items()}
    files[ATTRIBUTION] = notice
    files[f"review/{digest(review_sha256)}.zip"] = review_body
    return files, metadata


def build_recovery(repository_root, store_root, review_body, review_sha256, code_revision):
    files, metadata = verified_closure(repository_root, store_root, review_body, review_sha256)
    manifest = {
        "schema_version": 1,
        "kind": "explorer_recovery",
        "policy": POLICY,
        "packager_code_revision": _revision(code_revision),
        "review_archive_sha256": digest(review_sha256),
        "explorer_report": metadata["explorer_report"],
        "game_cutoff": metadata["game_cutoff"],
        "ranking_ready": False,
        "files": file_index(files),
    }
    body = encode_archive({**files, MANIFEST: json_bytes(manifest)})
    return body, manifest


def _recovery(body, expected_sha256):
    files = read_archive(body, expected_sha256)
    manifest_body = files.pop(MANIFEST)
    manifest = decode_object(manifest_body)
    if (
        manifest.keys()
        != {
            "schema_version",
            "kind",
            "policy",
            "packager_code_revision",
            "review_archive_sha256",
            "explorer_report",
            "game_cutoff",
            "ranking_ready",
            "files",
        }
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["kind"] != "explorer_recovery"
        or manifest["policy"] != POLICY
        or manifest["ranking_ready"] is not False
    ):
        raise ValueError("unsupported recovery manifest")
    _revision(manifest["packager_code_revision"])
    digest(manifest["explorer_report"])
    review_name = f"review/{digest(manifest['review_archive_sha256'])}.zip"
    for name in files:
        allowed = name in {ATTRIBUTION, review_name} or any(
            re.fullmatch(
                re.escape(store) + r"/(objects/[a-f0-9]{64}|manifests/[a-f0-9]{64}\.json)", name
            )
            for store in STORES
        )
        if not allowed:
            raise ValueError("unreviewed recovery member")
    if review_name not in files or ATTRIBUTION not in files:
        raise ValueError("review archive and attribution required")
    check_index(files, manifest["files"])
    return files, manifest, manifest_body


def restore_recovery(repository_root, body, expected_sha256, destination):
    """Restore under the repository lease into a new directory, never over old work."""
    files, manifest, manifest_body = _recovery(body, expected_sha256)
    destination = Path(destination)
    safe_path(destination.parent, destination.name)
    if destination.exists():
        raise ValueError("restore destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".recovery-", dir=destination.parent))
    try:
        for name, content in files.items():
            target = safe_path(staging, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        review_hash = manifest["review_archive_sha256"]
        expected, metadata = verified_closure(
            repository_root, staging, files[f"review/{review_hash}.zip"], review_hash
        )
        if expected != files:
            raise ValueError("recovery members differ from the exact replay dependency closure")
        if (
            metadata["explorer_report"] != manifest["explorer_report"]
            or metadata["game_cutoff"] != manifest["game_cutoff"]
        ):
            raise ValueError("recovery manifest disagrees with replay")
        # Keep the verified provenance alongside the restored bytes, without
        # treating the outer manifest as a replay dependency of itself.
        with (staging / MANIFEST).open("xb") as handle:
            handle.write(manifest_body)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists() or destination.is_symlink():
            raise ValueError("restore destination appeared during replay")
        # Repository lease serializes participating writers; this is not a
        # distributed production-store publication or concurrency mechanism.
        os.rename(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "archive_sha256": sha256(body),
        "destination": str(destination),
        "files_restored": len(files) + 1,
        "review_archive_sha256": manifest["review_archive_sha256"],
        "explorer_report": metadata["explorer_report"],
        "game_cutoff": metadata["game_cutoff"],
        "ranking_ready": False,
        "semantic_replay_verified": True,
    }
