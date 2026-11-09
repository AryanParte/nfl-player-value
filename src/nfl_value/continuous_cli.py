"""Build/replay a continuous-variance research artifact from immutable parent sources."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.continuous_recovery import experiment, validate_plan
from nfl_value.contrast_cohorts import make_cohorts
from nfl_value.first_unit import select_first_units
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, replay, sha256
from nfl_value.pregame_inputs import _rows
from nfl_value.qb_recovery import prepare
from nfl_value.qb_recovery_cli import load_evidence
from nfl_value.source_audit import aware_time


def load_context(raw, inputs, parent_store, plan, progress=lambda _: None):
    validate_plan(plan)
    parent = json.loads(parent_store.read(plan["parent_report"], manifest=True))
    if (
        parent["experiment"] != "multiseason-variance-recovery-v1"
        or parent["ranking_ready"] is not False
        or parent["plan_sha256"] != sha256(json_bytes(parent["plan"]))
    ):
        raise ValueError("verified original multi-season research parent required")
    models = json.loads(parent_store.read(parent["objects"]["models"]))
    results = json.loads(parent_store.read(parent["objects"]["predictions"]))
    rows, datasets = [], {}
    cutoff = aware_time(parent["evidence_cutoff"])
    for year in parent["plan"]["seasons"]:
        progress(f"Replaying archived {year} sources")
        refs = parent["input_reports"]["seasons"][str(year)]
        datasets[year] = load_evidence(
            raw,
            inputs,
            refs["offensive"],
            refs["weekly_rosters"],
            cutoff=cutoff,
            legacy=year == 2024,
        )
        ledger, evidence, _, provenance = datasets[year]
        assert_numerically_equal(provenance, parent["source_provenance"]["seasons"][str(year)])
        selected, _ = prepare(ledger, evidence, season=year, low_week=1, high_week=18)
        if year == 2026 and any(p["week"] >= 10 for p in selected):
            raise ValueError("training archive reaches the reserved future window")
        rows.extend(selected)
    rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
    current = [p for p in rows if p["game_id"].startswith("2026_")]
    depth = replay(raw, parent["input_reports"]["depth_charts"])
    if (
        depth["source"]["kind"] != "depth_charts"
        or depth["source"]["season"] != 2026
        or any(aware_time(t) > cutoff for t in depth["retrieval"].values())
    ):
        raise ValueError("depth source kind/season/cutoff mismatch")
    _, evidence, games, _ = datasets[2026]
    first = select_first_units(
        _rows(raw.read(depth["objects"]["raw"]), {"pos_grp"}), games, requested_roles=("QB",)
    )
    cohorts = make_cohorts(current, evidence, first, games, cutoff=cutoff)
    assert_numerically_equal(cohorts["weights"]["QB"], parent["season"]["benchmark_weights"])
    values = results["estimates"]["evolving"]
    counts = Counter(p["qb"] for p in current)
    if (
        [v["player_id"] for v in values] != sorted(counts)
        or len(current) != parent["season"]["plays"]
        or len({p["game_id"] for p in current}) != parent["season"]["games"]
    ):
        raise ValueError("parent/current population differs")
    for v in values:
        game_counts = Counter(p["game_id"] for p in current if p["qb"] == v["player_id"])
        if (
            v["opportunities"] != counts[v["player_id"]]
            or v["season"] != 2026
            or v["ranking_ready"] is not False
            or {g["game_id"]: g["opportunities"] for g in v["game_ledger"]} != game_counts
            or len(v["game_ledger"]) != len(game_counts)
        ):
            raise ValueError("parent player/game exposure differs")
    return {"parent": parent, "models": models, "rows": rows, "current": current, "values": values}


def run(raw, inputs, parent_store, plan, progress=lambda _: None, checkpoint=lambda *_: None):
    return experiment(
        load_context(raw, inputs, parent_store, plan, progress), plan, progress, checkpoint
    )


def replay_experiment(raw, inputs, parent_store, output, report_id, progress=lambda _: None):
    saved = json.loads(output.read(report_id, manifest=True))
    if (
        saved["experiment"] != "continuous-variance-recovery-v1"
        or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
        or saved["environment"]["numpy"] != np.__version__
        or saved["environment"]["scipy"] != scipy.__version__
        or saved["plan_sha256"] != sha256(json_bytes(saved["plan"]))
    ):
        raise ValueError("unsupported continuous replay environment/policy")
    models = json.loads(output.read(saved["objects"]["models"]))
    results = json.loads(output.read(saved["objects"]["predictions"]))
    actual, actual_models, actual_results = run(raw, inputs, parent_store, saved["plan"], progress)
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
    parser.add_argument("--parent-store", type=Path, default=Path("data/derived/multiseason"))
    parser.add_argument(
        "--output-store", type=Path, default=Path("data/derived/continuous-variance")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument(
        "--plan", type=Path, default=Path("config/continuous-variance-v1.json")
    )
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    stores = [SnapshotStore(p) for p in [args.raw_store, args.input_store, args.parent_store]]
    output = SnapshotStore(args.output_store)

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        if args.command == "build":
            revision = committed_revision()

            def checkpoint(scenario, trial):
                # Content-addressed checkpoints aid failure diagnosis; never reused as
                # input to a build or replay, which both recompute every requested draw.
                output.put(
                    json_bytes({"code_revision": revision, "scenario": scenario, "trial": trial})
                )

            report, models, results = run(
                *stores, json.loads(args.plan.read_text()), progress, checkpoint
            )
            rid, saved = save(output, report, models, results, code_revision=revision)
        else:
            rid = args.report_id
            saved = replay_experiment(*stores, output, rid, progress)
        print(
            json.dumps(
                {
                    "report_id": rid,
                    "fits": saved["fits"],
                    "calibration": saved["calibration"],
                    "season": saved["season"],
                    "ranking_ready": False,
                },
                indent=2,
            )
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        np.linalg.LinAlgError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Continuous recovery failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
