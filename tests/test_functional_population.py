"""Independent Gaussian identities for the population-moment diagnosis."""

import runpy
import unittest
from math import erf, sqrt

import numpy as np


class PopulationMomentTests(unittest.TestCase):
    def test_absolute_normal_moments(self):
        helper = runpy.run_path("scripts/functional_population_diagnostic.py")["projection_moments"]
        mass, first, second, error = helper([0.0], [[1.0]], [1.0], abs, cusp=0.0)
        expected = np.sqrt(2 / np.pi)
        self.assertAlmostEqual(mass, expected, places=12)
        np.testing.assert_allclose(first, 0, atol=1e-12)
        np.testing.assert_allclose(second, [[2 * expected]], atol=1e-12)
        self.assertLess(error, 1e-8)

    def test_correlated_linear_and_quadratic_moments(self):
        helper = runpy.run_path("scripts/functional_population_diagnostic.py")["projection_moments"]
        covariance = np.array([[2.0, 0.5], [0.5, 1.0]])
        a = np.array([1.0, -2.0])
        linear = helper([0.0, 0.0], covariance, a, lambda x: x)
        self.assertAlmostEqual(linear[0], 0, places=12)
        np.testing.assert_allclose(linear[1], [1, -1.5], atol=1e-12)
        np.testing.assert_allclose(linear[2], 0, atol=1e-12)
        quadratic = helper([0.0, 0.0], covariance, a, lambda x: x * x)
        self.assertAlmostEqual(quadratic[0], 4, places=12)
        np.testing.assert_allclose(quadratic[1], 0, atol=1e-12)
        np.testing.assert_allclose(quadratic[2], [[10, -1], [-1, 8.5]], atol=1e-12)

    def test_nonzero_conditional_mean(self):
        helper = runpy.run_path("scripts/functional_population_diagnostic.py")["projection_moments"]
        mu = np.array([2.0, -1.0])
        cov = np.array([[2.0, 0.5], [0.5, 1.0]])
        mass, first, second, _ = helper(mu, cov, [1.0, 2.0], lambda _: 1)
        self.assertAlmostEqual(mass, 1, places=12)
        np.testing.assert_allclose(first, mu, atol=1e-12)
        np.testing.assert_allclose(second, cov + np.outer(mu, mu), atol=1e-12)
        with self.assertRaises(ValueError):
            helper(mu, cov, [0.0, 0.0], lambda _: 1)

    def test_surrogate_tilt_bound_against_gaussian_characteristic_function(self):
        helpers = runpy.run_path("scripts/functional_population_diagnostic.py")
        mu, cov = np.array([0.3, -0.4]), np.array([[2.0, 0.3], [0.3, 0.5]])
        a, epsilon = np.array([0.4, 1.2]), 0.001
        attenuation = np.exp(-0.5 * (a @ cov @ a))
        mass = 1 + epsilon * attenuation * np.sin(a @ mu)
        movement = epsilon * attenuation * (cov @ a) * np.cos(a @ mu) / mass
        z, first, _, _ = helpers["projection_moments"](
            mu, cov, a, lambda x: 1 + epsilon * np.sin(x)
        )
        self.assertAlmostEqual(z, mass, places=12)
        np.testing.assert_allclose(first / z - mu, movement, atol=1e-12)
        bound = helpers["tilted_mean_displacement_bound"]
        self.assertLess(np.linalg.norm(movement), bound(cov, epsilon))
        self.assertEqual(bound(cov, 0), 0)
        for amplitude in (-0.001, 1, np.nan):
            with self.assertRaises(ValueError):
                bound(cov, amplitude)

    def test_initial_box_uses_allocation_counts_not_mixture_masses(self):
        box = runpy.run_path("scripts/functional_population_diagnostic.py")["initial_pilot_box"](7)
        unit = ((erf(8.5 / sqrt(2)) - erf(7.5 / sqrt(2))) / 2) ** 2
        defensive = ((erf(8.5 / (3 * sqrt(2))) - erf(7.5 / (3 * sqrt(2)))) / 2) ** 2
        target = 0.9 * unit + 0.1 * erf(1 / sqrt(2)) ** 2
        self.assertAlmostEqual(box["target_probability"], target, places=13)
        self.assertAlmostEqual(box["proposal_probability"], 0.9 * unit + 0.1 * defensive, places=13)
        expected = 2048 * (3 * unit + defensive)
        self.assertAlmostEqual(box["expected_total_points"], expected, places=12)
        self.assertAlmostEqual(box["any_point_probability_upper_bound"], expected, places=12)
        self.assertGreater(target, 0.04)
        self.assertLess(expected, 0.04)
        self.assertNotAlmostEqual(expected, 8192 * box["proposal_probability"], places=5)


if __name__ == "__main__":
    unittest.main()
