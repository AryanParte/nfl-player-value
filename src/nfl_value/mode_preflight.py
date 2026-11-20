"""Known-answer feasibility study. This report cannot certify an NFL reference."""

import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.stats import binomtest

from nfl_value.coarse_control_study import (
    kernel_hash,
    known_inputs,
    known_parents,
    plain_assessment,
    validate_point_fit,
)
from nfl_value.conditional_cli import environment
from nfl_value.control_variates import integrate_controlled
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.mode_proposal import (
    KIND,
    Work,
    fit_modes,
    geometry_hash,
    make_proposal,
    pad_modes,
    restore_modes,
)
from nfl_value.tail_controls import TailTarget, tail_proposal
from nfl_value.two_level_reference import combine, sampling_hash

PLAN_HASH = "cbd0c022a598659f408c557079933e1e9e5eb0ca907da779fe60a10bf3d9a433"
EXPERIMENT = "mode-preflight-report-v1"


def validate_plan(plan):
    if sha256(json_bytes(plan)) != PLAN_HASH:
        raise ValueError("mode preflight differs from frozen design")


class ExtendedTarget(TailTarget):
    def __init__(self, index):
        if index not in (8, 9):
            raise ValueError("unknown extension")
        super().__init__(7)
        if index == 8:
            self.means[1] = [-7, 0, 7, 0]
            self.covariances[1] = np.diag([0.36, 1, 0.36, 1])
            self.probabilities = np.array([0.93, 0.07])
        else:
            self.means = np.array([[0.5, -0.4, 0.2, 0], [5, -6, 4, -3]])
            sd = np.array([0.4, 0.7, 1, 1.2])
            c = np.outer(sd, sd) * 0.3 ** np.abs(np.arange(4)[:, None] - np.arange(4))
            self.covariances = np.array([0.8 * np.eye(4), c])
            self.probabilities = np.array([0.92, 0.08])


def inputs(plan):
    parent_plan = json.loads(Path(plan["parent_plan"]).read_text())
    certificate, density = known_parents(parent_plan)
    result = {}
    for i in plan["known_targets"]:
        if i < 8:
            target, sampling, _geometry, truth_bytes = known_inputs(
                i, parent_plan, certificate, density
            )
            truth = json.loads(truth_bytes)
        else:
            target, sampling = ExtendedTarget(i), tail_proposal()
            truth = {k: v.tolist() for k, v in target.exact().items()}
        result[i] = (target, sampling, truth)
    return result


def oracle_proposal(target, initial):
    means, covs, masses = pad_modes(target.means, target.covariances, target.probabilities)
    g = dict(
        kind="known-component-oracle-diagnostic-v1",
        initial_sampling_sha256=sampling_hash(initial),
        component_means=means.tolist(),
        component_covariances=covs.tolist(),
        component_masses=masses.tolist(),
        geometry_uses_evaluation=False,
        unavailable_to_nfl=True,
    )
    return make_proposal(initial, means, covs, masses, g)


def summarize(records, plan):
    n = len(records)
    if n == 0:
        raise ValueError("empty preflight denominator")
    complete = [r for r in records if r["status"] == "complete"]
    precise = sum(r["precision_passed"] for r in complete)
    joint = sum(r["simultaneous_covered"] for r in complete)
    marginal = (
        np.sum([r["marginal_covered"] for r in complete], axis=0) if complete else np.zeros(7, int)
    )
    mp = [float(binomtest(int(x), n, 0.95, alternative="less").pvalue) for x in marginal]
    jp = float(binomtest(joint, n, 0.95, alternative="less").pvalue)
    return dict(
        requested=n,
        complete=len(complete),
        failed=sum(r["status"] == "failed" for r in records),
        unattempted=sum(r["status"] == "unattempted" for r in records),
        precision_fraction=precise / n,
        joint_coverage=joint / n,
        marginal_coverage=(marginal / n).tolist(),
        marginal_undercoverage_pvalues=mp,
        joint_undercoverage_pvalue=jp,
        wrong_endpoint_rejections=sum(r["wrong_endpoints_rejected"] for r in complete),
        screen_passed=bool(
            len(complete) == n
            and precise / n >= plan["minimum_precision_fraction"]
            and min(mp) >= plan["marginal_undercoverage_alpha"]
            and jp >= plan["joint_undercoverage_alpha"]
        ),
        numerical_certified=False,
    )


def trial(target, initial, truth, plan, entropy, arm):
    if arm not in ("candidate", "oracle"):
        raise ValueError("explicit candidate or diagnostic arm required")
    record = dict(entropy=entropy, status="failed")
    work = Work(plan)
    fine_function = target.integrand({k: np.array(v) for k, v in truth.items()})

    def fine(x, logq):
        work.charge("fine_evaluation", len(x))
        return fine_function(x, logq)

    def coarse(x, logq):
        work.charge("coarse_evaluation", len(x))
        return fine_function(x, logq) * (
            1 + plan["known_surrogate_amplitude"] * np.sin(x.sum(axis=1))[:, None]
        )

    def log_density(x):
        return target.logpdf(x) + np.log1p(
            plan["known_surrogate_amplitude"] * np.sin(x.sum(axis=1))
        )

    try:
        sampling = (
            fit_modes(log_density, initial, entropy=entropy, plan=plan, work=work)
            if arm == "candidate"
            else oracle_proposal(target, initial)
        )
        record.update(geometry=sampling.diagnostics, geometry_sha256=geometry_hash(sampling))
        out = integrate_controlled(fine, coarse, sampling, entropy=entropy, plan=plan)
        record.update(
            coarse=out["coarse"].tolist(),
            correction=out["correction"].tolist(),
            plain_coarse=out["plain_coarse"].tolist(),
            fit=out["fit"],
            plain_assessment=plain_assessment(
                combine(out["plain_coarse"], out["correction"]), plan
            ),
        )
        record.update(plain_assessment(out["total"], plan))
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        record["error"] = str(exc)
    record["work"] = work.record()
    record["fit_trace"] = work.trace
    return record


def experiment(plan, progress=lambda _: None, checkpoint=lambda *_: None):
    validate_plan(plan)
    fixtures = inputs(plan)
    cases, timings = [], {}
    start = perf_counter()
    for stage, (arm, indices) in enumerate(
        [("candidate", plan["known_targets"]), ("oracle", plan["oracle_targets"])]
    ):
        for i in indices:
            target, initial, truth = fixtures[i]
            records, begin = [], perf_counter()
            for j in range(plan["trials"]):
                entropy = [plan["base_seed"], stage, i, j]
                r = (
                    dict(
                        status="unattempted",
                        entropy=entropy,
                        error="overall preflight time exhausted",
                    )
                    if perf_counter() - start > plan["maximum_seconds_total"]
                    else trial(target, initial, truth, plan, entropy, arm)
                )
                records.append(dict(trial=j, **r))
            case = dict(
                arm=arm,
                target=i,
                truth=truth,
                initial_sampling_sha256=sampling_hash(initial),
                records=records,
                decision=summarize(records, plan),
            )
            cases.append(case)
            key = f"{arm}-{i}"
            timings[key] = perf_counter() - begin
            checkpoint(key, case)
            progress(f"{key}: {json.dumps(case['decision'], sort_keys=True)}")
    return dict(
        experiment=EXPERIMENT,
        plan=plan,
        cases=cases,
        screen_passed=all(c["decision"]["screen_passed"] for c in cases if c["arm"] == "candidate"),
        numerical_certified=False,
        ranking_ready=False,
        nfl_data_used=False,
    ), timings


def validate_case(case, initial, truth, plan):
    arm, i = case["arm"], case["target"]
    if (
        arm not in ("candidate", "oracle")
        or case["truth"] != truth
        or case["initial_sampling_sha256"] != sampling_hash(initial)
        or [r["trial"] for r in case["records"]] != list(range(plan["trials"]))
    ):
        raise ValueError("preflight case truth, geometry or trial denominator differs")
    for j, r in enumerate(case["records"]):
        entropy = [plan["base_seed"], int(arm == "oracle"), i, j]
        if r["entropy"] != entropy or r["status"] not in ("complete", "failed", "unattempted"):
            raise ValueError("preflight entropy or trial status differs")
        if r["status"] == "unattempted":
            if r.get("error") != "overall preflight time exhausted":
                raise ValueError("unexplained unattempted trial")
            continue
        w = r["work"]
        if (
            any(type(v) is not int or v < 0 for v in w["counts"].values())
            or sum(w["counts"].values()) != w["total"]
            or not 0 <= w["total"] <= plan["maximum_target_evaluations"]
        ):
            raise ValueError("preflight work accounting differs")
        if "geometry" in r:
            sampling = restore_modes(r["geometry"], initial)
            if geometry_hash(sampling) != r["geometry_sha256"] or r["geometry"]["kind"] != (
                KIND if arm == "candidate" else "known-component-oracle-diagnostic-v1"
            ):
                raise ValueError("preflight proposal source/arm differs")
            if arm == "candidate" and (
                r["geometry"]["entropy"] != entropy
                or r["geometry"]["search_entropy"] != [*entropy, 10]
                or r["geometry"]["pilot_entropy"] != [*entropy, 11]
            ):
                raise ValueError("preflight fitting random domains differ")
        if "coarse" in r:
            if "geometry" not in r:
                raise ValueError("preflight evaluated without fitted geometry")
            total = combine(r["coarse"], r["correction"])
            plain = combine(r["plain_coarse"], r["correction"])
            if total.shape != (plan["replicates"], 9) or plain.shape != total.shape:
                raise ValueError("preflight raw replicate dimensions differ")
            validate_point_fit(r["fit"], sampling, [*entropy, 2], plan, 9)
            actual = plain_assessment(total, plan)
            if json_bytes(actual) != json_bytes({k: r[k] for k in actual}) or json_bytes(
                r["plain_assessment"]
            ) != json_bytes(plain_assessment(plain, plan)):
                raise ValueError("preflight decisions do not reproduce")
            expected_eval = dict(
                coarse_evaluation=plan["training_nodes"]
                + plan["replicates"]
                * (plan["nodes_per_replicate"] + plan["correction_nodes_per_replicate"]),
                fine_evaluation=plan["replicates"] * plan["correction_nodes_per_replicate"],
            )
            if any(w["counts"].get(k) != v for k, v in expected_eval.items()):
                raise ValueError("preflight evaluation calls disagree with complete replicates")
        elif r["status"] == "complete":
            raise ValueError("complete preflight trial missing raw evidence")
        if r["status"] == "failed" and not r.get("error"):
            raise ValueError("unexplained failed preflight trial")
    if json_bytes(case["decision"]) != json_bytes(summarize(case["records"], plan)):
        raise ValueError("preflight summary differs from retained trials")


def validate(result):
    p = result["plan"]
    validate_plan(p)
    if (
        result["experiment"] != EXPERIMENT
        or any(
            result[k] is not False
            for k in ("numerical_certified", "ranking_ready", "nfl_data_used")
        )
        or [(c["arm"], c["target"]) for c in result["cases"]]
        != [
            (a, i)
            for a, ids in [("candidate", p["known_targets"]), ("oracle", p["oracle_targets"])]
            for i in ids
        ]
    ):
        raise ValueError("preflight scope cannot certify or publish")
    fixtures = inputs(p)
    for c in result["cases"]:
        _target, initial, truth = fixtures[c["target"]]
        validate_case(c, initial, truth, p)
    passed = all(c["decision"]["screen_passed"] for c in result["cases"] if c["arm"] == "candidate")
    if result["screen_passed"] is not passed:
        raise ValueError("preflight screen flag differs")


def save(output, result, revision, expected_kernel):
    validate(result)
    if kernel_hash() != expected_kernel:
        raise ValueError("numerical source changed during preflight")
    index = [
        {"arm": c["arm"], "target": c["target"], "object": output.put(json_bytes(c))}
        for c in result["cases"]
    ]
    manifest = dict(
        experiment=EXPERIMENT,
        plan=result["plan"],
        plan_sha256=PLAN_HASH,
        code_revision=revision,
        kernel_sha256=expected_kernel,
        environment=environment({"plan_version": 2}),
        cases=index,
        screen_passed=result["screen_passed"],
        numerical_certified=False,
        ranking_ready=False,
        nfl_data_used=False,
    )
    return output.put(json_bytes(manifest), manifest=True), manifest


def load(output, rid):
    m = json.loads(output.read(rid, manifest=True))
    validate_plan(m["plan"])
    if (
        m["experiment"] != EXPERIMENT
        or m["plan_sha256"] != PLAN_HASH
        or m["kernel_sha256"] != kernel_hash()
        or m["environment"] != environment({"plan_version": 2})
    ):
        raise ValueError("preflight source, environment or plan differs")
    result = {
        k: m[k]
        for k in (
            "experiment",
            "plan",
            "screen_passed",
            "numerical_certified",
            "ranking_ready",
            "nfl_data_used",
        )
    }
    result["cases"] = []
    for entry in m["cases"]:
        case = json.loads(output.read(entry["object"]))
        if case["arm"] != entry["arm"] or case["target"] != entry["target"]:
            raise ValueError("preflight case index differs")
        result["cases"].append(case)
    validate(result)
    return m, result
