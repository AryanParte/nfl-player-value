"""Build or independently replay the bounded offline numerical-reference pilot."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.reference_pilot import experiment, load_inputs


def run(stores, plan, progress=lambda _: None, checkpoint=lambda *_: None):
    context, parent = load_inputs(*stores, plan, progress)
    return experiment(context, parent, plan, progress, checkpoint)


def replay_pilot(stores, output, rid, progress=lambda _: None):
    saved = json.loads(output.read(rid, manifest=True))
    if (
        saved["experiment"] != "variance-reference-pilot-v1"
        or saved["plan_sha256"] != sha256(json_bytes(saved["plan"]))
        or saved["environment"]["numpy"] != np.__version__
        or saved["environment"]["scipy"] != scipy.__version__
        or saved["replay_tolerance"] != {"absolute": 1e-9, "relative": 1e-8}
    ):
        raise ValueError("unsupported pilot replay policy/environment")
    expected_models = json.loads(output.read(saved["objects"]["models"]))
    expected_results = json.loads(output.read(saved["objects"]["predictions"]))
    actual, models, results, timings = run(stores, saved["plan"], progress)
    expected = {
        k: v
        for k, v in saved.items()
        if k not in {"objects", "environment", "code_revision", "replay_tolerance"}
    }
    assert_numerically_equal(actual, expected)
    assert_numerically_equal(models, expected_models)
    assert_numerically_equal(results, expected_results)
    return saved, timings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, default in [
        ("raw-store", "data/raw/source-snapshots"),
        ("input-store", "data/derived/offensive-inputs"),
        ("multiseason-store", "data/derived/multiseason"),
        ("previous-store", "data/derived/continuous-variance-diagnostic"),
        ("output-store", "data/derived/variance-reference"),
    ]:
        parser.add_argument("--" + flag, type=Path, default=Path(default))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument(
        "--plan", type=Path, default=Path("config/variance-reference-smooth-v1.json")
    )
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    stores = [
        SnapshotStore(p)
        for p in [args.raw_store, args.input_store, args.multiseason_store, args.previous_store]
    ]
    output = SnapshotStore(args.output_store)

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        if args.command == "build":
            revision = committed_revision()

            def checkpoint(name, result):
                output.put(json_bytes(dict(code_revision=revision, case=name, diagnostics=result)))

            report, models, results, timings = run(
                stores, json.loads(args.plan.read_text()), progress, checkpoint
            )
            rid, saved = save(output, report, models, results, code_revision=revision)
        else:
            rid = args.report_id
            saved, timings = replay_pilot(stores, output, rid, progress)
        print(
            json.dumps(
                dict(
                    report_id=rid,
                    numerical_pilot_passed=saved["numerical_pilot_passed"],
                    cases={
                        name: {
                            k: v
                            for k, v in r.items()
                            if k in {"status", "error", "target_evaluations", "failed_stage"}
                        }
                        for name, r in saved["cases"].items()
                    },
                    wall_seconds=timings,
                    ranking_ready=False,
                ),
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Reference pilot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
