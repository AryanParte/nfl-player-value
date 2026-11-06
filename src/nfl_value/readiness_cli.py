"""Assess sources or prepare/replay an Explorer candidate. Never update a pointer."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.readiness import POLICY, assess_sources, replay_readiness, save_readiness
from nfl_value.refresh_candidate import prepare_candidate, replay_candidate
from nfl_value.source_audit import aware_time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument(
        "--explorer-store", type=Path, default=Path("data/derived/defense-explorer")
    )
    parser.add_argument(
        "--candidate-store", type=Path, default=Path("data/derived/explorer-candidates")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("assess", "prepare"):
        sub = commands.add_parser(command)
        sub.add_argument("--cutoff", required=True)
        for source in POLICY["required_sources"]:
            sub.add_argument("--" + source.replace("_", "-"))
        if command == "prepare":
            sub.add_argument("--previous-explorer")
    commands.add_parser("replay-readiness").add_argument("report_id")
    commands.add_parser("replay-candidate").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        stores = tuple(
            SnapshotStore(p)
            for p in (args.raw_store, args.input_store, args.explorer_store, args.candidate_store)
        )
        raw, inputs, explorers, candidates = stores
        if args.command.startswith("replay-"):
            report = (
                replay_readiness(raw, candidates, args.report_id)
                if args.command == "replay-readiness"
                else replay_candidate(*stores, args.report_id)
            )
            result = {
                "report_id": args.report_id,
                "kind": report["kind"],
                "cutoff": report["cutoff"],
                "verified_at_original_cutoff_only": True,
                "ranking_ready": False,
                "published": False,
            }
            blocked = report.get("ready_for_explorer_build") is False
        else:
            revision = committed_revision()
            receipts = {kind: getattr(args, kind) for kind in POLICY["required_sources"]}
            cutoff = aware_time(args.cutoff)
            candidate_id = None
            if args.command == "prepare":
                rid, report, candidate_id = prepare_candidate(
                    *stores,
                    receipts,
                    cutoff=cutoff,
                    code_revision=revision,
                    previous_explorer=args.previous_explorer,
                )
            else:
                report = assess_sources(raw, receipts, cutoff=cutoff, code_revision=revision)
                rid = save_readiness(candidates, report)
            blocked = not report["ready_for_explorer_build"]
            result = {
                "readiness_report": rid,
                "candidate_id": candidate_id,
                "cutoff": report["cutoff"],
                "ready_for_explorer_build": not blocked,
                "blockers": report["blockers"],
                "completed_games": len(report["game_coverage"]["matched_games"])
                if report["game_coverage"]
                else None,
                "ranking_ready": False,
                "published": False,
            }
        print(json.dumps(result, sort_keys=True, indent=2))
        return 2 if blocked else 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Explorer readiness failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
