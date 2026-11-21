"""Independent Gaussian derivatives for the post-result geometry explanation."""

from pathlib import Path
import runpy
import unittest

import numpy as np
from scipy.stats import norm

M = runpy.run_path(str(Path(__file__).parents[1] / "scripts/mode_tail_geometry.py"))


class ModeTailGeometryTests(unittest.TestCase):
    def test_derivative_ratio_and_polynomial_against_independent_formulas(self):
        x = np.array([0.02, 0.2, 0.8, 1.7, 2.4, 3.4, 3.8, 3.99])
        for w in [0.05, 0.5]:
            g = M["log_derivative_ratio"](x, w)
            direct = -(1 - w) * x * norm.pdf(x) - w * (x - 4) / 4 * norm.pdf(x, loc=4, scale=2)
            reconstructed = (1 - w) * x * norm.pdf(x) * np.expm1(g)
            np.testing.assert_allclose(direct, reconstructed, atol=1e-15, rtol=1e-13)
            h = 1e-6
            numerical = (
                M["log_derivative_ratio"](x + h, w) - M["log_derivative_ratio"](x - h, w)
            ) / (2 * h)
            exact = -(3 * x**3 - 8 * x * x - 16 * x + 16) / (4 * x * (4 - x))
            np.testing.assert_allclose(numerical, exact, rtol=1e-7, atol=1e-8)

    def test_mode_count_changes_with_independent_stronger_component(self):
        weak, strong = M["diagnose"](0.05), M["diagnose"](0.5)
        self.assertEqual(weak["fine_target_modes"], 1)
        self.assertEqual(strong["fine_target_modes"], 2)
        self.assertEqual(len(strong["stationary_points"]), 3)
        for d in [weak, strong]:
            for p in d["stationary_points"]:
                self.assertLess(abs(p["direct_derivative"]), 1e-12)
        self.assertLess(max(weak["critical_log_derivative_ratios"]), 0)
        with self.assertRaises(ValueError):
            M["log_derivative_ratio"](4, 0.05)
