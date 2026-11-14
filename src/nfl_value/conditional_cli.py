"""Immutable square-root arithmetic controls and explicit gate verification."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from nfl_value.conditional_study import known_study, validate_known, validate_plan
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.ingest_cli import committed_revision


def save(store, study, plan, revision):
    validate_known(study, plan)
    manifest = {
        "experiment": "conditional-solver-controls-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "code_revision": revision,
        "environment": {"numpy": np.__version__, "scipy": scipy.__version__},
        "candidate_gates": study["candidate_gates"],
        "ranking_ready": False,
        "objects": {"study": store.put(json_bytes(study))},
    }
    return store.put(json_bytes(manifest), manifest=True)


def load(store, rid):
    manifest = json.loads(store.read(rid, manifest=True))
    validate_plan(manifest["plan"])
    if (
        manifest["experiment"] != "conditional-solver-controls-v1"
        or manifest["plan_sha256"] != sha256(json_bytes(manifest["plan"]))
        or manifest["environment"] != {"numpy": np.__version__, "scipy": scipy.__version__}
        or manifest["ranking_ready"] is not False
    ):
        raise ValueError("conditional controls environment, plan or admission differs")
    study = json.loads(store.read(manifest["objects"]["study"]))
    gates = validate_known(study, manifest["plan"])
    if gates != manifest["candidate_gates"]:
        raise ValueError("conditional controls manifest decision differs")
    return manifest, study


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-store", type=Path, default=Path("data/derived/conditional-controls")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("known")
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    output = SnapshotStore(args.output_store)
    progress = lambda message: print(message, file=sys.stderr, flush=True)
    try:
        if args.command == "known":
            revision = committed_revision()
            plan = json.loads(Path("config/conditional-solver-v1.json").read_text())
            study, timings = known_study(plan, progress)
            rid = save(output, study, plan, revision)
        else:
            manifest, expected = load(output, args.report_id)
            study, timings = known_study(manifest["plan"], progress)
            if json_bytes(study) != json_bytes(expected):
                raise ValueError("conditional controls do not reproduce")
            rid = args.report_id
        print(
            json.dumps(
                {
                    "report_id": rid,
                    "candidate_gates": study["candidate_gates"],
                    "timings": timings,
                    "ranking_ready": False,
                },
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Conditional study failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
