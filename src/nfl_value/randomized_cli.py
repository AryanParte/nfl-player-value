"""Reproducible known-answer randomized-reference study, offline by construction."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.randomized_controls import experiment, validate_plan, validate_result


def summary(result):
    output = deepcopy(result)
    for cases in [*output["selection"].values(), output["confirmation"]]:
        for case in cases:
            case.pop("trials")
    return output


def save(output, result, model_plan, revision):
    validate_result(result)
    manifest = dict(
        **summary(result),
        code_revision=revision,
        plan_sha256=sha256(json_bytes(result["plan"])),
        model_plan=model_plan,
        model_plan_sha256=sha256(json_bytes(model_plan)),
        environment=dict(numpy=np.__version__, scipy=scipy.__version__),
        objects=dict(study=output.put(json_bytes(result))),
    )
    rid = output.put(json_bytes(manifest), manifest=True)
    return rid, manifest


def load(output, rid):
    manifest = json.loads(output.read(rid, manifest=True))
    validate_plan(manifest["plan"])
    if (
        manifest["environment"] != dict(numpy=np.__version__, scipy=scipy.__version__)
        or manifest["plan_sha256"] != sha256(json_bytes(manifest["plan"]))
        or manifest["model_plan_sha256"] != sha256(json_bytes(manifest["model_plan"]))
    ):
        raise ValueError("control plan or environment mismatch")
    result = json.loads(output.read(manifest["objects"]["study"]))
    validate_result(result)
    if json_bytes(summary(result)) != json_bytes({k: manifest[k] for k in summary(result)}):
        raise ValueError("control manifest and experiment mismatch")
    return manifest, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-store", type=Path, default=Path("data/derived/randomized-controls")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument(
        "--plan", type=Path, default=Path("config/randomized-reference-v1.json")
    )
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    output = SnapshotStore(args.output_store)

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    try:
        if args.command == "build":
            revision = committed_revision()
            plan = json.loads(args.plan.read_text())
            model = json.loads(Path("config/continuous-variance-v1.json").read_text())

            def checkpoint(name, record):
                output.put(json_bytes(dict(code_revision=revision, checkpoint=name, record=record)))

            result = experiment(plan, model, progress, checkpoint)
            rid, manifest = save(output, result, model, revision)
        else:
            manifest, expected = load(output, args.report_id)
            actual = experiment(manifest["plan"], manifest["model_plan"], progress)
            if json_bytes(actual) != json_bytes(expected):
                raise ValueError("control study does not replay byte-for-byte")
            rid = args.report_id
        print(
            json.dumps(
                dict(
                    report_id=rid,
                    selected=manifest["selected"],
                    controls_passed=manifest["controls_passed"],
                    ranking_ready=False,
                ),
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Randomized-reference study failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
