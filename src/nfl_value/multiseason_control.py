"""Fresh synthetic variance-knowledge controls; never a production uncertainty fix."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.multiseason_math import contrast, design, variance_cells
from nfl_value.multiseason_simulation import simulate, summary
from nfl_value.qb_math import row_digest
from nfl_value.qb_recovery import prepare
from nfl_value.qb_recovery_cli import load_evidence
from nfl_value.source_audit import aware_time
from nfl_value.variance_mixture import integrate, interval, moments


def controls(prepared, contrasts, parent_plan, plan, progress=lambda _: None):
    if (
        set(plan)
        != {
            "plan_version",
            "source_report",
            "seed",
            "replicates",
            "scenario",
            "controls",
            "changes_real_model",
        }
        or type(plan["plan_version"]) is not int
        or plan["plan_version"] != 1
        or type(plan["seed"]) is not int
        or not 1 <= plan["seed"] < 2**32
        or plan["seed"] == parent_plan["simulation_seed"]
        or type(plan["replicates"]) is not int
        or not 2 <= plan["replicates"] <= 1024
        or plan["scenario"] != "continuous_hierarchy"
        or plan["controls"] != ["integrated", "known_ratios", "known_ratios_shared_innovation"]
        or plan["changes_real_model"] is not False
    ):
        raise ValueError("invalid fresh variance-control plan")
    simulation_plan = {
        **parent_plan,
        "simulation_seed": plan["seed"],
        "simulation_replicates": plan["replicates"],
    }
    beta, y = simulate(prepared, simulation_plan, plan["scenario"])
    truth = contrasts @ beta
    known = {
        g: parent_plan["stress_noise_sd"] ** 2 / s**2
        for g, s in parent_plan["stress_effect_sd"].items()
    }
    reports, coverage = {}, {}
    for name in plan["controls"]:
        progress("Fresh variance control: " + name)
        if name == "integrated":
            cells = variance_cells(prepared, "evolving", parent_plan)
        else:
            precision = {**known}
            if name == "known_ratios_shared_innovation":
                precision["innovation"] = precision["qb"]
            penalty = np.array(
                [
                    0.0 if n.startswith("context/") else precision[n.split("/")[0]]
                    for n in prepared.names
                ]
            )
            cells = [{"penalty": penalty, "game_precision": precision["game"], "log_prior": 0.0}]
        result = integrate(
            prepared,
            y,
            contrasts,
            cells,
            shape=parent_plan["noise_prior_shape"],
            scale=parent_plan["noise_prior_scale"],
            progress=progress,
        )
        point, _ = moments(result)
        low, high = interval(result, iterations=parent_plan["quantile_iterations"])
        coverage[name] = ((low <= truth) & (truth <= high)).mean(axis=0)
        reports[name] = summary(truth, point, low, high)
    for name in plan["controls"][1:]:
        difference = coverage[name] - coverage["integrated"]
        reports[name]["paired_coverage_change_vs_integrated"] = {
            "mean": float(difference.mean()),
            "monte_carlo_se": float(difference.std(ddof=1) / np.sqrt(len(difference))),
        }
    return {
        "experiment": "multiseason-known-ratios-control-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)).hexdigest(),
        "source_plan_sha256": sha256(json_bytes(parent_plan)).hexdigest(),
        "synthetic_responses_sha256": sha256(y.astype("<f8").tobytes()).hexdigest(),
        "known_precision_ratios": known,
        "results": reports,
        "ranking_ready": False,
        "scope": "Fresh failure-analysis draws. Known synthetic ratios are unavailable in NFL data; no real model, intervals, eligibility or admission changes.",
    }


def run(raw, inputs, parent_store, plan, progress=lambda _: None):
    parent = json.loads(parent_store.read(plan["source_report"], manifest=True))
    if (
        parent["experiment"] != "multiseason-variance-recovery-v1"
        or parent["ranking_ready"] is not False
    ):
        raise ValueError("known original multi-season research report required")
    models = json.loads(parent_store.read(parent["objects"]["models"]))
    results = json.loads(parent_store.read(parent["objects"]["predictions"]))
    rows = []
    for year in parent["plan"]["seasons"]:
        refs = parent["input_reports"]["seasons"][str(year)]
        ledger, evidence, _, _ = load_evidence(
            raw,
            inputs,
            refs["offensive"],
            refs["weekly_rosters"],
            cutoff=aware_time(parent["evidence_cutoff"]),
            legacy=year == 2024,
        )
        rows.extend(prepare(ledger, evidence, season=year, low_week=1, high_week=18)[0])
    rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
    weights = parent["season"]["benchmark_weights"]["first_unit"]
    prepared, _ = design(
        rows, "evolving", scoring_season=parent["plan"]["scoring_season"], extra_qbs=weights
    )
    original = models["evolving"]
    if prepared.names != original["names"] or row_digest(rows) != original["training_rows_sha256"]:
        raise ValueError("control must retain the exact original design and row identities")
    values = results["estimates"]["evolving"]
    contrasts = np.array(
        [
            contrast(
                prepared.names,
                v["player_id"],
                v["opportunities"],
                weights,
                season=parent["plan"]["scoring_season"],
            )
            for v in values
        ]
    )
    return controls(prepared, contrasts, parent["plan"], plan, progress)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", type=Path, default=Path("data/raw/source-snapshots"))
    parser.add_argument("--input-store", type=Path, default=Path("data/derived/offensive-inputs"))
    parser.add_argument("--parent-store", type=Path, default=Path("data/derived/multiseason"))
    parser.add_argument(
        "--output-store", type=Path, default=Path("data/derived/multiseason-control")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument(
        "--plan", type=Path, default=Path("config/multiseason-control-v1.json")
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
            report = run(*stores, json.loads(args.plan.read_text()), progress)
            rid, saved = save(output, report, {}, {}, code_revision=revision)
        else:
            rid = args.report_id
            saved = json.loads(output.read(rid, manifest=True))
            if (
                saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
                or saved["environment"]["numpy"] != np.__version__
            ):
                raise ValueError("unsupported control replay environment/policy")
            import scipy

            if saved["environment"]["scipy"] != scipy.__version__:
                raise ValueError("control replay requires recorded SciPy")
            for h in saved["objects"].values():
                if json.loads(output.read(h)) != {}:
                    raise ValueError("unexpected control artifact contents")
            expected = {
                k: v
                for k, v in saved.items()
                if k not in {"code_revision", "environment", "replay_tolerance", "objects"}
            }
            actual = run(*stores, saved["plan"], progress)
            assert_numerically_equal(actual, expected)
        print(
            json.dumps(
                {"report_id": rid, "results": saved["results"], "ranking_ready": False}, indent=2
            )
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Fresh variance control failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
