"""Budget isolation, analytical signed answers and complete-study selection."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import ndtr
from scipy.stats import norm

from nfl_value.coarse_control_study import archive, kernel_hash
from nfl_value.coarse_work import budget_decision, execution_plan, validate_matched_work
from nfl_value.component_allocation import integrate_allocated
from nfl_value.continuous_math import normal_logpdf
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_preflight import (
    arms,
    experiment_kind,
    load,
    save,
    summarize,
    trial,
    validate_case,
    validate_plan,
)
from nfl_value.replicated_reference import SamplingProposal
from nfl_value.tail_controls import tail_proposal
from nfl_value.two_level_reference import sampling_hash


def plan():
    return json.loads(Path("config/coarse-work-preflight-v1.json").read_text())


class AnalyticProposal(SamplingProposal):
    def __init__(self):
        super().__init__(np.zeros(1), np.eye(1), np.zeros(1), np.eye(1), {})

    def components(self, method):
        if method != "stabilized-mixture":
            raise ValueError("unexpected method")
        return [
            (0.7, np.array([-1.0]), np.array([[1.44]]), None),
            (0.3, np.array([0.5]), np.array([[2.25]]), 5),
        ]


class Toy:
    def logpdf(self, x):
        return normal_logpdf(x, [-1, 0, 0, 0], np.eye(4))

    def integrand(self, truth):
        return lambda x, logq: (
            np.exp(self.logpdf(x) - logq)[:, None]
            * np.column_stack(
                [
                    np.ones(len(x)),
                    -2 + x[:, 0],
                    -3 + x[:, 1],
                    ndtr(-2 - x[:, :2]),
                    ndtr(2 - x[:, :2]),
                    ndtr(1.5 - x[:, :2]),
                ]
            )
        )


class CoarseWorkTests(unittest.TestCase):
    def test_frozen_scope_and_only_computation_settings_can_vary(self):
        p = plan()
        validate_plan(p)
        original = json_bytes(p)
        self.assertEqual(sum(len(ids) for _, ids in arms(p)) * p["trials"], 1536)
        domains = {a: j for j, (a, ids) in enumerate(arms(p)) if ids}
        self.assertEqual(domains, {"candidate": 0, "double": 7, "quadruple": 8})
        for arm, nodes, ceiling in [
            ("candidate", 1024, 90000),
            ("double", 2048, 160000),
            ("quadruple", 4096, 300000),
        ]:
            effective = execution_plan(p, arm)
            self.assertEqual(effective["nodes_per_replicate"], nodes)
            self.assertEqual(effective["maximum_target_evaluations"], ceiling)
            self.assertLessEqual(
                {k for k in p if p[k] != effective[k]},
                {"nodes_per_replicate", "maximum_target_evaluations"},
            )
        self.assertEqual(original, json_bytes(p))
        with self.assertRaisesRegex(ValueError, "undeclared"):
            execution_plan(p, "polynomial")
        for change in [
            {"reference_endpoint_cdf_tolerance": 1},
            {"nodes_per_replicate": True},
            {"nodes_per_replicate": 1536},
        ]:
            bad = deepcopy(p)
            bad["work_budgets"]["double"].update(change)
            with self.assertRaises(ValueError):
                execution_plan(bad, "double")
            with self.assertRaises(ValueError):
                validate_plan(bad)
        legacy = json.loads(Path("config/endpoint-control-preflight-v2.json").read_text())
        self.assertIs(execution_plan(legacy, "candidate"), legacy)

    def test_single_global_budget_no_complementary_case_fallback(self):
        p = plan()
        cases = [
            dict(arm=a, target=i, decision=dict(screen_passed=(i != k)))
            for k, a in enumerate(p["work_budget_order"])
            for i in p["known_targets"]
        ]
        self.assertIsNone(budget_decision(cases, p)["selected_arm"])
        for arm in reversed(p["work_budget_order"]):
            for c in cases:
                if c["arm"] == arm:
                    c["decision"]["screen_passed"] = True
            d = budget_decision(cases, p)
            self.assertEqual(d["selected_arm"], arm)
            self.assertEqual(
                d["selected_coarse_nodes"], execution_plan(p, arm)["nodes_per_replicate"]
            )
            self.assertTrue(d["fresh_confirmation_required"])
            self.assertFalse(d["numerical_certified"])
            self.assertFalse(d["ranking_ready"])
        for bad in [cases[:-1], cases[::-1], [*cases, cases[0]]]:
            with self.assertRaisesRegex(ValueError, "case universe"):
                budget_decision(bad, p)
        for status in ("failed", "unattempted"):
            summary = summarize([dict(status=status)], p)
            self.assertFalse(summary["screen_passed"])
            self.assertEqual(summary["requested"], 1)
            self.assertEqual(summary[status], 1)

    def test_signed_integrals_against_independent_analytic_answers(self):
        q, p = AnalyticProposal(), plan()
        p.update(
            training_nodes=512,
            replicates=16,
            correction_nodes_per_replicate=32,
            allocation_replicates=8,
            allocation_component_nodes=16,
            allocation_minimum_nodes=16,
        )
        intercept = np.array([-1.2, -0.5, 1.2, 0.5, 0.8, 0.3])
        slopes = np.array([0.5, -0.7, 0.5, -0.7, 0.5, -0.7])

        def fine(x, logq):
            z = (x[:, 0] + 1) / 1.2
            mass = np.exp(norm.logpdf(x[:, 0], -1, 1.2) - logq)
            return mass[:, None] * np.column_stack(
                [np.ones(len(x)), -2 + 0.3 * z, -3 - z, ndtr(intercept + z[:, None] * slopes)]
            )

        def coarse(x, logq):
            return fine(x, logq) * (1 + 0.001 * np.sin(x[:, 0]))[:, None]

        truth = np.r_[1, -2, -3, ndtr(intercept / np.sqrt(1 + slopes**2))]
        fitted, pilots = [], []
        for j, n in enumerate((256, 512, 1024)):
            out = integrate_allocated(
                fine,
                coarse,
                q,
                entropy=[90261, j],
                fitting_entropy=[90260],
                plan={**p, "nodes_per_replicate": n},
                adaptive=True,
                endpoint_settings=p["endpoint_control"],
            )
            np.testing.assert_allclose(out["total"].mean(axis=0), truth, atol=4e-5)
            self.assertTrue(np.all(out["total"][:, 1:3] < 0))
            self.assertEqual(sum(out["components"]["applied_counts"]), n)
            fitted.append(json_bytes(out["fit"]))
            pilots.append(json_bytes(out["components"]["pilot_controlled"]))
        self.assertEqual(len(set(fitted)), 1)
        self.assertEqual(len(set(pilots)), 1)

    def test_matched_trials_call_counts_budget_integrity_and_saved_selection(self):
        p = plan()
        p.update(
            known_targets=[3],
            double_targets=[3],
            quadruple_targets=[3],
            trials=1,
            search_nodes=64,
            starts=4,
            ratio_starts=2,
            em_nodes=128,
            em_steps=2,
            mass_pilot_nodes=128,
            training_nodes=256,
            replicates=8,
            correction_nodes_per_replicate=16,
            allocation_component_nodes=4,
            allocation_minimum_nodes=2,
        )
        for a, n in zip(p["work_budget_order"], [64, 128, 256]):
            p["work_budgets"][a]["nodes_per_replicate"] = n
        target, initial, cases = Toy(), tail_proposal(), []
        for a, domain in (("candidate", 0), ("double", 7), ("quadruple", 8)):
            r = trial(target, initial, {}, p, [p["base_seed"], domain, 3, 0], a)
            self.assertIn("coarse", r, r.get("error"))
            e = execution_plan(p, a)
            self.assertEqual(
                r["work"]["counts"]["coarse_evaluation"],
                256 + 8 * 4 * 8 + 8 * (e["nodes_per_replicate"] + 16),
            )
            self.assertEqual(r["work"]["counts"]["fine_evaluation"], 8 * 16)
            case = dict(
                arm=a,
                target=3,
                truth={},
                initial_sampling_sha256=sampling_hash(initial),
                records=[dict(trial=0, **r)],
                decision=summarize([r], p),
            )
            validate_case(case, initial, {}, p, target=target)
            bad = deepcopy(case)
            bad["records"][0]["components"]["applied_counts"][0] *= 2
            with self.assertRaisesRegex(ValueError, "allocation"):
                validate_case(bad, initial, {}, p, target=target)
            cases.append(case)
        validate_matched_work(cases, p)
        for field in ("fit", "components"):
            bad = deepcopy(cases)
            r = bad[1]["records"][0]
            if field == "fit":
                r["fit"]["responses_sha256"] = "0" * 64
            else:
                r["components"]["pilot_plain"][0][0][0] += 0.01
            with self.assertRaisesRegex(ValueError, "matched budget"):
                validate_matched_work(bad, p)
        for j, n in enumerate((64, 128, 256)):
            self.assertEqual(
                cases[j]["records"][0]["work"]["total"] - cases[0]["records"][0]["work"]["total"],
                8 * (n - 64),
            )
        decision = budget_decision(cases, p)
        result = dict(
            experiment=experiment_kind(p),
            plan=p,
            cases=cases,
            screen_passed=decision["selected_arm"] is not None,
            work_decision=decision,
            numerical_certified=False,
            ranking_ready=False,
            nfl_data_used=False,
        )
        # Small deterministic fixture; production's exact frozen-plan hash is
        # exercised separately above, never bypassed by the real CLI.
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("nfl_value.mode_preflight.validate_plan"),
            patch("nfl_value.mode_preflight.inputs", return_value={3: (target, initial, {})}),
        ):
            store = SnapshotStore(Path(tmp))
            rid, m = save(store, result, "test-producer", kernel_hash())
            self.assertEqual(load(store, rid)[1], result)
            bad = deepcopy(m)
            bad["work_decision"]["fresh_confirmation_required"] = False
            altered = store.put(json_bytes(bad), manifest=True)
            with self.assertRaisesRegex(ValueError, "selection"):
                load(store, altered)

    def test_work_report_cannot_open_nfl_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid = store.put(
                json_bytes(dict(plan=plan(), experiment=experiment_kind(plan()))), manifest=True
            )
            with patch("nfl_value.coarse_control_study.archive_inputs") as access:
                with self.assertRaisesRegex(ValueError, "frozen design"):
                    archive(store, rid)
                access.assert_not_called()


if __name__ == "__main__":
    unittest.main()
