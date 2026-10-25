"""Build/replay the fixed historical defensive information-loss experiment offline."""

import argparse
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline_cli import assert_numerically_equal
from nfl_value.defense_inputs import replay_defense_inputs
from nfl_value.defensive_model import experiment
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.offensive_inputs import replay_offensive_inputs


def run(raw, inputs, candidates, *, defensive_report, candidate_report, plan):
    d = replay_defense_inputs(raw, inputs, defensive_report)
    c = replay_offensive_inputs(raw, candidates, candidate_report)
    if d["report_version"] != 2 or not d["game_coverage"]["coverage_complete"] or not c["game_coverage"]["coverage_complete"]:
        raise ValueError("reconciled completion-v2 inputs required")
    rich, degraded = (json.loads(inputs.read(d["objects"][k])) for k in ("rich", "degraded"))
    ledger = json.loads(candidates.read(c["objects"]["ledger"]))
    report, models, predictions = experiment(rich, degraded, ledger, plan)
    report["input_reports"] = {"defensive": defensive_report, "candidate": candidate_report}
    report["source_provenance"] = {
        "defensive": rich["provenance"], "candidate": ledger["provenance"],
        "derivative_license": d["derived_participation_license"], "license_url": d["license_url"],
        "attribution": d["attribution"],
        "transformations": "Matched play/game aggregation, regularized defensive regression, predictions and diagnostics. Software MIT does not relicense data derivatives."}
    return report, models, predictions


def envelope(report, payload, kind, *, code_revision, environment):
    return {"artifact_version": 1, "kind": kind, "scope": report["scope"], "ranking_ready": False,
            "plan": report["plan"], "input_reports": report["input_reports"], "source_provenance": report["source_provenance"],
            "code_revision": code_revision, "environment": environment, kind: payload}


def save(output, report, models, predictions, *, code_revision):
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("full committed code revision required")
    environment = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__, "platform": platform.platform()}
    objects = {kind: output.put(json_bytes(envelope(report, payload, kind, code_revision=code_revision, environment=environment)))
               for kind, payload in (("models", models), ("predictions", predictions))}
    saved = {**report, "code_revision": code_revision, "environment": environment, "objects": objects,
             "replay_tolerance": {"absolute": 1e-9, "relative": 1e-8}}
    return output.put(json_bytes(saved), manifest=True), saved


def replay_experiment(raw, inputs, candidates, output, report_id):
    saved = json.loads(output.read(report_id, manifest=True))
    if saved["experiment_version"] != 1 or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}:
        raise ValueError("unsupported defensive experiment or tolerance")
    if saved["environment"]["numpy"] != numpy.__version__ or saved["environment"]["scipy"] != scipy.__version__:
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    report, models, predictions = run(raw, inputs, candidates, defensive_report=saved["input_reports"]["defensive"],
                                      candidate_report=saved["input_reports"]["candidate"], plan=saved["plan"])
    expected = {k: v for k, v in saved.items() if k not in {"code_revision", "environment", "objects", "replay_tolerance"}}
    assert_numerically_equal(report, expected)
    for kind, payload in (("models", models), ("predictions", predictions)):
        actual = envelope(report, payload, kind, code_revision=saved["code_revision"], environment=saved["environment"])
        assert_numerically_equal(actual, json.loads(output.read(saved["objects"][kind])))
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/defense-inputs"))
    parser.add_argument("--candidate-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/defensive-model"))
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--defensive-report", required=True)
    build.add_argument("--candidate-report", required=True)
    build.add_argument("--plan", type=Path, required=True)
    commands.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, inputs, candidates, output = (SnapshotStore(p) for p in (args.raw_store, args.input_store, args.candidate_store, args.output_store))
        if args.command == "build":
            revision = committed_revision()
            result = run(raw, inputs, candidates, defensive_report=args.defensive_report, candidate_report=args.candidate_report,
                         plan=json.loads(args.plan.read_text()))
            report_id, report = save(output, *result, code_revision=revision)
        else:
            report_id = args.report_id
            report = replay_experiment(raw, inputs, candidates, output, report_id)
        print(json.dumps({"report_id": report_id, "selected_defender_penalties": report["selected_defender_penalties"],
                          "evaluation": report["evaluation"], "degraded_minus_rich": report["degraded_minus_rich"]["defender"],
                          "objects": report["objects"], "ranking_ready": False}, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Defensive experiment failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
