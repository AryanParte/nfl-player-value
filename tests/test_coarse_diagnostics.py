"""Independent known-variance answers for descriptive paired diagnostics."""

import runpy
import unittest

import numpy as np


class CoarseDiagnosticTests(unittest.TestCase):
    def test_proposal_diagnostics_retain_failed_confidence_fits_and_zero_envelopes(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["proposal_diagnostics"]
        stage = dict(
            prior_mass_estimates=[1],
            component_means=[[0], [1], [2]],
            moments=[
                dict(active=True, effective_weights=3, maximum_weight=0.5),
                dict(active=False),
                dict(active=True, effective_weights=2, maximum_weight=0.7),
            ],
        )
        fit = dict(proposal_fit=dict(stages=[stage, stage]))
        value = helper(
            [
                dict(status="complete", fit=fit),
                dict(status="failed", fit=fit),
                dict(status="failed"),
            ],
            0,
        )
        self.assertEqual(value["requested"], 3)
        self.assertEqual(value["retained_fits"], 2)
        for stage in value["rounds"]:
            self.assertEqual(stage["components"][0]["active"], 2)
            self.assertEqual(stage["components"][1]["inactive"], 2)
            self.assertIsNone(stage["components"][1]["effective_weight_quantiles"])
            self.assertEqual(stage["components"][2]["maximum_weight_quantiles"], [0.7] * 5)

    def test_initial_concentration_diagnostic_counts_failed_confidence_trials(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")["initial_stress_diagnostics"]
        first = np.ones((64, 9))
        second = first.copy()
        second[0, 0] = 100
        value = helper([dict(raw=first, status="complete"), dict(raw=second, status="failed")])
        self.assertEqual(value["trials"], 2)
        self.assertEqual(value["trials_reaching_previous_hierarchy_share"], 1)
        self.assertAlmostEqual(value["replicate_mass_maximum_share_quantiles"][0], 1 / 64)
        self.assertAlmostEqual(value["replicate_mass_maximum_share_quantiles"][-1], 100 / 163)
        with self.assertRaises(ValueError):
            helper([dict(raw=first * 0)])

    def test_wrong_endpoint_diagnostic_cannot_borrow_a_mean_failure(self):
        helper = runpy.run_path("scripts/analyze_coarse_controls.py")[
            "isolated_wrong_endpoint_diagnostics"
        ]
        # Mean failure alone cannot count as wrong-endpoint detection.
        raw = np.tile([1, 2, -2, 0.025, 0.025, 0.975, 0.975, 0.975, 0.975], (8, 1))
        nuisance_only = dict(coarse=raw, correction=np.zeros_like(raw))
        one_wrong = raw.copy()
        one_wrong[:, 7] = 0.9
        both_wrong = one_wrong.copy()
        both_wrong[:, 8] = 0.92
        result = helper(
            [
                nuisance_only,
                dict(coarse=one_wrong, correction=np.zeros_like(raw)),
                dict(coarse=both_wrong, correction=np.zeros_like(raw)),
                {"status": "failed"},
            ],
            0.001,
        )
        self.assertEqual(result["requested_trials"], 4)
        self.assertEqual(result["available_confidence_trials"], 3)
        self.assertEqual(result["at_least_one_wrong_endpoint_excluded_trials"], 2)
        self.assertEqual(result["both_wrong_endpoints_excluded_trials"], 1)

    def test_known_gap_error_and_disagreement_are_distinguished(self):
        helpers = runpy.run_path("scripts/analyze_coarse_controls.py")
        truth = helpers["TRUTH"]
        a, b = truth.copy(), truth.copy()
        a[1] = 0.02  # inaccurate point, but its wide interval still includes truth
        b[3] += 0.003  # small-error interval excludes the CDF tolerance region
        records = [
            dict(status="complete", bounds=dict(estimate=a, low=a - 0.03, high=a + 0.03)),
            dict(status="complete", bounds=dict(estimate=b, low=b - 0.0001, high=b + 0.0001)),
            dict(status="failed"),
        ]
        result = helpers["known_gate_decomposition"](
            records, dict(reference_mean_tolerance_sd=0.01, reference_endpoint_cdf_tolerance=0.001)
        )
        self.assertEqual(result["failed_confidence_trials"], 1)
        means, cdfs = (result["groups"][k] for k in ("mean_sd", "endpoint_cdf"))
        self.assertEqual(means["point_only_failed_trials"], 1)
        self.assertEqual(means["interval_excludes_tolerance_trials"], 0)
        self.assertEqual(cdfs["discrepancy_plus_error_failed_trials"], 2)
        self.assertEqual(cdfs["point_only_failed_trials"], 1)
        self.assertEqual(cdfs["error_only_failed_trials"], 1)
        self.assertEqual(cdfs["interval_excludes_tolerance_trials"], 1)

    def test_point_error_diagnosis_does_not_drop_failed_confidence_trials(self):
        helpers = runpy.run_path("scripts/analyze_coarse_controls.py")
        raw = np.tile([1, 2, -2, 0.025, 0.025, 0.975, 0.975, 0.9, 0.9], (4, 1))
        valid = dict(
            status="failed",
            coarse=raw,
            plain_coarse=raw,
            correction=np.zeros_like(raw),
            plain_assessment={"status": "failed"},
        )
        unavailable = {**valid, "coarse": -raw, "plain_coarse": -raw}
        result = helpers["raw_estimator_diagnostics"]([valid, unavailable, {"status": "failed"}])
        for side in ("adjusted", "plain"):
            self.assertEqual(result[side]["defined_estimates"], 1)
            self.assertEqual(result[side]["unavailable_estimates"], 2)
            self.assertEqual(result[side]["included_failed_confidence_trials"], 1)
            np.testing.assert_allclose(result[side]["bias"], [0, 2, -2, 0, 0, 0, 0])
            self.assertIsNone(result[side]["empirical_sd"])

    def test_joint_diagnosis_retains_failed_trials_and_uses_both_controls(self):
        helpers = runpy.run_path("scripts/analyze_coarse_controls.py")
        x = np.array([-1, -1, 1, 1.0])
        y = np.array([-1, 1, -1, 1.0])
        r = 0.975
        plain = np.column_stack([10 + x, r * (10 + x) + y])
        h = np.column_stack([x, y])
        fit = dict(
            joint_fit=dict(
                function_means=plain,
                control_means=h,
                numerator_slopes=[1, 0.5],
                mass_slopes=[0, r],
                layout=dict(anchors=[0, r], mass_columns=[0, 0]),
            )
        )
        adjusted, before = helpers["training_integrals"](fit)
        np.testing.assert_array_equal(before, plain)
        np.testing.assert_allclose(adjusted, np.column_stack([np.full(4, 10), 10 * r + 0.5 * y]))
        retained = dict(
            status="failed",
            fit=fit,
            coarse=adjusted,
            plain_coarse=plain,
            correction=np.zeros_like(plain),
        )
        result = helpers["joint_known_diagnostics"]([retained, {"status": "failed"}])
        self.assertEqual(result["requested_trials"], 2)
        self.assertEqual(result["retained_trials"], 1)
        for phase in ("training", "evaluation"):
            influence = result["phases"][phase]["fixed_ratio_influence"][0]
            self.assertEqual(influence["defined"], 1)
            np.testing.assert_allclose(influence["quantiles"], [0.25] * 5)

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
