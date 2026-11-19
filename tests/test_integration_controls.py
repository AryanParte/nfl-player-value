"""Analytical integration-covariance answers and independent-stage accounting."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np

from nfl_value.coarse_control_study import (
    experiment_name,
    fitting_evaluations,
    validate_fit,
    validate_plan,
)
from nfl_value.control_variates import integrate_controlled
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.integration_controls import integration_scales
from test_control_variates import GaussianMixture


def plan():
    return json.loads(Path("config/coarse-control-v2.json").read_text())


class IntegrationControlTests(unittest.TestCase):
    def test_frozen_budget_and_rules(self):
        p = plan()
        old = json.loads(Path("config/coarse-control-v1.json").read_text())
        validate_plan(p)
        changed = {
            "base_seed",
            "plan_version",
            "training_nodes",
            "integration_fit_replicates",
            "integration_scale_ridge",
            "preceding_control_report",
            "preceding_nfl_report",
        }
        self.assertEqual(
            {k: v for k, v in p.items() if k not in changed},
            {k: v for k, v in old.items() if k not in changed},
        )
        work = (
            fitting_evaluations(p)
            + p["replicates"] * (p["nodes_per_replicate"] + 2 * p["correction_nodes_per_replicate"])
            + 1
        )
        self.assertEqual(work, 88065)
        self.assertLess(work, p["maximum_target_evaluations_per_case"])
        self.assertNotEqual(experiment_name(p, "controls"), experiment_name(old, "controls"))
        for key in ("integration_fit_replicates", "integration_scale_ridge", "base_seed"):
            with self.assertRaises(ValueError):
                validate_plan({**p, key: p[key] * 2})

    def test_analytical_covariance_centering_signed_scales_and_zero_variance(self):
        x = np.array([-3.0, -1.0, 1.0, 3.0])
        orthogonal = np.array([1.0, -1.0, -1.0, 1.0])
        controls = np.column_stack([x + 17, x - 8, np.full(4, 2.0)])
        responses = np.column_stack([2 * x + orthogonal - 20, -3 * x + 5, x])
        ridge = 0.1
        result = integration_scales(responses, controls, ridge)
        np.testing.assert_allclose(result["alpha"], [2 / 1.1, -3 / 1.1, 0], atol=1e-15)
        np.testing.assert_allclose(result["cross_products"], [40, -60, 0], atol=0)
        np.testing.assert_allclose(result["control_squares"], [20, 20, 0], atol=0)
        # Offsets, jointly permuting nets, and signed rescaling don't change the
        # adjusted integral. No nonnegative or unit-interval alpha constraint.
        transformed = integration_scales(responses[::-1] + 100, -2 * controls[::-1], ridge)
        np.testing.assert_allclose(np.array(transformed["alpha"]) * -2, result["alpha"])

    def test_two_fits_evaluation_and_correction_are_disjoint_and_fully_counted(self):
        p = {
            **plan(),
            "training_nodes": 128,
            "integration_fit_replicates": 8,
            "replicates": 4,
            "nodes_per_replicate": 64,
            "correction_nodes_per_replicate": 16,
        }
        sampling = GaussianMixture(coincident=True)
        fine_calls, coarse_calls = [], []

        def values(x):
            return np.column_stack([np.ones(len(x)), -3 + 2 * x[:, 0], x[:, 1]])

        def fine(x, q):
            fine_calls.append(x.copy())
            return values(x)

        def coarse(x, q):
            coarse_calls.append(x.copy())
            return values(x) + [2, -5, 1]

        entropy = [2026, 17, 10]
        out = integrate_controlled(fine, coarse, sampling, entropy=entropy, plan=p)
        self.assertEqual(sum(map(len, coarse_calls)), fitting_evaluations(p) + 4 * (64 + 16))
        self.assertEqual(sum(map(len, fine_calls)), 4 * 16)
        # All coarse draws unique across the four entropy domains. Fine and coarse
        # correction deliberately share points, preserving their covariance.
        points = np.vstack(coarse_calls)
        self.assertEqual(len(np.unique(points, axis=0)), len(points))
        np.testing.assert_array_equal(np.vstack(fine_calls), np.vstack(coarse_calls[-16:]))
        np.testing.assert_allclose(out["total"], np.tile([1, -3, 0], (4, 1)), atol=2e-6)
        np.testing.assert_allclose(out["correction"], np.tile([-2, 5, -1], (4, 1)), atol=1e-14)
        validate_fit(out["fit"], sampling, [*entropy, 2], p, 3)
        stage = out["fit"]["integration_fit"]
        self.assertEqual(stage["entropy"], [*entropy, 3])
        self.assertEqual(stage["nodes_per_replicate"], p["nodes_per_replicate"])
        again = integrate_controlled(fine, coarse, sampling, entropy=entropy, plan=p)
        self.assertEqual(json_bytes(out["fit"]), json_bytes(again["fit"]))
        for key in ("total", "coarse", "plain_coarse", "correction"):
            np.testing.assert_array_equal(out[key], again[key])

        for change in ("alpha", "response", "product", "entropy", "nodes", "shape", "base"):
            bad = deepcopy(out["fit"])
            r = bad["integration_fit"]
            if change == "alpha":
                r["alpha"][1] += 1
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
            else:
                r["base_fit"]["coefficients"][0][1] += 1
            with self.assertRaises(ValueError, msg=change):
                validate_fit(bad, sampling, [*entropy, 2], p, 3)

    def test_invalid_covariance_inputs_fail(self):
        valid = np.ones((4, 3))
        for f, h, ridge in (
            (valid[:3], valid[:3], 1e-6),
            (valid, valid[:, :2], 1e-6),
            (valid, valid * np.nan, 1e-6),
            (valid, valid, 0),
            (valid, valid, -1),
            (valid, valid, np.inf),
        ):
            with self.assertRaises(ValueError):
                integration_scales(f, h, ridge)


if __name__ == "__main__":
    unittest.main()
