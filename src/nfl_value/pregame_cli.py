"""Build or replay immutable pregame input reports without network access."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.pregame_inputs import build_inputs, replay_inputs
from nfl_value.source_audit import aware_time


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/pregame-inputs"))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    for kind in ("schedules", "pbp", "depth-charts"):
        build.add_argument(f"--{kind}", required=True, help="immutable source receipt ID")
    build.add_argument("--cutoff", required=True, help="timezone-aware publication evidence cutoff")
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, derived = SnapshotStore(args.store), SnapshotStore(args.output_store)
        if args.command == "build":
            report = build_inputs(raw, schedules=args.schedules, pbp=args.pbp, depth_charts=args.depth_charts, cutoff=aware_time(args.cutoff), code_revision=committed_revision())
            report_id = derived.put(json_bytes(report), manifest=True)
        else:
            report_id = args.report_id
            report = replay_inputs(raw, derived, report_id)
        selection = report["first_unit"]
        print(json.dumps({
            "report_id": report_id, "season": report["season"], "cutoff": report["cutoff"],
            "game_coverage_complete": report["game_coverage"]["coverage_complete"],
            "matched_games": len(report["game_coverage"]["matched_games"]),
            "unresolved_games": report["game_coverage"]["unresolved_games"],
            "role_coverage_complete": selection["role_coverage_complete"] if selection else {},
            "first_unit_issues": len(selection["issues"]) if selection else None,
            "historical_availability": report["historical_availability"], "ranking_ready": False,
        }, indent=2, sort_keys=True))
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Pregame inputs failed: {exc}", file=sys.stderr)
        return 1
    # Success means a reproducible diagnostic report, never permission to rank.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
