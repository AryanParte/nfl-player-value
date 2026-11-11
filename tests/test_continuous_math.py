"""Continuous integration references independent of the fitted NFL design."""

import json
from pathlib import Path
import unittest

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import stdtr
from scipy.stats import multivariate_normal, multivariate_t

from nfl_value.continuous_math import Target, compare, integrate, proposal, quantiles
from nfl_value.variance_mixture import normalized_weights, system


def plan():
    p = json.loads(Path("config/continuous-variance-v1.json").read_text())
    p["sobol_powers"] = [7, 8, 9, 10]
    return p


class ContinuousMathTests(unittest.TestCase):
    def test_exact_mixture_quantiles_match_independent_roots_and_ignore_zero_mass_brackets(self):
        result = dict(
            location=np.array([[[-1.0], [2.0]], [[3.0], [4.0]], [[1e20], [-1e20]]]),
            diagonal=np.array([[1.0, 4.0], [4.0, 1.0], [1e40, 1e40]]),
            scale=np.array([[5.0], [10.0], [5.0]]),
            shape=5.0,
            weights=np.array([[0.3], [0.7], [0.0]]),
        )
        low, high = quantiles(result, 40)
        for col in range(2):

            def cdf(value):
                return sum(
                    result["weights"][j, 0]
                    * stdtr(
                        10,
                        (value - result["location"][j, col, 0])
                        / np.sqrt(result["diagonal"][j, col] * result["scale"][j, 0] / 5),
                    )
                    for j in range(2)
                )

            for probability, values in [(0.025, low), (0.975, high)]:
                self.assertAlmostEqual(
                    values[col, 0],
                    brentq(lambda x: cdf(x) - probability, -100, 100, xtol=1e-12),
                    places=9,
                )
        point = {**result, "diagonal": np.zeros((3, 2))}
        a, b = quantiles(point, 40)
        np.testing.assert_array_equal(a[:, 0], [-1.0, 2.0])
        np.testing.assert_array_equal(b[:, 0], [3.0, 4.0])
        with self.assertRaisesRegex(ValueError, "root accuracy"):
            quantiles(result, 1)

    def test_stratified_heavy_tailed_proposal_targets_same_integral_and_nested_prefix(self):
        mean, cov = np.array([2.0, -1.0]), np.array([[2.0, 0.3], [0.3, 0.5]])
        p = {**plan(), "numerical_proposal": "stratified_student_t5_v1"}
        target = lambda x: multivariate_normal.logpdf(x, mean=mean, cov=cov)
        geometry = proposal(target, 2, p)
        points, correction = geometry.draw_stratified(11, 412)
        density = geometry.masses[0] * multivariate_normal.pdf(
            points, mean=geometry.means[0], cov=geometry.covariances[0]
        )
        for j in range(1, len(geometry.means)):
            density += geometry.masses[j] * multivariate_t.pdf(
                points, loc=geometry.means[j], shape=geometry.covariances[j], df=5
            )
        mass = np.tile(geometry.masses, 2**11)
        np.testing.assert_allclose(np.exp(correction), density / mass, rtol=1e-13)
        weights = normalized_weights(np.array([target(x) for x in points]) - correction)
        np.testing.assert_allclose(weights @ points, mean, atol=0.01)
        centered = points - mean
        np.testing.assert_allclose((centered.T * weights) @ centered, cov, atol=0.025)
        prefix, _ = geometry.draw_stratified(9, 412)
        np.testing.assert_array_equal(prefix, points[: len(prefix)])
        with self.assertRaisesRegex(ValueError, "stratified"):
            geometry.draw(7, 412)

    def test_proposal_density_and_normal_integral(self):
        mean, cov = np.array([2.0, -1.0]), np.array([[2.0, 0.3], [0.3, 0.5]])
        target = lambda x: multivariate_normal.logpdf(x, mean=mean, cov=cov)
        p = plan()
        geometry = proposal(target, 2, p)
        points, log_q = geometry.draw(11, 412)
        independent_q = sum(
            w * multivariate_normal.pdf(points, mean=m, cov=c)
            for w, m, c in zip(geometry.masses, geometry.means, geometry.covariances)
        )
        np.testing.assert_allclose(np.exp(log_q), independent_q, atol=1e-14)
        weights = normalized_weights(np.array([target(x) for x in points]) - log_q)
        np.testing.assert_allclose(weights @ points, mean, atol=0.01)
        centered = points - mean
        np.testing.assert_allclose((centered.T * weights) @ centered, cov, atol=0.025)
        prefix, _ = geometry.draw(9, 412)
        np.testing.assert_array_equal(prefix, points[:512])

    def test_random_effect_integral_matches_independent_scalar_quadrature(self):
        for policy in [None, "stratified_student_t5_v1"]:
            with self.subTest(policy=policy):
                self.check_scalar_reference(policy)

    def check_scalar_reference(self, policy):
        rng = np.random.default_rng(412)
        x = np.column_stack([np.ones(24), np.tile([-1.0, 1.0], 12)])
        y = 0.5 + 1.5 * x[:, 1] + rng.normal(size=24)
        d = system(x, ["context/intercept", "qb/a"], 1)
        p = plan()
        if policy is not None:
            p["numerical_proposal"] = policy
        t = Target(d, y, ["qb"], {"noise_prior_shape": 3.0, "noise_prior_scale": 4.5}, p)
        l = np.array([[0.0, 1.0]])
        fit, summary, mode, diagnostic = integrate(t, l, p)
        reference = t.log_target(np.array([0.0]))

        def weight(z):
            return np.exp(t.log_target(np.array([z])) - reference)

        a, b = (
            p["log_precision_mean"] - 8 * p["log_precision_sd"],
            p["log_precision_mean"] + 8 * p["log_precision_sd"],
        )
        denominator = quad(weight, a, b, epsabs=1e-9)[0]

        def value(z):
            return t.conditional(np.array([z]), l)

        exact_mean = (
            quad(lambda z: weight(z) * value(z)["location"][0, 0], a, b, epsabs=1e-8)[0]
            / denominator
        )

        def cdf(endpoint):
            def integrand(z):
                result = value(z)
                scale = np.sqrt(
                    result["diagonal"][0] * result["posterior_scale"][0] / result["posterior_shape"]
                )
                return weight(z) * stdtr(
                    2 * result["posterior_shape"], (endpoint - result["location"][0, 0]) / scale
                )

            return quad(integrand, a, b, epsabs=1e-8)[0] / denominator

        exact_low = brentq(lambda v: cdf(v) - 0.025, -10, 10)
        exact_high = brentq(lambda v: cdf(v) - 0.975, -10, 10)
        self.assertAlmostEqual(summary["mean"][0], exact_mean, delta=0.003)
        self.assertAlmostEqual(summary["low"][0], exact_low, delta=0.006)
        self.assertAlmostEqual(summary["high"][0], exact_high, delta=0.006)
        self.assertTrue(diagnostic["valid"])
        self.assertGreater(summary["effective_samples"], 128)
        self.assertEqual(fit["coefficient_mean"].shape, (2,))
        self.assertLess(mode["low"][0], mode["high"][0])

    def test_numerical_failure_is_retained_and_shared_scale_compares_without_units(self):
        x = np.column_stack([np.ones(12), np.tile([-1.0, 1.0], 6)])
        d = system(x, ["context/intercept", "qb/a"], 1)
        p = {**plan(), "sobol_powers": [7, 8], "minimum_effective_samples": 1e9}
        t = Target(
            d,
            x[:, 1] + np.arange(12) * 0.1,
            ["qb"],
            {"noise_prior_shape": 3.0, "noise_prior_scale": 4.5},
            p,
        )
        _, s, _, diagnostic = integrate(t, np.array([[0.0, 1.0]]), p)
        self.assertFalse(diagnostic["valid"])
        self.assertEqual(diagnostic["nodes_per_scramble"], 256)
        self.assertEqual(compare(s, s), {"mean": 0.0, "endpoint": 0.0})
        other = {**s, "mean": s["mean"] + s["sd"]}
        self.assertAlmostEqual(compare(s, other)["mean"], 1.0)
        with self.assertRaises(ValueError):
            t.conditional([np.nan], np.array([[0.0, 1.0]]))


if __name__ == "__main__":
    unittest.main()
