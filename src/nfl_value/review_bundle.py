"""Offline static review bundles, deliberately not a ranking publication gate.

Replay precedes staging. Only the selected public observations, reviewed decision
record and Vite assets enter the archive. No raw source archive is redistributed.
The command records integrity and provenance, not model admission or freshness.
"""

from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from nfl_value.admission import _unique_object, load_registry
from nfl_value.defense_explorer import _publish_bytes, replay_explorer
from nfl_value.ingestion import json_bytes, sha256


MAX_FILE = 8 * 1024 * 1024
MAX_BUNDLE = 32 * 1024 * 1024
REGISTRY_PATH = "config/admission-2026-v1.json"
POLICY_PATH = "web/src/release-policy.json"


def safe_path(root: Path, relative: str) -> Path:
    """Reject links at every path level, including an existing destination root."""
    part = PurePosixPath(relative)
    if part.is_absolute() or str(part) != relative or ".." in part.parts or "\\" in relative:
        raise ValueError("unsafe bundle path")
    target = root / relative
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise ValueError("bundle paths cannot contain symbolic links")
    return target


def read_file(root: Path, relative: str) -> bytes:
    path = safe_path(root, relative)
    with path.open("rb") as handle:
        body = handle.read(MAX_FILE + 1)
    if len(body) > MAX_FILE:
        raise ValueError("bundle file exceeds size limit")
    return body


def read_policy(root: Path) -> dict:
    policy = json.loads(read_file(root, POLICY_PATH), object_pairs_hook=_unique_object)
    if (
        not isinstance(policy, dict)
        or policy.keys() != {"schema_version", "registry_sha256", "registry_revision"}
        or type(policy["schema_version"]) is not int
        or policy["schema_version"] != 1
        or not re.fullmatch(r"[a-f0-9]{64}", str(policy["registry_sha256"]))
        or not re.fullmatch(r"[a-f0-9]{40}", str(policy["registry_revision"]))
    ):
        raise ValueError("unsupported review bundle policy")
    return policy


def review_inputs(root: Path, raw, inputs, output, report_id: str, code_revision: str):
    """Fully verify local source replay and evidence before returning staged bytes."""
    if not re.fullmatch(r"[a-f0-9]{40}", code_revision):
        raise ValueError("committed bundle revision required")
    policy = read_policy(root)
    registry_body = read_file(root, REGISTRY_PATH)
    registry = load_registry(
        root / REGISTRY_PATH, repository_root=root, expected_sha256=policy["registry_sha256"]
    )
    # Bind the bytes read above too; a changed file between reads must not escape.
    if sha256(registry_body) != registry.registry_sha256:
        raise ValueError("registry changed during preparation")
    report, payload = replay_explorer(raw, inputs, output, report_id)
    body = output.read(report["object"])
    if json_bytes(payload) != body or sha256(body) != report["object"]:
        raise ValueError("Explorer bytes disagree with replay")
    if (
        payload["data_mode"] != "observed"
        or payload["ranking_ready"] is not False
        or payload["season"] != registry.season
        or any(
            p["cavaa"] is not None or p["defensive_snaps"] is not None for p in payload["players"]
        )
    ):
        raise ValueError("review bundle requires observed, unadmitted same-season evidence")
    files = {
        f"data/{report['object']}.json": body,
        "data/latest.json": json_bytes({"schema_version": 1, "snapshot_id": report["object"]}),
        f"data/admission/{registry.registry_sha256}.json": registry_body,
    }
    metadata = {
        "schema_version": 1,
        "kind": "archived_exploratory_review",
        "ranking_ready": False,
        "code_revision": code_revision,
        "registry_sha256": registry.registry_sha256,
        "registry_revision": policy["registry_revision"],
        "decision_version": registry.decision_version,
        "decided_at": registry.decided_at,
        "explorer_report": report_id,
        "explorer_snapshot": report["object"],
        "season": payload["season"],
        "game_cutoff": payload["cutoff"],
        "coverage": payload["coverage"],
        "source_receipts": payload["provenance"]["source_receipts"],
        "npm_lock_sha256": sha256(read_file(root, "web/package-lock.json")),
    }
    return files, metadata


def stage_review(destination: Path, files: dict[str, bytes]) -> None:
    """Immutable data first, atomic local pointer last; never delete old objects."""
    for name, body in files.items():
        target = safe_path(destination, name)
        if name != "data/latest.json" and target.exists() and read_file(destination, name) != body:
            raise ValueError("existing immutable public object disagrees")
    for name, body in sorted(files.items(), key=lambda item: item[0] == "data/latest.json"):
        target = safe_path(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "data/latest.json" or not target.exists():
            _publish_bytes(target, body, replace=name == "data/latest.json")


def bundle_files(dist: Path, expected: dict[str, bytes], metadata: dict) -> dict[str, bytes]:
    """Select public output only; reject a stale build or substituted data bytes."""
    files = {name: read_file(dist, name) for name in expected}
    if files != expected:
        raise ValueError("built data differs from verified review inputs")
    files["index.html"] = read_file(dist, "index.html")
    assets = safe_path(dist, "assets")
    # Vite's current output is flat, with JS/CSS only. Any future asset family
    # requires an explicit review, not recursive inclusion of arbitrary files.
    for path in sorted(assets.iterdir()):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+\.(js|css)", path.name):
            raise ValueError("unexpected static asset")
        files[f"assets/{path.name}"] = read_file(dist, f"assets/{path.name}")
    if not any(name.endswith(".js") for name in files) or not any(
        name.endswith(".css") for name in files
    ):
        raise ValueError("compiled JavaScript and CSS required")
    files["review-manifest.json"] = json_bytes(
        {
            **metadata,
            "files": {
                name: {"sha256": sha256(body), "bytes": len(body)}
                for name, body in sorted(files.items())
            },
        }
    )
    return files


def archive_bytes(files: dict[str, bytes]) -> bytes:
    """Deterministic uncompressed ZIP: fixed metadata, order and exact bytes."""
    if sum(map(len, files.values())) > MAX_BUNDLE:
        raise ValueError("review bundle exceeds size limit")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, body in sorted(files.items()):
            if (
                str(PurePosixPath(name)) != name
                or name.startswith("/")
                or ".." in PurePosixPath(name).parts
                or "\\" in name
            ):
                raise ValueError("unsafe archive path")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body)
    return buffer.getvalue()


def save_archive(destination: Path, body: bytes) -> Path:
    target = safe_path(destination, f"{sha256(body)}.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        with target.open("rb") as handle:
            existing = handle.read(MAX_BUNDLE + 65537)
        if existing != body:
            raise ValueError("existing immutable review archive disagrees")
    else:
        _publish_bytes(target, body, replace=False)
    return target
