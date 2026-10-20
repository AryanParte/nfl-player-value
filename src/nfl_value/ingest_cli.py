"""Explicit online capture and strictly offline replay entry points."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.ingestion import SnapshotStore, capture, replay
from nfl_value.sources import source_spec


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/raw/source-snapshots"))
    commands = parser.add_subparsers(dest="command", required=True)
    online = commands.add_parser("capture", help="download and audit one selected public source")
    online.add_argument("source", choices=("pbp", "rosters", "depth_charts"))
    online.add_argument("--season", type=int, required=True)
    offline = commands.add_parser("replay", help="verify a receipt using local bytes only")
    offline.add_argument("receipt_id")
    args = parser.parse_args(argv)
    try:
        store = SnapshotStore(args.store)
        if args.command == "capture":
            root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
            if Path.cwd().resolve() != root or Path(__file__).resolve() != root / "src/nfl_value/ingest_cli.py":
                raise ValueError("capture must run from the repository root with PYTHONPATH=src to identify the executing source revision")
            dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", "src", "pyproject.toml"], text=True)
            if dirty.strip():
                raise ValueError("commit source/package changes before capture so the receipt identifies reproducible code")
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            receipt_id, receipt = capture(store, source_spec(args.source, args.season), code_revision=revision)
        else:
            receipt_id = args.receipt_id
            receipt = replay(store, receipt_id)
        print(json.dumps({"receipt_id": receipt_id, "source": receipt["source"]["kind"], "season": receipt["source"]["season"], "audit": receipt["audit"]}, sort_keys=True, indent=2))
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Source snapshot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
