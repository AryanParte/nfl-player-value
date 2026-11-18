"""Independent known-variance answers for descriptive paired diagnostics."""

import runpy
import unittest

import numpy as np


class CoarseDiagnosticTests(unittest.TestCase):
    def test_reducing_mass_variance_can_destroy_ratio_cancellation(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["fixed_ratio_variance"]
        x = np.array([-3.0, -1.0, 1.0, 3.0])
        e = np.array([1.0, -1.0, -1.0, 1.0])
        anchors = np.array([0.0, 0.025, 0.975])
        mass = 10 + x
        plain = np.column_stack([mass, 2 * x + e, 0.025 * mass + e, 0.975 * mass + e])
        adjusted = plain.copy()
        adjusted[:, 0] = 10
        result = helper(adjusted, plain, anchors)
        # Var(x)/Var(e)=5 and Cov(x,e)=0. Removing only mass noise
        # leaves numerator variances unchanged but loses exact covariance.
        np.testing.assert_allclose(result["unnormalized"], [0, 1, 1, 1])
        np.testing.assert_allclose(
            result["fixed_ratio_influence"], [1, 1 + 5 * 0.025**2, 1 + 5 * 0.975**2]
        )
        scaled = helper(-7 * adjusted, -7 * plain, anchors)
        np.testing.assert_allclose(scaled["fixed_ratio_influence"], result["fixed_ratio_influence"])
        constant = np.ones((4, 4))
        self.assertEqual(helper(constant, constant, anchors)["fixed_ratio_influence"], [None] * 3)
        for a, p, r in (
            (adjusted[:1], plain[:1], anchors),
            (adjusted, plain, anchors[:2]),
            (adjusted, plain * np.nan, anchors),
        ):
            with self.assertRaises(ValueError):
                helper(a, p, r)

    def test_ratio_objective_keeps_training_evaluation_and_shift_order_separate(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["ratio_objective_diagnostics"]
        x = np.array([-3.0, -1.0, 1.0, 3.0])
        e = np.array([1.0, -1.0, -1.0, 1.0])
        mass = 10 + x
        plain = np.column_stack([mass, e, 0.025 * mass + e, 0.975 * mass + e])
        h = np.column_stack([x, np.zeros((4, 3))])
        f, control = np.column_stack([plain, 2 * plain]), np.column_stack([h, 2 * h])
        record = dict(
            contrasts=1,
            shifts=[1.0, -1.0],
            fit=dict(
                integration_fit=dict(function_means=f, control_means=control, alpha=np.ones(8))
            ),
            coarse=f,
            plain_coarse=f,
            correction=np.zeros_like(f),
        )
        result = helper(record)["phases"]
        self.assertEqual(list(result["training"]), ["1.0", "-1.0"])
        for shift in ("1.0", "-1.0"):
            train = result["training"][shift]["upper_cdf"]["fixed_ratio_influence"]
            self.assertEqual(train["worse"], 1)
            np.testing.assert_allclose(train["quantiles"], [1 + 5 * 0.975**2] * 3)
            evaluation = result["evaluation"][shift]["upper_cdf"]["fixed_ratio_influence"]
            self.assertEqual(evaluation["quantiles"], [1.0, 1.0, 1.0])

    def test_integration_training_diagnostic_has_known_residual_variance(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["integration_diagnostics"]
        x = np.array([-3, -1, 1, 3])
        orthogonal = np.array([1, -1, -1, 1])
        f = np.column_stack([2 * x + orthogonal, -3 * x, np.ones(4)])
        h = np.column_stack([x, x, np.zeros(4)])
        record = dict(integration_fit=dict(function_means=f, control_means=h, alpha=[2, -3, 0]))
        result = helper([record])
        self.assertEqual(result["negative_alpha_count"], 1)
        self.assertEqual(result["zero_alpha_count"], 1)
        self.assertEqual(result["defined_training_variance_ratios"], 2)
        self.assertEqual(result["undefined_training_variance_ratios"], 1)
        self.assertAlmostEqual(result["training_variance_ratio_quantiles"][-1], 4 / 84)
        with self.assertRaises(ValueError):
            helper(
                [
                    dict(
                        integration_fit=dict(
                            function_means=f, control_means=h[:-1], alpha=[2, -3, 0]
                        )
                    )
                ]
            )

    def test_archived_influence_uses_ratio_covariance_and_separate_levels(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["influence_diagnostics"]
        noise = np.array([-2, -1, 1, 2], float)
        mass = 2 + 0.1 * noise
        truth = np.array([-3, 0.025, 0.975])
        scale = np.array([1, 0.1, 0.2])
        base = np.column_stack((mass, mass[:, None] * truth + noise[:, None] * scale))
        plain = np.column_stack((mass, mass[:, None] * truth + 2 * noise[:, None] * scale))
        correction = np.column_stack((np.zeros(4), 0.1 * noise[:, None] * scale))
        record = dict(
            contrasts=1, shifts=[0.0], coarse=base, plain_coarse=plain, correction=correction
        )
        result = helper(record)["0.0"]
        for i, label in enumerate(("mean_sd", "lower_cdf", "upper_cdf")):
            row = result[label]
            self.assertAlmostEqual(row["adjusted_to_plain_variance"][0], (1.1 / 2.1) ** 2)
            self.assertAlmostEqual(row["correction_to_coarse_standard_error"][0], 0.1)
            self.assertAlmostEqual(row["coarse_fraction_of_separate_variance"][0], 1 / 1.01)
            self.assertAlmostEqual(
                row["adjusted_standard_error"][0],
                1.1 * scale[i] * np.sqrt(noise.var(ddof=1) / 4) / 2,
            )
        with self.assertRaises(ValueError):
            helper({**record, "correction": correction[:-1]})

    def test_archived_influence_preserves_declared_shift_order_and_zero_variance(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["influence_diagnostics"]
        constant = np.tile([2, -6, 0.05, 1.95], (4, 1))
        variable = constant.copy()
        variable[:, 1] += [-2, -1, 1, 2]
        raw = np.column_stack((variable, constant, 2 * variable))
        result = helper(
            dict(
                contrasts=1,
                shifts=[0.0, 1.0, -1.0],
                coarse=raw,
                plain_coarse=raw,
                correction=np.zeros_like(raw),
            )
        )
        self.assertEqual(list(result), ["0.0", "1.0", "-1.0"])
        self.assertEqual(result["1.0"]["mean_sd"]["adjusted_to_plain_variance"], [None])
        self.assertEqual(result["0.0"]["mean_sd"]["adjusted_to_plain_variance"], [1.0])
        self.assertEqual(result["0.0"]["mean_sd"], result["-1.0"]["mean_sd"])

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
