"""Archived model pilot authorized only by a replay-verified numerical control study."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from nfl_value.baseline_cli import save
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.randomized_cli import load as load_controls
from nfl_value.reference_pilot import CASES, experiment, load_inputs
from nfl_value.replicated_reference import reference_integral


def authorize(controls, control_id):
    manifest, result = load_controls(controls, control_id)
    if result["controls_passed"] is not True or result["selected"] is None:
        raise ValueError(
            "known-answer selection and fresh confirmation must pass before NFL inputs"
        )
    return manifest, result


def run(
    stores, controls, control_id, primary_plan, progress=lambda _: None, checkpoint=lambda *_: None
):
    certificate, result = authorize(controls, control_id)
    plan = certificate["plan"]
    context, parent = load_inputs(*stores, primary_plan, progress)

    def reference(name, target, contrasts, summaries, progress):
        return reference_integral(
            target, contrasts, summaries, plan, result["selected"], CASES.index(name), progress
        )

    report, models, outputs, timings = experiment(
        context, parent, primary_plan, progress, checkpoint, reference_evaluator=reference
    )
    report.update(
        experiment="replicated-reference-pilot-v1",
        primary_plan=primary_plan,
        primary_plan_sha256=sha256(json_bytes(primary_plan)),
        plan=plan,
        plan_sha256=sha256(json_bytes(plan)),
        control_report_id=control_id,
        control_source_revision=certificate["code_revision"],
        control_study_sha256=certificate["objects"]["study"],
        reference_method=result["selected"],
    )
    return report, models, outputs, timings


def replay(stores, controls, output, report_id, progress=lambda _: None):
    saved = json.loads(output.read(report_id, manifest=True))
    if (
        saved["experiment"] != "replicated-reference-pilot-v1"
        or saved["plan_sha256"] != sha256(json_bytes(saved["plan"]))
        or saved["primary_plan_sha256"] != sha256(json_bytes(saved["primary_plan"]))
        or saved["environment"]["numpy"] != np.__version__
        or saved["environment"]["scipy"] != scipy.__version__
    ):
        raise ValueError("unsupported randomized pilot policy or environment")
    expected_models = output.read(saved["objects"]["models"])
    expected_predictions = output.read(saved["objects"]["predictions"])
    actual, models, predictions, timings = run(
        stores, controls, saved["control_report_id"], saved["primary_plan"], progress
    )
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"objects", "environment", "code_revision", "replay_tolerance"}
    }
    if (
        json_bytes(actual) != json_bytes(expected)
        or json_bytes(models) != expected_models
        or json_bytes(predictions) != expected_predictions
    ):
        raise ValueError("randomized pilot does not reproduce byte-for-byte")
    return saved, timings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, default in [
        ("raw-store", "data/raw/source-snapshots"),
        ("input-store", "data/derived/offensive-inputs"),
        ("multiseason-store", "data/derived/multiseason"),
        ("previous-store", "data/derived/continuous-variance-diagnostic"),
        ("controls-store", "data/derived/randomized-controls-adaptive"),
        ("output-store", "data/derived/randomized-reference"),
    ]:
        parser.add_argument("--" + flag, type=Path, default=Path(default))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument("control_report_id")
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        controls = SnapshotStore(args.controls_store)
        output = SnapshotStore(args.output_store)
        stores = [
            SnapshotStore(p)
            for p in [args.raw_store, args.input_store, args.multiseason_store, args.previous_store]
        ]
        if args.command == "build":
            revision = committed_revision()
            certificate, _ = authorize(controls, args.control_report_id)
            primary_plan = json.loads(Path(certificate["plan"]["parent_plan"]).read_text())

            def checkpoint(name, r):
                output.put(json_bytes(dict(code_revision=revision, case=name, diagnostics=r)))

            report, models, outputs, timings = run(
                stores, controls, args.control_report_id, primary_plan, progress, checkpoint
            )
            rid, saved = save(output, report, models, outputs, code_revision=revision)
        else:
            rid = args.report_id
            saved, timings = replay(stores, controls, output, rid, progress)
        print(
            json.dumps(
                dict(
                    report_id=rid,
                    numerical_pilot_passed=saved["numerical_pilot_passed"],
                    cases={
                        k: {
                            j: v
                            for j, v in r.items()
                            if j in {"status", "error", "target_evaluations", "failed_stage"}
                        }
                        for k, r in saved["cases"].items()
                    },
                    wall_seconds=timings,
                    ranking_ready=False,
                ),
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Randomized pilot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
