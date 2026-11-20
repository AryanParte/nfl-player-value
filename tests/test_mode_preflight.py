"""Independent formulas, work limits and non-admission for mode preflight."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm, t

from nfl_value.coarse_control_study import archive
from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_proposal import Work, WorkLimit, fit_modes, pad_modes, restore_modes
from nfl_value.mode_preflight import (
    ExtendedTarget,
    oracle_proposal,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.tail_controls import tail_proposal
from nfl_value.two_level_reference import sampling_hash


def plan():
    return json.loads(Path("config/mode-preflight-v1.json").read_text())


def small_plan():
    return {
        **plan(),
        "training_nodes": 128,
        "replicates": 8,
        "nodes_per_replicate": 64,
        "correction_nodes_per_replicate": 16,
        "mass_pilot_nodes": 128,
    }


class ModePreflightTests(unittest.TestCase):
    def test_discovery_on_independent_rotated_gaussian_and_call_accounting(self):
        p = plan()
        initial = tail_proposal()
        mean = np.array([1.25, -1.5, 0.3, 0.7])
        l = np.array([[0.7, 0, 0, 0], [0.2, 1, 0, 0], [0.1, -0.3, 0.8, 0], [0, 0.1, 0.2, 1.2]])
        cov = l @ l.T
        calls = []

        def density(x):
            calls.append(len(x))
            return normal_logpdf(x, mean, cov)

        w = Work(p)
        q = fit_modes(density, initial, entropy=[16, 2, 11], plan=p, work=w)
        self.assertEqual(len(q.diagnostics["discovered_modes"]), 1)
        np.testing.assert_allclose(q.mixture_means, np.tile(mean, (3, 1)), atol=2e-5)
        np.testing.assert_allclose(q.mixture_covariances, np.tile(1.5 * cov, (3, 1, 1)), atol=2e-5)
        self.assertEqual(w.total, sum(calls))
        self.assertEqual(len(q.diagnostics["attempts"]), 24)
        self.assertTrue(all(a["calls"] <= 384 for a in q.diagnostics["attempts"]))
        self.assertEqual(w.counts["hessian_0"], 33)
        self.assertEqual(w.counts["search_cloud"], 256)
        self.assertEqual(w.counts["mass_pilot"], 4096)
        self.assertNotEqual(
            q.diagnostics["search_responses_sha256"], q.diagnostics["pilot_responses_sha256"]
        )
        self.assertEqual(sampling_hash(q), sampling_hash(restore_modes(q.diagnostics, initial)))
        np.testing.assert_array_equal(q.components(METHOD)[-1][1], initial.prior_mean)
        self.assertEqual(q.components(METHOD)[-1][0], 0.1)

    def test_duplicate_components_preserve_density_and_mass(self):
        m, c, p = pad_modes([[0, 0], [2, -1]], [np.eye(2), 2 * np.eye(2)], [0.8, 0.2])
        self.assertAlmostEqual(sum(p), 1)
        self.assertEqual(p.tolist(), [0.4, 0.2, 0.4])
        x = np.array([[0.0, 0.0], [1.0, 2.0], [-4.0, 5.0]])
        actual = sum(w * np.exp(normal_logpdf(x, a, b)) for a, b, w in zip(m, c, p))
        expected = 0.8 * np.exp(normal_logpdf(x, np.zeros(2), np.eye(2))) + 0.2 * np.exp(
            normal_logpdf(x, [2, -1], 2 * np.eye(2))
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-14)

    def test_target_and_time_caps_do_not_silently_overrun(self):
        p = {**plan(), "maximum_target_evaluations": 3, "maximum_seconds_per_trial": 2}
        now = [0.0]
        work = Work(p, clock=lambda: now[0])
        work.charge("fine", 3)
        with self.assertRaisesRegex(WorkLimit, "evaluation"):
            work.charge("coarse", 1)
        self.assertEqual(work.total, 3)
        now[0] = 3
        with self.assertRaisesRegex(WorkLimit, "time"):
            work.charge("fine", 1)

    def test_failed_search_retains_all_bounded_start_attempts(self):
        p = {**plan(), "optimizer_calls_per_start": 1}
        work = Work(p)
        with self.assertRaisesRegex(ValueError, "mode count"):
            fit_modes(
                lambda x: -0.5 * np.sum(x * x, axis=1),
                tail_proposal(),
                entropy=[7, 8],
                plan=p,
                work=work,
            )
        self.assertEqual(len(work.trace["attempts"]), 24)
        self.assertTrue(all(a["calls"] == 1 and not a["usable"] for a in work.trace["attempts"]))
        self.assertEqual(work.total, 256 + 1 + 24)

    def test_screen_is_not_a_numerical_certificate_and_failures_stay(self):
        p = plan()
        good = dict(
            status="complete",
            precision_passed=True,
            simultaneous_covered=True,
            marginal_covered=[True] * 7,
            wrong_endpoints_rejected=True,
        )
        records = [deepcopy(good) for _ in range(32)]
        self.assertTrue(summarize(records, p)["screen_passed"])
        self.assertFalse(summarize(records, p)["numerical_certified"])
        records[0] = dict(status="failed", error="mass interval includes zero")
        result = summarize(records, p)
        self.assertFalse(result["screen_passed"])
        self.assertEqual(result["requested"], 32)
        self.assertEqual(result["joint_coverage"], 31 / 32)
        records[1] = dict(status="unattempted", error="runtime cap")
        self.assertEqual(summarize(records, p)["unattempted"], 1)

    def test_preflight_cannot_authorize_archived_nfl_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(
                json_bytes(dict(plan=plan(), experiment="mode-preflight-report-v1")), manifest=True
            )
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()

    def test_unknown_arm_never_silently_selects_oracle(self):
        with self.assertRaisesRegex(ValueError, "explicit candidate"):
            trial(None, None, {}, plan(), [1, 2], "canddiate")

    def test_plan_and_corrupt_geometry_are_rejected(self):
        p = plan()
        validate_plan(p)
        p["reference_endpoint_cdf_tolerance"] = 0.1
        with self.assertRaisesRegex(ValueError, "frozen"):
            validate_plan(p)
        initial = tail_proposal()
        q = oracle_proposal(ExtendedTarget(8), initial)
        for mutate in [
            lambda g: g["component_masses"].__setitem__(0, 0),
            lambda g: g.update(geometry_uses_evaluation=True),
            lambda g: g.update(initial_sampling_sha256="0" * 64),
            lambda g: g["component_covariances"][0][0].__setitem__(0, -1),
        ]:
            g = deepcopy(q.diagnostics)
            mutate(g)
            with self.assertRaises((ValueError, np.linalg.LinAlgError)):
                restore_modes(g, initial)

    def test_new_fixture_endpoint_truth_by_reverse_convolution(self):
        for index in (8, 9):
            target = ExtendedTarget(index)
            truth = target.exact()
            for j in range(2):
                a = target.contrasts[j]
                means = target.means @ a
                var = np.array([a @ c @ a for c in target.covariances])
                for label, probability in [("low", 0.025), ("high", 0.975)]:
                    bound = truth[label][j]
                    actual = quad(
                        lambda noise: (
                            t.pdf(noise, 20)
                            * sum(
                                w
                                * norm.cdf(
                                    (bound - np.sqrt(target.noise[j]) * noise - m) / np.sqrt(v)
                                )
                                for w, m, v in zip(target.probabilities, means, var)
                            )
                        ),
                        -np.inf,
                        np.inf,
                        epsabs=2e-10,
                    )[0]
                    self.assertAlmostEqual(actual, probability, places=8)
            expected = target.probabilities @ (target.means @ target.contrasts.T)
            np.testing.assert_allclose(truth["mean"], expected, rtol=1e-14)

    def test_negative_integrals_independent_domains_and_raw_validation(self):
        # Independent toy model, not a new draw from the declared study fixtures.
        p = small_plan()
        p["trials"] = 1
        initial = tail_proposal()

        class Toy:
            means = np.array([[-1.0, 0, 0, 0]])
            covariances = np.array([np.eye(4)])
            probabilities = np.array([1.0])

            def integrand(self, exact):
                def f(x, logq):
                    w = np.exp(normal_logpdf(x, self.means[0], self.covariances[0]) - logq)
                    return w[:, None] * np.column_stack(
                        [
                            np.ones(len(x)),
                            x[:, 0],
                            x[:, 1],
                            np.full((len(x), 2), 0.025),
                            np.full((len(x), 2), 0.975),
                            np.full((len(x), 2), 0.9),
                        ]
                    )

                return f

        r = trial(Toy(), initial, {}, p, [p["base_seed"], 1, 6, 0], "oracle")
        self.assertIn("coarse", r)
        total = np.array(r["coarse"]) + np.array(r["correction"])
        self.assertLess(total[:, 1].mean(), -0.5)
        self.assertEqual(r["fit"]["training_entropy"], [p["base_seed"], 1, 6, 0, 2])
        case = dict(
            arm="oracle",
            target=6,
            truth={},
            initial_sampling_sha256=sampling_hash(initial),
            records=[dict(trial=0, **r)],
            decision=summarize([r], p),
        )
        validate_case(case, initial, {}, p)
        changed = deepcopy(case)
        changed["records"][0]["coarse"][0][0] += 1
        with self.assertRaises(ValueError):
            validate_case(changed, initial, {}, p)
        changed = deepcopy(case)
        changed["records"][0]["work"]["total"] -= 1
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_case(changed, initial, {}, p)


if __name__ == "__main__":
    unittest.main()
