"""Offline build/replay of the frozen multi-season and defensive recovery unit."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.defense_inputs import replay_defense_inputs
from nfl_value.defense_variance import diagnose
from nfl_value.first_unit import select_first_units
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, replay
from nfl_value.multiseason import experiment
from nfl_value.multiseason_math import validate_plan
from nfl_value.pregame_inputs import _rows
from nfl_value.qb_recovery_cli import load_evidence
from nfl_value.source_audit import aware_time


def run(
    raw, inputs, defense_inputs, *, input_reports, evidence_cutoff, plan, progress=lambda _: None
):
    validate_plan(plan)
    if set(input_reports) != {"seasons", "depth_charts", "defense"} or set(
        input_reports["seasons"]
    ) != {str(s) for s in plan["seasons"]}:
        raise ValueError("exact frozen input report references required")
    cutoff = aware_time(evidence_cutoff)
    datasets = {}
    for year in plan["seasons"]:
        refs = input_reports["seasons"][str(year)]
        if set(refs) != {"offensive", "weekly_rosters"}:
            raise ValueError("exact offensive/roster source references required")
        progress(f"Replaying archived {year} sources")
        datasets[year] = load_evidence(
            raw,
            inputs,
            refs["offensive"],
            refs["weekly_rosters"],
            cutoff=cutoff,
            legacy=year == 2024,
        )
        if datasets[year][0]["provenance"]["season"] != year:
            raise ValueError("declared season and archived source disagree")
    depth = replay(raw, input_reports["depth_charts"])
    if (
        depth["source"]["kind"] != "depth_charts"
        or depth["source"]["season"] != plan["scoring_season"]
        or any(aware_time(t) > cutoff for t in depth["retrieval"].values())
    ):
        raise ValueError("depth source kind/season/cutoff mismatch")
    first_unit = select_first_units(
        _rows(raw.read(depth["objects"]["raw"]), {"pos_grp"}),
        datasets[plan["scoring_season"]][2],
        requested_roles=("QB",),
    )
    # Validate every source before expensive fitting; an invalid defense archive
    # is not quietly skipped when offensive modeling succeeds.
    defense = replay_defense_inputs(raw, defense_inputs, input_reports["defense"])
    if defense["season"] != plan["scoring_season"] - 1 or aware_time(defense["cutoff"]) > cutoff:
        raise ValueError("defense season/cutoff mismatch")
    rich, degraded = [
        json.loads(defense_inputs.read(defense["objects"][view])) for view in ["rich", "degraded"]
    ]
    report, models, results = experiment(
        datasets, first_unit, cutoff=cutoff, plan=plan, progress=progress
    )
    report["defense"] = diagnose(rich, degraded, plan, progress)
    report.update(
        input_reports=input_reports,
        evidence_cutoff=evidence_cutoff,
        source_provenance={
            "seasons": {str(y): d[3] for y, d in datasets.items()},
            "depth_charts": input_reports["depth_charts"],
            "defense": {
                k: defense[k]
                for k in [
                    "source_receipts",
                    "cutoff",
                    "derived_participation_license",
                    "license_url",
                    "attribution",
                    "historical_availability",
                ]
            },
        },
    )
    return report, models, results


def replay_experiment(raw, inputs, defense_inputs, output, report_id, *, progress=lambda _: None):
    saved = json.loads(output.read(report_id, manifest=True))
    if saved["experiment"] != "multiseason-variance-recovery-v1" or saved["replay_tolerance"] != {
        "absolute": 1e-9,
        "relative": 1e-8,
    }:
        raise ValueError("unsupported multi-season replay policy")
    if (
        saved["environment"]["numpy"] != numpy.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    models = json.loads(output.read(saved["objects"]["models"]))
    results = json.loads(output.read(saved["objects"]["predictions"]))
    actual, actual_models, actual_results = run(
        raw,
        inputs,
        defense_inputs,
        input_reports=saved["input_reports"],
        evidence_cutoff=saved["evidence_cutoff"],
        plan=saved["plan"],
        progress=progress,
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"objects", "environment", "code_revision", "replay_tolerance"}
    }
    assert_numerically_equal(actual, expected)
    assert_numerically_equal(actual_models, models)
    assert_numerically_equal(actual_results, results)
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--defense-store", type=Path, default=Path("data/derived/defense-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/multiseason"))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--inputs", type=Path, required=True)
    build.add_argument("--plan", type=Path, default=Path("config/multiseason-v1.json"))
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    stores = [SnapshotStore(p) for p in [args.raw_store, args.input_store, args.defense_store]]
    output = SnapshotStore(args.output_store)

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        if args.command == "build":
            revision = committed_revision()
            report, models, results = run(
                *stores,
                **json.loads(args.inputs.read_text()),
                plan=json.loads(args.plan.read_text()),
                progress=progress,
            )
            rid, saved = save(output, report, models, results, code_revision=revision)
        else:
            rid = args.report_id
            saved = replay_experiment(*stores, output, rid, progress=progress)
        print(
            json.dumps(
                {
                    "report_id": rid,
                    "season": saved["season"],
                    "evaluation": saved["evaluation"],
                    "calibration": saved["calibration"],
                    "defense": saved["defense"],
                    "ranking_ready": False,
                },
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Multi-season recovery failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
