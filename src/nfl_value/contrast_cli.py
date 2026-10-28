"""Build/replay archived positional diagnostics with exact lineage and numerical checks."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.contrasts import experiment
from nfl_value.contrast_math import validate_plan
from nfl_value.first_unit import select_first_units
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, replay
from nfl_value.pregame_inputs import _rows, _team_games
from nfl_value.roster_inputs import replay_roster_inputs
from nfl_value.source_audit import aware_time


def run(raw, offensive, rosters, *, roster_report, depth_charts, evidence_cutoff, plan):
    validate_plan(plan)
    roster = replay_roster_inputs(raw, offensive, rosters, roster_report)
    receipt = replay(raw, depth_charts)
    season = roster["season"]
    if receipt["source"]["kind"] != "depth_charts" or receipt["source"]["season"] != season:
        raise ValueError("depth receipt source kind/season mismatch")
    cutoff = aware_time(evidence_cutoff)
    if any(
        aware_time(t) > cutoff for t in [roster["evidence_cutoff"], *receipt["retrieval"].values()]
    ):
        raise ValueError("evidence was retrieved after contrast cutoff")
    inputs = json.loads(offensive.read(roster["offensive_report_id"], manifest=True))
    if not roster["game_coverage_complete"] or not inputs["game_coverage"]["coverage_complete"]:
        raise ValueError("complete reconciled game coverage required")
    ledger = json.loads(offensive.read(inputs["objects"]["ledger"]))
    evidence = json.loads(rosters.read(roster["objects"]["evidence"]))
    games = _team_games(inputs["game_coverage"])
    schedule = json.loads(raw.read(inputs["source_receipts"]["schedules"], manifest=True))
    if {g.team_id for g in games} != set(schedule["audit"]["teams"]):
        raise ValueError("completed games must cover declared season teams")
    depth_bytes = raw.read(receipt["objects"]["raw"])
    # Identity consistency is a whole-selection check in the depth adapter.
    # Selecting the full season then slicing could let a later identity issue
    # contaminate an earlier prefix. Select independently for each window.
    first_units = {
        str(week): select_first_units(
            _rows(depth_bytes, {"pos_grp"}),
            [g for g in games if int(g.game_id.split("_")[1]) <= week],
            requested_roles=tuple(plan["roles"]),
        )
        for week in plan["windows"][str(season)]
    }
    report, models, results = experiment(
        ledger,
        evidence,
        first_units,
        games,
        season=season,
        cutoff=cutoff,
        plan=plan,
    )
    report["input_reports"] = {"roster": roster_report, "offensive": roster["offensive_report_id"]}
    report["depth_charts"] = depth_charts
    report["game_cohort_cutoff"] = roster["game_cohort_cutoff"]
    report["source_attribution"] = {
        **roster["source_attribution"],
        "depth_charts": {
            k: receipt["source"][k] for k in ("license_id", "license_url", "attribution")
        },
    }
    report["historical_availability"] = {
        "retrospective_depth_team_games": sum(
            aware_time(receipt["retrieval"]["data"]) >= g.kickoff for g in games
        ),
        "retrospective_roster_team_games": roster["audit"][
            "team_games_with_retrospective_roster_retrieval"
        ],
        "historically_available_evidence_validated": False,
    }
    return report, models, results


def replay_contrasts(raw, offensive, rosters, output, report_id):
    saved = json.loads(output.read(report_id, manifest=True))
    if (
        saved["experiment_kind"] != "positional-contrast-diagnostics"
        or type(saved["experiment_version"]) is not int
        or saved["experiment_version"] != 1
        or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
    ):
        raise ValueError("unsupported contrast artifact or replay policy")
    if (
        saved["environment"]["numpy"] != numpy.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    report, models, results = run(
        raw,
        offensive,
        rosters,
        roster_report=saved["input_reports"]["roster"],
        depth_charts=saved["depth_charts"],
        evidence_cutoff=saved["evidence_cutoff"],
        plan=saved["plan"],
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"code_revision", "environment", "objects", "replay_tolerance"}
    }
    # Reuse the existing snapshot writer; its 'predictions' object holds this
    # experiment's diagnostic results, including cohort/exposure evidence.
    assert_numerically_equal(json.loads(json.dumps(report)), expected)
    assert_numerically_equal(models, json.loads(output.read(saved["objects"]["models"])))
    assert_numerically_equal(
        json.loads(json.dumps(results)), json.loads(output.read(saved["objects"]["predictions"]))
    )
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument(
        "--offensive-store", type=Path, default=Path("data/derived/offensive-inputs")
    )
    parser.add_argument("--roster-store", type=Path, default=Path("data/derived/roster-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/contrasts"))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--roster-report", required=True)
    build.add_argument("--depth-charts", required=True)
    build.add_argument("--evidence-cutoff", required=True)
    build.add_argument("--plan", type=Path, required=True)
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    try:
        raw, offensive, rosters, output = (
            SnapshotStore(p)
            for p in (args.raw_store, args.offensive_store, args.roster_store, args.output_store)
        )
        if args.command == "build":
            revision = committed_revision()
            report, models, results = run(
                raw,
                offensive,
                rosters,
                roster_report=args.roster_report,
                depth_charts=args.depth_charts,
                evidence_cutoff=args.evidence_cutoff,
                plan=json.loads(args.plan.read_text()),
            )
            report_id, report = save(output, report, models, results, code_revision=revision)
        else:
            report_id = args.report_id
            report = replay_contrasts(raw, offensive, rosters, output, report_id)
        print(
            json.dumps(
                {"report_id": report_id, "summary": report["summary"], "ranking_ready": False},
                indent=2,
                sort_keys=True,
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
        print(f"Contrast experiment failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
