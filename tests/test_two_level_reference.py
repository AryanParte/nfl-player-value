"""Analytical accounting and adversarial controls for the opt-in reference."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.stats import norm, t

from nfl_value.density_holdout import StabilizedProposal
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.repaired_functional import authorize, load, save, validate_archive, validate_plan
from nfl_value.replicated_reference import (
    conditional_integrand,
    confidence_sets,
    diagnose_reference,
    summarize_integrals,
)
from nfl_value.two_level_reference import combine, integrate, restore_proposal


def plan():
    return json.loads(Path("config/repaired-functional-v1.json").read_text())


def sampling():
    return StabilizedProposal(
        np.zeros(1),
        np.eye(1),
        np.zeros(1),
        np.eye(1),
        {},
        np.zeros((3, 1)),
        np.ones((3, 1, 1)),
        np.full(3, 1 / 3),
    )


class TwoLevelTests(unittest.TestCase):
    def test_raw_levels_failure_denominator_and_archive_gate_cannot_be_forged(self):
        p = plan()
        shifts = [0.0, -1.0, 1.0]
        summaries = {s: {"mean": np.zeros(2)} for s in shifts}
        raw = np.tile([1.0, 0.0, 0.0, 0.025, 0.025, 0.975, 0.975] * 3, (32, 1))
        reference = summarize_integrals(raw, summaries, p, sampling(), "stabilized-mixture")
        from nfl_value.ingestion import sha256

        record = dict(
            status="complete",
            numerical_valid=True,
            primary_qmc_valid=True,
            contrasts=2,
            shifts=shifts,
            entropy=[p["base_seed"], 1, 0, 0],
            geometry_sha256=sha256(json_bytes({})),
            coarse=raw.tolist(),
            correction=np.zeros_like(raw).tolist(),
            reference=reference,
            diagnosis=diagnose_reference(reference, contrasts=2, shifts=shifts, plan=p),
            evaluations=dict(fine=2049, coarse=67584),
        )
        cases = {
            name: dict(status="unattempted", numerical_valid=False, error="bounded fixture")
            for name in p["cases"]
        }
        cases["real_evolving"] = record
        result = dict(
            plan=p,
            cases=cases,
            nfl_data_used=True,
            calibration_completed=False,
            ranking_ready=False,
            numerical_pilot_passed=False,
        )
        validate_archive(result)
        for mutation in ["omit", "admit", "coarse", "error", "budget", "entropy"]:
            bad = deepcopy(result)
            r = bad["cases"]["real_evolving"]
            if mutation == "omit":
                bad["cases"].pop("real_team")
            elif mutation == "admit":
                bad["numerical_pilot_passed"] = True
            elif mutation == "coarse":
                r["coarse"][0][0] += 0.1
            elif mutation == "error":
                r["reference"]["bounds"]["low"][1] -= 0.1
            elif mutation == "budget":
                r["evaluations"]["fine"] -= 1
            else:
                r["entropy"][0] += 1
            with self.assertRaises(ValueError):
                validate_archive(bad)

    def test_large_surrogate_error_is_corrected_before_signed_normalization(self):
        def fine(points, logq):
            return np.tile([2.0, -6.0, 0.0], (len(points), 1))

        def coarse(points, logq):
            return np.tile([8.0, 24.0, -1.0], (len(points), 1))

        total, base, delta = integrate(
            fine, coarse, sampling(), entropy=[115, 1], replicates=8, nodes=64, correction_nodes=16
        )
        np.testing.assert_allclose(base, np.tile([8, 24, -1], (8, 1)), atol=1e-14)
        np.testing.assert_allclose(delta, np.tile([-6, -30, 1], (8, 1)), atol=1e-14)
        bounds = confidence_sets(total, [-1, 0, 0])
        np.testing.assert_allclose(bounds["estimate"], [2, -3, 0], atol=1e-13)
        np.testing.assert_allclose(bounds["low"], bounds["high"], atol=1e-13)

    def test_levels_are_independent_pair_points_identical_and_replay_exact(self):
        seen = []

        def fine(points, logq):
            seen.append(("fine", points.copy()))
            return np.column_stack([np.ones(len(points)), points[:, 0]])

        def coarse(points, logq):
            seen.append(("coarse", points.copy()))
            return np.column_stack([np.ones(len(points)), points[:, 0]])

        out = integrate(
            fine, coarse, sampling(), entropy=[115, 2], replicates=4, nodes=32, correction_nodes=32
        )
        coarse_nodes = np.vstack([x for name, x in seen[:16]])
        paired = seen[16:]
        for i in range(0, len(paired), 2):
            self.assertEqual((paired[i][0], paired[i + 1][0]), ("fine", "coarse"))
            np.testing.assert_array_equal(paired[i][1], paired[i + 1][1])
        self.assertFalse(
            np.array_equal(coarse_nodes, np.vstack([x for name, x in paired if name == "fine"]))
        )
        np.testing.assert_array_equal(out[2], np.zeros_like(out[2]))
        repeat = integrate(
            fine, coarse, sampling(), entropy=[115, 2], replicates=4, nodes=32, correction_nodes=32
        )
        for a, b in zip(out, repeat):
            np.testing.assert_array_equal(a, b)

    def test_independent_normal_and_student_functionals_with_biased_surrogate(self):
        location, scale = np.array([-2.0, 1.0]), np.sqrt(0.2)

        class Target:
            def prior(self, point, shift):
                return np.array([norm.logpdf(point[0])])

            def conditional(self, point, contrasts):
                return dict(
                    diagonal=np.ones(2),
                    posterior_scale=np.array([2.0]),
                    posterior_shape=10.0,
                    location=location[:, None],
                    log_likelihood=np.array([0.0]),
                )

        summaries = {
            0.0: dict(
                mean=location,
                sd=np.full(2, scale * np.sqrt(20 / 18)),
                low=location + scale * t.ppf(0.025, 20),
                high=location + scale * t.ppf(0.975, 20),
            )
        }
        fine = conditional_integrand(Target(), np.eye(2), summaries, 0.0)

        def coarse(x, q):
            return 1.5 * np.asarray(fine(x, q))

        total, _, _ = integrate(
            fine, coarse, sampling(), entropy=[115, 3], replicates=8, nodes=64, correction_nodes=16
        )
        result = summarize_integrals(
            total, summaries, {**plan(), "replicates": 8}, sampling(), "stabilized-mixture"
        )
        self.assertTrue(result["valid"])
        np.testing.assert_allclose(
            result["bounds"]["estimate"], [1, 0, 0, 0.025, 0.025, 0.975, 0.975], atol=1e-13
        )

    def test_invalid_nets_dimensions_and_fine_failure_are_never_zero_likelihood(self):
        f = lambda x, q: np.ones((len(x), 2))
        for n in [1, 3, 4, True, 16.0]:
            with self.assertRaises(ValueError):
                integrate(f, f, sampling(), entropy=[4], replicates=4, nodes=32, correction_nodes=n)
        with self.assertRaisesRegex(ValueError, "paired finite"):
            integrate(
                lambda x, q: np.ones((len(x), 1)),
                f,
                sampling(),
                entropy=[4],
                replicates=4,
                nodes=32,
                correction_nodes=16,
            )
        with self.assertRaisesRegex(ValueError, "bad fine"):
            integrate(
                lambda x, q: (_ for _ in ()).throw(ValueError("bad fine")),
                f,
                sampling(),
                entropy=[4],
                replicates=4,
                nodes=32,
                correction_nodes=16,
            )
        for b, d in [
            (np.ones((2, 2)), np.ones((3, 2))),
            (np.zeros((1, 2)), np.zeros((1, 2))),
            (np.ones((2, 2)), np.full((2, 2), np.nan)),
        ]:
            with self.assertRaises(ValueError):
                combine(b, d)

    def test_frozen_policy_and_saved_kernel_hash_bind_authorization(self):
        p = plan()
        validate_plan(p)
        for key, value in [
            ("base_seed", 42),
            ("replicates", 64),
            ("correction_nodes_per_replicate", 128),
            ("reference_mean_tolerance_sd", 0.02),
        ]:
            with self.assertRaises(ValueError):
                validate_plan({**p, key: value})
        result = dict(experiment="repaired-functional-controls-v1", plan=p, controls_passed=False)
        with tempfile.TemporaryDirectory() as directory:
            output = SnapshotStore(directory)
            rid, m = save(output, result, "a" * 40)
            with (
                patch("nfl_value.repaired_functional.validate_known", return_value=False),
                patch(
                    "nfl_value.repaired_functional.load_conditional",
                    side_effect=AssertionError("NFL gate crossed"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "before NFL"):
                    authorize(output, rid)
            m["kernel_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "statistical code"):
                load(output, output.put(json_bytes(m), manifest=True))
            m["objects"]["study"] = "f" * 64
            with self.assertRaises((ValueError, OSError)):
                load(output, output.put(json_bytes(m), manifest=True))

    def test_saved_proposal_preserves_components_and_rejects_drift(self):
        g = dict(
            pilot_initial_geometry=dict(mode=[0.0], covariance=[[1.0]]),
            component_means=[[0.0], [1.0], [-1.0]],
            component_covariances=[[[1.0]], [[2.0]], [[3.0]]],
            component_masses=[0.2, 0.3, 0.5],
            geometry_uses_primary_qmc=False,
            learning_is_target_density_only=True,
        )
        p = restore_proposal(g, dict(log_precision_mean=2.0, log_precision_sd=3.0))
        np.testing.assert_allclose(
            [x[0] for x in p.components("stabilized-mixture")],
            [0.18, 0.27, 0.45, 0.1],
            rtol=0,
            atol=1e-16,
        )
        self.assertEqual(p.prior_mean.tolist(), [2.0])
        for key, value in [
            ("component_masses", [0.2, 0.3, 0.6]),
            ("geometry_uses_primary_qmc", True),
            ("component_means", [[float("nan")], [1.0], [-1.0]]),
        ]:
            bad = deepcopy(g)
            bad[key] = value
            with self.assertRaises(ValueError):
                restore_proposal(bad, dict(log_precision_mean=2.0, log_precision_sd=3.0))


if __name__ == "__main__":
    unittest.main()
