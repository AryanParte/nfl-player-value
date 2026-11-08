"""Diagnostic oracle control. Simulation truth must never set real-player intervals."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore
from nfl_value.qb_math import RestrictedLikelihood, contrast, design, fit
from nfl_value.qb_recovery import prepare
from nfl_value.qb_recovery_cli import load_evidence, replay_experiment
from nfl_value.qb_simulation import Z95, simulate, summarize
from nfl_value.source_audit import aware_time


def validate_control(control):
    if (
        set(control)
        != {"control_version", "seed", "replicates", "scenario", "estimators", "purpose"}
        or type(control["control_version"]) is not int
        or control["control_version"] != 1
    ):
        raise ValueError("invalid variance control version")
    if (
        type(control["seed"]) is not int
        or control["seed"] < 0
        or type(control["replicates"]) is not int
        or not 2 <= control["replicates"] <= 1024
    ):
        raise ValueError("invalid variance control seed/replicates")
    if (
        control["scenario"] != "matched_hierarchy"
        or control["estimators"] != ["empirical_bayes", "known_variances"]
        or control["purpose"] != "diagnose conditional hyperparameter uncertainty; never admission"
    ):
        raise ValueError("unreviewed variance control policy")


def oracle(prepared, y, simulation_plan):
    """Known σ² and τ² in a synthetic hierarchy, including uncertain fixed context."""
    variance = simulation_plan["simulation_noise_sd"] ** 2
    ratios = [variance / simulation_plan["simulation_effect_sd"][g] ** 2 for g in prepared.groups]
    _, _, mean, estimated_scale_covariance, estimated_scale = RestrictedLikelihood(
        prepared, y
    ).solve(np.log(ratios))
    return mean, estimated_scale_covariance * variance / estimated_scale


def control_experiment(prepared, contrasts, plan, control, *, progress=lambda message: None):
    validate_control(control)
    simulation_plan = {
        **plan,
        "simulation_seed": control["seed"],
        "simulation_replicates": control["replicates"],
    }
    errors = {name: [] for name in control["estimators"]}
    widths = {name: [] for name in control["estimators"]}
    for i in range(control["replicates"]):
        truth, y = simulate(prepared, simulation_plan, scenario="matched_hierarchy", replicate=i)
        model, covariance = fit(prepared, y, plan)
        fitted = {
            "empirical_bayes": (np.array(model["coefficients"]), covariance),
            "known_variances": oracle(prepared, y, simulation_plan),
        }
        for name, (mean, cov) in fitted.items():
            errors[name].append(contrasts @ (mean - truth))
            v = np.einsum("ij,jk,ik->i", contrasts, cov, contrasts)
            if not np.isfinite(v).all() or np.min(v) < -1e-9:
                raise ValueError("invalid diagnostic contrast variance")
            widths[name].append(2 * Z95 * np.sqrt(np.maximum(v, 0)))
        if (i + 1) % 8 == 0:
            progress(f"Variance control: {i + 1}/{control['replicates']}")
    return {
        name: summarize(errors[name], widths[name], replicates=control["replicates"], failures=[])
        for name in control["estimators"]
    }


def run(raw, inputs, output, *, parent_id, control, progress=lambda message: None):
    # Replay all parent sources, folds and simulations before trusting its design.
    parent = replay_experiment(raw, inputs, output, parent_id, progress=progress)
    plan = parent["plan"]
    ids = parent["input_reports"]
    ledger, evidence, _, _ = load_evidence(
        raw,
        inputs,
        ids["current"],
        ids["current_roster"],
        cutoff=aware_time(parent["evidence_cutoff"]),
    )
    rows, audit = prepare(ledger, evidence, season=plan["current_season"], low_week=1, high_week=18)
    assert_numerically_equal(audit, parent["cohort_audits"]["current"])
    weights = parent["season"]["benchmark_weights"]["first_unit"]
    prepared = design(rows, "joint", extra_qbs=weights)
    results = json.loads(output.read(parent["objects"]["predictions"]))["player_contrasts"]
    contrasts = np.array(
        [contrast(prepared.names, p["player_id"], p["opportunities"], weights) for p in results]
    )
    scores = control_experiment(prepared, contrasts, plan, control, progress=progress)
    return {
        "experiment": "qb-variance-oracle-control-v1",
        "parent_report": parent_id,
        "control_plan": control,
        "player_order": [p["player_id"] for p in results],
        "results": scores,
        "ranking_ready": False,
        "purpose": control["purpose"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-report", required=True)
    parser.add_argument("--plan", type=Path, default=Path("config/qb-variance-control-v1.json"))
    parser.add_argument("--replay", help="Saved control report; no source downloads")
    args = parser.parse_args(argv)
    raw = SnapshotStore(Path("data/raw/source-snapshots"))
    inputs = SnapshotStore(Path("data/derived/offensive-inputs"))
    output = SnapshotStore(Path("data/derived/qb-recovery"))
    progress = lambda message: print(message, file=sys.stderr, flush=True)
    try:
        if args.replay:
            saved = json.loads(output.read(args.replay, manifest=True))
            if (
                saved["experiment"] != "qb-variance-oracle-control-v1"
                or saved["parent_report"] != args.parent_report
            ):
                raise ValueError("variance control parent/policy mismatch")
            if (
                saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
                or saved["environment"]["numpy"] != np.__version__
                or saved["environment"]["scipy"] != scipy.__version__
            ):
                raise ValueError("variance control environment/tolerance mismatch")
            report = run(
                raw,
                inputs,
                output,
                parent_id=args.parent_report,
                control=saved["control_plan"],
                progress=progress,
            )
            expected = {
                k: v
                for k, v in saved.items()
                if k not in {"code_revision", "environment", "objects", "replay_tolerance"}
            }
            assert_numerically_equal(report, expected)
            for obj in saved["objects"].values():
                if json.loads(output.read(obj)) != {}:
                    raise ValueError("unexpected diagnostic model/prediction object")
            rid = args.replay
        else:
            revision = committed_revision()
            report = run(
                raw,
                inputs,
                output,
                parent_id=args.parent_report,
                control=json.loads(args.plan.read_text()),
                progress=progress,
            )
            rid, saved = save(output, report, {}, {}, code_revision=revision)
        print(json.dumps({"report_id": rid, **report}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Variance control failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
