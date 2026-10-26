"""Build or replay weekly roster evidence using archived receipts only."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.roster_inputs import build_roster_inputs, replay_roster_inputs, save_roster_inputs
from nfl_value.source_audit import aware_time


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument(
        "--offensive-store", type=Path, default=Path("data/derived/offensive-inputs")
    )
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/roster-inputs"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--weekly-rosters", required=True)
    build.add_argument("--offensive-report-id", required=True)
    build.add_argument("--evidence-cutoff", required=True)
    commands.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, offensive, derived = (
            SnapshotStore(p) for p in (args.store, args.offensive_store, args.output_store)
        )
        if args.command == "build":
            report, evidence = build_roster_inputs(
                raw,
                offensive,
                weekly_rosters=args.weekly_rosters,
                offensive_report_id=args.offensive_report_id,
                evidence_cutoff=aware_time(args.evidence_cutoff),
                code_revision=committed_revision(),
            )
            report_id, report = save_roster_inputs(derived, report, evidence)
        else:
            report_id = args.report_id
            report = replay_roster_inputs(raw, offensive, derived, report_id)
        print(
            json.dumps(
                {
                    "report_id": report_id,
                    "season": report["season"],
                    "audit": report["audit"],
                    "ranking_ready": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        print(f"Roster inputs failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
