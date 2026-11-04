"""Build a reproducible static review archive from committed code and local inputs.

This is an archived exploratory site, not a ranking publication or source refresh.
No network capture, deployment, installation or hosted pointer update occurs.
"""

import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, sha256
from nfl_value.review_bundle import (
    REGISTRY_PATH,
    archive_bytes,
    bundle_files,
    read_file,
    read_policy,
    review_inputs,
    save_archive,
    stage_review,
)


def build_review(root, report_id, raw, inputs, output, destination):
    revision = committed_revision()
    dirty = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "web",
            "config",
            "src",
            "pyproject.toml",
        ],
        cwd=root,
        text=True,
    )
    if dirty.strip():
        raise ValueError("commit web/config/source changes before a reproducible review build")
    policy = read_policy(root)
    registry = json.loads(read_file(root, REGISTRY_PATH))
    # Evidence links must name Git bytes that really match the reviewed sources.
    for source in registry["sources"].values():
        historical = subprocess.check_output(
            ["git", "show", f"{policy['registry_revision']}:{source['path']}"], cwd=root
        )
        if sha256(historical) != source["sha256"]:
            raise ValueError("evidence link revision disagrees with reviewed bytes")
    files, metadata = review_inputs(root, raw, inputs, output, report_id, revision)
    node = subprocess.check_output(["node", "--version"], cwd=root, text=True).strip()
    if not re.fullmatch(r"v24\.\d+\.\d+", node):
        raise ValueError("review builds require the supported Node 24 toolchain")
    metadata["toolchain"] = {
        "node": node,
        "npm": subprocess.check_output(["npm", "--version"], cwd=root, text=True).strip(),
        "python": sys.version.split()[0],
    }
    subprocess.run(
        ["npm", "--prefix", "web", "ls", "--all", "--parseable"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    stage_review(root / "web/public", files)
    # Run the locked local tools; no npx, install, downloads or inferred build.
    subprocess.run(
        ["npm", "--prefix", "web", "run", "build"], cwd=root, check=True, stdout=sys.stderr
    )
    if (
        committed_revision() != revision
        or subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", "web", "config"],
            cwd=root,
            text=True,
        ).strip()
    ):
        raise ValueError("source changed during review build")
    body = archive_bytes(bundle_files(root / "web/dist", files, metadata))
    target = save_archive(destination, body)
    return {
        "archive": str(target),
        "archive_sha256": sha256(body),
        "archive_bytes": len(body),
        **metadata,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_id")
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/defense-explorer"))
    parser.add_argument("--destination", type=Path, default=Path("artifacts/review-bundles"))
    args = parser.parse_args(argv)
    try:
        result = build_review(
            Path.cwd(),
            args.report_id,
            *(SnapshotStore(p) for p in (args.raw_store, args.input_store, args.output_store)),
            args.destination,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Static review build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
