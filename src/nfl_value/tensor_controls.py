"""Predeclared known-answer selection; no football data, fitting or calibration."""

from copy import deepcopy

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import logsumexp, stdtr, stdtrit
from scipy.stats import multivariate_normal, norm, t

from nfl_value.tensor_cubature import integrate
from nfl_value.variance_reference import build_transport, reference_integral


def moment_control(method, dimensions, *, tail=False):
    d = dimensions
    cov = np.diag(np.linspace(0.7, 1.1, d))
    cov[0, 1] = cov[1, 0] = 0.35
    means = np.array([np.linspace(-0.4, 0.4, d), np.linspace(1.3, -0.8, d)])
    probabilities = np.array([0.8, 0.2])
    covariances = np.array([cov, cov])
    if tail:
        means = np.zeros((2, d))
        means[1, 0] = 4
        covariances = np.array([np.eye(d), np.eye(d)])
        covariances[1, 0, 0] = 4
        probabilities = np.array([0.95, 0.05])
    expected = np.r_[
        1.0,
        probabilities @ means,
        probabilities @ (np.diagonal(covariances, axis1=1, axis2=2) + means**2),
    ]

    def f(points):
        eta = stdtrit(5, points) if method == "gauss-legendre" else points
        log_proposal = np.sum(
            t.logpdf(eta, 5) if method == "gauss-legendre" else norm.logpdf(eta), axis=1
        )
        log_density = logsumexp(
            np.array(
                [
                    np.log(p) + multivariate_normal.logpdf(eta, mean=m, cov=c)
                    for p, m, c in zip(probabilities, means, covariances)
                ]
            ),
            axis=0,
        )
        weight = np.exp(log_density - log_proposal)
        return weight[:, None] * np.column_stack([np.ones(len(eta)), eta, eta**2])

    r = integrate(f, d, method=method, rtol=1e-4, atol=1e-6, max_evaluations=90000)
    difference = np.abs(r.estimate - expected)
    tolerance = 1e-6 + 1e-4 * np.abs(r.estimate)
    covered = bool(np.all(difference <= r.error + 1e-10))
    false_convergence = bool(r.status == "converged" and np.any(difference > tolerance))
    return dict(
        dimensions=d,
        tail=tail,
        status=r.status,
        order=r.order,
        evaluations=r.evaluations,
        expected=expected.tolist(),
        estimate=r.estimate.tolist(),
        error=r.error.tolist(),
        maximum_actual_error=float(difference.max()),
        estimated_error_covers_actual=covered,
        false_convergence=false_convergence,
        valid=covered and not false_convergence,
        history=r.history,
    )


class MixingTarget:
    """Correlated Gaussian mixture with exactly specified Student-t conditionals."""

    def __init__(self, model_plan):
        self.groups = ["qb", "offense"]
        self.plan = {**model_plan, "log_precision_mean": 0.0, "log_precision_sd": 3.0}
        self.means = np.array([[0.5, -0.7], [2.5, -1.2]])
        self.probabilities = np.array([0.8, 0.2])
        self.covariance = np.array([[0.5, 0.35], [0.35, 2.0]])
        self.noise = np.diag([0.2, 0.4])

    def prior(self, x, qb_shift=0):
        return np.atleast_1d(multivariate_normal.logpdf(x, mean=[qb_shift, 0.0], cov=np.eye(2) * 9))

    def log_target(self, x):
        return float(
            logsumexp(
                [
                    np.log(p) + multivariate_normal.logpdf(x, mean=m, cov=self.covariance)
                    for p, m in zip(self.probabilities, self.means)
                ]
            )
        )

    def conditional(self, x, l, need_games=False):
        return dict(
            mean=np.asarray(x)[:, None],
            game_mean=np.empty((0, 1)),
            location=(l @ x)[:, None],
            diagonal=np.einsum("ij,jk,ik->i", l, self.noise, l),
            posterior_shape=10.0,
            posterior_scale=np.array([10.0]),
            log_likelihood=np.array([self.log_target(x) - self.prior(x)[0]]),
        )


def exact_summary(target, l):
    """Independent scalar Normal/Student-t convolution; never the tensor algorithm."""
    means = target.means @ l.T
    mean = target.probabilities @ means
    normal_var = np.einsum("ij,jk,ik->i", l, target.covariance, l)
    noise = np.einsum("ij,jk,ik->i", l, target.noise, l)
    variance = normal_var + target.probabilities @ (means - mean) ** 2 + noise * 10 / 9
    summary = dict(mean=mean, sd=np.sqrt(variance))
    for key, probability in [("low", 0.025), ("high", 0.975)]:
        endpoints = []
        for j in range(len(l)):

            def cdf(q):
                return sum(
                    p
                    * quad(
                        lambda z: (
                            norm.pdf(z)
                            * stdtr(20, (q - m - np.sqrt(normal_var[j]) * z) / np.sqrt(noise[j]))
                        ),
                        -10,
                        10,
                        epsabs=1e-11,
                    )[0]
                    for p, m in zip(target.probabilities, means[:, j])
                )

            endpoints.append(brentq(lambda q: cdf(q) - probability, -30, 30, xtol=1e-11))
        summary[key] = np.array(endpoints)
    return summary


def select(reports):
    acceptable = [k for k, r in reports.items() if r["controls_passed"]]
    return (
        min(
            acceptable,
            key=lambda k: (
                -sum(c["status"] == "converged" for c in reports[k]["moments"]),
                reports[k]["correct_endpoints"]["evaluations"],
                k != "gauss-legendre",
            ),
        )
        if acceptable
        else None
    )


def run(model_plan, plans):
    target = MixingTarget(model_plan)
    l = np.array([[1.0, -1.0], [1.0, 1.0]])
    exact = exact_summary(target, l)
    reports = {}
    for method, p in plans.items():
        moments = [moment_control(method, d) for d in [2, 3, 4]]
        moments.append(moment_control(method, 4, tail=True))
        transport = build_transport(target, p)
        correct = reference_integral(target, l, transport, {0.0: exact}, p)
        bad = deepcopy(exact)
        bad["high"] -= 0.5
        incorrect = reference_integral(target, l, transport, {0.0: bad}, p)
        reports[method] = dict(
            moments=moments,
            correct_endpoints=correct,
            incorrect_endpoints=incorrect,
            controls_passed=bool(
                all(c["valid"] for c in moments) and correct["valid"] and not incorrect["valid"]
            ),
        )
    return dict(controls=reports, selected=select(reports), nfl_data_used=False, calibration=False)
