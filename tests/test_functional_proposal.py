"""Analytical moment, sampling independence and proposal integrity checks."""

from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy.integrate import quad
from scipy.stats import multivariate_normal, norm, t

from nfl_value.coarse_control_study import (
    assessment_plan,
    fitting_evaluations,
    known_case_count,
    validate_fit,
    validate_plan,
    plain_assessment,
    validate_known,
    validate_archive,
)
from nfl_value.density_holdout import coverage_summary
from nfl_value.control_variates import GaussianControls, integrate_controlled
from nfl_value.functional_proposal import (
    envelopes,
    fit_functional_proposal,
    moment_component,
    restore_functional,
    validate_functional_fit,
)
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.joint_controls import ratio_layout
from nfl_value.tail_controls import TailTarget, tail_proposal, tail_truth_bytes
from nfl_value.two_level_reference import sampling_hash, restore_proposal
from nfl_value.replicated_reference import summarize_integrals, diagnose_reference
from nfl_value.coarse_control_study import plain_reference
from nfl_value.reference_pilot import CASES


def plan():
    return json.loads(Path("config/coarse-control-v4.json").read_text())


def small_plan():
    return {
        **plan(),
        "proposal_nodes": 128,
        "training_nodes": 128,
        "replicates": 4,
        "nodes_per_replicate": 64,
        "correction_nodes_per_replicate": 16,
    }


def normal_values(points, logq):
    weight = np.exp(-0.5 * np.sum(points**2, axis=1) - 2 * np.log(2 * np.pi) - logq)
    return weight[:, None] * np.column_stack(
        [
            np.ones(len(points)),
            points[:, 0],
            np.full(len(points), 0.025),
            np.full(len(points), 0.975),
        ]
    )


class FunctionalProposalTests(unittest.TestCase):
    def test_failed_confidence_retains_and_validates_fitted_evidence(self):
        p = {**small_plan(), "coverage_trials": 1, "initial_stress_trials": 0}
        initial = tail_proposal()
        layout = ratio_layout(2, wrong_endpoints=True)

        def f(x, q):
            v = normal_values(x, q)
            return v[:, [0, 1, 1, 2, 2, 3, 3, 3, 3]]

        entropy = [p["base_seed"], 0, 0, 0]
        out = integrate_controlled(f, f, initial, entropy=entropy, plan=p, layout=layout)
        out["coarse"][0, 0] = -1  # deliberately invalid numerical mass
        raw = out["coarse"] + out["correction"]
        assessment = plain_assessment(raw, assessment_plan(p, 0))
        self.assertEqual(assessment["status"], "failed")
        r = dict(
            trial=0,
            entropy=entropy,
            coarse=out["coarse"].tolist(),
            correction=out["correction"].tolist(),
            plain_coarse=out["plain_coarse"].tolist(),
            fit=out["fit"],
            plain_assessment=plain_assessment(
                out["plain_coarse"] + out["correction"], assessment_plan(p, 0)
            ),
            **assessment,
        )
        geometry = initial.diagnostics
        case = dict(
            target=0,
            truth={},
            geometry_sha256=sha256(json_bytes(geometry)),
            sampling_sha256=sampling_hash(initial),
            records=[r],
            decision=coverage_summary([r], assessment_plan(p, 0)),
        )
        result = dict(
            experiment="coarse-control-controls-v4",
            plan=p,
            cases=[case],
            nfl_data_used=False,
            ranking_ready=False,
            calibration_completed=False,
            controls_passed=False,
            initial_stress=[],
        )
        with (
            patch("nfl_value.coarse_control_study.known_parents", return_value=({}, {})),
            patch("nfl_value.coarse_control_study.known_case_count", return_value=1),
            patch(
                "nfl_value.coarse_control_study.known_inputs",
                return_value=(None, initial, geometry, json_bytes({})),
            ),
        ):
            self.assertFalse(validate_known(result))
            r["fit"]["proposal_fit"]["entropy"][-1] = 0
            with self.assertRaisesRegex(ValueError, "provenance"):
                validate_known(result)

    def test_archived_reference_binds_the_actual_fitted_proposal(self):
        p = small_plan()
        model_plan = dict(log_precision_mean=0.0, log_precision_sd=3.0)
        geometry = dict(
            pilot_initial_geometry=dict(mode=[0.0] * 4, covariance=np.eye(4).tolist()),
            component_means=np.zeros((3, 4)).tolist(),
            component_covariances=np.array([np.eye(4)] * 3).tolist(),
            component_masses=[1 / 3] * 3,
            geometry_uses_primary_qmc=False,
            learning_is_target_density_only=True,
        )
        initial = restore_proposal(geometry, model_plan)
        cases = {}
        for i, name in enumerate(CASES):
            entropy = [p["base_seed"], 1, i, 0]
            out = integrate_controlled(
                normal_values,
                normal_values,
                initial,
                entropy=entropy,
                plan=p,
                layout=ratio_layout(1),
            )
            sampling = out["sampling"]
            reference = summarize_integrals(
                out["total"], {0.0: {"mean": [0.0]}}, p, sampling, "stabilized-mixture"
            )
            cases[name] = dict(
                status="complete",
                entropy=entropy,
                fit=out["fit"],
                coarse=out["coarse"].tolist(),
                plain_coarse=out["plain_coarse"].tolist(),
                correction=out["correction"].tolist(),
                reference=reference,
                geometry_sha256=sha256(json_bytes(sampling.diagnostics)),
                sampling_sha256=sampling_hash(sampling),
                contrasts=1,
                shifts=[0.0],
                primary_qmc_valid=True,
                numerical_valid=reference["valid"],
                plain_reference=plain_reference(
                    out["plain_coarse"] + out["correction"], 1, [0.0], p, sampling
                ),
                diagnosis=diagnose_reference(reference, contrasts=1, shifts=[0.0], plan=p),
                evaluations={"fine": 4 * 16 + 1, "coarse": 4 * (64 + 16) + fitting_evaluations(p)},
            )
        result = dict(
            plan=p,
            cases=cases,
            model_plan=model_plan,
            nfl_data_used=True,
            calibration_completed=False,
            ranking_ready=False,
            numerical_pilot_passed=all(r["numerical_valid"] for r in cases.values()),
        )
        with patch("nfl_value.coarse_control_study.validate_plan"):
            validate_archive(result)
            cases[CASES[0]]["fit"]["proposal_fit"] = deepcopy(
                cases[CASES[0]]["fit"]["proposal_fit"]
            )
            cases[CASES[0]]["fit"]["proposal_fit"]["component_means"][0][0] += 0.1
            with self.assertRaisesRegex(ValueError, "reference geometry differs"):
                validate_archive(result)

    def test_frozen_budget_and_separate_control_families(self):
        p = plan()
        validate_plan(p)
        self.assertEqual(known_case_count(p), 8)
        self.assertEqual(fitting_evaluations(p) + 64 * (1024 + 2 * 32) + 1, 88065)
        old = json.loads(Path("config/coarse-control-v3.json").read_text())
        for key in (
            "replicates",
            "nodes_per_replicate",
            "coverage_trials",
            "correction_nodes_per_replicate",
            "reference_mean_tolerance_sd",
            "reference_endpoint_cdf_tolerance",
            "minimum_precision_fraction",
            "maximum_target_evaluations_per_case",
            "maximum_seconds_per_case",
            "maximum_seconds_total",
            "future_test",
            "cases",
        ):
            self.assertEqual(p[key], old[key])
        for index in range(7):
            for key in ("marginal_undercoverage_alpha", "joint_undercoverage_alpha"):
                self.assertEqual(assessment_plan(p, index)[key], assessment_plan(old, index)[key])
        self.assertEqual(assessment_plan(p, 7)["marginal_undercoverage_alpha"], 0.01 / 7)
        self.assertEqual(assessment_plan(p, 7)["joint_undercoverage_alpha"], 0.01)
        self.assertEqual(assessment_plan(p, 7)["plan_version"], 2)
        with self.assertRaises(ValueError):
            validate_plan({**p, "proposal_nodes": 4096})

    def test_envelopes_have_independent_answers_and_prior_scale_invariance(self):
        f = np.array([[1, -2, 0.01, 0.99], [3, 6, 0.15, 2.85]])
        q = np.array([0.25, 0.75])
        layout = ratio_layout(1)
        e, z = envelopes(f, q, layout)
        self.assertEqual(z, [2.5])
        np.testing.assert_allclose(e, [[1.2, 0.006, 0.006], [3.6, 0.03, 0.03]], atol=1e-15)
        # An independently scaled prior must not dominate another prior's fit.
        doubled, zs = envelopes(np.column_stack([f, f * 100]), q, ratio_layout(1, 2))
        np.testing.assert_allclose(doubled, e, atol=1e-15)
        np.testing.assert_allclose(zs, [2.5, 250])
        signed = f.copy()
        signed[:, 1] *= -1
        np.testing.assert_array_equal(envelopes(signed, q, layout)[0], e)
        for bad in (f * np.nan, np.column_stack([[-1, -3], f[:, 1:]]), f * 0):
            with self.assertRaises(ValueError):
                envelopes(bad, q, layout)
        bad_layout = deepcopy(layout)
        bad_layout["mass_columns"][1] = 1
        with self.assertRaises(ValueError):
            envelopes(f, q, bad_layout)

    def test_moments_and_shrinkage_against_hand_computed_values(self):
        x = np.array([[-1.0, 0], [1.0, 2]])
        ref = np.eye(2) * 2
        mean, cov, d = moment_component(x, np.array([1.0, 3]), ref, (np.zeros(2), np.eye(2)))
        np.testing.assert_allclose(mean, [0.5, 1.5])
        empirical = np.ones((2, 2)) * 0.75
        np.testing.assert_allclose(d["centered_covariance"], empirical)
        self.assertAlmostEqual(d["effective_weights"], 1.6)
        np.testing.assert_allclose(cov, 1.5 * (1.6 * empirical + 4 * ref) / 5.6, atol=1e-14)
        zero = moment_component(x, np.zeros(2), ref, (np.array([3.0, 4]), ref))
        np.testing.assert_array_equal(zero[0], [3, 4])
        np.testing.assert_array_equal(zero[1], ref)
        self.assertEqual(zero[2], {"active": False, "reason": "zero_envelope"})

    def test_adaptation_preserves_support_and_does_not_use_known_truth(self):
        p = small_plan()
        initial = tail_proposal()
        with patch.object(TailTarget, "exact", side_effect=AssertionError("truth access")):
            result = fit_functional_proposal(
                normal_values, initial, entropy=[1, 4], plan=p, layout=ratio_layout(1)
            )
        self.assertEqual(len(result.components("stabilized-mixture")), 4)
        self.assertEqual(
            [m for m, *_ in result.components("stabilized-mixture")], [0.3, 0.3, 0.3, 0.1]
        )
        np.testing.assert_array_equal(result.prior_mean, initial.prior_mean)
        np.testing.assert_array_equal(result.prior_covariance, initial.prior_covariance)
        self.assertTrue(
            np.isfinite(result.logpdf([[100, -100, 100, -100]], "stabilized-mixture")).all()
        )
        restored = restore_functional(result.diagnostics)
        self.assertEqual(sampling_hash(result), sampling_hash(restored))
        validate_functional_fit(
            result.diagnostics, initial, entropy=[1, 4], plan=p, layout=ratio_layout(1)
        )

    def test_independent_training_evaluation_paired_correction_and_exact_work(self):
        p, initial = small_plan(), tail_proposal()
        calls, fine_calls = [], []

        def coarse(x, q):
            calls.append(x.copy())
            value = normal_values(x, q)
            value[:, 1] -= 3 * value[:, 0]
            return value * 1.001

        def fine(x, q):
            fine_calls.append(x.copy())
            value = normal_values(x, q)
            value[:, 1] -= 3 * value[:, 0]
            return value

        entropy = [2026, 19, 42]
        out = integrate_controlled(
            fine, coarse, initial, entropy=entropy, plan=p, layout=ratio_layout(1)
        )
        self.assertEqual(sum(map(len, calls)), fitting_evaluations(p) + 4 * (64 + 16))
        all_points = np.vstack(calls)
        self.assertEqual(len(np.unique(all_points, axis=0)), len(all_points))
        np.testing.assert_array_equal(np.vstack(fine_calls), np.vstack(calls[-16:]))
        self.assertNotIn("joint_fit", out["fit"])
        self.assertNotIn("integration_fit", out["fit"])
        validate_fit(out["fit"], initial, [*entropy, 2], p, 4, ratio_layout(1))
        replay = integrate_controlled(
            fine, coarse, initial, entropy=entropy, plan=p, layout=ratio_layout(1)
        )
        self.assertEqual(json_bytes(out["fit"]), json_bytes(replay["fit"]))
        np.testing.assert_array_equal(out["total"], replay["total"])
        self.assertTrue(np.all(out["total"][:, 1] < 0))
        # Fixed constant probability ratios survive adaptation and correction.
        np.testing.assert_allclose(
            out["total"][:, 2:] / out["total"][:, [0]], [[0.025, 0.975]] * 4, atol=1e-14
        )

    def test_geometry_and_stage_corruption_cannot_relabel_a_fit(self):
        p, initial = small_plan(), tail_proposal()
        good = fit_functional_proposal(
            normal_values, initial, entropy=[2, 4], plan=p, layout=ratio_layout(1)
        ).diagnostics
        for kind in (
            "stage_entropy",
            "stage_covariance",
            "final",
            "support",
            "layout",
            "mass",
            "nodes",
            "zero",
        ):
            g = deepcopy(good)
            s = g["stages"][0]
            if kind == "stage_entropy":
                s["entropy"][-1] += 1
            elif kind == "stage_covariance":
                s["component_covariances"][0][0][0] += 1
            elif kind == "final":
                g["component_means"][0][0] += 1
            elif kind == "support":
                g["defensive_covariance"][0][0] += 1
            elif kind == "layout":
                g["layout"]["anchors"][1] = 0.025
            elif kind == "mass":
                s["prior_mass_estimates"][0] = -1
            elif kind == "nodes":
                s["nodes"] += 1
            else:
                s["moments"][0] = {"active": False, "reason": "zero_envelope"}
            # Even a recomputed content hash cannot hide inconsistent geometry.
            s["stage_sha256"] = sha256(
                json_bytes({k: v for k, v in s.items() if k != "stage_sha256"})
            )
            with self.assertRaises((ValueError, np.linalg.LinAlgError), msg=kind):
                validate_functional_fit(g, initial, entropy=[2, 4], plan=p, layout=ratio_layout(1))

    def test_adapted_gaussian_controls_still_have_zero_integral(self):
        # Independently integrate q*h using Gaussian quadrature for each basis
        # component: integral(phi_k H)-integral(q) = 0 for the constant column,
        # and centered Gaussian first/second moments vanish for all others.
        from scipy.special import roots_hermitenorm

        p, initial = small_plan(), tail_proposal()
        sampling = fit_functional_proposal(
            normal_values, initial, entropy=[3, 4], plan=p, layout=ratio_layout(1)
        )
        basis = GaussianControls(sampling)
        z, w = roots_hermitenorm(3)
        grid = np.array(np.meshgrid(z, z, z, z, indexing="ij")).reshape(4, -1).T
        weight = (
            np.prod(np.array(np.meshgrid(w, w, w, w, indexing="ij")), axis=0).ravel()
            / (2 * np.pi) ** 2
        )
        expected = []
        for j, (_mass, mean, cov, _df) in enumerate(sampling.components("stabilized-mixture")):
            x = mean + grid @ np.linalg.cholesky(cov).T
            centered = (x - mean) @ np.linalg.inv(np.linalg.cholesky(cov)).T
            q = np.exp(sampling.logpdf(x, "stabilized-mixture"))
            density = multivariate_normal.pdf(x, mean=mean, cov=cov)
            polynomial = np.column_stack(
                [
                    np.ones(len(x)),
                    centered,
                    *[
                        centered[:, i] * centered[:, k] - int(i == k)
                        for i in range(4)
                        for k in range(i, 4)
                    ],
                ]
            )
            identity = density[:, None] * polynomial
            identity[:, 0] -= q
            actual = basis.features(x, np.log(q))[:, j * 15 : (j + 1) * 15] * q[:, None]
            np.testing.assert_allclose(actual, identity, rtol=1e-12, atol=1e-13)
            expected.append(float(weight.sum() - 1))
            expected.extend(weight @ centered)
            expected.extend(
                weight @ (centered[:, i] * centered[:, j] - int(i == j))
                for i in range(4)
                for j in range(i, 4)
            )
        self.assertEqual(len(expected), basis.width)
        np.testing.assert_allclose(expected, 0, atol=1e-14)

    def test_remote_truth_uses_reverse_noise_convolution(self):
        target = TailTarget(7)
        truth = json.loads(tail_truth_bytes(7))
        means = target.means @ target.contrasts.T
        variances = np.array(
            [
                np.einsum("ij,jk,ik->i", target.contrasts, c, target.contrasts)
                for c in target.covariances
            ]
        )
        expected = target.probabilities @ means
        np.testing.assert_allclose(truth["mean"], expected)
        np.testing.assert_allclose(
            np.square(truth["sd"]),
            target.probabilities @ (variances + (means - expected) ** 2) + target.noise * 20 / 18,
        )
        for label, p in (("low", 0.025), ("high", 0.975)):
            for j in range(2):
                q = truth[label][j]
                actual = sum(
                    prob
                    * quad(
                        lambda e: (
                            t.pdf(e, 20)
                            * norm.cdf((q - m[j] - np.sqrt(target.noise[j]) * e) / np.sqrt(v[j]))
                        ),
                        -np.inf,
                        np.inf,
                        epsabs=2e-11,
                    )[0]
                    for prob, m, v in zip(target.probabilities, means, variances)
                )
                self.assertAlmostEqual(actual, p, places=9)


if __name__ == "__main__":
    unittest.main()
