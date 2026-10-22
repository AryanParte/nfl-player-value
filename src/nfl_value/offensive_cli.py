"""Build/replay an offensive opportunity ledger using local source receipts."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.offensive_inputs import build_offensive_inputs, replay_offensive_inputs, save_offensive_inputs
from nfl_value.source_audit import aware_time


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/offensive-inputs"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for kind in ("schedules", "pbp"):
        build.add_argument(f"--{kind}", required=True)
    build.add_argument("--cutoff", required=True)
    commands.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, derived = SnapshotStore(args.store), SnapshotStore(args.output_store)
        if args.command == "build":
            report, ledger = build_offensive_inputs(raw, schedules=args.schedules, pbp=args.pbp, cutoff=aware_time(args.cutoff), code_revision=committed_revision())
            report_id, report = save_offensive_inputs(derived, report, ledger)
        else:
            report_id = args.report_id
            report = replay_offensive_inputs(raw, derived, report_id)
        print(json.dumps({"report_id": report_id, "season": report["season"], "objects": report["objects"],
                          "game_coverage_complete": report["game_coverage"]["coverage_complete"],
                          "opportunity_audit": report["opportunity_audit"], "ranking_ready": False}, indent=2, sort_keys=True))
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Offensive inputs failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
