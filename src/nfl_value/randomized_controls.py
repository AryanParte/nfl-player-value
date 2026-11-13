"""Frozen analytic targets and coverage experiment; never NFL calibration."""

from copy import deepcopy

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import logsumexp, stdtr
from scipy.stats import beta, binomtest, multivariate_normal, norm

from nfl_value.replicated_reference import (
    confidence_sets,
    fit_proposal,
    functional_check,
    replicate_integrals,
)
from nfl_value.ingestion import json_bytes
from nfl_value.adaptive_proposal import fit_adaptive


def validate_plan(p):
    expected = dict(
        plan_version=1,
        base_seed=2026111213,
        replicates=32,
        nodes_per_replicate=2048,
        selection_trials=128,
        confirmation_trials=256,
        proposals=["local-t", "defensive-mixture"],
        student_df=5,
        prior_proposal_mass=0.1,
        confidence_level=0.95,
        coverage_lower_bound=0.9,
        minimum_precision_fraction=0.9,
        marginal_undercoverage_alpha=0.01 / 28,
        reference_mean_tolerance_sd=0.01,
        reference_endpoint_cdf_tolerance=0.001,
        parent_plan="config/variance-reference-sparse-v1.json",
        failure_policy="retain_all_trials_no_calibration_or_admission",
        future_test=dict(season=2026, weeks=[10], fitting_update_allowed=False),
    )
    if p.get("plan_version") == 2:
        expected.update(plan_version=2, base_seed=2026111214, proposals=["adaptive-mixture"])
    if json_bytes(p) != json_bytes(expected):
        raise ValueError("randomized study differs from frozen design")


class KnownTarget:
    def __init__(self, index, model_plan):
        if type(index) is not int or index not in range(4):
            raise ValueError("unknown analytic fixture")
        d = min(index + 2, 4)
        self.groups = list(range(d))
        self.plan = {**model_plan, "log_precision_mean": 0.0, "log_precision_sd": 3.0}
        if index == 3:
            self.means = np.array([[0, 0, 0, 0], [4, 0, 0, 0]])
            self.covariances = np.array([np.eye(4), np.diag([4, 1, 1, 1])])
            self.probabilities = np.array([0.95, 0.05])
        else:
            mean = np.linspace(0.4, -0.8, d)
            self.means = np.array([mean, mean + np.array([2, -0.5, 1, -1])[:d]])
            sd = np.linspace(0.6, 1.3, d)
            covariance = np.outer(sd, sd) * 0.65 ** np.abs(np.arange(d)[:, None] - np.arange(d))
            self.covariances = np.array([covariance, covariance])
            self.probabilities = np.array([0.8, 0.2])
        self.contrasts = np.array([[1, -1, 0.5, -0.25], [0.5, 0.5, -0.5, 0.5]])[:, :d]
        self.noise = np.array([0.2, 0.4])

    def logpdf(self, points):
        return logsumexp(
            np.stack(
                [
                    np.log(p) + np.atleast_1d(multivariate_normal.logpdf(points, mean=m, cov=c))
                    for p, m, c in zip(self.probabilities, self.means, self.covariances)
                ]
            ),
            axis=0,
        )

    def log_target(self, point):
        return float(self.logpdf(point)[0])

    def exact(self):
        means = self.means @ self.contrasts.T
        variances = np.array(
            [np.einsum("ij,jk,ik->i", self.contrasts, c, self.contrasts) for c in self.covariances]
        )
        mean = self.probabilities @ means
        var = self.probabilities @ (variances + (means - mean) ** 2) + self.noise * 20 / 18
        result = dict(mean=mean, sd=np.sqrt(var))
        for label, probability in [("low", 0.025), ("high", 0.975)]:
            endpoints = []
            for j in range(2):

                def cdf(q):
                    return sum(
                        p
                        * quad(
                            lambda z: (
                                norm.pdf(z)
                                * stdtr(20, (q - m[j] - np.sqrt(v[j]) * z) / np.sqrt(self.noise[j]))
                            ),
                            -10,
                            10,
                            epsabs=1e-11,
                            epsrel=1e-11,
                        )[0]
                        for p, m, v in zip(self.probabilities, means, variances)
                    )

                endpoints.append(brentq(lambda q: cdf(q) - probability, -40, 40, xtol=1e-11))
            result[label] = np.array(endpoints)
        return result

    def integrand(self, exact):
        def f(points, log_q):
            weight = np.exp(self.logpdf(points) - log_q)
            location = points @ self.contrasts.T
            return weight[:, None] * np.column_stack(
                [
                    np.ones(len(points)),
                    (location - exact["mean"]) / exact["sd"],
                    stdtr(20, (exact["low"] - location) / np.sqrt(self.noise)),
                    stdtr(20, (exact["high"] - location) / np.sqrt(self.noise)),
                    stdtr(20, (exact["high"] - 0.5 - location) / np.sqrt(self.noise)),
                ]
            )

        return f


def assess_trial(replicas, plan):
    expected = np.array([1, 0, 0, 0.025, 0.025, 0.975, 0.975])
    den = [-1, 0, 0, 0, 0, 0, 0]
    bounds = confidence_sets(replicas[:, :7], den)
    marginal = confidence_sets(replicas[:, :7], den, simultaneous=False)
    wrong = confidence_sets(replicas[:, [0, 1, 2, 3, 4, 7, 8]], den)
    tolerances = np.r_[
        np.full(2, plan["reference_mean_tolerance_sd"]),
        np.full(4, plan["reference_endpoint_cdf_tolerance"]),
    ]
    numerical = {k: bounds[k][1:] for k in ["estimate", "low", "high"]}
    wrong_numerical = {k: wrong[k][1:] for k in ["estimate", "low", "high"]}
    precision, discrepancy = functional_check(numerical, expected[1:], tolerances)
    wrong_passed, _ = functional_check(wrong_numerical, expected[1:], tolerances)
    covered = (bounds["low"] <= expected) & (expected <= bounds["high"])
    marginal_covered = (marginal["low"] <= expected) & (expected <= marginal["high"])
    return dict(
        status="complete",
        covered=covered.tolist(),
        simultaneous_covered=bool(covered.all()),
        marginal_covered=marginal_covered.tolist(),
        precision_passed=precision,
        wrong_endpoints_rejected=not wrong_passed,
        maximum_mean_difference_plus_error_sd=float(discrepancy[:2].max()),
        maximum_endpoint_cdf_difference_plus_error=float(discrepancy[2:].max()),
        bounds={k: v.tolist() for k, v in bounds.items() if k != "critical"},
        marginal_bounds={k: v.tolist() for k, v in marginal.items() if k != "critical"},
        replicate_mass_maximum_share=float(replicas[:, 0].max() / replicas[:, 0].sum()),
    )


def coverage_decision(records, plan):
    n = len(records)
    if not n:
        raise ValueError("empty coverage denominator")
    complete = [r for r in records if r["status"] == "complete"]
    k = sum(r["simultaneous_covered"] for r in complete)
    lower = float(beta.ppf(0.05, k, n - k + 1)) if k else 0.0
    marginal = (
        np.sum([r["marginal_covered"] for r in complete], axis=0) if complete else np.zeros(7, int)
    )
    pvalues = [float(binomtest(int(k), n, 0.95, alternative="less").pvalue) for k in marginal]
    precise = sum(r["precision_passed"] for r in complete)
    rejects = sum(r["wrong_endpoints_rejected"] for r in complete)
    errors = np.array([r["bounds"]["estimate"] for r in complete])
    expected = np.array([1, 0, 0, 0.025, 0.025, 0.975, 0.975])
    return dict(
        trials=n,
        complete=len(complete),
        simultaneous_coverage=k / n,
        simultaneous_coverage_one_sided_95_lower=lower,
        marginal_coverage=(marginal / n).tolist(),
        marginal_undercoverage_pvalues=pvalues,
        precision_fraction=precise / n,
        wrong_endpoint_rejections=rejects,
        bias=(errors.mean(axis=0) - expected).tolist() if complete else None,
        empirical_sd=errors.std(axis=0, ddof=1).tolist() if len(complete) > 1 else None,
        maximum_replicate_mass_share=max(
            (r["replicate_mass_maximum_share"] for r in complete), default=None
        ),
        passed=bool(
            len(complete) == n
            and lower >= plan["coverage_lower_bound"]
            and min(pvalues) >= plan["marginal_undercoverage_alpha"]
            and precise / n >= plan["minimum_precision_fraction"]
            and rejects == n
        ),
    )


def select(selection, proposals):
    return next(
        (
            m
            for m in proposals
            if len(selection.get(m, [])) == 4 and all(r["decision"]["passed"] for r in selection[m])
        ),
        None,
    )


def experiment(plan, model_plan, progress=lambda _: None, checkpoint=lambda *_: None):
    validate_plan(plan)
    fixtures = [KnownTarget(i, model_plan) for i in range(4)]
    geometries = [
        fit_adaptive(t, plan, i) if plan["plan_version"] == 2 else fit_proposal(t)
        for i, t in enumerate(fixtures)
    ]
    answers = [t.exact() for t in fixtures]

    def stage(method, number, count):
        cases = []
        for i, (target, sampling, exact) in enumerate(zip(fixtures, geometries, answers)):
            records = []
            for trial in range(count):
                entropy = [plan["base_seed"], number, i, trial]
                try:
                    replicas = replicate_integrals(
                        target.integrand(exact),
                        sampling,
                        method,
                        entropy=entropy,
                        replicates=plan["replicates"],
                        nodes=plan["nodes_per_replicate"],
                    )
                    r = assess_trial(replicas, plan)
                    r["replicate_integrals"] = replicas.tolist()
                except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    r = dict(status="failed", error=str(exc))
                records.append(dict(trial=trial, entropy=entropy, **r))
                if (trial + 1) % 16 == 0:
                    progress(f"stage {number} {method} fixture {i}: {trial + 1}/{count}")
            result = dict(
                fixture=i,
                dimensions=len(target.groups),
                geometry=sampling.diagnostics,
                exact={k: v.tolist() for k, v in exact.items()},
                trials=records,
                decision=coverage_decision(records, plan),
            )
            cases.append(result)
            checkpoint(f"stage_{number}_{method}_{i}", result)
            progress(f"stage {number} {method} fixture {i}: {result['decision']}")
        return cases

    selection = {m: stage(m, 0, plan["selection_trials"]) for m in plan["proposals"]}
    candidate = select(selection, plan["proposals"])
    confirmation = stage(candidate, 1, plan["confirmation_trials"]) if candidate else []
    passed = bool(
        candidate is not None
        and len(confirmation) == 4
        and all(r["decision"]["passed"] for r in confirmation)
    )
    return dict(
        experiment="replicated-reference-controls-v1",
        plan=deepcopy(plan),
        selection=selection,
        selected_before_confirmation=candidate,
        confirmation=confirmation,
        selected=candidate if passed else None,
        controls_passed=passed,
        nfl_data_used=False,
        calibration_completed=False,
        ranking_ready=False,
    )


def validate_result(result):
    """Recompute the selection decision from every retained replicate, not flags."""
    p = result["plan"]
    validate_plan(p)
    if (
        result["experiment"] != "replicated-reference-controls-v1"
        or result["nfl_data_used"] is not False
        or result["calibration_completed"] is not False
        or result["ranking_ready"] is not False
        or set(result["selection"]) != set(p["proposals"])
    ):
        raise ValueError("invalid numerical control evidence scope")

    def check_cases(cases, stage, count):
        if [c["fixture"] for c in cases] != list(range(4)):
            raise ValueError("missing or duplicated analytic fixture")
        for i, case in enumerate(cases):
            if [r["trial"] for r in case["trials"]] != list(range(count)):
                raise ValueError("missing or duplicated coverage trial")
            for trial, r in enumerate(case["trials"]):
                if r["entropy"] != [p["base_seed"], stage, i, trial]:
                    raise ValueError("control entropy differs from frozen design")
                if r["status"] == "complete":
                    replicas = np.asarray(r["replicate_integrals"], dtype=float)
                    if replicas.shape != (p["replicates"], 9):
                        raise ValueError("incomplete replicate evidence")
                    actual = assess_trial(replicas, p)
                    if json_bytes(actual) != json_bytes({k: r[k] for k in actual}):
                        raise ValueError("control diagnostics do not reproduce")
                elif r["status"] != "failed" or not r.get("error"):
                    raise ValueError("unrecorded coverage failure")
            if json_bytes(coverage_decision(case["trials"], p)) != json_bytes(case["decision"]):
                raise ValueError("coverage decision does not reproduce")

    for method in p["proposals"]:
        check_cases(result["selection"][method], 0, p["selection_trials"])
    selected = select(result["selection"], p["proposals"])
    if selected != result["selected_before_confirmation"]:
        raise ValueError("candidate selection differs")
    if selected:
        check_cases(result["confirmation"], 1, p["confirmation_trials"])
    elif result["confirmation"]:
        raise ValueError("unselected method cannot enter confirmation")
    passed = bool(selected and all(c["decision"]["passed"] for c in result["confirmation"]))
    if result["controls_passed"] is not passed or result["selected"] != (
        selected if passed else None
    ):
        raise ValueError("false numerical-reference authorization")
    return selected if passed else None
