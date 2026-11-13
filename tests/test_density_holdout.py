"""Independent covariance algebra, holdout moments and non-admission contracts."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.integrate import quad
from scipy.special import stdtr
from scipy.stats import norm, t

from nfl_value.adaptive_proposal import AdaptiveProposal, shrink_covariance, weighted_mixture
from nfl_value.density_cli import load, pilot, save, validate_pilot_manifest
from nfl_value.density_holdout import (
    CurvedTarget,
    StabilizedProposal,
    coverage_summary,
    density_metrics,
    holdout,
    known_target,
    paired_summary,
    validate_density,
    validate_known,
    validate_plan,
)
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.replicated_reference import reference_integral
import scipy


def plan():
    return json.loads(Path("config/density-holdout-v2.json").read_text())


class DensityTests(unittest.TestCase):
    def test_supplied_proposal_integrates_independent_signed_student_t_answers(self):
        location = np.array([-2.0, 0.0])
        scale = np.sqrt(0.2)

        class Target:
            def log_target(self, point):
                return float(norm.logpdf(point[0]))

            def prior(self, point, shift):
                return np.array([self.log_target(point)])

            def conditional(self, point, contrasts):
                return dict(
                    diagonal=np.ones(2),
                    posterior_scale=np.array([2.0]),
                    posterior_shape=10.0,
                    location=location[:, None],
                    log_likelihood=np.array([0.0]),
                )

        proposal = StabilizedProposal(
            np.zeros(1),
            np.eye(1),
            np.zeros(1),
            np.eye(1),
            {"synthetic": True},
            np.zeros((3, 1)),
            np.ones((3, 1, 1)),
            np.full(3, 1 / 3),
        )
        summaries = {
            0.0: dict(
                mean=location,
                sd=np.full(2, scale * np.sqrt(20 / 18)),
                low=location + scale * t.ppf(0.025, 20),
                high=location + scale * t.ppf(0.975, 20),
            )
        }
        with patch(
            "nfl_value.replicated_reference.fit_proposal", side_effect=AssertionError("refit")
        ):
            result = reference_integral(
                Target(),
                np.eye(2),
                summaries,
                {**plan(), "replicates": 4, "nodes_per_replicate": 32},
                "stabilized-mixture",
                99,
                sampling=proposal,
            )
        self.assertTrue(result["valid"])
        self.assertEqual(result["geometry"], {"synthetic": True})
        np.testing.assert_allclose(
            result["bounds"]["estimate"],
            [1, 0, 0, 0.025, 0.025, 0.975, 0.975],
            atol=1e-13,
        )

    def test_pilot_replay_rejects_policy_environment_and_admission_drift(self):
        p = plan()
        manifest = dict(
            experiment="stabilized-reference-pilot-v1",
            plan=p,
            plan_sha256=sha256(json_bytes(p)),
            primary_plan={"synthetic": True},
            primary_plan_sha256=sha256(json_bytes({"synthetic": True})),
            environment=dict(numpy=np.__version__, scipy=scipy.__version__),
            calibration_completed=False,
            ranking_ready=False,
        )
        validate_pilot_manifest(manifest)
        for key, value in [
            ("plan_sha256", "f" * 64),
            ("primary_plan_sha256", "0" * 64),
            ("ranking_ready", True),
            ("environment", dict(numpy="wrong", scipy=scipy.__version__)),
        ]:
            with self.assertRaises(ValueError):
                validate_pilot_manifest({**manifest, key: value})

    def test_covariance_shrinkage_matches_independent_weighted_matrix_identity(self):
        x = np.array([[0.0, 0.0], [1.0, 2.0], [3.0, -1.0], [-2.0, 1.0]])
        w = np.array([0.97, 0.01, 0.01, 0.01])
        mean = np.sum(x * w[:, None], axis=0)
        empirical = sum(wi * np.outer(xi - mean, xi - mean) for xi, wi in zip(x, w))
        reference = np.array([[2.0, 0.25], [0.25, 1.0]])
        actual, n = shrink_covariance(empirical, w, reference)
        effective = 1 / sum(float(a) ** 2 for a in w)
        expected = (effective * empirical + 4 * reference) / (effective + 4)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-15)
        self.assertAlmostEqual(n, effective)
        singular = np.diag([2.0, 0.0])
        a, _ = shrink_covariance(singular, [1.0, 0.0, 0.0], np.eye(2))
        np.testing.assert_allclose(a, np.diag([1.2, 0.8]), rtol=0, atol=1e-15)
        for weights in [[0, 0], [-1, 2], [np.nan, 1]]:
            with self.assertRaises(ValueError):
                shrink_covariance(empirical, weights, reference)
        with self.assertRaises(np.linalg.LinAlgError):
            shrink_covariance(empirical, w, -np.eye(2))

    def test_rank_deficient_pilot_remains_supported_and_legacy_mode_is_unchanged(self):
        x = np.column_stack([np.linspace(-1, 1, 32), np.zeros(32)])
        weights = np.r_[0.95, np.full(31, 0.05 / 31)]
        old = weighted_mixture(x, weights, [1713])
        explicit = weighted_mixture(x, weights, [1713], reference_covariance=None)
        for a, b in zip(old[:3], explicit[:3]):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(old[3], explicit[3])
        new = weighted_mixture(x, weights, [1713], reference_covariance=np.eye(2))
        self.assertLess(np.linalg.eigvalsh(old[1]).min(), 1.1e-6)
        self.assertGreater(np.linalg.eigvalsh(new[1]).min(), 0.01)
        self.assertEqual(new[3]["shrinkage_pseudo_count"], 4)
        self.assertTrue(
            all(all(n >= 1 for n in r["component_effective_samples"]) for r in new[3]["attempts"])
        )
        self.assertAlmostEqual(new[2].sum(), 1)

    def test_paired_holdout_ratios_match_normal_density_answers(self):
        def sampling(cls, mean, var):
            return cls(
                np.array([mean]),
                np.array([[var]]),
                np.array([mean]),
                np.array([[var]]),
                {},
                np.full((3, 1), mean),
                np.full((3, 1, 1), var),
                np.full(3, 1 / 3),
            )

        class Target:
            def logpdf(self, x):
                return norm.logpdf(np.asarray(x)[:, 0])

            def log_target(self, x):
                return float(norm.logpdf(x[0]))

        old = sampling(AdaptiveProposal, 0.7, 1.5)
        new = sampling(StabilizedProposal, 0.0, 1.0)
        result = holdout(
            Target(), [(old, "adaptive-mixture"), (new, "stabilized-mixture")], plan(), 88, 0
        )
        expected = 0.5 * (np.log(1.5) + (1 + 0.7**2) / 1.5 - 1)
        second = 1.5 / np.sqrt(2 * 1.5 - 1) * np.exp(0.7**2 / (2 * 1.5 - 1))
        self.assertAlmostEqual(result["heldout_log_score_gain"], expected, delta=0.005)
        self.assertAlmostEqual(result["c2_existing"], second, delta=0.02)
        self.assertAlmostEqual(result["c2_stabilized"], 1, delta=0.005)
        self.assertLess(result["log_c2_ratio"], 0)
        identical = holdout(
            Target(),
            [
                (sampling(AdaptiveProposal, 0.0, 1.0), "adaptive-mixture"),
                (new, "stabilized-mixture"),
            ],
            plan(),
            88,
            1,
        )
        self.assertAlmostEqual(identical["heldout_log_score_gain"], 0, places=14)
        self.assertAlmostEqual(identical["c2_existing"], 1, places=13)
        with self.assertRaises(ValueError):
            density_metrics([[0, 0, 1, 1], [0, 0, 1, 1]])

    def test_curved_inverse_density_jacobian_and_independent_endpoint_answers(self):
        target = CurvedTarget({})
        z = np.array([[1.2, -0.7, 0.4, 1.1], [-0.5, 0.3, 1.5, -0.1]])
        x = z.copy()
        x[:, 1] += 0.5 * np.sin(x[:, 0])
        x[:, 3] += 0.5 * np.sin(x[:, 2])
        np.testing.assert_allclose(target.inverse(x), z, atol=1e-15)
        np.testing.assert_allclose(target.logpdf(x), norm.logpdf(z).sum(axis=1), atol=1e-14)
        jac = np.column_stack(
            [
                (
                    target.inverse(x[0] + np.eye(4)[i] * 1e-5)[0]
                    - target.inverse(x[0] - np.eye(4)[i] * 1e-5)[0]
                )
                / 2e-5
                for i in range(4)
            ]
        )
        self.assertAlmostEqual(np.linalg.det(jac), 1, places=9)
        exact = target.exact()
        variance = np.sum(target.contrasts**2, axis=1)
        np.testing.assert_allclose(exact["sd"] ** 2, variance + target.noise * 20 / 18, atol=1e-14)
        for j in range(2):
            for key, p in [("low", 0.025), ("high", 0.975)]:
                answer = quad(
                    lambda t: (
                        norm.pdf(t)
                        * stdtr(
                            20,
                            (exact[key][j] - np.sqrt(variance[j]) * t) / np.sqrt(target.noise[j]),
                        )
                    ),
                    -12,
                    12,
                    epsabs=1e-11,
                )[0]
                self.assertAlmostEqual(answer, p, places=10)

    def test_requested_density_denominator_pairing_and_raw_evidence(self):
        raw = np.tile([1.0, 0.2, 2.0, 1.5], (4, 1))
        g = dict(
            density_pilot_entropy=[1, 2, 3, 4],
            pilot_points_sha256="a" * 64,
            pilot_weights_sha256="b" * 64,
        )
        row = dict(
            trial=0,
            status="complete",
            training_log_score_gain=0.3,
            replicate_integrals=raw.tolist(),
            geometries={"adaptive-mixture": g, "stabilized-mixture": dict(g)},
            **density_metrics(raw),
        )
        rows = [
            row,
            dict(trial=1, status="failed", error="synthetic failure"),
            dict(trial=2, status="unattempted", error="budget"),
        ]
        validate_density(rows, 3)
        s = paired_summary(rows)
        self.assertEqual(
            (s["requested"], s["complete"], s["failed"], s["unattempted"]), (3, 1, 1, 1)
        )
        for mutate in ["pair", "raw", "omit"]:
            bad = deepcopy(rows)
            if mutate == "pair":
                bad[0]["geometries"]["stabilized-mixture"]["pilot_points_sha256"] = "c" * 64
            elif mutate == "raw":
                bad[0]["replicate_integrals"][0][2] *= 2
            else:
                bad.pop()
            with self.assertRaises(ValueError):
                validate_density(bad, 3)

    def test_failed_known_certificate_and_corrupt_manifest_cannot_reach_nfl_inputs(self):
        p = plan()
        validate_plan(p)
        with self.assertRaises(ValueError):
            validate_plan({**p, "coverage_trials": 128})
        cases = []
        for index in range(5):
            density = [dict(trial=i, status="failed", error="synthetic failure") for i in range(32)]
            coverage = [
                dict(
                    trial=i,
                    entropy=[p["base_seed"], 13, index, i],
                    status="failed",
                    error="no geometry",
                )
                for i in range(1024)
            ]
            target = known_target(index, {})
            cases.append(
                dict(
                    target=index,
                    dimensions=len(target.groups),
                    exact={k: v.tolist() for k, v in target.exact().items()},
                    density=density,
                    density_summary=paired_summary(density),
                    coverage=coverage,
                    coverage_geometry_sha256=None,
                    coverage_decision=coverage_summary(coverage, p),
                )
            )
        result = dict(
            experiment="density-holdout-controls-v1",
            plan=p,
            cases=cases,
            controls_passed=False,
            calibration_completed=False,
            ranking_ready=False,
            nfl_data_used=False,
        )
        self.assertFalse(validate_known(result, {}))
        with tempfile.TemporaryDirectory() as directory:
            output = SnapshotStore(directory)
            rid, manifest = save(output, result, {}, "a" * 40)
            self.assertEqual(load(output, rid)[1], result)
            with self.assertRaisesRegex(ValueError, "before CAVAA reference"):
                pilot([None] * 4, output, rid, {})
            manifest["objects"]["study"] = "f" * 64
            with self.assertRaises((ValueError, OSError)):
                load(output, output.put(json_bytes(manifest), manifest=True))
        for mutation in ["flag", "truth", "trial", "geometry"]:
            bad = deepcopy(result)
            if mutation == "flag":
                bad["controls_passed"] = True
            elif mutation == "truth":
                bad["cases"][4]["exact"]["low"][0] += 0.2
            elif mutation == "trial":
                bad["cases"][0]["coverage"][1]["entropy"][3] = 0
            else:
                bad["cases"][0]["coverage_geometry_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                validate_known(bad, {})


if __name__ == "__main__":
    unittest.main()
