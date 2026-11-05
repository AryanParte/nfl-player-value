"""Pack or restore a reviewed Explorer recovery archive; never upload or publish."""

import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import fetch_public, sha256
from nfl_value.recovery import build_recovery, restore_recovery
from nfl_value.recovery_io import MAX_ARCHIVE_BYTES, digest, read_bounded, save_recovery


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("review_archive", type=Path)
    pack.add_argument(
        "--sha256", required=True, help="Reviewed static ZIP digest, from its committed audit"
    )
    pack.add_argument("--store-root", type=Path, default=Path("."))
    pack.add_argument("--destination", type=Path, default=Path("artifacts/recovery"))
    restore = commands.add_parser("restore")
    source = restore.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--url", help="Exact canonical GitHub release asset URL")
    restore.add_argument(
        "--sha256", required=True, help="Trusted recovery ZIP digest, from its committed audit"
    )
    restore.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        revision = committed_revision()
        digest(args.sha256)
        if args.command == "pack":
            body, manifest = build_recovery(
                Path.cwd(),
                args.store_root,
                read_bounded(args.review_archive),
                args.sha256,
                revision,
            )
            path = save_recovery(args.destination, body)
            result = {
                "archive": str(path),
                "archive_sha256": sha256(body),
                "archive_bytes": len(body),
                "manifest": manifest,
                "uploaded": False,
            }
        else:
            if args.url:
                pattern = (
                    r"https://github\.com/AryanParte/nfl-player-value/releases/download/"
                    r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/" + args.sha256 + r"\.zip"
                )
                if not re.fullmatch(pattern, args.url):
                    raise ValueError(
                        "only the canonical repository's exact hash-named release asset is allowed"
                    )
                body = fetch_public(args.url, MAX_ARCHIVE_BYTES).body
            else:
                body = read_bounded(args.archive)
            result = restore_recovery(Path.cwd(), body, args.sha256, args.destination)
            result["validator_code_revision"] = revision
        print(json.dumps(result, sort_keys=True, indent=2))
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        zipfile.BadZipFile,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Explorer recovery failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
