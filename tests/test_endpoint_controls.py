"""Independent analytic identities, fitting isolation and immutable study contracts."""

from copy import deepcopy
import json
import runpy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.integrate import quad_vec
from scipy.special import ndtr
from scipy.stats import norm

from nfl_value.coarse_control_study import archive, validate_point_fit
from nfl_value.component_allocation import component_integrals
from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD, fit_control, training_points
from nfl_value.endpoint_controls import EndpointControls, fit_endpoint_basis
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.mode_preflight import (
    FreshCurvedTarget,
    FreshMixtureTarget,
    arms,
    experiment_kind,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.replicated_reference import SamplingProposal
from nfl_value.tail_controls import tail_proposal
from nfl_value.two_level_reference import sampling_hash


def plan(version=1):
    return json.loads(Path(f"config/endpoint-control-preflight-v{version}.json").read_text())


class AnalyticProposal(SamplingProposal):
    def __init__(self):
        super().__init__(np.zeros(1), np.eye(1), np.zeros(1), np.eye(1), {})

    def components(self, method):
        if method != METHOD:
            raise ValueError("unexpected method")
        return [
            (0.7, np.array([-1.0]), np.array([[1.44]]), None),
            (0.3, np.array([0.5]), np.array([[2.25]]), 5),
        ]


class EndpointControlTests(unittest.TestCase):
    def test_zero_integrals_against_independent_quadrature_with_student_sampling(self):
        q = AnalyticProposal()
        directions = [[[0.3, 1.2], [-1.5, -0.8]], [[1.1, -1.6], [-0.4, 0.2]]]
        basis = EndpointControls(q, directions)

        def integrand(x):
            points = np.array([[x]])
            logq = q.logpdf(points, METHOD)
            return basis.features(points, logq)[0] * np.exp(logq[0])

        integral, error = quad_vec(integrand, -np.inf, np.inf, epsabs=1e-10, epsrel=1e-10)
        self.assertLess(error, 1e-9)
        np.testing.assert_allclose(integral, 0, atol=3e-11)
        # A two-dimensional non-axis-aligned Gaussian expectation, independent tensor rule.
        nodes, weights = hermgauss(80)
        x, y = np.meshgrid(np.sqrt(2) * nodes, np.sqrt(2) * nodes)
        for b, a in [(0.7, [0.9, -0.5]), (-1.2, [0.2, 1.1]), (0, [0, 0])]:
            actual = np.sum(np.outer(weights, weights) * ndtr(b + a[0] * x + a[1] * y)) / np.pi
            self.assertAlmostEqual(actual, ndtr(b / np.sqrt(1 + np.dot(a, a))), places=12)

    def test_direction_fit_matches_independent_normal_equations_and_records_clipping(self):
        q, settings = AnalyticProposal(), plan()["endpoint_control"]
        points, weights = training_points(q, [90211], 256)
        logq = q.logpdf(points, METHOD)
        x = points[:, 0]
        y = np.column_stack(
            [np.ones(len(x)), -2 + x, x, ndtr(x), ndtr(-x), ndtr(2 + x), ndtr(2 - x)]
        )
        basis, evidence = fit_endpoint_basis(q, points, weights, logq, y, settings)
        probability = np.clip(y[:, 3:7], 1e-8, 1 - 1e-8)
        response = norm.ppf(probability)
        for j, (_, mean, cov, _) in enumerate(q.components(METHOD)):
            z = (x - mean[0]) / np.sqrt(cov[0, 0])
            w = weights * norm.pdf(x, mean[0], np.sqrt(cov[0, 0])) / np.exp(logq)
            w /= w.sum()
            design = np.column_stack([np.ones(len(x)), z])
            penalty = np.diag([0, settings["direction_ridge"]])
            answer = np.linalg.solve(
                design.T @ (w[:, None] * design) + penalty, design.T @ (w[:, None] * response)
            )
            np.testing.assert_allclose(basis.directions[j], answer.T, rtol=2e-13, atol=2e-13)
        record = evidence["endpoint_basis"]
        self.assertEqual(record["positive_mass_rows"], 256)
        self.assertGreater(sum(record["clipped_low"]) + sum(record["clipped_high"]), 0)
        bad = y.copy()
        bad[0, 3] = 1.1
        with self.assertRaisesRegex(ValueError, "probabilities"):
            fit_endpoint_basis(q, points, weights, logq, bad, settings)
        bad[0] = 0
        _, e = fit_endpoint_basis(q, points, weights, logq, bad, settings)
        self.assertEqual(e["endpoint_basis"]["zero_mass_rows"], 1)
        bad[0, 3] = 0.1
        with self.assertRaisesRegex(ValueError, "zero-mass"):
            fit_endpoint_basis(q, points, weights, logq, bad, settings)

    def test_signed_known_integral_and_independent_fit_do_not_change_target(self):
        q, settings, calls = AnalyticProposal(), plan()["endpoint_control"], []
        intercept, slopes = np.array([-1.2, -0.5, 1.2, 0.5]), np.array([0.5, -0.7, 0.5, -0.7])

        def f(x, logq):
            calls.append(len(x))
            z = (x[:, 0] + 1) / 1.2
            w = np.exp(norm.logpdf(x[:, 0], -1, 1.2) - logq)
            return w[:, None] * np.column_stack(
                [np.ones(len(x)), -2 + 0.3 * z, -3 - z, ndtr(intercept + z[:, None] * slopes)]
            )

        fitted = fit_control(
            f, q, entropy=[90212], nodes=512, relative_ridge=1e-6, endpoint_settings=settings
        )
        frozen = json_bytes(fitted.record())
        self.assertEqual(calls, [512])
        actual = component_integrals(
            f, q, entropy=[90213], replicates=16, counts=[256, 128], fitted=fitted
        )
        truth = np.r_[1, -2, -3, ndtr(intercept / np.sqrt(1 + slopes**2))]
        np.testing.assert_allclose(actual["controlled"].mean(axis=0), truth, atol=2e-5)
        self.assertEqual(frozen, json_bytes(fitted.record()))
        self.assertTrue(np.all(actual["controlled"][:, 1:3] < 0))
        validate_point_fit(
            fitted.record(),
            q,
            [90212],
            {"training_nodes": 512, "relative_ridge": 1e-6},
            7,
            endpoint_settings=settings,
        )
        corrupt = fitted.record()
        corrupt["endpoint_basis"]["centers"][0][0] += 0.1
        corrupt["endpoint_basis_sha256"] = sha256(json_bytes(corrupt["endpoint_basis"]))
        with self.assertRaisesRegex(ValueError, "analytic integral"):
            validate_point_fit(
                corrupt,
                q,
                [90212],
                {"training_nodes": 512, "relative_ridge": 1e-6},
                7,
                endpoint_settings=settings,
            )

    def test_collinear_constant_endpoints_remain_finite(self):
        q, settings = AnalyticProposal(), plan()["endpoint_control"]
        x = np.zeros((8, 1))
        y = np.tile([1, -1, -2, 0, 0.25, 1, 0.25], (8, 1))
        basis, evidence = fit_endpoint_basis(q, x, np.ones(8) / 8, q.logpdf(x, METHOD), y, settings)
        np.testing.assert_array_equal(basis.directions[:, :, 1:], 0)
        self.assertTrue(np.isfinite(basis.features(x, q.logpdf(x, METHOD))).all())
        self.assertEqual(evidence["endpoint_basis"]["clipped_low"], [8, 0, 0, 0])
        self.assertEqual(evidence["endpoint_basis"]["clipped_high"], [0, 0, 8, 0])

    def test_matched_methods_separate_evaluation_count_work_and_reconstruct_fit(self):
        for version in (1, 2):
            with self.subTest(version=version):
                self.check_matched_methods(version)

    def check_matched_methods(self, version):
        p = {
            **plan(version),
            "search_nodes": 64,
            "starts": 4,
            "ratio_starts": 2,
            "em_nodes": 128,
            "em_steps": 2,
            "mass_pilot_nodes": 128,
            "training_nodes": 256,
            "replicates": 8,
            "nodes_per_replicate": 64,
            "correction_nodes_per_replicate": 16,
            "trials": 1,
            "allocation_component_nodes": 4,
            "allocation_minimum_nodes": 2,
        }
        initial = tail_proposal()

        class Toy:
            def logpdf(self, x):
                return normal_logpdf(x, [-1, 0, 0, 0], np.eye(4))

            def integrand(self, truth):
                return lambda x, logq: (
                    np.exp(self.logpdf(x) - logq)[:, None]
                    * np.column_stack(
                        [
                            np.ones(len(x)),
                            x[:, :2],
                            ndtr(-2 - x[:, :2]),
                            ndtr(2 - x[:, :2]),
                            ndtr(1.5 - x[:, :2]),
                        ]
                    )
                )

        records = {}
        for arm, domain in (("candidate", 0), ("polynomial", 6)):
            r = trial(Toy(), initial, {}, p, [p["base_seed"], domain, 3, 0], arm)
            self.assertIn("coarse", r, r.get("error"))
            self.assertEqual(
                r["work"]["counts"]["coarse_evaluation"], 256 + 8 * 4 * 8 + 8 * (64 + 16)
            )
            case = dict(
                arm=arm,
                target=3,
                truth={},
                initial_sampling_sha256=sampling_hash(initial),
                records=[dict(trial=0, **r)],
                decision=summarize([r], p),
            )
            validate_case(case, initial, {}, p, target=Toy())
            if arm == "candidate":
                for change in ("directions", "responses_sha256", "coefficients"):
                    corrupt = deepcopy(case)
                    fit = corrupt["records"][0]["fit"]
                    if change == "directions":
                        fit["endpoint_basis"]["directions"][0][0][0] += 0.1
                    elif change == "coefficients":
                        fit["coefficients"][0][0] += 0.1
                        fit["coefficients_sha256"] = sha256(json_bytes(fit["coefficients"]))
                    else:
                        fit[change] = "0" * 64
                    with self.assertRaises(ValueError):
                        validate_case(corrupt, initial, {}, p, target=Toy())
            records[arm] = r
        self.assertEqual(records["candidate"]["geometry"], records["polynomial"]["geometry"])
        for key in ("training_entropy", "points_sha256", "responses_sha256"):
            self.assertEqual(records["candidate"]["fit"][key], records["polynomial"]["fit"][key])
        self.assertEqual(
            records["candidate"]["components"]["pilot_plain"],
            records["polynomial"]["components"]["pilot_plain"],
        )
        self.assertNotEqual(
            records["candidate"]["components"]["coarse_entropy"],
            records["polynomial"]["components"]["coarse_entropy"],
        )

    def test_diagnostics_retain_failed_confidence_and_explicit_zero_variance(self):
        analyze = runpy.run_path("scripts/analyze_mode_preflight.py")["endpoint_diagnostics"]
        r = np.arange(4.0)
        coarse, plain, correction = (np.zeros((4, 9)) for _ in range(3))
        coarse[:, 3] = r
        plain[:, 3] = 2 * r
        correction[:, 3] = 0.5 * r
        record = dict(
            trial=0,
            status="failed",
            coarse=coarse,
            plain_coarse=plain,
            correction=correction,
            fit=dict(coefficient_norm=2),
        )
        out = analyze([record, dict(trial=1, status="unattempted")])
        self.assertEqual((out["requested"], out["retained_raw_trials"]), (2, 1))
        row = out["trials"][0]
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["controlled_plain_variance_ratio"], [0.25, None, None, None])
        self.assertAlmostEqual(row["correction_variance_fraction"][0], 0.2, places=15)
        self.assertEqual(row["correction_variance_fraction"][1:], [None, None, None])
        self.assertAlmostEqual(row["residual_variances"]["coarse"][0], 5 / 3)

    def test_frozen_fresh_geometries_and_gate_precede_nfl_access(self):
        p = plan()
        validate_plan(p)
        self.assertEqual(sum(len(ids) for _, ids in arms(p)) * p["trials"], 768)
        curve = FreshCurvedTarget(p["fresh_targets"]["10"])
        z = np.array([[0.3, -0.2, 1.1, 0.7], [-1, 0.3, -0.5, -0.2]])
        x = z.copy()
        x[:, 1] += -0.8 * np.sin(z[:, 0])
        x[:, 3] += -0.8 * np.sin(z[:, 2])
        np.testing.assert_allclose(curve.inverse(x), z, atol=1e-15)
        np.testing.assert_allclose(
            curve.logpdf(x), normal_logpdf(z, [0] * 4, np.eye(4)), atol=1e-14
        )
        mixture = FreshMixtureTarget(p["fresh_targets"]["11"])
        expected = sum(
            w * np.exp(normal_logpdf(x, m, c))
            for w, m, c in zip(mixture.probabilities, mixture.means, mixture.covariances)
        )
        np.testing.assert_allclose(np.exp(mixture.logpdf(x)), expected, rtol=1e-13)
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(json_bytes(dict(plan=p, experiment=experiment_kind(p))), manifest=True)
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()
        p["endpoint_control"]["probability_clip"] = 1e-5
        with self.assertRaisesRegex(ValueError, "frozen design"):
            validate_plan(p)


if __name__ == "__main__":
    unittest.main()
