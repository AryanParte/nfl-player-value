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
from nfl_value.component_allocation import integrate_allocated, validate_components
from nfl_value.control_variates import fit_control, integrate_controlled
from nfl_value.density_holdout import CurvedTarget
from nfl_value.randomized_controls import KnownTarget
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
from nfl_value.protective_mixture import (
    KIND as PROTECTIVE_KIND,
    fit_protective_mixture,
    restore_protective_mixture,
)
from nfl_value.tail_controls import TailTarget, tail_proposal
from nfl_value.tail_mixture import (
    KIND as TAIL_KIND,
    fit_tail_mixture,
    restore_tail_mixture,
)
from nfl_value.two_level_reference import combine, sampling_hash

PLAN_HASH = "cbd0c022a598659f408c557079933e1e9e5eb0ca907da779fe60a10bf3d9a433"
EXPERIMENT = "mode-preflight-report-v1"
TAIL_PLAN_HASH = "3443c16fa5d36f25772a0ab5642c1ba7032c25a7693d0a7c736ade8eb56e6aa1"
PROTECTIVE_PLAN_HASH = "168ffd8a171a516b9d8d0094f882d11c78060e74663237814a712d1ff9d70b5c"
ALLOCATION_PLAN_HASH = "d0adbccfbbd77616e291045df541cad157ef7020d15284b804af0ac0128568fe"

ENDPOINT_PLAN_HASH = "0dbab8e1f87cddf352b85ef627e33ea56e986e586dfb2755579efd3ff57cc6fc"

ENDPOINT_REPAIR_PLAN_HASH = "98b684b106f66f79f06ed7b8b8f9b04a8c1a2d33aea5df52f76cd145f7302cbc"


def endpoint_plan(plan):
    return plan["experiment"] in ("endpoint-control-preflight-v1", "endpoint-control-preflight-v2")


def allocation_plan(plan):
    return plan["experiment"] == "allocation-discovery-preflight-v1" or endpoint_plan(plan)


def fitting_plan(plan, arm):
    if allocation_plan(plan) and arm == "previous":
        return {
            **plan,
            "search_nodes": plan["previous_search_nodes"],
            "starts": plan["previous_starts"],
        }
    return plan


def protective_plan(plan):
    return plan["experiment"] == "protective-mixture-preflight-v1" or allocation_plan(plan)


def tail_plan(plan):
    return plan["experiment"] == "tail-mixture-preflight-v1" or protective_plan(plan)


def experiment_kind(plan):
    if endpoint_plan(plan):
        return plan["experiment"].replace("preflight-", "preflight-report-")
    if allocation_plan(plan):
        return "allocation-discovery-preflight-report-v1"
    if protective_plan(plan):
        return "protective-mixture-preflight-report-v1"
    return "tail-mixture-preflight-report-v1" if tail_plan(plan) else EXPERIMENT


def arms(plan):
    return [
        ("candidate", plan["known_targets"]),
        ("oracle", plan["oracle_targets"]),
        ("baseline", plan.get("baseline_targets", [])),
        ("tail", plan.get("tail_targets", [])),
        ("equal", plan.get("equal_targets", [])),
        ("previous", plan.get("previous_targets", [])),
        ("polynomial", plan.get("polynomial_targets", [])),
    ]


def validate_plan(plan):
    expected = (
        ENDPOINT_REPAIR_PLAN_HASH
        if plan["experiment"] == "endpoint-control-preflight-v2"
        else ENDPOINT_PLAN_HASH
        if endpoint_plan(plan)
        else ALLOCATION_PLAN_HASH
        if allocation_plan(plan)
        else (
            PROTECTIVE_PLAN_HASH
            if protective_plan(plan)
            else (TAIL_PLAN_HASH if tail_plan(plan) else PLAN_HASH)
        )
    )
    if sha256(json_bytes(plan)) != expected:
        raise ValueError("mode preflight differs from frozen design")


def restore_proposal(g, initial, plan):
    if g["kind"] == PROTECTIVE_KIND:
        return restore_protective_mixture(g, initial, plan)
    if g["kind"] == TAIL_KIND:
        return restore_tail_mixture(g, initial, plan)
    return restore_modes(g, initial)


def mode_geometry(g):
    tail = g.get("tail_geometry", g)
    return tail.get("mode_geometry", tail)


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


class FreshCurvedTarget(CurvedTarget):
    def __init__(self, specification):
        super().__init__({})
        self.curvature = specification["curvature"]
        self.contrasts = np.array(specification["contrasts"])
        self.noise = np.array(specification["noise"])

    def inverse(self, points):
        z = np.atleast_2d(points).astype(float).copy()
        z[:, 1] -= self.curvature * np.sin(z[:, 0])
        z[:, 3] -= self.curvature * np.sin(z[:, 2])
        return z


class FreshMixtureTarget(KnownTarget):
    def __init__(self, specification):
        super().__init__(2, {})
        self.means = np.array(specification["means"])
        factor = np.array(specification["second_cholesky"])
        self.covariances = np.array(
            [specification["base_covariance_scale"] * np.eye(4), factor @ factor.T]
        )
        self.probabilities = np.array(specification["probabilities"])
        self.contrasts = np.array(specification["contrasts"])
        self.noise = np.array(specification["noise"])


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
        elif i < 10:
            target, sampling = ExtendedTarget(i), tail_proposal()
            truth = {k: v.tolist() for k, v in target.exact().items()}
        else:
            spec = plan["fresh_targets"][str(i)]
            target = (FreshCurvedTarget if spec["kind"] == "curved" else FreshMixtureTarget)(spec)
            sampling = tail_proposal()
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
    if (
        arm not in ("candidate", "oracle", "baseline", "tail", "equal", "previous", "polynomial")
        or (arm == "baseline" and not tail_plan(plan))
        or (arm == "tail" and not protective_plan(plan))
        or (arm in ("equal", "previous") and not allocation_plan(plan))
        or (arm == "polynomial" and not endpoint_plan(plan))
    ):
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
        fitting_entropy = (
            [entropy[0], 0, *entropy[2:]]
            if arm in ("baseline", "tail") or allocation_plan(plan)
            else entropy
        )
        fit_plan = fitting_plan(plan, arm)
        if arm == "oracle":
            sampling = oracle_proposal(target, initial)
        else:
            fitter = (
                fit_protective_mixture
                if (arm == "candidate" and protective_plan(plan)) or allocation_plan(plan)
                else (
                    fit_tail_mixture
                    if (arm == "candidate" and tail_plan(plan)) or arm == "tail"
                    else fit_modes
                )
            )
            sampling = fitter(
                log_density, initial, entropy=fitting_entropy, plan=fit_plan, work=work
            )
        record.update(geometry=sampling.diagnostics, geometry_sha256=geometry_hash(sampling))
        if allocation_plan(plan):
            out = integrate_allocated(
                fine,
                coarse,
                sampling,
                entropy=entropy,
                fitting_entropy=fitting_entropy,
                plan=plan,
                adaptive=arm in ("candidate", "polynomial"),
                endpoint_settings=(
                    plan["endpoint_control"] if endpoint_plan(plan) and arm == "candidate" else None
                ),
            )
            record["components"] = out["components"]
        else:
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
    for stage, (arm, indices) in enumerate(arms(plan)):
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
        experiment=experiment_kind(plan),
        plan=plan,
        cases=cases,
        screen_passed=all(c["decision"]["screen_passed"] for c in cases if c["arm"] == "candidate"),
        numerical_certified=False,
        ranking_ready=False,
        nfl_data_used=False,
    ), timings


def validate_case(case, initial, truth, plan, target=None):
    arm, i = case["arm"], case["target"]
    if (
        arm not in ("candidate", "oracle", "baseline", "tail", "equal", "previous", "polynomial")
        or case["truth"] != truth
        or case["initial_sampling_sha256"] != sampling_hash(initial)
        or [r["trial"] for r in case["records"]] != list(range(plan["trials"]))
    ):
        raise ValueError("preflight case truth, geometry or trial denominator differs")
    for j, r in enumerate(case["records"]):
        entropy = [
            plan["base_seed"],
            {
                "candidate": 0,
                "oracle": 1,
                "baseline": 2,
                "tail": 3,
                "equal": 4,
                "previous": 5,
                "polynomial": 6,
            }[arm],
            i,
            j,
        ]
        fitting_entropy = (
            [plan["base_seed"], 0, i, j]
            if arm in ("baseline", "tail") or allocation_plan(plan)
            else entropy
        )
        fit_plan = fitting_plan(plan, arm)
        if r["entropy"] != entropy or r["status"] not in ("complete", "failed", "unattempted"):
            raise ValueError("preflight entropy or trial status differs")
        if r["status"] == "unattempted":
            if r.get("error") != "overall preflight time exhausted":
                raise ValueError("unexplained unattempted trial")
            continue
        w = r["work"]
        if (
            any(type(v) is not int or v <= 0 for v in w["counts"].values())
            or sum(w["counts"].values()) != w["total"]
            or not 0 <= w["total"] <= plan["maximum_target_evaluations"]
        ):
            raise ValueError("preflight work accounting differs")
        if "geometry" in r:
            adapted = (
                (arm == "candidate" and tail_plan(plan)) or arm == "tail" or allocation_plan(plan)
            )
            sampling = restore_proposal(r["geometry"], initial, fit_plan)
            if geometry_hash(sampling) != r["geometry_sha256"] or r["geometry"]["kind"] != (
                PROTECTIVE_KIND
                if (arm == "candidate" and protective_plan(plan)) or allocation_plan(plan)
                else (
                    TAIL_KIND
                    if adapted
                    else (
                        KIND
                        if arm in ("candidate", "baseline")
                        else "known-component-oracle-diagnostic-v1"
                    )
                )
            ):
                raise ValueError("preflight proposal source/arm differs")
            if arm in ("candidate", "baseline", "tail", "equal", "previous", "polynomial") and (
                r["geometry"]["entropy"] != fitting_entropy
                or r["geometry"]["search_entropy"] != [*fitting_entropy, 10]
                or r["geometry"]["pilot_entropy"] != [*fitting_entropy, 11]
            ):
                raise ValueError("preflight fitting random domains differ")
            if allocation_plan(plan) and (
                w["counts"].get("search_cloud") != fit_plan["search_nodes"]
                or len(r["fit_trace"].get("attempts", [])) != fit_plan["starts"]
            ):
                raise ValueError("allocation study search settings differ")
            if adapted and any(
                w["counts"].get(f"em_pilot_{k}") != plan["em_nodes"]
                for k in range(plan["em_rounds"])
            ):
                raise ValueError("tail pilot calls differ")
            if adapted and any(
                w["counts"].get(k) != v for k, v in r["geometry"]["fit_work"]["counts"].items()
            ):
                raise ValueError("tail fitting calls differ from trial work")
        if "coarse" in r:
            if "geometry" not in r:
                raise ValueError("preflight evaluated without fitted geometry")
            total = combine(r["coarse"], r["correction"])
            plain = combine(r["plain_coarse"], r["correction"])
            if total.shape != (plan["replicates"], 9) or plain.shape != total.shape:
                raise ValueError("preflight raw replicate dimensions differ")
            endpoint_settings = (
                plan["endpoint_control"] if endpoint_plan(plan) and arm == "candidate" else None
            )
            validate_point_fit(
                r["fit"],
                sampling,
                [*(fitting_entropy if allocation_plan(plan) else entropy), 2],
                plan,
                9,
                endpoint_settings=endpoint_settings,
            )
            if endpoint_settings is not None:
                if target is None:
                    raise ValueError("endpoint fit replay requires declared target callable")
                fine = target.integrand({k: np.array(v) for k, v in truth.items()})

                def coarse(x, logq):
                    return fine(x, logq) * (
                        1 + plan["known_surrogate_amplitude"] * np.sin(x.sum(axis=1))[:, None]
                    )

                replay = fit_control(
                    coarse,
                    sampling,
                    entropy=[*fitting_entropy, 2],
                    nodes=plan["training_nodes"],
                    relative_ridge=plan["relative_ridge"],
                    endpoint_settings=endpoint_settings,
                ).record()
                if json_bytes(replay) != json_bytes(r["fit"]):
                    raise ValueError("endpoint fitting evidence does not reconstruct")
            if allocation_plan(plan):
                validate_components(
                    r, sampling, entropy, fitting_entropy, plan, arm in ("candidate", "polynomial")
                )
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
            if allocation_plan(plan):
                expected_eval["coarse_evaluation"] += (
                    plan["allocation_replicates"]
                    * plan["allocation_component_nodes"]
                    * len(sampling.components("stabilized-mixture"))
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
        result["experiment"] != experiment_kind(p)
        or any(
            result[k] is not False
            for k in ("numerical_certified", "ranking_ready", "nfl_data_used")
        )
        or [(c["arm"], c["target"]) for c in result["cases"]]
        != [(a, i) for a, ids in arms(p) for i in ids]
    ):
        raise ValueError("preflight scope cannot certify or publish")
    fixtures = inputs(p)
    for c in result["cases"]:
        target, initial, truth = fixtures[c["target"]]
        validate_case(c, initial, truth, p, target=target)
    by_key = {(c["arm"], c["target"]): c for c in result["cases"]}
    for i in p.get("baseline_targets", []):
        for candidate, baseline in zip(
            by_key[("candidate", i)]["records"], by_key[("baseline", i)]["records"]
        ):
            if (
                "geometry" in candidate
                and "geometry" in baseline
                and json_bytes(mode_geometry(candidate["geometry"]))
                != json_bytes(baseline["geometry"])
            ):
                raise ValueError("matched diagnostic initial mode geometry differs")
    for i in p.get("tail_targets", []):
        for candidate, tail in zip(
            by_key[("candidate", i)]["records"], by_key[("tail", i)]["records"]
        ):
            if (
                "geometry" in candidate
                and "geometry" in tail
                and json_bytes(candidate["geometry"]["tail_geometry"])
                != json_bytes(tail["geometry"])
            ):
                raise ValueError("matched diagnostic tail geometry differs")
    for i in p.get("equal_targets", []):
        for candidate, equal in zip(
            by_key[("candidate", i)]["records"], by_key[("equal", i)]["records"]
        ):
            for key in ("geometry", "fit"):
                if (
                    key in candidate
                    and key in equal
                    and json_bytes(candidate[key]) != json_bytes(equal[key])
                ):
                    raise ValueError("matched allocation fitting evidence differs")
            if "components" in candidate and "components" in equal:
                for key in ("pilot_entropy", "pilot_plain", "pilot_controlled", "allocation"):
                    if json_bytes(candidate["components"][key]) != json_bytes(
                        equal["components"][key]
                    ):
                        raise ValueError("matched allocation pilot evidence differs")
    for i in p.get("polynomial_targets", []):
        for candidate, polynomial in zip(
            by_key[("candidate", i)]["records"], by_key[("polynomial", i)]["records"]
        ):
            if (
                "geometry" in candidate
                and "geometry" in polynomial
                and (json_bytes(candidate["geometry"]) != json_bytes(polynomial["geometry"]))
            ):
                raise ValueError("matched endpoint proposal geometry differs")
            if "fit" in candidate and "fit" in polynomial:
                for key in (
                    "training_entropy",
                    "points_sha256",
                    "weights_sha256",
                    "responses_sha256",
                ):
                    if candidate["fit"][key] != polynomial["fit"][key]:
                        raise ValueError("matched endpoint training evidence differs")
            if "components" in candidate and "components" in polynomial:
                for key in ("pilot_entropy", "pilot_plain"):
                    if json_bytes(candidate["components"][key]) != json_bytes(
                        polynomial["components"][key]
                    ):
                        raise ValueError("matched endpoint pilot coordinates differ")
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
        experiment=experiment_kind(result["plan"]),
        plan=result["plan"],
        plan_sha256=sha256(json_bytes(result["plan"])),
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
        m["experiment"] != experiment_kind(m["plan"])
        or m["plan_sha256"] != sha256(json_bytes(m["plan"]))
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
