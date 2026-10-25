"""Build, replay or export a versioned observed Defense Explorer snapshot."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.defense_explorer import build_explorer, save_explorer, replay_explorer, export_explorer
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/defense-explorer"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for name in ("offensive-report", "depth-charts", "rosters"):
        build.add_argument("--"+name, required=True)
    commands.add_parser("replay").add_argument("report_id")
    export = commands.add_parser("export")
    export.add_argument("report_id")
    export.add_argument("--destination", type=Path, default=Path("web/public/data"))
    args = parser.parse_args(argv)
    try:
        raw, inputs, output = (SnapshotStore(p) for p in (args.raw_store, args.input_store, args.output_store))
        if args.command == "build":
            data = build_explorer(raw, inputs, offensive_report=args.offensive_report, depth_charts=args.depth_charts,
                                  rosters=args.rosters, code_revision=committed_revision())
            rid, report = save_explorer(output, data)
        else:
            rid = args.report_id
            report, data = replay_explorer(raw, inputs, output, rid)
        if args.command == "export":
            export_explorer(output, rid, args.destination)
        print(json.dumps({"report_id": rid, "snapshot_id": report["object"], "coverage": data["coverage"],
                          "cutoff": data["cutoff"], "ranking_ready": False}, indent=2))
    except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Defense Explorer failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
