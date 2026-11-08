"""Build/replay the preregistered QB recovery experiment from archived sources only."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, load_ledger, save
from nfl_value.first_unit import select_first_units
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, replay
from nfl_value.pregame_inputs import _rows, _team_games
from nfl_value.qb_recovery import experiment, validate_plan
from nfl_value.research_roster import replay_legacy
from nfl_value.roster_inputs import join_roster_evidence
from nfl_value.source_audit import aware_time
from nfl_value.weekly_rosters import WEEKLY_ROSTER_COLUMNS


def load_evidence(raw, inputs, report_id, roster_id, *, cutoff, legacy=False):
    ledger, report = load_ledger(raw, inputs, report_id)
    receipt = replay_legacy(raw, roster_id) if legacy else replay(raw, roster_id)
    season = report["season"]
    if receipt["source"]["kind"] != "weekly_rosters" or receipt["source"]["season"] != season:
        raise ValueError("QB recovery roster kind/season mismatch")
    if any(aware_time(t) > cutoff for t in [report["cutoff"], *receipt["retrieval"].values()]):
        raise ValueError("QB evidence was retrieved after declared evidence cutoff")
    schedule = replay(raw, report["source_receipts"]["schedules"])
    games = _team_games(report["game_coverage"])
    evidence, audit = join_roster_evidence(
        _rows(raw.read(receipt["objects"]["raw"]), WEEKLY_ROSTER_COLUMNS),
        season=season,
        team_games=games,
        season_teams=schedule["audit"]["teams"],
        workloads=ledger["observed_player_games"],
        retrieved_at=aware_time(receipt["retrieval"]["data"]),
    )
    if audit["team_games_without_roster_rows"]:
        raise ValueError("QB recovery requires weekly roster coverage of every completed team game")
    provenance = {
        "offensive": report_id,
        "weekly_rosters": roster_id,
        "source_receipts": report["source_receipts"],
        "game_cohort_cutoff": report["cutoff"],
        "roster_retrieval": receipt["retrieval"],
        "roster_integrity_policy": receipt.get("policy", "upstream-sha256-source-receipt-v1"),
        "source_attribution": {
            **report["source_attribution"],
            "weekly_rosters": {
                k: receipt["source"][k] for k in ("license_id", "license_url", "attribution")
            },
        },
        "roster_audit": audit,
    }
    return ledger, evidence, games, provenance


def run(raw, inputs, *, input_reports, evidence_cutoff, plan, progress=lambda message: None):
    validate_plan(plan)
    if set(input_reports) != {
        "historical",
        "current",
        "historical_roster",
        "current_roster",
        "depth_charts",
    }:
        raise ValueError("exact QB recovery input references required")
    cutoff = aware_time(evidence_cutoff)
    historical, he, _, hp = load_evidence(
        raw,
        inputs,
        input_reports["historical"],
        input_reports["historical_roster"],
        cutoff=cutoff,
        legacy=True,
    )
    current, ce, games, cp = load_evidence(
        raw, inputs, input_reports["current"], input_reports["current_roster"], cutoff=cutoff
    )
    depth = replay(raw, input_reports["depth_charts"])
    if (
        depth["source"]["kind"] != "depth_charts"
        or depth["source"]["season"] != plan["current_season"]
        or any(aware_time(t) > cutoff for t in depth["retrieval"].values())
    ):
        raise ValueError("depth source kind/season/evidence cutoff mismatch")
    first_unit = select_first_units(
        _rows(raw.read(depth["objects"]["raw"]), {"pos_grp"}), games, requested_roles=("QB",)
    )
    report, models, results = experiment(
        historical, current, he, ce, first_unit, games, cutoff=cutoff, plan=plan, progress=progress
    )
    report.update(
        input_reports=input_reports,
        evidence_cutoff=evidence_cutoff,
        source_provenance={
            "historical": hp,
            "current": cp,
            "depth_charts": input_reports["depth_charts"],
        },
    )
    return report, models, results


def replay_experiment(raw, inputs, output, report_id, *, progress=lambda message: None):
    saved = json.loads(output.read(report_id, manifest=True))
    if saved["experiment"] != "qb-dropback-recovery-v1" or saved["replay_tolerance"] != {
        "absolute": 1e-9,
        "relative": 1e-8,
    }:
        raise ValueError("unsupported QB recovery replay policy")
    if (
        saved["environment"]["numpy"] != numpy.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("replay requires recorded NumPy/SciPy versions")
    # Reject missing/corrupt outputs before spending time on numerical replay.
    models = json.loads(output.read(saved["objects"]["models"]))
    results = json.loads(output.read(saved["objects"]["predictions"]))
    report, actual_models, actual_results = run(
        raw,
        inputs,
        input_reports=saved["input_reports"],
        evidence_cutoff=saved["evidence_cutoff"],
        plan=saved["plan"],
        progress=progress,
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"code_revision", "environment", "replay_tolerance", "objects"}
    }
    assert_numerically_equal(report, expected)
    assert_numerically_equal(actual_models, models)
    assert_numerically_equal(actual_results, results)
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--output-store", type=Path, default=Path("data/derived/qb-recovery"))
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--inputs", type=Path, required=True)
    build.add_argument("--plan", type=Path, default=Path("config/qb-recovery-v1.json"))
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    raw, inputs, output = (
        SnapshotStore(p) for p in (args.raw_store, args.input_store, args.output_store)
    )

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        if args.command == "build":
            revision = committed_revision()
            spec = json.loads(args.inputs.read_text())
            report, models, results = run(
                raw, inputs, plan=json.loads(args.plan.read_text()), progress=progress, **spec
            )
            rid, saved = save(output, report, models, results, code_revision=revision)
        else:
            rid = args.report_id
            saved = replay_experiment(raw, inputs, output, rid, progress=progress)
        print(
            json.dumps(
                {
                    "report_id": rid,
                    "evaluation": saved["evaluation"],
                    "season": saved["season"],
                    "calibration": saved["calibration"],
                    "ranking_ready": False,
                },
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"QB recovery failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
