"""Build/replay the frozen observed-lineup audit from verified local archives."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, replay_experiment, save
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.pregame_inputs import _team_games
from nfl_value.roster_inputs import replay_roster_inputs
from nfl_value.transitions import experiment, validate_plan


def run(raw, offensive, rosters, baseline_store, *, baseline_report, roster_reports, plan):
    validate_plan(plan)
    if set(roster_reports) != set(plan["evaluation_labels"]):
        raise ValueError("both evaluation roster reports required")
    baseline = replay_experiment(raw, offensive, baseline_store, baseline_report)
    models = json.loads(baseline_store.read(baseline["objects"]["models"]))
    predictions = json.loads(baseline_store.read(baseline["objects"]["predictions"]))
    ledgers, evidence, games, provenance = {}, {}, {}, {}
    for label, input_key in (("historical_test", "historical"), ("transfer_test", "transfer")):
        roster = replay_roster_inputs(raw, offensive, rosters, roster_reports[label])
        if roster["offensive_report_id"] != baseline["input_reports"][input_key]:
            raise ValueError("roster and baseline offensive reports differ")
        inputs = json.loads(offensive.read(roster["offensive_report_id"], manifest=True))
        if not inputs["game_coverage"]["coverage_complete"] or not roster["game_coverage_complete"]:
            raise ValueError("complete reconciled game coverage required")
        ledgers[label] = json.loads(offensive.read(inputs["objects"]["ledger"]))
        evidence[label] = json.loads(rosters.read(roster["objects"]["evidence"]))
        games[label] = _team_games(inputs["game_coverage"])
        provenance[label] = {
            "offensive_report_id": roster["offensive_report_id"],
            "game_cohort_cutoff": roster["game_cohort_cutoff"],
            "evidence_cutoff": roster["evidence_cutoff"],
            "source_attribution": roster["source_attribution"],
            "historically_available_evidence_validated": False,
        }
    report, panels, cases = experiment(
        ledgers, evidence, games, baseline, models, predictions, plan=plan
    )
    report.update(
        input_baseline_report=baseline_report,
        input_roster_reports=roster_reports,
        source_provenance=provenance,
    )
    return report, panels, cases


def replay_transitions(raw, offensive, rosters, baseline_store, output, report_id):
    saved = json.loads(output.read(report_id, manifest=True))
    if (
        saved["experiment_kind"] != "observed-lineup-transitions"
        or type(saved["experiment_version"]) is not int
        or saved["experiment_version"] != 1
        or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
    ):
        raise ValueError("unsupported transition artifact or replay policy")
    if (
        saved["environment"]["numpy"] != numpy.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    report, panels, cases = run(
        raw,
        offensive,
        rosters,
        baseline_store,
        baseline_report=saved["input_baseline_report"],
        roster_reports=saved["input_roster_reports"],
        plan=saved["plan"],
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"code_revision", "environment", "objects", "replay_tolerance"}
    }
    assert_numerically_equal(report, expected)
    assert_numerically_equal(panels, json.loads(output.read(saved["objects"]["models"])))
    assert_numerically_equal(cases, json.loads(output.read(saved["objects"]["predictions"])))
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    paths = {
        "raw": "data/raw/source-snapshots",
        "offensive": "data/derived/offensive-inputs",
        "roster": "data/derived/roster-inputs",
        "baseline": "data/derived/baseline",
        "output": "data/derived/transitions",
    }
    for name, default in paths.items():
        parser.add_argument(f"--{name}-store", type=Path, default=Path(default))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--baseline-report", required=True)
    build.add_argument("--historical-roster-report", required=True)
    build.add_argument("--transfer-roster-report", required=True)
    build.add_argument("--plan", type=Path, required=True)
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, offensive, rosters, baseline, output = (
            SnapshotStore(getattr(args, f"{n}_store")) for n in paths
        )
        if args.command == "build":
            revision = committed_revision()
            report, panels, cases = run(
                raw,
                offensive,
                rosters,
                baseline,
                baseline_report=args.baseline_report,
                roster_reports={
                    "historical_test": args.historical_roster_report,
                    "transfer_test": args.transfer_roster_report,
                },
                plan=json.loads(args.plan.read_text()),
            )
            rid, report = save(output, report, panels, cases, code_revision=revision)
        else:
            rid = args.report_id
            report = replay_transitions(raw, offensive, rosters, baseline, output, rid)
        print(
            json.dumps(
                {"report_id": rid, "summary": report["summary"], "ranking_ready": False},
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
        print(f"Transition audit failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
