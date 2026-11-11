"""Independent analytic answers, dependency contracts and fail-closed references."""

from copy import deepcopy
from itertools import product
import json
from pathlib import Path
from time import perf_counter
import unittest

import numpy as np
from scipy.integrate._rules import GenzMalikCubature
from scipy.special import erf

from nfl_value.dimension_cubature import Rule, integrate
from nfl_value.reference_pilot import validate_plan
from nfl_value.variance_mixture import system
from nfl_value.variance_reference import (
    BoundedTarget,
    build_transport,
    qmc_integrate,
    reference_integral,
)
from test_variance_reference import AnalyticTarget


class DimensionCubatureTests(unittest.TestCase):
    def test_actual_random_effect_budget_retains_complete_reference(self):
        p = json.loads(Path("config/variance-reference-adaptive-v1.json").read_text())
        model = json.loads(Path("config/continuous-variance-v1.json").read_text())
        x = np.column_stack([np.ones(24), np.tile([-1, 1], 12), np.repeat([-1, 1], 12)])
        d = system(x, ["context/intercept", "qb/a", "offense/a"], 1)
        target = BoundedTarget(
            d,
            x[:, 1] + np.random.default_rng(642).normal(size=24),
            ["qb", "offense"],
            {"noise_prior_shape": 3, "noise_prior_scale": 4.5},
            model,
            evaluation_limit=50000,
            deadline=perf_counter() + 60,
        )
        geometry = build_transport(target, p)
        l = np.array([[0.0, 1.0, -1.0]])
        _, summaries, _ = qmc_integrate(target, l, geometry, p)
        target.evaluation_limit = target.evaluations + 65
        failed = reference_integral(target, l, geometry, summaries, p)
        self.assertFalse(failed["valid"])
        self.assertEqual(failed["subdivisions"], 1)
        self.assertTrue(failed["subdivision_limit_from_solve_budget"])
        self.assertLessEqual(target.evaluations, target.evaluation_limit)
        target.evaluation_limit = 50000
        same = reference_integral(
            target, l, geometry, summaries, {**p, "cubature_max_subdivisions": 1}
        )
        self.assertEqual(failed["checks"], same["checks"])
        complete = reference_integral(target, l, geometry, summaries, p)
        self.assertTrue(complete["valid"], complete)

    def test_all_polynomial_moments_through_rule_degrees(self):
        for d in [2, 3, 4]:
            rule = Rule(d)
            exponents = np.array([p for p in product(range(8), repeat=d) if sum(p) <= 7])
            values = np.prod(rule.nodes[:, None, :] ** exponents[None, :, :], axis=2)
            truth = np.prod(np.where(exponents % 2, 0.0, 2.0 / (exponents + 1)), axis=1)
            np.testing.assert_allclose(rule.high_weights @ values, truth, atol=5e-14, rtol=0)
            lower = exponents.sum(axis=1) <= 5
            np.testing.assert_allclose(
                rule.low_weights @ values[:, lower], truth[lower], atol=5e-14, rtol=0
            )
            f = lambda x: np.column_stack([np.exp(x[:, 0]), np.cos(x).sum(axis=1)])
            low, high = -np.ones(d), np.arange(1, d + 1, dtype=float)
            region = rule.region(f, low, high)
            original = GenzMalikCubature(d)
            np.testing.assert_allclose(region.estimate, original.estimate(f, low, high), rtol=1e-14)
            np.testing.assert_allclose(
                region.error, original.estimate_error(f, low, high), rtol=1e-9
            )

    def test_analytic_anisotropic_gaussians_signed_vectors_and_actual_error(self):
        for d in [2, 3, 4]:
            a, center = np.array([30.0, 2.0, 0.5, 8.0])[:d], np.array([0.23, 0.6, 0.8, 0.4])[:d]

            def f(x):
                value = np.exp(-np.sum(a * (x - center) ** 2, axis=1))
                return np.column_stack([value, -2 * value, np.ones(len(x))])

            exact = np.prod(
                np.sqrt(np.pi)
                / (2 * np.sqrt(a))
                * (erf(np.sqrt(a) * (1 - center)) + erf(np.sqrt(a) * center))
            )
            r = integrate(f, np.zeros(d), np.ones(d), rtol=1e-5, atol=1e-8, max_subdivisions=600)
            self.assertEqual(r.status, "converged")
            actual_error = np.abs(r.estimate - [exact, -2 * exact, 1.0])
            self.assertTrue(np.all(actual_error <= r.error + 1e-13), (actual_error, r.error))
            self.assertTrue(np.all(r.error <= 1e-8 + 1e-5 * np.abs(r.estimate)))
            self.assertEqual(sum(r.axis_splits), r.subdivisions)
            self.assertGreater(r.axis_splits[0], r.axis_splits[1])
            again = integrate(
                f, np.zeros(d), np.ones(d), rtol=1e-5, atol=1e-8, max_subdivisions=600
            )
            np.testing.assert_array_equal(r.estimate, again.estimate)
            np.testing.assert_array_equal(r.error, again.error)
            self.assertEqual(r.axis_splits, again.axis_splits)

    def test_binary_work_bound_retains_nonconvergence_and_rejects_bad_inputs(self):
        calls = 0

        def f(x):
            nonlocal calls
            calls += len(x)
            return np.exp(12 * x[:, :1])

        for cap in [0, 1, 3]:
            calls = 0
            r = integrate(f, np.zeros(4), np.ones(4), rtol=1e-12, atol=1e-14, max_subdivisions=cap)
            self.assertEqual(r.status, "not_converged")
            self.assertEqual(calls, 57 * (1 + 2 * cap))
            self.assertEqual(calls, r.evaluations)
            self.assertEqual(r.subdivisions, cap)
            self.assertEqual(r.axis_splits, [cap, 0, 0, 0])
            self.assertTrue(np.all(r.error > 0))
        for bad in [lambda x: np.full((len(x), 1), np.nan), lambda x: np.ones(len(x))]:
            with self.assertRaisesRegex(ValueError, "finite vector"):
                integrate(bad, np.zeros(2), np.ones(2), rtol=1e-4, atol=1e-6, max_subdivisions=1)
        with self.assertRaises(ValueError):
            integrate(f, [0, 0], [1, -1], rtol=1e-4, atol=1e-6, max_subdivisions=1)
        with self.assertRaises(ValueError):
            Rule(5)

    def test_correlated_mixture_reference_and_wrong_endpoint_rejection(self):
        p = json.loads(Path("config/variance-reference-adaptive-v1.json").read_text())
        validate_plan(p)
        target = AnalyticTarget()
        l = np.array([[1.0, -1.0], [1.0, 1.0]])
        geometry = build_transport(target, p)
        _, summaries, _ = qmc_integrate(target, l, geometry, p)
        r = reference_integral(target, l, geometry, summaries, p)
        self.assertTrue(r["valid"], r)
        self.assertEqual(r["subdivision_strategy"], "largest_fourth_difference")
        broken = deepcopy(summaries)
        broken[0.0]["low"] += 0.5
        failed = reference_integral(target, l, geometry, broken, p)
        self.assertFalse(failed["valid"])
        self.assertGreater(
            failed["checks"]["0.0"]["maximum_endpoint_cdf_difference_plus_error"], 0.01
        )
        with self.assertRaisesRegex(ValueError, "subdivision"):
            validate_plan({**p, "reference_subdivision": "unsupported"})
        with self.assertRaisesRegex(ValueError, "bounded"):
            validate_plan({**p, "maximum_target_evaluations_per_case": 90001})


if __name__ == "__main__":
    unittest.main()
