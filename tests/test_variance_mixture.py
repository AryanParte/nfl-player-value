"""Independent observation-space and augmented-system checks of variance integration."""

import unittest

import numpy as np
from scipy.optimize import brentq
from scipy.special import logsumexp, stdtr

from nfl_value.variance_mixture import cell, integrate, interval, modal_interval, moments
from nfl_value.variance_mixture import response_stats, system


class VarianceMixtureTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(20261108)
        self.x = np.column_stack([np.ones(24), rng.normal(size=24), np.tile([1.0, 0.0], 12)])
        self.y = rng.normal(size=(24, 3))
        self.ids = [str(i // 4) for i in range(24)]
        self.s = system(self.x, ["intercept", "a", "b"], 1, self.ids)
        self.l = np.array([[0.0, 1.0, -1.0], [0.0, 2.0, -2.0]])

    def test_marginal_game_likelihood_matches_dense_observation_space(self):
        z = np.eye(6)[self.s.game_codes]
        d = np.array([0.0, 4.0, 7.0])
        g = 9.0
        actual = cell(self.s, response_stats(self.s, self.y), d, g, self.l, 3.0, 4.5)
        f, u = self.x[:, :1], self.x[:, 1:]
        v = np.eye(24) + (u / d[1:]) @ u.T + z @ z.T / g
        vi = np.linalg.inv(v)
        fixed_h = f.T @ vi @ f
        projected = vi - vi @ f @ np.linalg.solve(fixed_h, f.T @ vi)
        q = np.einsum("ij,ij->j", self.y, projected @ self.y)
        b = 4.5 + q / 2
        expected = -0.5 * (np.linalg.slogdet(v)[1] + np.linalg.slogdet(fixed_h)[1]) - 14.5 * np.log(
            b
        )
        np.testing.assert_allclose(actual["log_likelihood"], expected, atol=1e-12)
        np.testing.assert_allclose(actual["posterior_scale"], b, atol=1e-12)
        # A separate augmented coefficient solve checks the game posterior and
        # player-minus-benchmark covariance, including its off-diagonal terms.
        full_x = np.column_stack([self.x, z])
        h = full_x.T @ full_x + np.diag(np.r_[d, np.full(6, g)])
        beta = np.linalg.solve(h, full_x.T @ self.y)
        full_l = np.column_stack([self.l, np.zeros((2, 6))])
        np.testing.assert_allclose(actual["mean"], beta[:3], atol=1e-12)
        np.testing.assert_allclose(actual["game_mean"], beta[3:], atol=1e-12)
        np.testing.assert_allclose(
            actual["diagonal"], np.diag(full_l @ np.linalg.solve(h, full_l.T)), atol=1e-12
        )

    def test_mixture_quantiles_and_total_variance_are_not_averaged_endpoints(self):
        cells = [
            {"penalty": np.array([0.0, p, p]), "game_precision": 7.0, "log_prior": -np.log(2)}
            for p in [1.0, 30.0]
        ]
        fit = integrate(self.s, self.y, self.l, cells, shape=3, scale=4.5)
        low, high = interval(fit)
        mean, variance = moments(fit)
        for j in range(3):
            singles = integrate(self.s, self.y[:, j], self.l, cells, shape=3, scale=4.5)
            np.testing.assert_allclose(singles["weights"][:, 0], fit["weights"][:, j], atol=1e-12)
            for k in range(2):
                location = fit["location"][:, k, j]
                scale = np.sqrt(fit["diagonal"][:, k] * fit["scale"][:, j] / fit["shape"])

                def cdf(t):
                    return np.sum(
                        fit["weights"][:, j] * stdtr(2 * fit["shape"], (t - location) / scale)
                    )

                self.assertAlmostEqual(
                    low[k, j], brentq(lambda t: cdf(t) - 0.025, -100, 100), places=10
                )
                self.assertAlmostEqual(
                    high[k, j], brentq(lambda t: cdf(t) - 0.975, -100, 100), places=10
                )
                second = np.sum(
                    fit["weights"][:, j]
                    * (
                        location**2
                        + fit["diagonal"][:, k] * fit["scale"][:, j] / (fit["shape"] - 1)
                    )
                )
                self.assertAlmostEqual(variance[k, j], second - mean[k, j] ** 2, places=12)
        ml, mh = modal_interval(fit)
        self.assertEqual(ml.shape, (2, 3))
        self.assertTrue(np.all(mh > ml))
        self.assertFalse(np.allclose(low, ml))
        np.testing.assert_allclose(low[1], 2 * low[0], atol=1e-10)

    def test_prior_normalization_invalid_design_and_zero_contrast(self):
        with self.assertRaises(ValueError):
            system(self.x, ["a", "a", "b"], 1)
        with self.assertRaises(ValueError):
            response_stats(self.s, [float("nan")] * 24)
        cells = [{"penalty": np.array([0.0, 4.0, 4.0]), "game_precision": 7.0, "log_prior": 0.0}]
        fit = integrate(self.s, self.y[:, 0], np.zeros((1, 3)), cells, shape=3, scale=4.5)
        for bound in interval(fit):
            np.testing.assert_array_equal(bound, np.zeros((1, 1)))
        cells[0]["log_prior"] = 1.0
        with self.assertRaisesRegex(ValueError, "normalized"):
            integrate(self.s, self.y, self.l, cells, shape=3, scale=4.5)
        self.assertAlmostEqual(float(logsumexp([0.0])), 0.0)


if __name__ == "__main__":
    unittest.main()
