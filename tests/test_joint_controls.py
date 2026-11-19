"""Independent analytical ratio controls, tail truth and provenance regression."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm, t

from nfl_value.coarse_control_study import (
    assessment_plan,
    fitting_evaluations,
    known_case_count,
    validate_fit,
    validate_plan,
)
from nfl_value.control_variates import integrate_controlled
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.joint_controls import joint_slopes, coefficient_product, ratio_layout
from nfl_value.tail_controls import TailTarget, tail_proposal, tail_truth_bytes
from test_control_variates import GaussianMixture


def plan():
    return json.loads(Path("config/coarse-control-v3.json").read_text())


class JointControlTests(unittest.TestCase):
    def test_frozen_budgets_and_original_vs_tail_gates(self):
        p = plan()
        validate_plan(p)
        old = json.loads(Path("config/coarse-control-v2.json").read_text())
        for k in (
            "replicates",
            "training_nodes",
            "integration_fit_replicates",
            "integration_scale_ridge",
            "nodes_per_replicate",
            "correction_nodes_per_replicate",
            "coverage_trials",
            "maximum_seconds_per_case",
            "maximum_seconds_total",
            "maximum_target_evaluations_per_case",
            "reference_mean_tolerance_sd",
            "reference_endpoint_cdf_tolerance",
            "coverage_lower_bound",
            "minimum_precision_fraction",
            "cases",
            "future_test",
        ):
            self.assertEqual(p[k], old[k], k)
        self.assertEqual(known_case_count(p), 7)
        self.assertEqual(known_case_count(old), 5)
        self.assertEqual(fitting_evaluations(p) + 64 * (1024 + 2 * 32) + 1, 88065)
        for i in range(7):
            rules = assessment_plan(p, i)
            self.assertEqual(rules["plan_version"], 2)  # no unrelated older-v3 experiment rule
            self.assertEqual(rules["marginal_undercoverage_alpha"], 0.01 / (35 if i < 5 else 14))
            self.assertEqual(rules["joint_undercoverage_alpha"], 0.01 / (5 if i < 5 else 2))
        with self.assertRaises(ValueError):
            validate_plan({**p, "base_seed": p["base_seed"] + 1})

    def test_ratio_cancellation_has_independent_closed_form(self):
        x = np.array([-1, -1, 1, 1.0])
        y = np.array([-1, 1, -1, 1.0])
        r, ridge = 0.975, 0.01
        # N = r Z - 3y. Cancellation of shared x matters for normalized error.
        f = np.column_stack([1 + 2 * x, r * (1 + 2 * x) - 3 * y])
        h = np.column_stack([x, y])
        layout = dict(anchors=[0, r], mass_columns=[0, 0])
        slopes = joint_slopes(f, h, layout, ridge)
        np.testing.assert_allclose(
            slopes["numerator_slopes"], [2, -3] / np.array(1 + ridge), atol=1e-14
        )
        np.testing.assert_allclose(slopes["mass_slopes"], [0, 2 * r / (1 + ridge)], atol=1e-14)
        b = coefficient_product(np.eye(2), slopes, layout)
        adjusted = f - h @ b
        np.testing.assert_allclose(
            adjusted[:, 1] - r * adjusted[:, 0], -3 * y * ridge / (1 + ridge), atol=1e-14
        )
        # Offsets, signed rescaling and row order preserve the fitted adjustment.
        scales = np.array([-2.0, 5])
        changed = joint_slopes(f[::-1] + [10, 7], h[::-1] * scales + [3, -8], layout, ridge)
        product = coefficient_product(np.diag(scales), changed, layout)
        np.testing.assert_allclose(product, b, atol=1e-14)

    def test_duplicate_and_zero_directions_are_finite_without_jitter(self):
        x = np.array([-3, -1, 1, 3.0])
        f = np.column_stack([1 + x, -2 * x])
        h = np.column_stack([x, x])
        layout = dict(anchors=[0, 0], mass_columns=[0, 0])
        ridge = 0.1
        slopes = joint_slopes(f, h, layout, ridge)
        adjusted = f - h @ coefficient_product(np.eye(2), slopes, layout)
        np.testing.assert_allclose(adjusted[:, 1], -2 * x * ridge / (1 + ridge), atol=1e-14)
        empty = joint_slopes(f, h * 0, layout, ridge)
        np.testing.assert_array_equal(empty["numerator_slopes"], [0, 0])
        np.testing.assert_array_equal(empty["mass_slopes"], [0, 0])

    def test_declared_prior_order_uses_separate_masses(self):
        layout = ratio_layout(2, 3)
        self.assertEqual(layout["mass_columns"], [0] * 7 + [7] * 7 + [14] * 7)
        self.assertEqual(layout["anchors"], [0, 0, 0, 0.025, 0.025, 0.975, 0.975] * 3)
        self.assertEqual(ratio_layout(2, wrong_endpoints=True)["anchors"][-2:], [0.975, 0.975])
        x = np.array([-3, -1, 1, 3.0])
        h = np.column_stack([x, -x, 2 * x, 3 * x])
        f = 2 * h
        layout = dict(anchors=[0, 0.975, 0, 0.025], mass_columns=[0, 0, 2, 2])
        first = coefficient_product(np.eye(4), joint_slopes(f, h, layout, 1e-6), layout)
        f[:, :2] += x[:, None] * 10
        second = coefficient_product(np.eye(4), joint_slopes(f, h, layout, 1e-6), layout)
        np.testing.assert_array_equal(first[:, 2:], second[:, 2:])
        self.assertTrue(np.all(first[:2, 2:] == 0))

    def test_independent_stages_accounting_replay_and_corruption(self):
        p = {
            **plan(),
            "training_nodes": 128,
            "integration_fit_replicates": 8,
            "replicates": 4,
            "nodes_per_replicate": 64,
            "correction_nodes_per_replicate": 16,
        }
        sampling, calls, fine_calls = GaussianMixture(coincident=True), [], []

        def values(x):
            return np.column_stack([np.ones(len(x)), -3 + 2 * x[:, 0], x[:, 1]])

        def fine(x, q):
            fine_calls.append(x.copy())
            return values(x)

        def coarse(x, q):
            calls.append(x.copy())
            return values(x) + [2, -5, 1]

        entropy = [2026, 18, 7]
        layout = dict(anchors=[0, 0, 0.975], mass_columns=[0, 0, 0])
        out = integrate_controlled(fine, coarse, sampling, entropy=entropy, plan=p, layout=layout)
        self.assertEqual(sum(map(len, calls)), fitting_evaluations(p) + 4 * (64 + 16))
        points = np.vstack(calls)
        self.assertEqual(len(np.unique(points, axis=0)), len(points))
        np.testing.assert_array_equal(np.vstack(fine_calls), np.vstack(calls[-16:]))
        np.testing.assert_allclose(out["total"], np.tile([1, -3, 0], (4, 1)), atol=2e-6)
        validate_fit(out["fit"], sampling, [*entropy, 2], p, 3, layout)
        replay = integrate_controlled(
            fine, coarse, sampling, entropy=entropy, plan=p, layout=layout
        )
        self.assertEqual(json_bytes(out["fit"]), json_bytes(replay["fit"]))
        np.testing.assert_array_equal(out["total"], replay["total"])
        for change in (
            "slope",
            "response",
            "product",
            "entropy",
            "nodes",
            "shape",
            "base",
            "layout",
        ):
            bad = deepcopy(out["fit"])
            r = bad["joint_fit"]
            if change == "slope":
                r["mass_slopes"][0] += 1
            elif change == "response":
                r["function_means"][0][1] += 1
            elif change == "product":
                bad["coefficients"][0][1] += 1
                bad["coefficients_sha256"] = sha256(json_bytes(bad["coefficients"]))
            elif change == "entropy":
                r["entropy"][-1] = 0
            elif change == "nodes":
                r["nodes_per_replicate"] //= 2
            elif change == "shape":
                r["control_means"].pop()
            elif change == "base":
                r["base_fit"]["coefficients"][0][1] += 1
            else:
                r["layout"]["anchors"][1] = 0.1
            with self.assertRaises(ValueError, msg=change):
                validate_fit(bad, sampling, [*entropy, 2], p, 3, layout)

    def test_invalid_mass_layouts_fail(self):
        values = np.ones((4, 2))
        for layout in (
            dict(anchors=[0, 0.1], mass_columns=[0, 2]),
            dict(anchors=[0, 0.1], mass_columns=[1, 0]),
            dict(anchors=[0, np.nan], mass_columns=[0, 0]),
            dict(anchors=[0, 0.1], mass_columns=[False, 0]),
        ):
            with self.assertRaises(ValueError):
                joint_slopes(values, values, layout, 1e-6)


class TailTruthTests(unittest.TestCase):
    def test_moments_and_independent_student_noise_cdf_integration(self):
        expected = {
            5: ([0, 0], [2.6125 + 0.2 * 20 / 18, 1.075 + 0.4 * 20 / 18]),
            6: ([0, 0.4], [2.2125 + 0.2 * 20 / 18, 2.415 + 0.4 * 20 / 18]),
        }
        for index in (5, 6):
            target = TailTarget(index)
            truth = json.loads(tail_truth_bytes(index))
            np.testing.assert_allclose(truth["mean"], expected[index][0], atol=1e-14)
            np.testing.assert_allclose(np.array(truth["sd"]) ** 2, expected[index][1], atol=1e-14)
            for label, probability in (("low", 0.025), ("high", 0.975)):
                for j, contrast in enumerate(target.contrasts):
                    q = truth[label][j]
                    actual = 0.0
                    for w, mu, cov in zip(target.probabilities, target.means, target.covariances):
                        mean, sd = contrast @ mu, np.sqrt(contrast @ cov @ contrast)
                        actual += (
                            w
                            * quad(
                                lambda z: (
                                    t.pdf(z, 20)
                                    * norm.cdf((q - mean - np.sqrt(target.noise[j]) * z) / sd)
                                ),
                                -np.inf,
                                np.inf,
                                epsabs=1e-10,
                                epsrel=1e-10,
                            )[0]
                        )
                    self.assertAlmostEqual(actual, probability, places=9)

    def test_tail_support_finite_second_moments_and_frozen_parameters(self):
        p = plan()["tail_controls"]
        proposal = tail_proposal()
        self.assertFalse(proposal.diagnostics["fitted"])
        parts = proposal.components("stabilized-mixture")
        self.assertAlmostEqual(sum(w for w, *_ in parts), 1)
        self.assertEqual(len(parts), 4)
        np.testing.assert_array_equal(
            parts[-1][2], np.diag(p["proposal_defensive_covariance_diagonal"])
        )
        for index in (5, 6):
            target = TailTarget(index)
            np.testing.assert_array_equal(target.probabilities, p["component_probabilities"])
            np.testing.assert_array_equal(
                target.covariances[1],
                np.diag(
                    p["wide_covariance_diagonal" if index == 5 else "displaced_covariance_diagonal"]
                ),
            )
            if index == 6:
                np.testing.assert_array_equal(target.means[1], p["displaced_mean"])
            for cov in target.covariances:
                self.assertGreater(
                    np.linalg.eigvalsh(2 * np.linalg.inv(cov) - np.eye(4) / 9).min(), 0
                )
            self.assertTrue(np.isfinite(proposal.logpdf(target.means, "stabilized-mixture")).all())


if __name__ == "__main__":
    unittest.main()
