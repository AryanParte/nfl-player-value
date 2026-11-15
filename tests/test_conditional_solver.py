"""Independent prior restoration, exact/near alias and row-space checks."""

import unittest
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from nfl_value.conditional_reference import as_float, decimal_cell, reference_agreement
from nfl_value.conditional_solver import (
    SquareRootSystem,
    binary_nullspace,
    compensated_residual,
)
from nfl_value.conditional_archive import SquareRootTarget
from nfl_value.conditional_cli import load, save
from nfl_value.conditional_study import comparison, known_study, validate_known, validate_plan
from nfl_value.ingestion import SnapshotStore
from nfl_value.variance_mixture import cell, response_stats, system


class ConditionalSolverTests(unittest.TestCase):
    def test_exact_partition_nullspace_is_algebraic_and_near_alias_is_not_rounded(self):
        x = np.column_stack([np.ones(9), np.eye(3)[np.arange(9) % 3]])
        null, certificate = binary_nullspace(x)
        np.testing.assert_array_equal(x @ null, 0)
        self.assertEqual(certificate["nullity"], 1)
        x[0, 2] += 1e-8
        with self.assertRaisesRegex(ValueError, "binary"):
            binary_nullspace(x)

    def test_integrated_alias_restores_prior_uncertainty_and_signed_covariance(self):
        y = np.array([-2.0, -1.0, 0.0, 1.0, -1.0, -1.0, 0.0, 0.0])
        s = system(np.ones((8, 2)), ["context/intercept", "qb/a"], 1)
        solver = SquareRootSystem(s, y, {"qb": np.array([1])}, exact_aliases=True)
        l = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, -2.0], [0.0, 0.0]])
        actual = solver.cell([0, 1e-24], None, l, 3, 4.5)
        np.testing.assert_allclose(actual["mean"][:, 0], [y.mean(), 0], atol=1e-15)
        np.testing.assert_allclose(
            actual["diagonal"], [1e24, 1e24 + 1 / 8, 1 / 8, 4e24, 0], rtol=1e-14, atol=1e-15
        )
        np.testing.assert_allclose(actual["location"][:, 0], [0, y.mean(), y.mean(), 0, 0])
        np.testing.assert_allclose(actual["residual_quadratic"], ((y - y.mean()) ** 2).sum())
        self.assertEqual(solver.certificates["qb"]["nullity"], 1)

    def test_decimal_reference_matches_closed_form_at_two_precisions(self):
        x = np.ones((8, 2))
        y = np.array([-2.0, -1.0, 0.0, 1.0, -1.0, -1.0, 0.0, 0.0])
        l = np.array([[1.0, 1.0], [0.0, 1.0], [0.0, -2.0], [0.0, 0.0]])
        args = (x, y, 1, [0, 1e-24], [], None, l, 3, 4.5)
        low = decimal_cell(*args, digits=80)
        high = decimal_cell(*args, digits=110)
        self.assertTrue(reference_agreement(low, high))
        result = as_float(high)
        np.testing.assert_allclose(result["diagonal"], [1 / 8, 1e24, 4e24, 0], atol=1e-15)
        self.assertAlmostEqual(result["location"][0, 0], y.mean())
        damaged = dict(high, posterior_shape="123")
        self.assertFalse(reference_agreement(low, damaged))

    def test_qr_and_compression_match_ordinary_independent_conditional_fit(self):
        rng = np.random.default_rng(149)
        x = np.column_stack([np.ones(24), rng.normal(size=(24, 2))])
        y = rng.normal(size=(24, 2))
        s = system(x, ["context/intercept", "qb/a", "qb/b"], 1, [str(i // 4) for i in range(24)])
        l = np.array([[0.0, 1.0, -1.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        expected = cell(s, response_stats(s, y), [0, 3, 3], 7, l, 3, 4.5)
        for exact in (False, True):
            solver = SquareRootSystem(s, y, {"qb": np.array([1, 2])}, exact_aliases=exact)
            for compressed in (False, True):
                actual = solver.cell([0, 3, 3], 7, l, 3, 4.5, compressed=compressed)
                for key, value in expected.items():
                    np.testing.assert_allclose(actual[key], value, rtol=1e-12, atol=1e-12)
            if exact:
                self.assertEqual(solver.certificates["qb"]["reason"], "nonbinary_block_not_reduced")

    def test_permuted_alias_basis_and_prior_only_player_preserve_answers(self):
        codes = np.arange(24) % 3
        x = np.column_stack([np.ones(24), np.eye(3)[codes], np.zeros(24)])
        y = np.sin(np.arange(24))
        s = system(x, ["context/intercept", *[f"qb/{i}" for i in range(4)]], 1)
        l = np.vstack([np.eye(5), [0.0, 1.0, -1.0, 0.0, 0.0]])
        answers = []
        for reverse in (False, True):
            solver = SquareRootSystem(
                s, y, {"qb": np.arange(1, 5)}, exact_aliases=True, reverse_basis=reverse
            )
            answers.append(solver.cell([0, 1e-24, 1e-24, 1e-24, 1e-24], None, l, 3, 4.5))
        for key in answers[0]:
            np.testing.assert_allclose(answers[0][key], answers[1][key], rtol=1e-12, atol=1e-12)
        self.assertEqual(answers[0]["mean"][-1, 0], 0)
        self.assertAlmostEqual(answers[0]["diagonal"][4] / 1e24, 1)

    def test_invalid_group_precision_and_missing_observations_fail_closed(self):
        s = system(
            np.column_stack([np.ones(8), np.eye(2)[np.arange(8) % 2]]),
            ["context/intercept", "qb/a", "qb/b"],
            1,
        )
        for groups in ({"qb": [1]}, {"qb": [1, 2, 2]}, {"qb": [1.5, 2]}, {"qb": [-1, 2]}):
            with self.assertRaises(ValueError):
                SquareRootSystem(s, np.arange(8), groups, exact_aliases=True)
        with self.assertRaises(ValueError):
            SquareRootSystem(s, [np.nan] * 8, {"qb": [1, 2]})
        solver = SquareRootSystem(s, np.arange(8), {"qb": [1, 2]}, exact_aliases=True)
        with self.assertRaisesRegex(ValueError, "isotropic"):
            solver.cell([0, 1, 2], None, np.eye(3), 3, 4.5)
        for penalty in ([0, 0, 1], [1, 1, 1], [0, np.nan, 1]):
            with self.assertRaises(ValueError):
                solver.cell(penalty, None, np.eye(3), 3, 4.5)

    def test_compensated_original_residual_matches_independent_exact_products(self):
        from scipy.sparse import csr_matrix

        x = np.array([[1.0, 1.0, 1.0], [1.0, 1.0 + 1e-8, 0], [0, 0, 0]])
        b = np.array([[1e16, -31737306.0], [1.0, 31737306.0], [-1e16, -0.3]])
        y = np.array([[0.0, 0.1], [-1.0, 1.5], [2.0, -3.0]])
        actual = compensated_residual(csr_matrix(x), b, y)
        with localcontext() as ctx:
            ctx.prec = 110
            expected = np.array(
                [
                    [
                        float(
                            Decimal.from_float(y[i, j])
                            - sum(
                                (
                                    Decimal.from_float(x[i, k]) * Decimal.from_float(b[k, j])
                                    for k in range(x.shape[1])
                                ),
                                Decimal(0),
                            )
                        )
                        for j in range(y.shape[1])
                    ]
                    for i in range(y.shape[0])
                ]
            )
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(actual[0, 0], -1.0)
        with self.assertRaisesRegex(ValueError, "finite"):
            compensated_residual(csr_matrix(x), b * np.nan, y)
        with self.assertRaisesRegex(ValueError, "shapes"):
            compensated_residual(csr_matrix(x), b, y[:1])
        with self.assertRaises(FloatingPointError):
            compensated_residual(csr_matrix([[1e308]]), np.ones((1, 1)), np.zeros((1, 1)))

    def test_known_certificate_binds_all_cases_metrics_plan_and_bytes(self):
        plan = json.loads(Path("config/conditional-solver-v2.json").read_text())
        report, _ = known_study(plan)
        self.assertEqual(len(report["cases"]), 144)
        failures = [
            {k: c[k] for k in ("seed", "family", "weak_precision", "game_precision")}
            | {"result": c["candidate_results"]["exact_alias_residual"]}
            for c in report["cases"]
            if not c["candidate_results"]["exact_alias_residual"]["passed"]
        ]
        self.assertTrue(report["candidate_gates"]["exact_alias_residual"], failures)
        self.assertEqual(validate_known(report, plan), report["candidate_gates"])
        altered = deepcopy(plan)
        altered["variance_relative_tolerance"] *= 2
        with self.assertRaisesRegex(ValueError, "frozen"):
            validate_plan(altered)
        for mutation in ("case", "metric", "gate", "reference"):
            broken = deepcopy(report)
            if mutation == "case":
                broken["cases"].pop()
            elif mutation == "metric":
                broken["cases"][0]["candidate_results"]["exact_alias_residual"]["mean_error_sd"] = (
                    123
                )
            elif mutation == "reference":
                broken["cases"][0]["reference"]["posterior_shape"] = "123"
            else:
                broken["candidate_gates"]["exact_alias_residual"] = not broken["candidate_gates"][
                    "exact_alias_residual"
                ]
            with self.assertRaises(ValueError):
                validate_known(broken, plan)
        # Self-consistent fake references/outputs must not authorize a kernel.
        # The independent oracle is rebound to the frozen fixture on every load.
        forged = deepcopy(report)
        first = forged["cases"][0]
        for key in ("reference", "reference_lower_precision"):
            first[key]["location"][0][0] = "123"
        for result in first["candidate_results"].values():
            result["outputs"]["location"][0][0] = 123
            result.update(
                comparison(as_float(result["outputs"]), as_float(first["reference"]), plan)
            )
        with self.assertRaisesRegex(ValueError, "frozen fixture"):
            validate_known(forged, plan)
        with TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            rid = save(store, report, plan, "a" * 40)
            manifest, restored = load(store, rid)
            self.assertEqual(restored, report)
            # Deliberately damage the object; the existing content-addressed
            # store must reject it before any authorization is returned.
            path = store.root / "objects" / manifest["objects"]["study"]
            path.write_bytes(b"{}")
            with self.assertRaises(ValueError):
                load(store, rid)

    def test_square_root_target_preserves_prior_and_enforces_budget(self):
        from time import perf_counter

        x = np.column_stack([np.ones(8), np.eye(2)[np.arange(8) % 2]])
        s = system(x, ["context/intercept", "qb/a", "qb/b"], 1, [str(i // 2) for i in range(8)])
        target = SquareRootTarget(
            s,
            np.arange(8),
            ["qb", "game"],
            {"noise_prior_shape": 3, "noise_prior_scale": 4.5},
            {"log_precision_mean": 1, "log_precision_sd": 3},
            original_residual=True,
            evaluation_limit=1,
            deadline=perf_counter() + 10,
        )
        answer = target.conditional([0, 0], np.eye(3))
        self.assertTrue(np.isfinite(answer["log_likelihood"]).all())
        with self.assertRaisesRegex(ValueError, "budget"):
            target.conditional([0, 0], np.eye(3))


if __name__ == "__main__":
    unittest.main()
