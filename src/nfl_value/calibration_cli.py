"""Offline build/replay of known-effect calibration, with full upstream replay."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline import prepare_plays
from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.calibration import experiment
from nfl_value.calibration_math import validate_plan
from nfl_value.contrast_cli import replay_contrasts
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore


def run(raw, offensive, rosters, contrasts, *, contrast_report, plan):
    validate_plan(plan)
    # Check sources, cohort construction, all fitted coefficients, diagnostics
    # and archive hashes before trusting even the selected design metadata.
    upstream = replay_contrasts(raw, offensive, rosters, contrasts, contrast_report)
    season = upstream["season"]
    if str(season) not in plan["windows"]:
        raise ValueError("season absent from calibration plan")
    week = plan["windows"][str(season)]
    if week not in upstream["plan"]["windows"][str(season)]:
        raise ValueError("window absent from verified contrast archive")
    models = json.loads(contrasts.read(upstream["objects"]["models"]))
    windows = json.loads(contrasts.read(upstream["objects"]["predictions"]))
    inputs = json.loads(offensive.read(upstream["input_reports"]["offensive"], manifest=True))
    ledger = json.loads(offensive.read(inputs["objects"]["ledger"]))
    prefix = {**ledger, "plays": [p for p in ledger["plays"] if p["week"] <= week]}
    rows, _ = prepare_plays(prefix, season=season)
    report, diagnostics, results = experiment(
        rows,
        upstream,
        models[f"week-{week}/penalty-{plan['primary_actor_penalty']:g}"],
        windows[str(week)],
        plan=plan,
    )
    report["input_contrast_report"] = contrast_report
    return report, diagnostics, results


def replay_calibration(raw, offensive, rosters, contrasts, output, report_id):
    saved = json.loads(output.read(report_id, manifest=True))
    if (
        saved["experiment_kind"] != "known-effect-calibration"
        or type(saved["experiment_version"]) is not int
        or saved["experiment_version"] != 1
        or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
    ):
        raise ValueError("unsupported calibration artifact or replay policy")
    if (
        saved["environment"]["numpy"] != numpy.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    report, diagnostics, results = run(
        raw,
        offensive,
        rosters,
        contrasts,
        contrast_report=saved["input_contrast_report"],
        plan=saved["plan"],
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k
        not in {
            "code_revision",
            "environment",
            "objects",
            "replay_tolerance",
        }
    }
    assert_numerically_equal(report, expected)
    # Reuse the immutable writer's object slots; no production model or
    # real-data predictions are contained in either calibration object.
    assert_numerically_equal(diagnostics, json.loads(output.read(saved["objects"]["models"])))
    assert_numerically_equal(results, json.loads(output.read(saved["objects"]["predictions"])))
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    paths = {
        "raw": "data/raw/source-snapshots",
        "offensive": "data/derived/offensive-inputs",
        "roster": "data/derived/roster-inputs",
        "contrast": "data/derived/contrasts",
        "output": "data/derived/calibration",
    }
    for name, default in paths.items():
        parser.add_argument(f"--{name}-store", type=Path, default=Path(default))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--contrast-report", required=True)
    build.add_argument("--plan", type=Path, required=True)
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, offensive, rosters, contrasts, output = (
            SnapshotStore(getattr(args, f"{name}_store")) for name in paths
        )
        if args.command == "build":
            revision = committed_revision()
            report, diagnostics, results = run(
                raw,
                offensive,
                rosters,
                contrasts,
                contrast_report=args.contrast_report,
                plan=json.loads(args.plan.read_text()),
            )
            rid, report = save(output, report, diagnostics, results, code_revision=revision)
        else:
            rid = args.report_id
            report = replay_calibration(raw, offensive, rosters, contrasts, output, rid)
        print(
            json.dumps(
                {
                    "report_id": rid,
                    "season": report["season"],
                    "week": report["week"],
                    "ranking_ready": False,
                },
                sort_keys=True,
                indent=2,
            )
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Calibration experiment failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
