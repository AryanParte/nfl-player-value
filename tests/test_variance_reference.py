"""Independent transport and integration references, including deliberate failures."""

from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
import unittest
from unittest.mock import patch

import numpy as np
from scipy.integrate import quad
from scipy.stats import multivariate_normal

from nfl_value.continuous_math import Target
from nfl_value.variance_mixture import system
from nfl_value.variance_reference import (
    Axis,
    BoundedTarget,
    BudgetExceeded,
    build_transport,
    qmc_integrate,
    reference_integral,
)


def plan():
    return json.loads(Path("config/variance-reference-smooth-v1.json").read_text())


class AnalyticTarget:
    """Known correlated Gaussian mixing law, Student-t conditional observations."""

    def __init__(self):
        self.groups = ["qb", "offense"]
        self.plan = json.loads(Path("config/continuous-variance-v1.json").read_text())
        self.plan.update(log_precision_mean=0.0, log_precision_sd=3.0)
        self.mean = np.array([0.5, -0.7])
        self.covariance = np.array([[0.5, 0.35], [0.35, 2.0]])
        self.noise = np.diag([0.2, 0.4])

    def prior(self, x, qb_shift=0):
        return np.atleast_1d(multivariate_normal.logpdf(x, mean=[qb_shift, 0.0], cov=np.eye(2) * 9))

    def log_target(self, x):
        return float(multivariate_normal.logpdf(x, mean=self.mean, cov=self.covariance))

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


class ReferenceMathTests(unittest.TestCase):
    def test_axis_exact_cdf_density_inverse_and_untruncated_skew_tail(self):
        axis = Axis(
            np.array([-2.0, 0.0, 1.0, 4.0, 8.0]), np.array([0.0, 1.0, 0.8, 0.4, 0.0]), 0.0, 3.0, 0.1
        )
        for x in [-5.0, -2.0, -0.5, 1.5, 5.0, 12.0]:
            edges = sorted({-100.0, x, *(v for v in axis.grid if -100 < v < x)})
            integral = sum(
                quad(axis.pdf, a, b, epsabs=1e-12)[0] for a, b in zip(edges[:-1], edges[1:])
            )
            self.assertAlmostEqual(axis.cdf(x), integral, places=11)
        u = np.r_[1e-9, np.linspace(0.001, 0.999, 101), 1 - 1e-9]
        np.testing.assert_allclose(axis.cdf(axis.ppf(u)), u, atol=1e-13, rtol=0)
        self.assertLess(axis.ppf(np.array([1e-9]))[0], axis.grid[0])
        self.assertGreater(axis.ppf(np.array([1 - 1e-9]))[0], axis.grid[-1])
        self.assertGreater(axis.pdf(20), 0)
        mean, variance = axis.moments()
        expected_mean = sum(
            quad(lambda x: x * axis.pdf(x), a, b)[0]
            for a, b in zip([-100, *axis.grid], [*axis.grid, 100])
        )
        expected_second = sum(
            quad(lambda x: x * x * axis.pdf(x), a, b)[0]
            for a, b in zip([-100, *axis.grid], [*axis.grid, 100])
        )
        self.assertAlmostEqual(mean, expected_mean, places=10)
        self.assertAlmostEqual(variance, expected_second - expected_mean**2, places=10)
        with self.assertRaises(ValueError):
            axis.ppf(np.array([0.0]))
        with self.assertRaises(ValueError):
            Axis([0, 1], [0, 0], 0, 3, 0.1)

    def test_correlated_target_keeps_joint_correction_and_independent_reference(self):
        target = AnalyticTarget()
        p = plan()
        transport = build_transport(target, p)
        l = np.array([[1.0, -1.0], [1.0, 1.0]])
        fit, summaries, diagnostic = qmc_integrate(target, l, transport, p)
        self.assertTrue(diagnostic["valid"])
        np.testing.assert_allclose(summaries[0.0]["mean"], l @ target.mean, atol=0.015)
        true_variance = np.einsum("ij,jk,ik->i", l, target.covariance + 10 / 9 * target.noise, l)
        np.testing.assert_allclose(summaries[0.0]["sd"] ** 2, true_variance, rtol=0.02)
        result = reference_integral(target, l, transport, summaries, p)
        self.assertTrue(result["valid"], result)
        self.assertLess(result["checks"]["0.0"]["maximum_endpoint_cdf_difference"], 0.001)
        with patch.object(target, "conditional", wraps=target.conditional) as conditional:
            cached = reference_integral(
                target, l, transport, summaries, {**p, "reference_cache_nodes": 1024}
            )
            calls = conditional.call_count
        stats = cached.pop("cache")
        cached.pop("subdivision_limit")
        cached.pop("subdivision_limit_from_solve_budget")
        self.assertEqual(cached, result)
        self.assertEqual(calls, stats["misses"])
        self.assertEqual(stats["hits"] + calls, result["evaluations"])
        self.assertLess(calls, result["evaluations"] / 2)
        self.assertLessEqual(stats["retained"], 1024)
        broken = deepcopy(summaries)
        broken[0.0]["low"] += 0.5
        failed = reference_integral(target, l, transport, broken, p)
        self.assertFalse(failed["valid"])
        cached_failed = reference_integral(
            target, l, transport, broken, {**p, "reference_cache_nodes": 1024}
        )
        cached_failed.pop("cache")
        cached_failed.pop("subdivision_limit")
        cached_failed.pop("subdivision_limit_from_solve_budget")
        self.assertEqual(cached_failed, failed)
        self.assertFalse(
            reference_integral(
                target, l, transport, summaries, {**p, "cubature_max_subdivisions": 0}
            )["valid"]
        )
        self.assertEqual(fit["coefficient_mean"].shape, (2,))

    def test_scalar_random_effect_matches_independent_quadrature(self):
        x = np.column_stack([np.ones(24), np.tile([-1.0, 1.0], 12)])
        y = 0.5 + 1.5 * x[:, 1] + np.random.default_rng(412).normal(size=24)
        d = system(x, ["context/intercept", "qb/a"], 1)
        old = json.loads(Path("config/continuous-variance-v1.json").read_text())
        t = Target(d, y, ["qb"], {"noise_prior_shape": 3, "noise_prior_scale": 4.5}, old)
        l = np.array([[0.0, 1.0]])
        geometry = build_transport(t, plan())
        _, summaries, diagnostic = qmc_integrate(t, l, geometry, plan())
        shift = t.log_target(geometry.mode)
        weight = lambda v: np.exp(t.log_target(np.array([v])) - shift)
        normalizer = quad(weight, -18, 30, epsabs=1e-9)[0]
        exact = (
            quad(
                lambda v: weight(v) * t.conditional(np.array([v]), l)["location"][0, 0],
                -18,
                30,
                epsabs=1e-9,
            )[0]
            / normalizer
        )
        self.assertAlmostEqual(summaries[0.0]["mean"][0], exact, delta=0.002)
        self.assertTrue(diagnostic["valid"])
        self.assertTrue(
            reference_integral(t, l, geometry, summaries, {**plan(), "cubature_rule": "gk21"})[
                "valid"
            ]
        )

    def test_work_budget_is_enforced_without_changing_target(self):
        x = np.column_stack([np.ones(12), np.tile([-1.0, 1.0], 6)])
        d = system(x, ["context/intercept", "qb/a"], 1)
        old = json.loads(Path("config/continuous-variance-v1.json").read_text())
        t = BoundedTarget(
            d,
            x[:, 1],
            ["qb"],
            {"noise_prior_shape": 3, "noise_prior_scale": 4.5},
            old,
            evaluation_limit=1,
            deadline=perf_counter() + 10,
        )
        t.conditional(np.array([2.0]), np.array([[0.0, 1.0]]))
        with self.assertRaises(BudgetExceeded):
            t.conditional(np.array([2.0]), np.array([[0.0, 1.0]]))
        t.evaluation_limit = 10
        t.deadline = perf_counter() - 1
        with self.assertRaises(BudgetExceeded):
            t.log_target(np.array([3.0]))

    def test_solve_budget_retains_complete_failed_reference_estimate(self):
        x = np.column_stack([np.ones(24), np.tile([-1, 1], 12), np.repeat([-1, 1], 12)])
        d = system(x, ["context/intercept", "qb/a", "offense/a"], 1)
        old = json.loads(Path("config/continuous-variance-v1.json").read_text())
        target = BoundedTarget(
            d,
            x[:, 1] + np.random.default_rng(642).normal(size=24),
            ["qb", "offense"],
            {"noise_prior_shape": 3, "noise_prior_scale": 4.5},
            old,
            evaluation_limit=50000,
            deadline=perf_counter() + 60,
        )
        p = {**plan(), "reference_cache_nodes": 1024}
        geometry = build_transport(target, p)
        l = np.array([[0.0, 1.0, -1.0]])
        _, summaries, _ = qmc_integrate(target, l, geometry, p)
        before = target.evaluations
        target.evaluation_limit = before + 120
        result = reference_integral(target, l, geometry, summaries, p)
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "not_converged")
        self.assertTrue(result["subdivision_limit_from_solve_budget"])
        self.assertEqual(result["subdivisions"], 1)
        self.assertGreater(result["checks"]["0.0"]["estimated_mass_error"], 0)
        self.assertLessEqual(target.evaluations, target.evaluation_limit)
        target.evaluation_limit = 50000
        same = reference_integral(
            target, l, geometry, summaries, {**p, "cubature_max_subdivisions": 1}
        )
        self.assertEqual(same["checks"], result["checks"])


if __name__ == "__main__":
    unittest.main()
