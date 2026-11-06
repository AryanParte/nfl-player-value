"""Package/restore an Explorer launch candidate; no upload or publication."""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import sha256
from nfl_value.launch_bundle import build_launch, restore_launch
from nfl_value.recovery_io import read_bounded, save_recovery


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("candidate_id")
    pack.add_argument("review_archive", type=Path)
    pack.add_argument("--sha256", required=True, help="Trusted site review archive SHA-256")
    pack.add_argument("--store-root", type=Path, default=Path("."))
    pack.add_argument("--destination", type=Path, default=Path("artifacts/launch"))
    restore = commands.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--sha256", required=True, help="Independent trusted launch SHA-256")
    restore.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        revision = committed_revision()
        if args.command == "pack":
            # No caller-provided historical override: recheck this packaging attempt.
            checked_at = datetime.now(timezone.utc)
            body, manifest = build_launch(
                Path.cwd(),
                args.store_root,
                read_bounded(args.review_archive),
                args.sha256,
                args.candidate_id,
                checked_at,
                revision,
            )
            if committed_revision() != revision:
                raise ValueError("code changed during launch packaging")
            path = save_recovery(args.destination, body)
            result = {
                "archive": str(path),
                "archive_sha256": sha256(body),
                "archive_bytes": len(body),
                "manifest": manifest,
                "published": False,
                "uploaded": False,
            }
        else:
            result = restore_launch(
                Path.cwd(), read_bounded(args.archive), args.sha256, args.destination
            )
            result["validator_code_revision"] = revision
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        zipfile.BadZipFile,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Explorer launch package failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
