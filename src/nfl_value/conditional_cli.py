"""Immutable square-root arithmetic controls and explicit gate verification."""

import argparse
import json
from pathlib import Path
import sys
import platform

import numpy as np
import scipy

from nfl_value.conditional_study import known_study, validate_known, validate_plan
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.ingest_cli import committed_revision


def environment(plan):
    result = {"numpy": np.__version__, "scipy": scipy.__version__}
    if plan["plan_version"] >= 2:
        result.update(
            python=platform.python_version(), system=platform.system(), machine=platform.machine()
        )
        result["linear_algebra_build"] = {
            name: package.__config__.CONFIG.get("Build Dependencies", {})
            for name, package in (("numpy", np), ("scipy", scipy))
        }
    return result


def archive_inputs(plan, progress):
    from nfl_value.density_cli import load as load_density
    from nfl_value.reference_pilot import load_inputs

    root = Path("data/derived")
    _, density = load_density(SnapshotStore(root / "density-holdout"), plan["density_report"])
    trace = json.loads(
        SnapshotStore(root / "density-failure-trace").read(plan["trace_report"], manifest=True)
    )
    if (
        trace["parent_density_report"] != plan["density_report"]
        or trace["same_failure_reproduced"] is not True
    ):
        raise ValueError("archived failure trace provenance differs")
    stores = [SnapshotStore(Path("data/raw/source-snapshots"))] + [
        SnapshotStore(root / p)
        for p in ["offensive-inputs", "multiseason", "continuous-variance-diagnostic"]
    ]
    context, parent = load_inputs(*stores, density["primary_plan"], progress)
    return context, parent, density, trace


def run_archive(output, controls_store, control_id, revision, progress):
    from nfl_value.conditional_archive import archived_study

    certificate, controls = load(controls_store, control_id)
    plan = certificate["plan"]
    if certificate["candidate_gates"][plan["preferred_candidate"]] is not True:
        raise ValueError("preferred solver failed known-answer authorization")
    current, _ = known_study(plan)
    if json_bytes(current) != json_bytes(controls):
        raise ValueError("saved controls do not reproduce with the executing kernel/platform")
    context, parent, density, trace = archive_inputs(plan, progress)

    def checkpoint(case, record):
        output.put(json_bytes({"checkpoint": case, "record": record, "code_revision": revision}))

    result, timings = archived_study(
        context, parent, density, trace, controls, plan, progress, checkpoint
    )
    manifest = {
        "experiment": "conditional-solver-archive-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "code_revision": revision,
        "environment": environment(plan),
        "control_report": control_id,
        "control_source_revision": certificate["code_revision"],
        "objects": {"study": output.put(json_bytes(result))},
        "ranking_ready": False,
    }
    rid = output.put(json_bytes(manifest), manifest=True)
    return rid, manifest, result, timings


def save(store, study, plan, revision):
    validate_known(study, plan)
    manifest = {
        "experiment": "conditional-solver-controls-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "code_revision": revision,
        "environment": environment(plan),
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
        or manifest["environment"] != environment(manifest["plan"])
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
    parser.add_argument(
        "--controls-store", type=Path, default=Path("data/derived/conditional-controls")
    )
    parser.add_argument("--plan", type=Path, default=Path("config/conditional-solver-v2.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("known")
    sub.add_parser("replay").add_argument("report_id")
    sub.add_parser("archive").add_argument("control_report_id")
    sub.add_parser("replay-archive").add_argument("report_id")
    args = parser.parse_args(argv)
    output = SnapshotStore(args.output_store)
    progress = lambda message: print(message, file=sys.stderr, flush=True)
    try:
        if args.command in ("archive", "replay-archive"):
            controls_store = SnapshotStore(args.controls_store)
            if args.command == "archive":
                rid, _, study, timings = run_archive(
                    output, controls_store, args.control_report_id, committed_revision(), progress
                )
            else:
                expected = json.loads(output.read(args.report_id, manifest=True))
                validate_plan(expected["plan"])
                if (
                    expected["experiment"] != "conditional-solver-archive-v1"
                    or expected["plan_sha256"] != sha256(json_bytes(expected["plan"]))
                    or expected["ranking_ready"] is not False
                    or expected["environment"] != environment(expected["plan"])
                ):
                    raise ValueError("archive policy, environment or admission differs")
                # Verify saved raw bytes before rebuilding. The rebuilt manifest
                # binds exactly the original producing revision and dependencies.
                output.read(expected["objects"]["study"])
                rid, actual, study, timings = run_archive(
                    output,
                    controls_store,
                    expected["control_report"],
                    expected["code_revision"],
                    progress,
                )
                if rid != args.report_id or actual != expected:
                    raise ValueError("conditional archive does not reproduce")
            print(
                json.dumps(
                    {
                        "report_id": rid,
                        "timings": timings,
                        "failed_fit_replay": study["failed_fit_replay"]["status"],
                        "ranking_ready": False,
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "known":
            revision = committed_revision()
            plan = json.loads(args.plan.read_text())
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
