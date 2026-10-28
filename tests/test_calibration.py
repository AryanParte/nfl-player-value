"""Independent algebra and failure-mode tests for synthetic calibration."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.sparse import csr_matrix

from nfl_value.baseline import design, prepare_plays
from nfl_value.calibration_math import (
    Z95,
    alias_diagnostics,
    evaluate,
    groups,
    operator,
    oracle_variance,
    penalty_vector,
    simulate,
    summarize,
    validate_plan,
)
from nfl_value.contrast_math import fit_joint
from test_contrasts import fixture, plan as contrast_plan


def plan():
    result = json.loads(Path("config/calibration-v1.json").read_text())
    result.update(windows={"2025": 3}, replicates=16)
    return result


class CalibrationMathTests(unittest.TestCase):
    def test_plan_rejects_ambiguous_or_changed_policy(self):
        validate_plan(plan())
        for key, value in (
            ("replicates", True),
            ("replicates", 1),
            ("seed", -1),
            ("plan_version", True),
            ("windows", {"2025": True}),
            ("windows", {"2024": 6}),
            ("noise_sd", float("nan")),
            ("actor_penalties", [10, 10]),
            ("actor_penalties", [True]),
            ("primary_actor_penalty", 42),
            ("benchmark", "opportunity_weighted"),
            ("extra", 1),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**plan(), key: value})
        changed = plan()
        changed["scenarios"][0]["correlated_fraction"] = False
        with self.assertRaises(ValueError):
            validate_plan(changed)

    def test_cached_operator_intervals_and_exact_bias_match_dense_reference(self):
        x = np.array([[1.0, -1, 0], [1, 0, 0], [1, 1, 0], [1, 2, 0]])
        l = np.array([[0.0, 3, -3], [0, -1, 0]])
        d = np.array([0.0, 2, 4])
        beta = np.array([[0.0, 0], [1, -2], [0.5, -0.25]])
        noise = np.array([[1.0, -1], [0.5, 2], [-0.5, 0], [0.25, -2]])
        y = x @ beta + noise
        clusters = [np.array([0, 1]), np.array([2, 3])]
        op = operator(csr_matrix(x), l, d)
        error, bias, widths, _ = evaluate(
            csr_matrix(x),
            l,
            op,
            beta,
            y,
            game_indices=clusters,
            noise_indices=clusters,
            noise_sd=1.5,
            fraction=0.5,
        )
        h_inv = np.linalg.inv(x.T @ x + np.diag(d))
        fitted = np.linalg.solve(x.T @ x + np.diag(d), x.T @ y)
        residual = y - x @ fitted
        np.testing.assert_allclose(error, l @ (fitted - beta), atol=1e-12)
        np.testing.assert_allclose(bias, l @ (h_inv @ x.T @ x - np.eye(3)) @ beta, atol=1e-12)
        for b in range(2):
            meat = sum(np.outer(x[g].T @ residual[g, b], x[g].T @ residual[g, b]) for g in clusters)
            cov = l @ h_inv @ meat @ h_inv @ l.T
            np.testing.assert_allclose(
                (widths["game_cluster_cr0"][:, b] / (2 * Z95)) ** 2, np.diag(cov), atol=1e-12
            )
            np.testing.assert_allclose(
                (widths["conditional_gaussian"][:, b] / (2 * Z95)) ** 2,
                np.diag(l @ h_inv @ l.T) * np.mean(residual[:, b] ** 2),
            )
        omega = 1.5**2 * (0.5 * np.eye(4) + 0.5 * np.kron(np.eye(2), np.ones((2, 2))))
        oracle = l @ h_inv @ x.T @ omega @ x @ h_inv @ l.T
        np.testing.assert_allclose(
            (widths["oracle_sampling"][:, 0] / (2 * Z95)) ** 2, np.diag(oracle), atol=1e-12
        )

    def test_cached_response_fits_match_existing_joint_solver_including_cold_parameters(self):
        ledger = fixture()[0]
        rows, _ = prepare_plays(ledger, season=2025)
        model, covariance = fit_joint(
            rows, {"QB": ["00-9999999"]}, plan=contrast_plan(), actor_penalty=1000
        )
        names = model["features"]
        x, _, _ = design(rows, "joint", names)
        d = penalty_vector(names, actor=1000, context=1, team=50)
        l = np.eye(len(names))
        op = operator(x, l, d)
        beta = np.zeros((len(names), 2))
        y = np.repeat(np.array([p["offense_epa"] for p in rows])[:, None], 2, axis=1)
        error, bias, widths, _ = evaluate(
            x,
            l,
            op,
            beta,
            y,
            game_indices=groups([p["game_id"] for p in rows]),
            noise_indices=groups([p["game_id"] for p in rows]),
            noise_sd=1.5,
            fraction=0,
        )
        np.testing.assert_allclose(error[:, 0], model["coefficients"], atol=1e-12)
        np.testing.assert_allclose(
            (widths["conditional_gaussian"][:, 0] / (2 * Z95)) ** 2, np.diag(covariance), atol=1e-12
        )
        np.testing.assert_array_equal(bias, 0)

    def test_alias_and_prior_only_cases_change_attribution_without_changing_outcomes(self):
        x = csr_matrix([[1.0, 1, 0], [0, 0, 0], [1, 1, 0]])
        names = ["dropback/00-0000001", "target/00-0000002", "carry/00-0000003"]
        l = np.array([[4.0, -2, -2], [0, 1, -1]])
        result = alias_diagnostics(x, names, l, shift=0.25)
        self.assertEqual(result["observed_alias_pairs"], 1)
        self.assertEqual(result["prior_only_columns"], 1)
        self.assertEqual([c["max_play_expectation_change_ep"] for c in result["cases"]], [0, 0])
        self.assertEqual(
            [c["max_absolute_contrast_change_ep"] for c in result["cases"]], [1.5, 0.5]
        )
        op = operator(x, l, np.array([2.0, 2, 2]))
        cold_l = np.array([[0.0, 0, 1]])
        cold = operator(x, cold_l, np.array([2.0, 2, 2]))
        self.assertGreater(cold["conditional_diagonal"][0], 0)
        self.assertEqual(
            oracle_variance(cold["a"], groups(["a", "a", "b"]), noise_sd=1, fraction=0.5)[0], 0
        )
        self.assertEqual(op["a"].shape, (3, 2))

    def test_mc_uncertainty_uses_independent_replicates_not_player_cells(self):
        coverage = np.tile(np.array([[True, False, True, False]]), (100, 1))
        zeros = np.zeros((100, 4))
        result = summarize(
            zeros, zeros, {"x": np.ones((100, 4))}, {"x": coverage}, failure_bound=0.9
        )
        interval = result["intervals"]["x"]
        self.assertAlmostEqual(interval["coverage"], 0.5)
        self.assertAlmostEqual(interval["monte_carlo_se"], np.std([1, 0, 1, 0], ddof=1) / 2)
        self.assertFalse(interval["severe_undercoverage"])

    def test_oracle_sampling_width_does_not_correct_shrinkage_bias(self):
        x = csr_matrix(np.column_stack([np.ones(32), np.tile([-1.0, 1], 16)]))
        l = np.array([[0.0, 1.0]])
        d = np.array([0.0, 1000.0])
        op = operator(x, l, d)
        beta = np.tile([[0.0], [5.0]], (1, 2048))
        rng = np.random.default_rng(41)
        y = x @ beta + rng.normal(size=(32, 2048))
        cluster = groups([str(i // 4) for i in range(32)])
        error, bias, widths, covered = evaluate(
            x, l, op, beta, y, game_indices=cluster, noise_indices=cluster, noise_sd=1, fraction=0
        )
        result = summarize(error, bias, widths, covered, failure_bound=0.9)
        self.assertEqual(result["intervals"]["oracle_sampling"]["coverage"], 0)
        self.assertTrue(result["intervals"]["oracle_sampling"]["severe_undercoverage"])
        self.assertLess(
            abs(result["intervals"]["oracle_expectation_control"]["coverage"] - 0.95), 0.025
        )

    def test_simulated_responses_are_reproducible_and_share_the_same_truth_across_penalties(self):
        x = csr_matrix([[1.0, 1, 0], [1, 0, 1], [1, 1, 0], [1, 0, 1]])
        names = ["context/intercept", "dropback/00-0000001", "target/00-0000002"]
        d = penalty_vector(names, actor=1000, context=1, team=50)
        for i in range(4):
            args = dict(
                plan=plan(),
                season=2025,
                week=3,
                scenario_index=i,
                noise_groups=groups(["one", "one", "two", "two"]),
            )
            beta, y = simulate(x, names, d, **args)
            again = simulate(x, names, d, **args)
            np.testing.assert_array_equal(beta, again[0])
            np.testing.assert_array_equal(y, again[1])
            if i:
                np.testing.assert_array_equal(np.abs(beta[1:]), 0.25)
            changed = deepcopy(args)
            changed["plan"]["seed"] += 1
            self.assertFalse(np.array_equal(y, simulate(x, names, d, **changed)[1]))

    def test_invalid_and_singular_systems_fail_explicitly(self):
        for x, l, d in (
            (csr_matrix([[1.0, 1.0]]), np.ones((1, 2)), np.zeros(2)),
            (csr_matrix([[1.0, np.nan]]), np.ones((1, 2)), np.ones(2)),
            (csr_matrix([[1.0, 1.0]]), np.ones((1, 3)), np.ones(2)),
        ):
            with self.assertRaises(ValueError):
                operator(x, l, d)
        with self.assertRaises(ValueError):
            penalty_vector(["invented/x"], actor=1, context=1, team=1)


if __name__ == "__main__":
    unittest.main()
