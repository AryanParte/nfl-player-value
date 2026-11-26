"""Independent allocation references and failure-inclusive study accounting."""

from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.stats import norm

from nfl_value.coarse_control_study import archive
from nfl_value.component_allocation import (
    allocate,
    component_integrals,
    pilot_allocation,
    weighted_total,
)
from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD, controlled_integrals, fit_control
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_preflight import (
    arms,
    experiment_kind,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.replicated_reference import SamplingProposal, replicate_integrals
from nfl_value.tail_controls import tail_proposal
from nfl_value.two_level_reference import sampling_hash


def plan():
    return json.loads(Path("config/allocation-discovery-preflight-v1.json").read_text())


class TwoComponents(SamplingProposal):
    def __init__(self):
        super().__init__(np.zeros(1), np.eye(1), np.zeros(1), np.eye(1), {})

    def components(self, method):
        if method != METHOD:
            raise ValueError("unexpected method")
        return [(0.25, np.array([-1.0]), np.eye(1), None), (0.75, np.array([1.0]), np.eye(1), None)]


class ComponentAllocationTests(unittest.TestCase):
    def test_dynamic_program_matches_exhaustive_reference_and_ties(self):
        for scores in ([1, 2, 9], [1, 1, 1], [0, 0, 8], [1e-8, 1, 1e8]):
            feasible = [n for n in product((2, 4, 8, 16), repeat=3) if sum(n) == 16]
            reference = min(feasible, key=lambda n: (sum(s / x for s, x in zip(scores, n)), n))
            self.assertEqual(allocate(scores, 16, 2), list(reference))
        self.assertEqual(allocate([0] * 8, 1024, 32), [128] * 8)
        n = allocate([8, 1, 4, 0, 9, 12, 3, 8], 1024, 32)
        self.assertEqual(sum(n), 1024)
        self.assertTrue(all(x >= 32 and x & (x - 1) == 0 for x in n))
        for scores, budget, minimum in (
            ([-1, 2], 16, 2),
            ([np.nan], 16, 2),
            ([1] * 9, 16, 2),
            ([1], 15, 2),
        ):
            with self.assertRaises(ValueError):
                allocate(scores, budget, minimum)

    def test_component_weights_are_masses_not_unequal_sample_fractions(self):
        q, seen = TwoComponents(), []

        def f(x, logq):
            expected = 0.25 * norm.pdf(x[:, 0], -1) + 0.75 * norm.pdf(x[:, 0], 1)
            np.testing.assert_allclose(np.exp(logq), expected, rtol=1e-13)
            value = (2, -5)[len(seen) % 2]
            seen.append(len(x))
            return np.full((len(x), 1), value)

        result = component_integrals(f, q, entropy=[777], replicates=8, counts=[4, 32])
        np.testing.assert_array_equal(result["plain"], np.full((8, 1), -3.25))
        self.assertEqual(seen, [4, 32] * 8)
        self.assertNotEqual(-3.25, (4 * 2 - 32 * 5) / 36)
        self.assertEqual(
            weighted_total(result["plain_components"], [0.25, 0.75]).tolist(),
            result["plain"].tolist(),
        )

    def test_equal_nets_match_existing_integrators_exactly_and_signed_answer(self):
        q = TwoComponents()

        def f(x, logq):
            v = x[:, 0]
            return (np.exp(norm.logpdf(v) - logq) * (-2 + v - 0.1 * v**2))[:, None]

        args = dict(entropy=[778], replicates=8, nodes=512)
        expected = replicate_integrals(f, q, METHOD, **args)
        raw = component_integrals(f, q, entropy=args["entropy"], replicates=8, counts=[256, 256])
        np.testing.assert_array_equal(raw["plain"], expected)
        fit = fit_control(f, q, entropy=[779], nodes=256, relative_ridge=1e-6)
        control, plain = controlled_integrals(f, fit, q, **args)
        raw = component_integrals(
            f, q, entropy=args["entropy"], replicates=8, counts=[256, 256], fitted=fit
        )
        np.testing.assert_array_equal(raw["controlled"], control)
        np.testing.assert_array_equal(raw["plain"], plain)
        unequal = component_integrals(
            f, q, entropy=[780], replicates=16, counts=[256, 1024], fitted=fit
        )
        self.assertAlmostEqual(unequal["controlled"].mean(), -2.1, delta=0.01)
        for counts in ([3, 16], [16], [True, 16]):
            with self.assertRaises(ValueError):
                component_integrals(f, q, entropy=[1], replicates=8, counts=counts)

    def test_ratio_pilot_uses_covariance_and_ignores_wrong_endpoint_columns(self):
        p = plan()
        r = np.arange(8, dtype=float)
        plain = np.ones((8, 8, 9))
        plain[:, :, 0] = (2 + r / 10)[:, None]
        for k in range(1, 9):
            plain[:, :, k] = (k - 3) * plain[:, :, 0]
        control = plain.copy()
        for j in range(8):
            for k in range(1, 7):
                control[:, j, k] += (j + 1) * k * r / 1000
        masses = np.arange(1, 9, dtype=float) / 36
        out = pilot_allocation(plain, control, masses, p)
        np.testing.assert_allclose(out["anchors"], np.arange(1, 7) - 3, atol=1e-14)
        expected = []
        for j in range(8):
            variances = []
            for k in range(1, 7):
                x, z = control[:, j, k], control[:, j, 0]
                c = k - 3
                covariance = sum((a - x.mean()) * (b - z.mean()) for a, b in zip(x, z)) / 7
                variances.append(np.var(x, ddof=1) + c**2 * np.var(z, ddof=1) - 2 * c * covariance)
            expected.append(variances)
        np.testing.assert_allclose(out["residual_variances"], expected, atol=5e-16)
        scores = (
            masses**2
            * 32
            * (np.asarray(expected) / np.array(p["allocation_tolerances"]) ** 2).sum(axis=1)
        )
        np.testing.assert_allclose(out["scores"], scores, rtol=1e-10)
        control[:, :, 7:] = 1e15
        self.assertEqual(out, pilot_allocation(plain, control, masses, p))
        for corrupt in (np.full_like(plain, np.nan), -plain):
            with self.assertRaises(ValueError):
                pilot_allocation(corrupt, control, masses, p)

    def test_three_arms_match_fits_keep_separate_draws_count_work_and_reject_corruption(self):
        p = {
            **plan(),
            "search_nodes": 64,
            "starts": 4,
            "ratio_starts": 2,
            "previous_search_nodes": 32,
            "previous_starts": 5,
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
                            np.full((len(x), 2), 0.025),
                            np.full((len(x), 2), 0.975),
                            np.full((len(x), 2), 0.9),
                        ]
                    )
                )

        records = {}
        for arm, domain in (("candidate", 0), ("equal", 4), ("previous", 5)):
            record = trial(Toy(), initial, {}, p, [p["base_seed"], domain, 3, 0], arm)
            self.assertIn("coarse", record, record.get("error"))
            self.assertLess(np.array(record["coarse"])[:, 1].mean(), 0)
            self.assertEqual(
                record["work"]["counts"]["coarse_evaluation"], 256 + 8 * 4 * 8 + 8 * (64 + 16)
            )
            self.assertEqual(record["work"]["counts"]["fine_evaluation"], 8 * 16)
            case = dict(
                arm=arm,
                target=3,
                truth={},
                initial_sampling_sha256=sampling_hash(initial),
                records=[dict(trial=0, **record)],
                decision=summarize([record], p),
            )
            validate_case(case, initial, {}, p)
            for mutate in (
                lambda r: r["components"]["applied_counts"].__setitem__(0, 999),
                lambda r: r["components"]["allocation"]["scores"].__setitem__(0, 999),
                lambda r: r["components"]["pilot_plain"][0][0].__setitem__(1, 999),
                lambda r: r["components"]["pilot_controlled"][0][0].__setitem__(1, 999),
                lambda r: r["components"]["pilot_plain"][0][0].pop(),
                lambda r: r["components"]["coarse_components"][0][0].__setitem__(1, 999),
                lambda r: r["components"]["correction_components"][0][0].__setitem__(1, 999),
                lambda r: r["components"].update(pilot_entropy=[1]),
                lambda r: r["components"].update(sampling_sha256="0" * 64),
                lambda r: r["components"]["mixture_masses"].__setitem__(0, 0.5),
                lambda r: r["fit"].update(training_entropy=[1]),
                lambda r: r["work"]["counts"].update(coarse_evaluation=1),
            ):
                corrupt = deepcopy(case)
                mutate(corrupt["records"][0])
                with self.assertRaises(ValueError):
                    validate_case(corrupt, initial, {}, p)
            records[arm] = record
        for key in ("geometry", "fit"):
            self.assertEqual(records["candidate"][key], records["equal"][key])
        for key in ("pilot_plain", "pilot_controlled", "allocation"):
            self.assertEqual(
                records["candidate"]["components"][key], records["equal"]["components"][key]
            )
        self.assertNotEqual(records["candidate"]["geometry"], records["previous"]["geometry"])
        self.assertEqual(
            len({tuple(r["components"]["coarse_entropy"]) for r in records.values()}), 3
        )
        self.assertEqual(len({tuple(r["fit"]["training_entropy"]) for r in records.values()}), 1)
        c = records["candidate"]["components"]
        self.assertEqual(
            len(
                {tuple(c[k]) for k in ("pilot_entropy", "coarse_entropy", "correction_entropy")}
                | {tuple(records["candidate"]["fit"]["training_entropy"])}
            ),
            4,
        )

    def test_frozen_scope_no_oracle_and_nfl_gate(self):
        p = plan()
        validate_plan(p)
        self.assertEqual(sum(len(ids) for _, ids in arms(p)) * p["trials"], 576)
        self.assertEqual(p["oracle_targets"], [])
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(json_bytes(dict(plan=p, experiment=experiment_kind(p))), manifest=True)
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()
        p["allocation_minimum_nodes"] = 16
        with self.assertRaisesRegex(ValueError, "frozen design"):
            validate_plan(p)


if __name__ == "__main__":
    unittest.main()
