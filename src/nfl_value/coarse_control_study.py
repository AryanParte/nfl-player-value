"""Frozen independently fitted coarse-control numerical study."""

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
from nfl_value.two_level_reference import combine, restore_proposal, sampling_hash
from nfl_value.control_variates import integrate_controlled
from nfl_value.variance_reference import BudgetExceeded
from nfl_value.study_blocks import put_case, read_case


PLAN_HASHES = {
    1: "740aca9f2eb5b8d6e9e5cac44dc4fbea50b05a4d431975f2d9791e7850c5216e",
    2: "27e2f79434940d308552469bf27f8a9083d14413fe67f7b6e316c43e3a581e0f",
}


def validate_plan(plan):
    if sha256(json_bytes(plan)) != PLAN_HASHES.get(plan.get("plan_version")):
        raise ValueError("coarse control study differs from frozen design")


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


def plain_assessment(total, plan):
    try:
        return assess_trial(total, plan)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        return dict(status="failed", error=str(exc))


def plain_reference(total, contrasts, shifts, plan, sampling):
    try:
        summaries = {s: {"mean": np.zeros(contrasts)} for s in shifts}
        return dict(
            status="complete",
            reference=summarize_integrals(total, summaries, plan, sampling, "stabilized-mixture"),
        )
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        return dict(status="failed", error=str(exc))


def validate_point_fit(fit, sampling, entropy, plan, columns):
    dimension = len(sampling.mean)
    width = len(sampling.components("stabilized-mixture")) * (
        1 + dimension + dimension * (dimension + 1) // 2
    )
    coefficients = np.asarray(fit["coefficients"], float)
    if (
        coefficients.shape != (width, columns)
        or not np.isfinite(coefficients).all()
        or fit["training_entropy"] != entropy
        or fit["training_nodes"] != plan["training_nodes"]
        or fit["relative_ridge"] != plan["relative_ridge"]
        or fit["sampling_sha256"] != sampling_hash(sampling)
        or fit["coefficients_sha256"] != sha256(json_bytes(fit["coefficients"]))
        or fit["feature_count"] != width
    ):
        raise ValueError("fitted control provenance or dimensions differ")


def validate_fit(fit, sampling, entropy, plan, columns):
    validate_point_fit(fit, sampling, entropy, plan, columns)
    if plan["plan_version"] == 2:
        from nfl_value.integration_controls import validate_integration_fit

        validate_integration_fit(fit, sampling, entropy, plan, columns, validate_point_fit)
    elif "integration_fit" in fit:
        raise ValueError("integration fit is not part of this frozen design")


def fitting_evaluations(plan):
    return (
        plan["training_nodes"]
        + plan.get("integration_fit_replicates", 0) * plan["nodes_per_replicate"]
    )


def experiment_name(plan, kind):
    return f"coarse-control-{kind}-v{plan['plan_version']}"


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
                out = integrate_controlled(fine, coarse, sampling, entropy=entropy, plan=plan)
                record.update(
                    coarse=out["coarse"].tolist(),
                    plain_coarse=out["plain_coarse"].tolist(),
                    correction=out["correction"].tolist(),
                    fit=out["fit"],
                    plain_assessment=plain_assessment(
                        combine(out["plain_coarse"], out["correction"]), plan
                    ),
                )
                record.update(**assess_trial(out["total"], plan))
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
        experiment=experiment_name(plan, "controls"),
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
        result["experiment"] != experiment_name(result["plan"], "controls")
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
                validate_fit(r["fit"], sampling, [*r["entropy"], 2], plan, total.shape[1])
                if np.asarray(r["plain_coarse"]).shape != total.shape:
                    raise ValueError("paired plain dimensions differ")
                if json_bytes(r["plain_assessment"]) != json_bytes(
                    plain_assessment(combine(r["plain_coarse"], r["correction"]), plan)
                ):
                    raise ValueError("paired plain assessment differs")
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
    from nfl_value.ingestion import MAX_DOWNLOAD_BYTES

    validate_plan(result["plan"])
    executing_kernel = kernel_hash()
    if expected_kernel is not None and expected_kernel != executing_kernel:
        raise ValueError("statistical source changed during execution")
    body = json_bytes(result)
    if len(body) > MAX_DOWNLOAD_BYTES:
        cases = result["cases"]
        if not isinstance(cases, (list, dict)) or not cases:
            raise ValueError("large study requires complete case objects")
        entries = enumerate(cases) if isinstance(cases, list) else cases.items()
        body = json_bytes(
            dict(
                storage_format="coarse-control-case-index-v1",
                header={k: v for k, v in result.items() if k != "cases"},
                case_kind="list" if isinstance(cases, list) else "mapping",
                cases=[[str(k), put_case(output, v)] for k, v in entries],
                logical_sha256=sha256(body),
            )
        )
    manifest = dict(
        experiment=result["experiment"],
        plan=result["plan"],
        plan_sha256=sha256(json_bytes(result["plan"])),
        code_revision=revision,
        kernel_sha256=executing_kernel,
        environment=environment({"plan_version": 2}),
        objects={"study": output.put(body)},
        ranking_ready=False,
    )
    return output.put(json_bytes(manifest), manifest=True), manifest


def load(output, rid):
    manifest = json.loads(output.read(rid, manifest=True))
    validate_plan(manifest["plan"])
    if (
        manifest["plan_sha256"] != sha256(json_bytes(manifest["plan"]))
        or manifest["ranking_ready"] is not False
        or manifest["environment"] != environment({"plan_version": 2})
        or manifest["kernel_sha256"] != kernel_hash()
    ):
        raise ValueError("saved study environment or executing statistical code differs")
    result = json.loads(output.read(manifest["objects"]["study"]))
    if "storage_format" in result:
        index = result
        if (
            set(index) != {"storage_format", "header", "case_kind", "cases", "logical_sha256"}
            or index["storage_format"] != "coarse-control-case-index-v1"
            or index["case_kind"] not in ("list", "mapping")
            or not isinstance(index["header"], dict)
            or "cases" in index["header"]
            or not isinstance(index["cases"], list)
            or len(index["cases"]) != 5
            or any(not isinstance(x, list) or len(x) != 2 for x in index["cases"])
        ):
            raise ValueError("invalid complete study case index")
        names = [x[0] for x in index["cases"]]
        if any(not isinstance(k, str) for k in names) or len(set(names)) != len(names):
            raise ValueError("invalid study case index names")
        if index["case_kind"] == "list" and names != [str(i) for i in range(5)]:
            raise ValueError("study case index order differs")
        values = [read_case(output, digest) for _, digest in index["cases"]]
        cases = values if index["case_kind"] == "list" else dict(zip(names, values))
        result = dict(index["header"], cases=cases)
        if sha256(json_bytes(result)) != index["logical_sha256"]:
            raise ValueError("reconstructed logical study hash differs")
    if result["experiment"] != manifest["experiment"] or json_bytes(result["plan"]) != json_bytes(
        manifest["plan"]
    ):
        raise ValueError("study and manifest disagree")
    if result["experiment"] == experiment_name(result["plan"], "controls"):
        validate_known(result)
    elif result["experiment"] == experiment_name(result["plan"], "archive"):
        validate_archive(result)
    else:
        raise ValueError("unsupported coarse-control experiment")
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
                or np.asarray(r["plain_coarse"]).shape != total.shape
                or json_bytes(total.tolist()) != json_bytes(r["reference"]["replicate_integrals"])
                or r["geometry_sha256"] != sha256(json_bytes(r["reference"]["geometry"]))
                or r["sampling_sha256"]
                != sampling_hash(restore_proposal(r["reference"]["geometry"], result["model_plan"]))
            ):
                raise ValueError("archived entropy, levels or geometry disagree")
            sampling = restore_proposal(r["reference"]["geometry"], result["model_plan"])
            validate_fit(r["fit"], sampling, [*r["entropy"], 2], p, total.shape[1])
            plain = plain_reference(
                combine(r["plain_coarse"], r["correction"]),
                r["contrasts"],
                r["shifts"],
                p,
                sampling,
            )
            if json_bytes(plain) != json_bytes(r["plain_reference"]):
                raise ValueError("paired plain reference differs")
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
                * (p["nodes_per_replicate"] + p["correction_nodes_per_replicate"])
                + fitting_evaluations(p),
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
        result["experiment"] != experiment_name(result["plan"], "controls")
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
    previous_store = store("repaired-functional-nfl")
    previous_manifest = json.loads(
        previous_store.read(plan["parent_functional_report"], manifest=True)
    )
    previous = json.loads(previous_store.read(previous_manifest["objects"]["study"]))
    if (
        previous["primary_objects"] != primary["objects"]
        or previous["control_report"] != plan["parent_control_report"]
        or previous["evidence_cutoff"] != primary["evidence_cutoff"]
    ):
        raise ValueError("previous reference does not bind the same primary archive")
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
            if (
                reps * (n + 2 * correction) + 1 + fitting_evaluations(plan)
                > plan["maximum_target_evaluations_per_case"]
            ):
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
                evaluation_limit=reps * (n + correction) + fitting_evaluations(plan),
                deadline=deadline,
                original_residual=False,
            )
            offset = (
                fine.log_target(sampling.mean)
                - sampling.logpdf(sampling.mean, "stabilized-mixture")[0]
            )
            entropy = [plan["base_seed"], 1, index, 0]
            out = integrate_controlled(
                conditional_integrand(fine, contrasts, summaries, offset),
                conditional_integrand(coarse, contrasts, summaries, offset),
                sampling,
                entropy=entropy,
                plan=plan,
                progress=lambda s: progress(name + ": " + s),
            )
            total, base, delta = out["total"], out["coarse"], out["correction"]
            record.update(
                plain_coarse=out["plain_coarse"].tolist(),
                fit=out["fit"],
                plain_reference=plain_reference(
                    combine(out["plain_coarse"], delta), len(contrasts), shifts, plan, sampling
                ),
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
        experiment=experiment_name(plan, "archive"),
        plan=plan,
        cases=cases,
        control_report=control_id,
        previous_reference=plan["parent_functional_report"],
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
