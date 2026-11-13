"""Independent ratio algebra, signed accounting and randomized sampling contracts."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.stats import multivariate_normal, t

from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.randomized_cli import load, save
from nfl_value.randomized_controls import coverage_decision, select, validate_plan, validate_result
from nfl_value.replicated_reference import (
    SamplingProposal,
    confidence_sets,
    functional_check,
    replicate_integrals,
)


def plan():
    return json.loads(Path("config/randomized-reference-v1.json").read_text())


class ReplicateTests(unittest.TestCase):
    def test_ratio_sets_match_independent_quadratic_inversion(self):
        rng = np.random.default_rng(1701)
        samples = rng.multivariate_normal(
            [3, -4, 0.5], [[0.2, 0.1, -0.1], [0.1, 0.6, 0.01], [-0.1, 0.01, 0.3]], 32
        )
        result = confidence_sets(samples, [-1, 0, 0])
        mean = samples.mean(axis=0)
        covariance = np.cov(samples.T, ddof=1) / 32
        q = t.ppf(1 - 0.05 / 6, 31) ** 2
        for j in [1, 2]:
            roots = np.sort(
                np.roots(
                    [
                        mean[0] ** 2 - q * covariance[0, 0],
                        -2 * (mean[0] * mean[j] - q * covariance[0, j]),
                        mean[j] ** 2 - q * covariance[j, j],
                    ]
                )
            )
            np.testing.assert_allclose(
                [result["low"][j], result["high"][j]], roots, atol=1e-12, rtol=0
            )
        scaled = confidence_sets(samples * 71, [-1, 0, 0])
        for k in ["estimate", "low", "high"]:
            np.testing.assert_allclose(result[k][1:], scaled[k][1:], atol=1e-12)
        self.assertLess(result["high"][1], 0)

    def test_exact_zero_signed_ratios_and_constant_mass_student_interval(self):
        mass = np.linspace(1, 2, 32)
        a = confidence_sets(np.column_stack([mass, -3 * mass, np.zeros(32)]), [-1, 0, 0])
        np.testing.assert_allclose(a["low"][1:], [-3, 0], atol=1e-14)
        np.testing.assert_allclose(a["high"][1:], [-3, 0], atol=1e-14)
        y = np.linspace(-2, 4, 32)
        b = confidence_sets(np.column_stack([np.ones(32), y]), [-1, 0], simultaneous=False)
        half = t.ppf(0.975, 31) * y.std(ddof=1) / np.sqrt(32)
        np.testing.assert_allclose(
            [b["low"][1], b["high"][1]], [y.mean() - half, y.mean() + half], atol=1e-14
        )

    def test_unbounded_mass_and_corrupt_inputs_fail_explicitly(self):
        for data, den in [
            (np.zeros((32, 2)), [-1, 0]),
            (np.array([[0.1, 1], [8, 1]]), [-1, 0]),
            (np.ones((1, 2)), [-1, 0]),
            (np.ones((32, 2)), [-1, 1]),
            (np.full((32, 2), np.nan), [-1, 0]),
        ]:
            with self.assertRaises(ValueError):
                confidence_sets(data, den)

    def test_stratified_mixture_corrects_density_mass_and_replays(self):
        proposal = SamplingProposal(
            np.array([1.0, -1.0]),
            np.array([[1.0, 0.3], [0.3, 1.5]]),
            np.zeros(2),
            np.eye(2) * 9,
            {},
        )
        target = multivariate_normal(mean=[0.2, -0.4], cov=np.eye(2))

        def f(points, logq):
            weights = np.exp(target.logpdf(points) - logq)
            return weights[:, None] * np.column_stack([np.ones(len(points)), points])

        for method in ["local-t", "defensive-mixture"]:
            x = replicate_integrals(
                f, proposal, method, entropy=[1701, 99], replicates=8, nodes=512
            )
            np.testing.assert_allclose(x.mean(axis=0), [1, 0.2, -0.4], atol=0.03, rtol=0)
            np.testing.assert_array_equal(
                x,
                replicate_integrals(
                    f, proposal, method, entropy=[1701, 99], replicates=8, nodes=512
                ),
            )
            y = replicate_integrals(
                f, proposal, method, entropy=[1701, 100], replicates=8, nodes=512
            )
            self.assertFalse(np.array_equal(x, y))
        for nodes in [0, 3, 127]:
            with self.assertRaises(ValueError):
                replicate_integrals(f, proposal, "local-t", entropy=[17], nodes=nodes)
        with self.assertRaises(ValueError):
            replicate_integrals(
                lambda x, q: np.full((len(x), 1), np.nan),
                proposal,
                "local-t",
                entropy=[17],
                nodes=8,
            )

    def test_simultaneous_multiplicity_and_asymmetric_error_budget(self):
        x = np.random.default_rng(9).uniform(1, 2, (32, 4))
        a = confidence_sets(x, [-1, 0, 0, 0])
        b = confidence_sets(x, [-1, 0, 0, 0], simultaneous=False)
        self.assertGreater(a["critical"], b["critical"])
        valid, error = functional_check(
            dict(estimate=np.array([0.2]), low=np.array([0.0]), high=np.array([0.3])),
            np.array([0.0]),
            np.array([0.35]),
        )
        self.assertFalse(valid)
        self.assertAlmostEqual(error[0], 0.4)

    def test_frozen_plan_and_coverage_denominators_are_not_result_flags(self):
        p = plan()
        validate_plan(p)
        for changes in [
            {"replicates": 64},
            {"base_seed": 1},
            {"future_test": {"season": 2026, "weeks": [10], "fitting_update_allowed": 0}},
        ]:
            with self.assertRaises(ValueError):
                validate_plan({**p, **changes})
        good = dict(
            status="complete",
            simultaneous_covered=True,
            marginal_covered=[True] * 7,
            precision_passed=True,
            wrong_endpoints_rejected=True,
            bounds=dict(estimate=[1, 0, 0, 0.025, 0.025, 0.975, 0.975]),
            replicate_mass_maximum_share=1 / 32,
        )
        records = [deepcopy(good) for _ in range(128)]
        self.assertTrue(coverage_decision(records, p)["passed"])
        records[0] = dict(status="failed", error="unbounded")
        result = coverage_decision(records, p)
        self.assertEqual(result["trials"], 128)
        self.assertFalse(result["passed"])
        self.assertEqual(result["simultaneous_coverage"], 127 / 128)
        candidate = {
            "local-t": [dict(decision=dict(passed=False))] * 4,
            "defensive-mixture": [dict(decision=dict(passed=True))] * 4,
        }
        self.assertEqual(select(candidate, p["proposals"]), "defensive-mixture")
        candidate["defensive-mixture"].pop()
        self.assertIsNone(select(candidate, p["proposals"]))

    def test_artifact_preserves_failures_and_rejects_forged_or_missing_evidence(self):
        p = plan()
        records = []
        for i in range(4):
            trials = [
                dict(
                    trial=j,
                    entropy=[p["base_seed"], 0, i, j],
                    status="failed",
                    error="synthetic failure fixture",
                )
                for j in range(p["selection_trials"])
            ]
            records.append(dict(fixture=i, trials=trials, decision=coverage_decision(trials, p)))
        result = dict(
            experiment="replicated-reference-controls-v1",
            plan=p,
            selection={m: deepcopy(records) for m in p["proposals"]},
            selected_before_confirmation=None,
            confirmation=[],
            selected=None,
            controls_passed=False,
            nfl_data_used=False,
            calibration_completed=False,
            ranking_ready=False,
        )
        self.assertIsNone(validate_result(result))
        with tempfile.TemporaryDirectory() as directory:
            output = SnapshotStore(directory)
            rid, manifest = save(output, result, dict(synthetic=True), "a" * 40)
            _, replayed = load(output, rid)
            self.assertEqual(result, replayed)
            bad = deepcopy(manifest)
            bad["controls_passed"] = True
            with self.assertRaisesRegex(ValueError, "mismatch"):
                load(output, output.put(json_bytes(bad), manifest=True))
            bad = deepcopy(manifest)
            bad["objects"]["study"] = "f" * 64
            with self.assertRaises((ValueError, OSError)):
                load(output, output.put(json_bytes(bad), manifest=True))
        for mutation in ["flag", "omit", "duplicate", "decision", "entropy"]:
            bad = deepcopy(result)
            case = bad["selection"]["local-t"][0]
            if mutation == "flag":
                bad["controls_passed"] = True
            elif mutation == "omit":
                case["trials"].pop()
            elif mutation == "duplicate":
                case["trials"][1] = deepcopy(case["trials"][0])
            elif mutation == "decision":
                case["decision"]["passed"] = True
            else:
                case["trials"][0]["entropy"][1] = 1
            with self.assertRaises(ValueError):
                validate_result(bad)


if __name__ == "__main__":
    unittest.main()
