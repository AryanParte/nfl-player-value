"""Independent finite-sum EM, signed accounting and retained diagnostic contracts."""

from copy import deepcopy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.stats import multivariate_normal

from nfl_value.coarse_control_study import archive
from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_preflight import (
    arms,
    experiment_kind,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.mode_proposal import Work, make_proposal, pad_modes
from nfl_value.tail_controls import tail_proposal
from nfl_value.tail_mixture import em_step, fit_tail_mixture, reserve_tail, restore_tail_mixture
from nfl_value.two_level_reference import sampling_hash


def plan():
    return json.loads(Path("config/tail-mixture-preflight-v1.json").read_text())


def small_plan():
    return {
        **plan(),
        "em_nodes": 128,
        "em_steps": 2,
        "mass_pilot_nodes": 128,
        "training_nodes": 128,
        "replicates": 8,
        "nodes_per_replicate": 64,
        "correction_nodes_per_replicate": 16,
        "trials": 1,
    }


class TailMixtureTests(unittest.TestCase):
    def test_matched_error_summary_keeps_failed_confidence_points(self):
        summarize_pair = runpy.run_path("scripts/analyze_mode_preflight.py")["matched_comparison"]
        raw = np.array([[1, -1, 0, 0.025, 0.025, 0.975, 0.975, 0.9, 0.9]] * 2)
        records = [
            dict(
                trial=i,
                status="failed" if i == 0 else "complete",
                coarse=raw.tolist(),
                correction=np.zeros_like(raw).tolist(),
            )
            for i in range(2)
        ]
        result = summarize_pair(dict(records=records), dict(records=records))
        self.assertEqual(result["defined_point_pairs"], 2)
        self.assertEqual(result["included_failed_confidence_pairs"], 1)
        self.assertEqual(result["paired_point_errors"]["adjusted_rmse"][1], 1)

    def test_weighted_em_against_independent_density_and_moment_sums(self):
        initial = tail_proposal()
        means = np.array([[0, 0, 0, 0], [2, -1, 0, 1], [-2, 2, 1, 0]], float)
        covs = np.array([np.eye(4), 2 * np.eye(4), 0.7 * np.eye(4)])
        masses = np.array([0.5, 0.3, 0.2])
        q = make_proposal(initial, means, covs, masses, {})
        x = np.array(
            [
                [-3, 1, 0, 2],
                [-1, -2, 2, 0],
                [0, 0, 0, -1],
                [1, -1, 1, 1],
                [2, 0, -1, 0],
                [3, 2, 1, -2],
                [-2, 3, -1, -1],
            ],
            float,
        )
        w = np.arange(1, len(x) + 1, dtype=float)
        w /= w.sum()
        updated, diag = em_step(
            x, w, q, np.eye(4), pseudo_count=0, bounds=[1e-12, 1e6], mass_floor=1e-8
        )
        density = np.array(
            [
                [
                    a * multivariate_normal.pdf(row, mean=m, cov=c)
                    for a, m, c in zip(masses, means, covs)
                ]
                for row in x
            ]
        )
        allocated = np.array([weight * row / sum(row) for weight, row in zip(w, density)])
        expected_masses = np.array([sum(allocated[:, j]) for j in range(3)])
        expected_means, expected_cov = [], []
        for j in range(3):
            z = allocated[:, j] / expected_masses[j]
            mean = sum(a * row for a, row in zip(z, x))
            cov = sum(a * np.outer(row - mean, row - mean) for a, row in zip(z, x))
            expected_means.append(mean)
            expected_cov.append(cov)
        np.testing.assert_allclose(updated.mixture_masses, expected_masses, rtol=1e-13)
        np.testing.assert_allclose(updated.mixture_means, expected_means, atol=2e-14)
        np.testing.assert_allclose(updated.mixture_covariances, expected_cov, atol=2e-14)
        self.assertGreaterEqual(diag["objective_after"] + 1e-12, diag["objective_before"])

    def test_identical_components_recover_known_gaussian_signed_moments(self):
        initial = tail_proposal()
        q = make_proposal(initial, [initial.mean] * 3, [np.eye(4)] * 3, [0.2, 0.3, 0.5], {})
        z, w = hermgauss(4)
        indices = np.array(np.meshgrid(*([np.arange(4)] * 4), indexing="ij")).reshape(4, -1).T
        mean = np.array([-2.0, 1, -0.5, 0.3])
        chol = np.array([[1, 0, 0, 0], [0.2, 0.8, 0, 0], [0, 0.1, 1.2, 0], [0, 0, 0.2, 0.6]])
        x = mean + np.sqrt(2) * z[indices] @ chol.T
        weights = np.prod(w[indices] / np.sqrt(np.pi), axis=1)
        updated, _ = em_step(
            x, weights, q, np.eye(4), pseudo_count=0, bounds=[1e-10, 36], mass_floor=0.01
        )
        np.testing.assert_allclose(updated.mixture_means, np.tile(mean, (3, 1)), atol=1e-13)
        np.testing.assert_allclose(
            updated.mixture_covariances, np.tile(chol @ chol.T, (3, 1, 1)), atol=1e-13
        )
        np.testing.assert_allclose(updated.mixture_masses, [0.2, 0.3, 0.5], atol=1e-13)

    def test_broad_slot_splits_duplicates_and_preserves_defensive_support(self):
        initial = tail_proposal()
        for count in [1, 2, 3]:
            centers = np.array([[j * 2, 0, 0, 0] for j in range(count)])
            m, c, w = pad_modes(centers, [np.eye(4)] * count, np.ones(count) / count)
            mode = make_proposal(initial, m, c, w, dict(discovered_modes=centers.tolist()))
            proposal, available = reserve_tail(mode, initial, 0.2)
            self.assertEqual(available, count < 3)
            self.assertEqual(proposal.components(METHOD)[-1][0], 0.1)
            np.testing.assert_array_equal(proposal.prior_covariance, initial.prior_covariance)
            self.assertAlmostEqual(sum(proposal.mixture_masses), 1)
            if count == 3:
                np.testing.assert_array_equal(proposal.mixture_means, centers)
            else:
                self.assertEqual(
                    sum(
                        np.array_equal(v, initial.prior_covariance)
                        for v in proposal.mixture_covariances
                    ),
                    1,
                )

    def test_collinear_and_concentrated_pilots_have_bounded_proposal_covariance(self):
        initial = tail_proposal()
        x = np.ones((5, 4))
        q, diag = em_step(
            x,
            [1, 0, 0, 0, 0],
            initial,
            np.eye(4),
            pseudo_count=6,
            bounds=[1e-6, 36],
            mass_floor=0.01,
        )
        self.assertEqual(diag["effective_weights"], [1, 1, 1])
        self.assertGreater(np.linalg.eigvalsh(q.mixture_covariances).min(), 0)
        with self.assertRaises(ValueError):
            em_step(
                x,
                [-1, 2, 0, 0, 0],
                initial,
                np.eye(4),
                pseudo_count=6,
                bounds=[1e-6, 36],
                mass_floor=0.01,
            )

    def test_independent_pilots_exact_work_and_corrupt_stage_rejection(self):
        p, initial = small_plan(), tail_proposal()
        calls = []

        def density(x):
            calls.append(len(x))
            return normal_logpdf(x, [-1, 0.5, 0, 0], np.eye(4))

        work = Work(p)
        q = fit_tail_mixture(density, initial, entropy=[901, 0, 1, 0], plan=p, work=work)
        self.assertEqual(sum(calls), work.total)
        self.assertEqual(work.counts["em_pilot_0"], 128)
        self.assertEqual(work.counts["em_pilot_1"], 128)
        self.assertEqual(
            [s["entropy"] for s in q.diagnostics["stages"]],
            [[901, 0, 1, 0, 20, 0], [901, 0, 1, 0, 20, 1]],
        )
        self.assertEqual(
            sampling_hash(q), sampling_hash(restore_tail_mixture(q.diagnostics, initial, p))
        )
        for mutate in [
            lambda g: g["stages"][0]["log_density"].__setitem__(0, 99),
            lambda g: g["stages"][0]["entropy"].append(9),
            lambda g: g["component_means"][0].__setitem__(0, 99),
            lambda g: g["fit_work"].update(total=0),
        ]:
            g = deepcopy(q.diagnostics)
            mutate(g)
            with self.assertRaises(ValueError):
                restore_tail_mixture(g, initial, p)

    def test_matched_diagnostic_domains_signed_raw_and_work_validation(self):
        p, initial = small_plan(), tail_proposal()

        class Toy:
            def logpdf(self, x):
                return normal_logpdf(x, [-1, 0, 0, 0], np.eye(4))

            def integrand(self, exact):
                return lambda x, logq: (
                    np.exp(self.logpdf(x) - logq)[:, None]
                    * np.column_stack(
                        [
                            np.ones(len(x)),
                            x[:, 0],
                            x[:, 1],
                            np.full((len(x), 2), 0.025),
                            np.full((len(x), 2), 0.975),
                            np.full((len(x), 2), 0.9),
                        ]
                    )
                )

        candidate = trial(Toy(), initial, {}, p, [p["base_seed"], 0, 3, 0], "candidate")
        baseline = trial(Toy(), initial, {}, p, [p["base_seed"], 2, 3, 0], "baseline")
        self.assertEqual(candidate["geometry"]["mode_geometry"], baseline["geometry"])
        self.assertNotEqual(
            candidate["fit"]["training_entropy"], baseline["fit"]["training_entropy"]
        )
        self.assertLess(np.array(candidate["coarse"])[:, 1].mean(), 0)
        for arm, record in [("candidate", candidate), ("baseline", baseline)]:
            case = dict(
                arm=arm,
                target=3,
                truth={},
                initial_sampling_sha256=sampling_hash(initial),
                records=[dict(trial=0, **record)],
                decision=summarize([record], p),
            )
            validate_case(case, initial, {}, p)
            altered = deepcopy(case)
            altered["records"][0]["work"]["counts"]["em_pilot_0"] = 0
            with self.assertRaises(ValueError):
                validate_case(altered, initial, {}, p)

    def test_frozen_scope_and_nonadmission_before_nfl_inputs(self):
        p = plan()
        validate_plan(p)
        validate_plan(json.loads(Path("config/mode-preflight-v1.json").read_text()))
        self.assertEqual(sum(len(indices) for _, indices in arms(p)) * p["trials"], 448)
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(json_bytes(dict(plan=p, experiment=experiment_kind(p))), manifest=True)
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()
        p["em_steps"] += 1
        with self.assertRaisesRegex(ValueError, "frozen design"):
            validate_plan(p)


if __name__ == "__main__":
    unittest.main()
