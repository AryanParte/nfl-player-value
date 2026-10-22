"""Build/replay paired defensive research inputs from local immutable receipts."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.defense_inputs import build_defense_inputs, replay_defense_inputs, save_defense_inputs
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.source_audit import aware_time


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/defense-inputs"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for kind in ("schedules", "pbp", "participation"):
        build.add_argument(f"--{kind}", required=True, help="source receipt ID")
    build.add_argument("--cutoff", required=True)
    commands.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, derived = SnapshotStore(args.store), SnapshotStore(args.output_store)
        if args.command == "build":
            report, rich, degraded = build_defense_inputs(raw, schedules=args.schedules, pbp=args.pbp, participation=args.participation,
                                                        cutoff=aware_time(args.cutoff), code_revision=committed_revision())
            report_id, report = save_defense_inputs(derived, report, rich, degraded)
        else:
            report_id = args.report_id
            report = replay_defense_inputs(raw, derived, report_id)
        audit = report["join_audit"]
        print(json.dumps({"report_id": report_id, "season": report["season"], "objects": report["objects"],
                          "paired_games": audit["paired_games"], "paired_plays": audit["paired_plays"],
                          "rejection_counts": audit["rejection_counts"], "experiment_run": False, "ranking_ready": False}, sort_keys=True, indent=2))
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Defensive inputs failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
