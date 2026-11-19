"""Consumed-control error decomposition; cannot authorize an NFL reference."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import roots_hermitenorm, stdtr
from scipy.stats import kurtosis, norm, skew, t

from nfl_value.density_holdout import known_target
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.repaired_functional import known_parents
from nfl_value.two_level_reference import restore_proposal, sampling_hash


def sine_moment(target, endpoint):
    """E[(F(endpoint|X)-.975) sin(sum X)] by conditional-normal reduction."""
    l, s = target.contrasts[0], np.ones(2)
    answer, error = 0.0, 0.0
    for mass, mean, covariance in zip(target.probabilities, target.means, target.covariances):
        variance = l @ covariance @ l
        covariance_uv = l @ covariance @ s
        attenuation = np.exp(-0.5 * (s @ covariance @ s - covariance_uv**2 / variance))

        def integrand(z):
            h = (
                stdtr(20, (endpoint - l @ mean - np.sqrt(variance) * z) / np.sqrt(target.noise[0]))
                - 0.975
            )
            return (
                norm.pdf(z)
                * h
                * attenuation
                * np.sin(s @ mean + covariance_uv / np.sqrt(variance) * z)
            )

        value, uncertainty = quad(integrand, -12, 12, epsabs=1e-12, epsrel=1e-12)
        answer += mass * value
        error += mass * uncertainty
    return float(answer), float(error)


def tensor_moment(target, endpoint, order):
    nodes, weights = roots_hermitenorm(order)
    z = np.stack(np.meshgrid(nodes, nodes, indexing="ij"), axis=-1).reshape(-1, 2)
    w = np.outer(weights, weights).ravel() / (2 * np.pi)
    result = 0.0
    for mass, mean, cov in zip(target.probabilities, target.means, target.covariances):
        x = mean + z @ np.linalg.cholesky(cov).T
        h = stdtr(20, (endpoint - x @ target.contrasts[0]) / np.sqrt(target.noise[0])) - 0.975
        result += mass * np.dot(w, h * np.sin(x.sum(axis=1)))
    return float(result)


def summarize(values, truth):
    x = np.asarray(values, float)
    means = x.mean(axis=1)
    variances = x.var(axis=1, ddof=1) / x.shape[1]
    empirical = float(means.var(ddof=1))
    half = t.isf(0.025, x.shape[1] - 1) * np.sqrt(variances)
    pooled = (x - truth).ravel()
    return dict(
        trials=len(x),
        replicates=x.shape[1],
        true_mean=truth,
        empirical_bias=float(means.mean() - truth),
        empirical_trial_variance=empirical,
        mean_estimated_variance=float(variances.mean()),
        estimated_to_empirical_variance_ratio=float(variances.mean() / empirical),
        centered_student_coverage=float(np.mean(np.abs(means - truth) <= half)),
        pooled_replicate_skewness=float(skew(pooled, bias=False)),
        pooled_replicate_excess_kurtosis=float(kurtosis(pooled, bias=False)),
        standardized_trial_error_quantiles=np.quantile(
            (means - truth) / np.sqrt(variances), [0.005, 0.025, 0.5, 0.975, 0.995]
        ).tolist(),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("store", type=Path)
    p.add_argument("checkpoint")
    p.add_argument("--plan", type=Path, default=Path("config/repaired-functional-v1.json"))
    args = p.parse_args()
    plan = json.loads(args.plan.read_text())
    certificate, density = known_parents(plan)
    target = known_target(0, certificate["model_plan"])
    payload = json.loads(SnapshotStore(args.store).read(args.checkpoint))
    case = payload["record"]
    geometry = density["cases"][0]["density"][0]["geometries"]["stabilized-mixture"]
    if (
        payload["case"] != "0"
        or case["target"] != 0
        or case["sampling_sha256"] != sampling_hash(restore_proposal(geometry, target.plan))
        or len(case["records"]) != plan["coverage_trials"]
        or any(
            r["trial"] != i
            or r["entropy"] != [plan["base_seed"], 0, 0, i]
            or r["status"] != "complete"
            for i, r in enumerate(case["records"])
        )
    ):
        raise ValueError("complete declared corrected-control records required")
    endpoint = target.exact()["high"][0]
    exact, error = sine_moment(target, endpoint)
    tensor = [tensor_moment(target, endpoint, n) for n in [128, 256]]
    if max(abs(x - exact) for x in tensor) > 1e-9 or error > 1e-9:
        raise ValueError("independent sine-moment answers disagree")
    base = np.array([r["coarse"] for r in case["records"]])
    correction = np.array([r["correction"] for r in case["records"]])
    if (
        base.shape != (plan["coverage_trials"], plan["replicates"], 9)
        or correction.shape != base.shape
    ):
        raise ValueError("incomplete raw levels")
    b = base[:, :, 5] - 0.975 * base[:, :, 0]
    c = correction[:, :, 5] - 0.975 * correction[:, :, 0]
    truth = plan["known_surrogate_amplitude"] * exact
    result = dict(
        checkpoint=args.checkpoint,
        plan_sha256=sha256(json_bytes(plan)),
        analysis="consumed_control_0_upper_endpoint_influence_not_admission",
        independent_sine_moment=exact,
        quadrature_error=error,
        tensor_crosschecks=tensor,
        coarse=summarize(b, truth),
        correction=summarize(c, -truth),
        combined=summarize(b + c, 0.0),
        coarse_fraction_of_separate_empirical_variance=float(
            b.mean(axis=1).var(ddof=1) / (b.mean(axis=1).var(ddof=1) + c.mean(axis=1).var(ddof=1))
        ),
        ranking_ready=False,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
