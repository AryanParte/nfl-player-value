"""Fit and numerically replay a versioned offline outcome-model experiment."""

import argparse
import json
from math import isclose
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline import experiment
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.offensive_inputs import replay_offensive_inputs


def load_ledger(raw: SnapshotStore, inputs: SnapshotStore, report_id: str) -> tuple[dict, dict]:
    report = replay_offensive_inputs(raw, inputs, report_id)
    if not report["game_coverage"]["coverage_complete"]:
        raise ValueError("baseline requires complete reconciled game coverage")
    if report["opportunity_audit"]["player_game_team_conflicts"]:
        raise ValueError("unresolved player-game team conflict")
    return json.loads(inputs.read(report["objects"]["ledger"])), report


def run(raw: SnapshotStore, inputs: SnapshotStore, *, historical_report: str, transfer_report: str, plan: dict):
    historical, h_report = load_ledger(raw, inputs, historical_report)
    transfer, t_report = load_ledger(raw, inputs, transfer_report)
    report, models, predictions = experiment(historical, transfer, plan)
    report["input_reports"] = {"historical": historical_report, "transfer": transfer_report}
    report["source_provenance"] = {"historical": {k: h_report[k] for k in ("code_revision", "cutoff", "source_receipts", "source_attribution")},
                                   "transfer": {k: t_report[k] for k in ("code_revision", "cutoff", "source_receipts", "source_attribution")}}
    return report, models, predictions


def assert_numerically_equal(actual, expected, *, path="root") -> None:
    """Exact structure/identities; small floating-point platform differences allowed."""
    if isinstance(expected, float):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-9):
            raise ValueError(f"numeric replay differs at {path}")
    elif isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise ValueError(f"replay structure differs at {path}")
        for k in expected:
            assert_numerically_equal(actual[k], expected[k], path=f"{path}.{k}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"replay length differs at {path}")
        for i, (a, b) in enumerate(zip(actual, expected)):
            assert_numerically_equal(a, b, path=f"{path}[{i}]")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"replay differs at {path}")


def save(output: SnapshotStore, report: dict, models: dict, predictions: dict, *, code_revision: str):
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("full committed code revision required")
    saved = {**report, "code_revision": code_revision,
             "environment": {"python": platform.python_version(), "numpy": numpy.__version__,
                             "scipy": scipy.__version__, "platform": platform.platform()},
             "replay_tolerance": {"absolute": 1e-9, "relative": 1e-8},
             "objects": {"models": output.put(json_bytes(models)), "predictions": output.put(json_bytes(predictions))}}
    return output.put(json_bytes(saved), manifest=True), saved


def replay_experiment(raw: SnapshotStore, inputs: SnapshotStore, output: SnapshotStore, report_id: str):
    saved = json.loads(output.read(report_id, manifest=True))
    if saved["experiment_version"] != 1 or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}:
        raise ValueError("unsupported experiment or tolerance policy")
    if saved["environment"]["numpy"] != numpy.__version__ or saved["environment"]["scipy"] != scipy.__version__:
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    report, models, predictions = run(raw, inputs, historical_report=saved["input_reports"]["historical"],
                                    transfer_report=saved["input_reports"]["transfer"], plan=saved["plan"])
    expected = {k: v for k, v in saved.items() if k not in {"code_revision", "environment", "objects", "replay_tolerance"}}
    assert_numerically_equal(report, expected)
    assert_numerically_equal(models, json.loads(output.read(saved["objects"]["models"])))
    assert_numerically_equal(predictions, json.loads(output.read(saved["objects"]["predictions"])))
    return saved


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/baseline"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--historical-report", required=True)
    build.add_argument("--transfer-report", required=True)
    build.add_argument("--plan", type=Path, required=True)
    commands.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, inputs, output = SnapshotStore(args.raw_store), SnapshotStore(args.input_store), SnapshotStore(args.output_store)
        if args.command == "build":
            revision = committed_revision()
            plan = json.loads(args.plan.read_text())
            report, models, predictions = run(raw, inputs, historical_report=args.historical_report,
                                            transfer_report=args.transfer_report, plan=plan)
            report_id, report = save(output, report, models, predictions, code_revision=revision)
        else:
            report_id = args.report_id
            report = replay_experiment(raw, inputs, output, report_id)
        print(json.dumps({"report_id": report_id, "selected_actor_penalty": report["selected_actor_penalty"],
                          "evaluation": report["evaluation"], "objects": report["objects"], "ranking_ready": False}, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Baseline failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
