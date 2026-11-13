"""Known answers, independent construction and numerical failures, without NFL data."""

from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import stdtr, stdtrit
from scipy.stats import multivariate_normal, norm, t

from nfl_value.reference_pilot import validate_plan
from nfl_value.sparse_cubature import fejer, grid, integrate, point_count
from nfl_value.variance_reference import build_transport, reference_integral
from test_variance_reference import AnalyticTarget


def plan():
    return json.loads(Path("config/variance-reference-sparse-v1.json").read_text())


class SkewTarget(AnalyticTarget):
    def __init__(self):
        super().__init__()
        self.probabilities = np.array([0.8, 0.2])
        self.means = np.array([self.mean, [2.5, -1.2]])

    def log_target(self, x):
        return float(
            np.log(
                sum(
                    p * multivariate_normal.pdf(x, mean=m, cov=self.covariance)
                    for p, m in zip(self.probabilities, self.means)
                )
            )
        )


class SparseCubatureTests(unittest.TestCase):
    def test_fejer_moments_and_exact_nested_angles(self):
        for level in range(1, 7):
            x, w = fejer(level)
            for degree in range(len(x) + 1):
                self.assertAlmostEqual(w @ x**degree, 1 / (degree + 1), places=13)
            if level > 1:
                np.testing.assert_array_equal(x[1::2], fejer(level - 1)[0])
            self.assertFalse(w.flags.writeable)
        for bad in [True, 0, 11]:
            with self.assertRaises(ValueError):
                fejer(bad)

    def test_sparse_counts_polynomials_and_independent_tensor_combination(self):
        self.assertEqual(point_count(4, 8), 65537)
        for d in (2, 3, 4):
            nodes, weights, born = grid(d, 4)
            for level in range(5):
                self.assertEqual(sum(born <= level), point_count(d, level))
                self.assertTrue(np.all(weights[born > level, level] == 0))
            for powers in product(range(5), repeat=d):
                # Minimal univariate level for each degree; telescoping gives exactness.
                needed = sum(max(0, int(np.ceil(np.log2(k + 1))) - 1) for k in powers)
                if needed <= 4:
                    expected = np.prod([1 / (k + 1) for k in powers])
                    actual = weights[:, -1] @ np.prod(nodes**powers, axis=1)
                    self.assertAlmostEqual(actual, expected, places=12)
        # Independently use the 2D combination formula, rather than difference weights.
        f = lambda x: np.exp(x[:, 0] + 0.3 * x[:, 1]) * (1 + x[:, 0] * x[:, 1])
        nodes, weights, _ = grid(2, 3)
        expected = 0.0
        for total, sign in [(5, 1), (4, -1)]:
            for a in range(1, total):
                xa, wa = fejer(a)
                xb, wb = fejer(total - a)
                xy = np.array(list(product(xa, xb)))
                expected += sign * np.kron(wa, wb) @ f(xy)
        self.assertAlmostEqual(weights[:, -1] @ f(nodes), expected, places=13)

    def test_known_correlated_skew_tail_integrals_and_signed_components(self):
        for d in (2, 3, 4):
            cov = np.diag(np.linspace(0.7, 1.1, d))
            cov[0, 1] = cov[1, 0] = 0.35
            means = np.array([np.linspace(-0.4, 0.4, d), np.linspace(1.3, -0.8, d)])
            probabilities = np.array([0.8, 0.2])
            exact_mean = probabilities @ means
            expected = np.r_[1.0, exact_mean, np.diag(cov) + probabilities @ (means**2)]

            def f(unit):
                eta = stdtrit(5, unit)
                density = sum(
                    p * multivariate_normal.pdf(eta, mean=m, cov=cov)
                    for p, m in zip(probabilities, means)
                )
                weight = density / np.prod(t.pdf(eta, 5), axis=1)
                return weight[:, None] * np.column_stack([np.ones(len(unit)), eta, eta**2])

            result = integrate(f, d, rtol=1e-4, atol=1e-6, max_level=9, max_evaluations=90000)
            difference = np.abs(result.estimate - expected)
            np.testing.assert_array_less(difference, result.error + 1e-10)
            if result.status == "converged":
                np.testing.assert_array_less(difference, 1e-6 + 1e-4 * np.abs(result.estimate))
            self.assertLess(result.estimate[1], 0)  # Preserve an analytically negative integral.
            self.assertLessEqual(result.evaluations, 90000)

    def test_budget_complete_levels_replay_and_invalid_integrands(self):
        f = lambda x: np.column_stack([np.exp(6 * x[:, 0]), -np.exp(4 * x[:, 1])])
        a = integrate(f, 3, rtol=1e-8, atol=1e-10, max_level=9, max_evaluations=50)
        self.assertEqual(a.status, "not_converged")
        self.assertEqual(a.evaluations, point_count(3, a.level))
        self.assertLessEqual(a.evaluations, 50)
        b = integrate(f, 3, rtol=1e-8, atol=1e-10, max_level=a.level, max_evaluations=50)
        np.testing.assert_array_equal(a.estimate, b.estimate)
        self.assertEqual(a.history, b.history)
        used = []

        def seen(x):
            used.extend(map(tuple, x))
            return f(x)

        c = integrate(seen, 3, rtol=1e-8, atol=1e-10, max_level=9, max_evaluations=90000)
        self.assertEqual(len(set(used)), len(used))
        self.assertEqual(c.status, "converged")
        expected = np.array([np.expm1(6) / 6, -np.expm1(4) / 4])
        np.testing.assert_array_less(np.abs(c.estimate - expected), c.error + 1e-12)
        for broken in [lambda x: np.full((len(x), 1), np.nan), lambda x: x[:, 0]]:
            with self.assertRaises(ValueError):
                integrate(broken, 2, rtol=1e-4, atol=1e-6, max_level=4, max_evaluations=1000)
        for bad in [0, True, 1.5]:
            with self.assertRaises(ValueError):
                integrate(f, 2, rtol=1e-4, atol=1e-6, max_level=4, max_evaluations=bad)

    def test_skew_mixture_endpoints_against_independent_scalar_convolution(self):
        target, p = SkewTarget(), plan()
        validate_plan(p)
        transport = build_transport(target, p)
        l = np.array([[1.0, -1.0], [1.0, 1.0]])
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
                                * stdtr(
                                    20, (q - m - np.sqrt(normal_var[j]) * z) / np.sqrt(noise[j])
                                )
                            ),
                            -10,
                            10,
                            epsabs=1e-11,
                        )[0]
                        for p, m in zip(target.probabilities, means[:, j])
                    )

                endpoints.append(brentq(lambda q: cdf(q) - probability, -30, 30, xtol=1e-11))
            summary[key] = np.array(endpoints)
        correct = reference_integral(target, l, transport, {0.0: summary}, p)
        self.assertTrue(correct["valid"], correct)
        bad = deepcopy(summary)
        bad["high"] -= 0.5
        self.assertFalse(reference_integral(target, l, transport, {0.0: bad}, p)["valid"])
        insufficient = reference_integral(
            target, l, transport, {0.0: summary}, {**p, "maximum_target_evaluations_per_case": 20}
        )
        self.assertFalse(insufficient["valid"])
        self.assertEqual(insufficient["status"], "not_converged")

    def test_rule_policy_cannot_silently_mix_reference_versions(self):
        p = plan()
        for changes in [
            {"reference_cache_nodes": 1024},
            {"cubature_max_subdivisions": 10},
            {"reference_subdivision": "largest_fourth_difference"},
            {"reference_sparse_level": True},
            {"reference_sparse_level": 10},
            {"reference_transport": "posterior_whitened_product_student_t5"},
            {"cubature_rule": "genz-malik"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_plan({**p, **changes})


if __name__ == "__main__":
    unittest.main()
