"""Frozen known-answer coverage and repaired-target functional comparison."""

import json
from pathlib import Path
from time import perf_counter

import numpy as np

from nfl_value.conditional_archive import SquareRootTarget
from nfl_value.conditional_cli import archive_inputs, environment, load as load_conditional
from nfl_value.conditional_study import known_study
from nfl_value.density_cli import load as load_density, validate_pilot_manifest
from nfl_value.density_holdout import coverage_summary, known_target, known_truth_bytes
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.multiseason_math import GROUPS
from nfl_value.randomized_controls import assess_trial
from nfl_value.reference_pilot import CASES, prepare_case
from nfl_value.replicated_reference import (
    conditional_integrand,
    diagnose_reference,
    summarize_integrals,
)
from nfl_value.two_level_reference import combine, integrate, restore_proposal, sampling_hash
from nfl_value.variance_reference import BudgetExceeded


PLAN_HASH = "08212be5992c526863cb10fde04d80c5a8fc500acb6aa0cfd83edf080b430f10"


def validate_plan(plan):
    if sha256(json_bytes(plan)) != PLAN_HASH:
        raise ValueError("repaired functional study differs from frozen design")


def kernel_hash():
    # Bind the whole statistical implementation, including imported helpers.
    root = Path(__file__).parent
    return sha256(json_bytes({p.name: sha256(p.read_bytes()) for p in sorted(root.glob("*.py"))}))


def store(name):
    return SnapshotStore(Path("data/derived") / name)


def known_parents(plan):
    validate_plan(plan)
    m, density = load_density(store("density-controls"), plan["density_controls"])
    if density["controls_passed"] is not True:
        raise ValueError("parent known coverage failed")
    return m, density


def known(plan, progress=lambda _: None, checkpoint=lambda *_: None):
    certificate, density = known_parents(plan)
    cases, timings = [], {}
    for index in range(5):
        begin = perf_counter()
        geometry = density["cases"][index]["density"][0]["geometries"]["stabilized-mixture"]
        target = known_target(index, certificate["model_plan"])
        sampling = restore_proposal(geometry, target.plan)
        truth = json.loads(known_truth_bytes(index))
        fine = target.integrand({k: np.asarray(v) for k, v in truth.items()})

        def coarse(points, logq):
            return fine(points, logq) * (
                1 + plan["known_surrogate_amplitude"] * np.sin(points.sum(axis=1))[:, None]
            )

        records = []
        for trial in range(plan["coverage_trials"]):
            entropy = [plan["base_seed"], 0, index, trial]
            record = dict(trial=trial, entropy=entropy, status="failed")
            try:
                total, base, correction = integrate(
                    fine,
                    coarse,
                    sampling,
                    entropy=entropy,
                    replicates=plan["replicates"],
                    nodes=plan["nodes_per_replicate"],
                    correction_nodes=plan["correction_nodes_per_replicate"],
                )
                record.update(coarse=base.tolist(), correction=correction.tolist())
                record.update(**assess_trial(total, plan))
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                record["error"] = str(exc)
            records.append(record)
            if (trial + 1) % 128 == 0:
                progress(f"Known {index}: {trial + 1}/{plan['coverage_trials']}")
        decision = coverage_summary(records, plan)
        cases.append(
            dict(
                target=index,
                truth=truth,
                geometry_sha256=sha256(json_bytes(geometry)),
                sampling_sha256=sampling_hash(sampling),
                records=records,
                decision=decision,
            )
        )
        timings[str(index)] = perf_counter() - begin
        checkpoint(str(index), cases[-1])
        progress(
            f"Known {index}: passed={decision['passed']}; coverage={decision['simultaneous_coverage']}"
        )
    result = dict(
        experiment="repaired-functional-controls-v1",
        plan=plan,
        cases=cases,
        controls_passed=all(c["decision"]["passed"] for c in cases),
        nfl_data_used=False,
        calibration_completed=False,
        ranking_ready=False,
    )
    return result, timings


def validate_known(result):
    plan = result["plan"]
    certificate, density = known_parents(plan)
    if (
        result["experiment"] != "repaired-functional-controls-v1"
        or result["nfl_data_used"] is not False
        or result["ranking_ready"] is not False
        or result["calibration_completed"] is not False
        or [c["target"] for c in result["cases"]] != list(range(5))
    ):
        raise ValueError("invalid known-answer scope or complete case denominator")
    for index, case in enumerate(result["cases"]):
        geometry = density["cases"][index]["density"][0]["geometries"]["stabilized-mixture"]
        sampling = restore_proposal(geometry, known_target(index, certificate["model_plan"]).plan)
        if (
            json_bytes(case["truth"]) != known_truth_bytes(index)
            or case["geometry_sha256"] != sha256(json_bytes(geometry))
            or case["sampling_sha256"] != sampling_hash(sampling)
            or [r["trial"] for r in case["records"]] != list(range(plan["coverage_trials"]))
        ):
            raise ValueError("known truth, geometry or trial denominator differs")
        for r in case["records"]:
            if r["entropy"] != [plan["base_seed"], 0, index, r["trial"]]:
                raise ValueError("known independent entropy differs")
            if r["status"] == "complete":
                total = combine(r["coarse"], r["correction"])
                if total.shape != (plan["replicates"], 9):
                    raise ValueError("known replicate shape differs")
                actual = assess_trial(total, plan)
                if json_bytes(actual) != json_bytes({k: r[k] for k in actual}):
                    raise ValueError("known numerical decisions do not reproduce")
            elif r["status"] != "failed" or not r.get("error"):
                raise ValueError("unexplained known failure")
        if json_bytes(case["decision"]) != json_bytes(coverage_summary(case["records"], plan)):
            raise ValueError("known coverage decision does not reproduce")
    passed = all(c["decision"]["passed"] for c in result["cases"])
    if result["controls_passed"] is not passed:
        raise ValueError("known gate flag differs from evidence")
    return passed


def save(output, result, revision, *, expected_kernel=None):
    executing_kernel = kernel_hash()
    if expected_kernel is not None and expected_kernel != executing_kernel:
        raise ValueError("statistical source changed during execution")
    manifest = dict(
        experiment=result["experiment"],
        plan=result["plan"],
        plan_sha256=PLAN_HASH,
        code_revision=revision,
        kernel_sha256=executing_kernel,
        environment=environment({"plan_version": 2}),
        objects={"study": output.put(json_bytes(result))},
        ranking_ready=False,
    )
    return output.put(json_bytes(manifest), manifest=True), manifest


def load(output, rid):
    manifest = json.loads(output.read(rid, manifest=True))
    validate_plan(manifest["plan"])
    if (
        manifest["plan_sha256"] != PLAN_HASH
        or manifest["ranking_ready"] is not False
        or manifest["environment"] != environment({"plan_version": 2})
        or manifest["kernel_sha256"] != kernel_hash()
    ):
        raise ValueError("saved study environment or executing statistical code differs")
    result = json.loads(output.read(manifest["objects"]["study"]))
    if result["experiment"] != manifest["experiment"] or json_bytes(result["plan"]) != json_bytes(
        manifest["plan"]
    ):
        raise ValueError("study and manifest disagree")
    if result["experiment"] == "repaired-functional-controls-v1":
        validate_known(result)
    elif result["experiment"] == "repaired-functional-archive-v1":
        validate_archive(result)
    else:
        raise ValueError("unsupported repaired experiment")
    return manifest, result


def validate_archive(result):
    p = result["plan"]
    validate_plan(p)
    if (
        set(result["cases"]) != set(CASES)
        or result["nfl_data_used"] is not True
        or result["calibration_completed"] is not False
        or result["ranking_ready"] is not False
    ):
        raise ValueError("invalid archived case denominator or admission scope")
    for i, name in enumerate(CASES):
        r = result["cases"][name]
        if r["status"] == "complete":
            total = combine(r["coarse"], r["correction"])
            if (
                r["entropy"] != [p["base_seed"], 1, i, 0]
                or json_bytes(total.tolist()) != json_bytes(r["reference"]["replicate_integrals"])
                or r["geometry_sha256"] != sha256(json_bytes(r["reference"]["geometry"]))
                or r["sampling_sha256"]
                != sampling_hash(restore_proposal(r["reference"]["geometry"], result["model_plan"]))
            ):
                raise ValueError("archived entropy, levels or geometry disagree")
            diagnosis = diagnose_reference(
                r["reference"], contrasts=r["contrasts"], shifts=r["shifts"], plan=p
            )
            if (
                json_bytes(diagnosis) != json_bytes(r["diagnosis"])
                or type(r["primary_qmc_valid"]) is not bool
                or r["numerical_valid"] is not (r["reference"]["valid"] and r["primary_qmc_valid"])
            ):
                raise ValueError("archived numerical diagnosis or gate differs")
            expected = {
                "fine": p["replicates"] * p["correction_nodes_per_replicate"] + 1,
                "coarse": p["replicates"]
                * (p["nodes_per_replicate"] + p["correction_nodes_per_replicate"]),
            }
            if r["evaluations"] != expected:
                raise ValueError("incomplete archived work labeled complete")
        elif (
            r["status"] not in ("failed", "unattempted")
            or r["numerical_valid"] is not False
            or not r.get("error")
        ):
            raise ValueError("unexplained or admitted incomplete archived case")
    if result["numerical_pilot_passed"] is not all(
        r["numerical_valid"] for r in result["cases"].values()
    ):
        raise ValueError("archived pilot gate differs from full denominator")


def authorize(controls, control_id):
    certificate, result = load(controls, control_id)
    if (
        result["experiment"] != "repaired-functional-controls-v1"
        or result["controls_passed"] is not True
    ):
        raise ValueError("new complete numerical coverage required before NFL access")
    plan = certificate["plan"]
    cm, expected = load_conditional(
        store("conditional-residual-controls"), plan["conditional_controls"]
    )
    current, _ = known_study(cm["plan"])
    if json_bytes(current) != json_bytes(expected):
        raise ValueError("executing conditional controls do not reproduce")
    return plan, cm


def archive(controls, control_id, progress=lambda _: None, checkpoint=lambda *_: None):
    plan, conditional = authorize(controls, control_id)
    context, parent, density, _ = archive_inputs(conditional["plan"], progress)
    output = store("density-reference")
    primary = json.loads(output.read(plan["primary_pilot"], manifest=True))
    validate_pilot_manifest(primary)
    if (
        primary["parent_report"] != density["parent_report"]
        or json_bytes(primary["source_provenance"]) != json_bytes(parent["source_provenance"])
        or primary["evidence_cutoff"] != parent["evidence_cutoff"]
    ):
        raise ValueError("primary target, source archive or cutoff differs")
    for digest in primary["objects"].values():
        output.read(digest)
    predictions = json.loads(output.read(primary["objects"]["predictions"]))
    repaired_store = store("conditional-throughput-archive")
    cm = json.loads(repaired_store.read(plan["conditional_archive"], manifest=True))
    repaired = json.loads(repaired_store.read(cm["objects"]["study"]))
    if (
        cm["control_report"] != plan["conditional_controls"]
        or repaired["failed_fit_replay"]["status"] != "complete"
        or json_bytes(repaired["model_plan"]) != json_bytes(parent["plan"])
    ):
        raise ValueError("saved repaired geometry provenance differs")
    cases, timings = {}, {}
    began = perf_counter()
    for index, name in enumerate(CASES):
        start = perf_counter()
        deadline = min(
            began + plan["maximum_seconds_total"], start + plan["maximum_seconds_per_case"]
        )
        record = dict(status="unattempted", numerical_valid=False)
        if start >= deadline:
            record["error"] = "declared total budget exhausted"
            cases[name] = record
            continue
        fine = coarse = None
        try:
            d, y, contrasts, variant, _ = prepare_case(context, parent["plan"], name)
            if sha256(y.astype("<f8").tobytes()) != primary["cases"][name]["response_sha256"]:
                raise ValueError("primary response differs from frozen target")
            shifts = (
                [0.0, *parent["plan"]["qb_prior_mean_shifts"]] if name == "real_evolving" else [0.0]
            )
            summaries = {
                s: {k: np.array(v) for k, v in predictions[name]["summaries"][str(s)].items()}
                for s in shifts
            }
            geometry = (
                repaired["failed_fit_replay"]["geometries"]["stabilized-mixture"]
                if name == "continuous_prior_0"
                else density["cases"][name]["density"][0]["geometries"]["stabilized-mixture"]
            )
            sampling = restore_proposal(geometry, parent["plan"])
            groups = [g for g in GROUPS[variant] if g != "innovation"] + ["game"]
            n, correction = plan["nodes_per_replicate"], plan["correction_nodes_per_replicate"]
            reps = plan["replicates"]
            if reps * (n + 2 * correction) + 1 > plan["maximum_target_evaluations_per_case"]:
                raise BudgetExceeded("declared combined evaluation budget cannot complete design")
            args = (d, y, groups, context["parent"]["plan"], parent["plan"])
            fine = SquareRootTarget(
                *args,
                evaluation_limit=reps * correction + 1,
                deadline=deadline,
                original_residual=True,
            )
            coarse = SquareRootTarget(
                *args,
                evaluation_limit=reps * (n + correction),
                deadline=deadline,
                original_residual=False,
            )
            offset = (
                fine.log_target(sampling.mean)
                - sampling.logpdf(sampling.mean, "stabilized-mixture")[0]
            )
            entropy = [plan["base_seed"], 1, index, 0]
            total, base, delta = integrate(
                conditional_integrand(fine, contrasts, summaries, offset),
                conditional_integrand(coarse, contrasts, summaries, offset),
                sampling,
                entropy=entropy,
                replicates=reps,
                nodes=n,
                correction_nodes=correction,
                progress=lambda s: progress(name + ": " + s),
            )
            # Preserve completed raw work even when confidence construction fails.
            record.update(coarse=base.tolist(), correction=delta.tolist())
            reference = summarize_integrals(total, summaries, plan, sampling, "stabilized-mixture")
            diagnosis = diagnose_reference(
                reference, contrasts=len(contrasts), shifts=shifts, plan=plan
            )
            record.update(
                status="complete",
                primary_qmc_valid=primary["cases"][name]["qmc"]["valid"],
                numerical_valid=bool(reference["valid"] and primary["cases"][name]["qmc"]["valid"]),
                response_sha256=sha256(y.astype("<f8").tobytes()),
                contrasts=len(contrasts),
                shifts=shifts,
                entropy=entropy,
                geometry_sha256=sha256(json_bytes(geometry)),
                sampling_sha256=sampling_hash(sampling),
                reference=reference,
                diagnosis=diagnosis,
                coarse=base.tolist(),
                correction=delta.tolist(),
                maximum_relative_mass_correction=float(
                    np.max(np.abs(delta[:, :: 1 + 3 * len(contrasts)])) / np.mean(base[:, 0])
                ),
            )
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            record.update(
                status="failed", error=str(exc), budget_exhausted=isinstance(exc, BudgetExceeded)
            )
        record["evaluations"] = {
            "fine": fine.evaluations if fine else 0,
            "coarse": coarse.evaluations if coarse else 0,
        }
        cases[name] = record
        timings[name] = perf_counter() - start
        checkpoint(name, record)
        progress(
            f"{name}: {record['status']}; numerical_valid={record['numerical_valid']}; seconds={timings[name]:.1f}"
        )
        del fine, coarse
    return dict(
        experiment="repaired-functional-archive-v1",
        plan=plan,
        cases=cases,
        control_report=control_id,
        primary_objects=primary["objects"],
        model_plan=parent["plan"],
        source_provenance=parent["source_provenance"],
        evidence_cutoff=parent["evidence_cutoff"],
        season=primary["season"],
        numerical_pilot_passed=all(r["numerical_valid"] for r in cases.values()),
        nfl_data_used=True,
        calibration_completed=False,
        ranking_ready=False,
    ), timings
