"""Independent Gaussian/polynomial references and fail-closed candidate selection."""

from copy import deepcopy
import json
from math import factorial
from pathlib import Path
import unittest

import numpy as np
from scipy.stats import multivariate_normal

from nfl_value.reference_pilot import validate_plan
from nfl_value.sparse_cubature import integrate as sparse_integrate
from nfl_value.tensor_controls import run, select
from nfl_value.tensor_cubature import integrate, rule
from nfl_value.variance_reference import NormalReferenceTransport, build_transport
from test_variance_reference import AnalyticTarget


class TensorTests(unittest.TestCase):
    def test_exact_zero_with_relative_only_tolerance_is_not_nan_or_failure(self):
        f = lambda x: np.zeros((len(x), 2))
        results = [sparse_integrate(f, 2, rtol=1e-4, atol=0, max_level=4, max_evaluations=1000)]
        for method in ["gauss-legendre", "gauss-hermite"]:
            results.append(integrate(f, 2, method=method, rtol=1e-4, atol=0, max_evaluations=1000))
        for result in results:
            self.assertEqual(result.status, "converged")
            np.testing.assert_array_equal(result.estimate, 0)
            np.testing.assert_array_equal(result.error, 0)
            self.assertEqual(result.history[-1]["maximum_error_ratio"], 0)

    def test_known_control_rejections_cannot_be_promoted_to_nfl_reference(self):
        plans = {
            f"gauss-{m}": json.loads(Path(f"config/variance-reference-{m}-v1.json").read_text())
            for m in ("legendre", "hermite")
        }
        model = json.loads(Path("config/continuous-variance-v1.json").read_text())
        result = run(model, plans)
        self.assertIsNone(result["selected"])
        self.assertFalse(result["nfl_data_used"] or result["calibration"])
        for record in result["controls"].values():
            self.assertFalse(record["controls_passed"])
            self.assertFalse(record["correct_endpoints"]["valid"])
            self.assertFalse(record["incorrect_endpoints"]["valid"])
        for p in plans.values():
            with self.assertRaisesRegex(ValueError, "failed frozen controls"):
                validate_plan(p)
        hermite = result["controls"]["gauss-hermite"]
        self.assertTrue(
            all(c["status"] == "converged" and c["valid"] for c in hermite["moments"][:3])
        )
        self.assertLess(max(c["maximum_actual_error"] for c in hermite["moments"][:3]), 1e-9)
        self.assertEqual(hermite["moments"][-1]["status"], "not_converged")
        self.assertTrue(
            any(
                not c["estimated_error_covers_actual"]
                for c in result["controls"]["gauss-legendre"]["moments"]
            )
        )

    def test_public_rule_moments_have_independent_analytic_answers(self):
        for order in [3, 7, 11, 15]:
            for method in ["gauss-legendre", "gauss-hermite"]:
                x, w = rule(method, order)
                for power in range(2 * order):
                    expected = (
                        1 / (power + 1)
                        if method == "gauss-legendre"
                        else 0
                        if power % 2
                        else factorial(power) / (2 ** (power // 2) * factorial(power // 2))
                    )
                    # Odd moments cancel large signed terms; scale by their
                    # absolute weighted magnitude, not the zero exact result.
                    scale = max(1, abs(expected), w @ np.abs(x**power))
                    self.assertAlmostEqual(
                        w @ (x**power) / scale,
                        expected / scale,
                        delta=1e-12,
                    )

    def test_complete_order_budget_and_signed_known_integral(self):
        for method in ["gauss-legendre", "gauss-hermite"]:
            calls = []

            def f(x):
                calls.extend(map(tuple, x))
                return np.column_stack([np.ones(len(x)), -(x[:, 0] ** 2), x[:, 0] * x[:, 1]])

            partial = integrate(f, 4, method=method, rtol=1e-6, atol=1e-8, max_evaluations=2402)
            self.assertEqual(partial.evaluations, 2401)
            self.assertEqual(partial.status, "not_converged")
            r = integrate(f, 4, method=method, rtol=1e-6, atol=1e-8, max_evaluations=90000)
            self.assertEqual(r.status, "converged")
            self.assertEqual(r.evaluations, 7**4 + 11**4)
            expected = [1, -1 / 3, 1 / 4] if method == "gauss-legendre" else [1, -1, 0]
            np.testing.assert_allclose(r.estimate, expected, atol=1e-12, rtol=0)
            again = integrate(f, 4, method=method, rtol=1e-6, atol=1e-8, max_evaluations=90000)
            np.testing.assert_array_equal(again.estimate, r.estimate)
            self.assertEqual(again.history, r.history)
        for method in ["unsupported", "gauss-legendre"]:
            with self.assertRaises(ValueError):
                integrate(
                    lambda x: np.full((len(x), 1), np.nan),
                    2,
                    method=method,
                    rtol=1e-4,
                    atol=1e-6,
                    max_evaluations=100,
                )

    def test_normal_geometry_has_exact_gaussian_density_and_jacobian(self):
        p = json.loads(Path("config/variance-reference-hermite-v1.json").read_text())
        with self.assertRaisesRegex(ValueError, "failed frozen controls"):
            validate_plan(p)
        axes = build_transport(AnalyticTarget(), p)
        g = NormalReferenceTransport(axes)
        z = np.array([[0.2, -1.1], [-3.0, 4.0]])
        eta = g.transform(z)
        np.testing.assert_allclose(
            g.logpdf(eta),
            multivariate_normal.logpdf(eta, mean=g.mean, cov=np.diag(g.scale**2)),
            atol=1e-12,
        )
        np.testing.assert_allclose(
            g.logpdf(eta),
            multivariate_normal.logpdf(z, mean=np.zeros(2), cov=np.eye(2)) - np.log(g.scale).sum(),
            atol=1e-12,
        )
        for changes in [
            {"cubature_rule": "gauss-legendre"},
            {"reference_transport": "independent_student_t5_moments"},
            {"reference_cache_nodes": 1024},
            {"cubature_max_subdivisions": 10},
            {"reference_sparse_level": 9},
        ]:
            with self.assertRaises(ValueError):
                validate_plan({**p, **changes})

    def test_selection_rejects_failed_controls_and_uses_frozen_tiebreak(self):
        report = dict(
            controls_passed=False,
            moments=[{"status": "converged"}],
            correct_endpoints={"evaluations": 100},
        )
        reports = {"gauss-legendre": deepcopy(report), "gauss-hermite": deepcopy(report)}
        self.assertIsNone(select(reports))
        reports["gauss-legendre"]["controls_passed"] = True
        self.assertEqual(select(reports), "gauss-legendre")
        reports["gauss-hermite"]["controls_passed"] = True
        self.assertEqual(select(reports), "gauss-legendre")
        reports["gauss-hermite"]["correct_endpoints"]["evaluations"] = 99
        self.assertEqual(select(reports), "gauss-hermite")


if __name__ == "__main__":
    unittest.main()
