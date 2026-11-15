"""Frozen density comparison, known-answer confirmation and gated archived pilot."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import scipy

from nfl_value.baseline_cli import save as save_pilot
from nfl_value.density_holdout import (
    fit_pair,
    holdout,
    known_experiment,
    paired_summary,
    validate_density,
    validate_known,
    validate_plan,
)
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.ingest_cli import committed_revision
from nfl_value.multiseason_math import GROUPS
from nfl_value.reference_pilot import (
    CASES,
    experiment as pilot_experiment,
    load_inputs,
    prepare_case,
)
from nfl_value.replicated_reference import reference_integral
from nfl_value.variance_reference import BoundedTarget


def summary(result):
    out = deepcopy(result)
    cases = out["cases"].values() if isinstance(out["cases"], dict) else out["cases"]
    for c in cases:
        c.pop("density", None)
        c.pop("coverage", None)
    return out


def save(output, result, model_plan, revision):
    manifest = dict(
        **summary(result),
        code_revision=revision,
        model_plan=model_plan,
        plan_sha256=sha256(json_bytes(result["plan"])),
        model_plan_sha256=sha256(json_bytes(model_plan)),
        environment=dict(numpy=np.__version__, scipy=scipy.__version__),
        objects=dict(study=output.put(json_bytes(result))),
    )
    return output.put(json_bytes(manifest), manifest=True), manifest


def load(output, rid):
    m = json.loads(output.read(rid, manifest=True))
    validate_plan(m["plan"])
    if (
        m["plan_sha256"] != sha256(json_bytes(m["plan"]))
        or m["model_plan_sha256"] != sha256(json_bytes(m["model_plan"]))
        or m["environment"] != dict(numpy=np.__version__, scipy=scipy.__version__)
    ):
        raise ValueError("density plan or environment changed")
    result = json.loads(output.read(m["objects"]["study"]))
    if json_bytes(summary(result)) != json_bytes({k: m[k] for k in summary(result)}):
        raise ValueError("density manifest and study disagree")
    if m["experiment"] == "density-holdout-controls-v1":
        validate_known(result, m["model_plan"])
    elif m["experiment"] == "archived-density-holdout-v1":
        validate_archived(result)
    else:
        raise ValueError("unsupported density experiment")
    return m, result


def authorize(controls, rid):
    m, result = load(controls, rid)
    if m["experiment"] != "density-holdout-controls-v1" or result["controls_passed"] is not True:
        raise ValueError("complete known-answer controls required before CAVAA reference")
    return m, result


def archived_density(
    stores, plan, primary_plan, progress=lambda _: None, checkpoint=lambda *_: None
):
    validate_plan(plan)
    context, parent = load_inputs(*stores, primary_plan, progress)
    start = perf_counter()
    cases = {}
    timings = {}
    for index, name in enumerate(CASES):
        begin = perf_counter()
        records = []
        d, y, _, variant, _ = prepare_case(context, parent["plan"], name)
        target = BoundedTarget(
            d,
            y,
            [g for g in GROUPS[variant] if g != "innovation"] + ["game"],
            context["parent"]["plan"],
            parent["plan"],
            evaluation_limit=plan["maximum_target_evaluations_per_case"],
            deadline=min(start + 3600, begin + plan["maximum_seconds_per_case"]),
        )
        for trial in range(plan["archived_density_trials"]):
            if perf_counter() >= target.deadline or target.evaluations >= target.evaluation_limit:
                record = dict(status="unattempted", error="declared case/pilot budget exhausted")
            else:
                record = dict(status="failed")
                try:
                    pairs, gain = fit_pair(target, plan, 100 + index, trial)
                    record.update(
                        training_log_score_gain=gain,
                        geometries={label: p.diagnostics for p, label in pairs},
                    )
                    record.update(
                        status="complete", **holdout(target, pairs, plan, 100 + index, trial)
                    )
                except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    record.update(status="failed", error=str(exc))
            records.append(dict(trial=trial, **record))
            progress(f"{name} density pair {trial + 1}: {record['status']}")
        case = dict(
            target=100 + index,
            density=records,
            density_summary=paired_summary(records),
            target_evaluations=target.evaluations,
            response_sha256=sha256(y.astype("<f8").tobytes()),
        )
        cases[name] = case
        timings[name] = perf_counter() - begin
        checkpoint(name, case)
        progress(f"{name}: {case['density_summary']}; seconds={timings[name]:.1f}")
    report = dict(
        experiment="archived-density-holdout-v1",
        plan=plan,
        primary_plan=primary_plan,
        primary_plan_sha256=sha256(json_bytes(primary_plan)),
        parent_report=primary_plan["parent_report"],
        parent_code_revision=parent["code_revision"],
        source_provenance=parent["source_provenance"],
        input_reports=parent["input_reports"],
        evidence_cutoff=parent["evidence_cutoff"],
        cases=cases,
        nfl_data_used=True,
        calibration_completed=False,
        ranking_ready=False,
        decision="Density-only diagnosis. No player functional, numerical authorization or calibration pass.",
    )
    validate_archived(report)
    return report, parent["plan"], timings


def validate_archived(result):
    p = result["plan"]
    validate_plan(p)
    if (
        result["experiment"] != "archived-density-holdout-v1"
        or set(result["cases"]) != set(CASES)
        or result["calibration_completed"] is not False
        or result["ranking_ready"] is not False
        or result["nfl_data_used"] is not True
        or result["primary_plan_sha256"] != sha256(json_bytes(result["primary_plan"]))
    ):
        raise ValueError("invalid archived density scope")
    for index, name in enumerate(CASES):
        c = result["cases"][name]
        if c["target"] != 100 + index:
            raise ValueError("changed archived target identity")
        if (
            type(c["target_evaluations"]) is not int
            or not 0 <= c["target_evaluations"] <= p["maximum_target_evaluations_per_case"]
        ):
            raise ValueError("invalid archived work accounting")
        validate_density(c["density"], p["archived_density_trials"])
        if json_bytes(c["density_summary"]) != json_bytes(paired_summary(c["density"])):
            raise ValueError("archived density summary does not reproduce")
        for trial, r in enumerate(c["density"]):
            if "geometries" in r and any(
                d["density_pilot_entropy"] != [p["base_seed"], 10, 100 + index, trial]
                for d in r["geometries"].values()
            ):
                raise ValueError("archived density entropy changed")


def validate_model_policy(control_plan, archived_plan):
    # These exact archived runner settings do not enter fit_proposal's returned
    # geometry or any known-target functional. Bind them rather than ignoring
    # arbitrary extras. Every actual model/numerical parameter must still match.
    extensions = dict(diagnostic_trial_cap=8, numerical_proposal="stratified_student_t5_v1")
    if set(extensions) & set(control_plan) or json_bytes(archived_plan) != json_bytes(
        {**control_plan, **extensions}
    ):
        raise ValueError("coverage and archived model policies differ")


def pilot(stores, controls, rid, primary_plan, progress=lambda _: None, checkpoint=lambda *_: None):
    certificate, _ = authorize(controls, rid)
    plan = certificate["plan"]
    context, parent = load_inputs(*stores, primary_plan, progress)
    validate_model_policy(certificate["model_plan"], parent["plan"])

    def reference(name, target, contrasts, summaries, progress):
        index = 100 + CASES.index(name)
        pairs, _ = fit_pair(target, plan, index, 0)
        return reference_integral(
            target,
            contrasts,
            summaries,
            plan,
            "stabilized-mixture",
            index,
            progress,
            sampling=pairs[1][0],
        )

    report, models, outputs, timings = pilot_experiment(
        context, parent, primary_plan, progress, checkpoint, reference_evaluator=reference
    )
    report.update(
        experiment="stabilized-reference-pilot-v1",
        primary_plan=primary_plan,
        primary_plan_sha256=sha256(json_bytes(primary_plan)),
        plan=plan,
        plan_sha256=sha256(json_bytes(plan)),
        control_report_id=rid,
        control_source_revision=certificate["code_revision"],
        control_study_sha256=certificate["objects"]["study"],
    )
    return report, models, outputs, timings


def validate_pilot_manifest(raw):
    validate_plan(raw["plan"])
    if (
        raw["experiment"] != "stabilized-reference-pilot-v1"
        or raw["plan_sha256"] != sha256(json_bytes(raw["plan"]))
        or raw["primary_plan_sha256"] != sha256(json_bytes(raw["primary_plan"]))
        or raw["environment"]["numpy"] != np.__version__
        or raw["environment"]["scipy"] != scipy.__version__
        or raw["calibration_completed"] is not False
        or raw["ranking_ready"] is not False
    ):
        raise ValueError("pilot policy, environment or admission metadata changed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [
        ("raw-store", "data/raw/source-snapshots"),
        ("input-store", "data/derived/offensive-inputs"),
        ("multiseason-store", "data/derived/multiseason"),
        ("previous-store", "data/derived/continuous-variance-diagnostic"),
        ("output-store", "data/derived/density-holdout"),
        ("controls-store", "data/derived/density-controls"),
    ]:
        parser.add_argument("--" + name, type=Path, default=Path(default))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("known")
    sub.add_parser("density")
    sub.add_parser("pilot").add_argument("control_report_id")
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)

    def progress(s):
        print(s, file=sys.stderr, flush=True)

    try:
        output = SnapshotStore(args.output_store)
        controls = SnapshotStore(args.controls_store)
        stores = [
            SnapshotStore(p)
            for p in [args.raw_store, args.input_store, args.multiseason_store, args.previous_store]
        ]
        timings = {}
        if args.command == "replay":
            raw = json.loads(output.read(args.report_id, manifest=True))
            if raw["experiment"] == "stabilized-reference-pilot-v1":
                validate_pilot_manifest(raw)
                actual, models, predictions, timings = pilot(
                    stores, controls, raw["control_report_id"], raw["primary_plan"], progress
                )
                expected = {
                    k: v
                    for k, v in raw.items()
                    if k not in {"objects", "environment", "code_revision", "replay_tolerance"}
                }
                if (
                    json_bytes(actual) != json_bytes(expected)
                    or json_bytes(models) != output.read(raw["objects"]["models"])
                    or json_bytes(predictions) != output.read(raw["objects"]["predictions"])
                ):
                    raise ValueError("pilot replay differs")
            else:
                saved, expected = load(output, args.report_id)
                if saved["experiment"] == "density-holdout-controls-v1":
                    actual = known_experiment(saved["plan"], saved["model_plan"], progress)
                else:
                    actual, _, timings = archived_density(
                        stores, saved["plan"], saved["primary_plan"], progress
                    )
                if json_bytes(actual) != json_bytes(expected):
                    raise ValueError("density study replay differs")
            rid = args.report_id
        else:
            revision = committed_revision()
            plan = json.loads(Path("config/density-holdout-v2.json").read_text())
            validate_plan(plan)
            primary_plan = json.loads(Path(plan["parent_plan"]).read_text())

            def checkpoint(name, result):
                output.put(json_bytes(dict(code_revision=revision, checkpoint=name, record=result)))

            if args.command == "known":
                model_plan = json.loads(Path("config/continuous-variance-v1.json").read_text())
                result = known_experiment(plan, model_plan, progress, checkpoint)
                validate_known(result, model_plan)
                rid, _ = save(output, result, model_plan, revision)
            elif args.command == "density":
                result, model_plan, timings = archived_density(
                    stores, plan, primary_plan, progress, checkpoint
                )
                rid, _ = save(output, result, model_plan, revision)
            else:
                result, models, predictions, timings = pilot(
                    stores, controls, args.control_report_id, primary_plan, progress, checkpoint
                )
                rid, _ = save_pilot(output, result, models, predictions, code_revision=revision)
        print(json.dumps(dict(report_id=rid, wall_seconds=timings, ranking_ready=False), indent=2))
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Density study failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
