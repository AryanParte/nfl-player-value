"""Independent known-variance answers for descriptive paired diagnostics."""

import runpy
import unittest

import numpy as np


class CoarseDiagnosticTests(unittest.TestCase):
    def test_paired_variance_and_bias_have_independent_closed_answers(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["paired_errors"]
        noise = np.array([-2, -1, 1, 2])[:, None]
        truth = np.array([-3.0, 1.0])
        plain = truth + noise * [1, 2]
        adjusted = truth + noise * [0.5, 1] + [0, 0.25]
        result = helper(adjusted, plain, truth)
        np.testing.assert_allclose(result["adjusted_to_plain_variance"], [0.25, 0.25])
        np.testing.assert_allclose(result["adjusted_bias"], [0, 0.25])
        np.testing.assert_allclose(result["adjusted_to_plain_mse"], [0.25, 0.25625])
        self.assertEqual(result["paired_complete_trials"], 4)
        with self.assertRaises(ValueError):
            helper(adjusted[:-1], plain, truth)

    def test_first_order_mass_and_ratio_variances_are_distinct(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["delta_variance"]
        noise = np.array([-1.0, 0, 0, 1])
        raw = np.tile([2, 0, 0, 0.05, 0.05, 1.95, 1.95], (2, 4, 1)).astype(float)
        raw[:, :, 1] += noise
        result = helper(raw)
        self.assertEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], noise.var(ddof=1) / 4 / 4)
        np.testing.assert_array_equal(result[2:], np.zeros(5))


if __name__ == "__main__":
    unittest.main()
