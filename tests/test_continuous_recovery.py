"""Cumulative accounting, consumed draws, failure denominators and replay contracts."""

from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import active_children, get_context
import socket
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline_cli import save
from nfl_value.continuous_cli import replay_experiment
from nfl_value.continuous_recovery import (
    calibration,
    initialize_worker,
    experiment,
    predict_frozen,
    simulate,
    summarize_trials,
    validate_plan,
)
from nfl_value.ingestion import SnapshotStore
from nfl_value.multiseason import experiment as previous_experiment
from nfl_value.multiseason_math import design
from nfl_value.qb_recovery import prepare
from nfl_value.source_audit import aware_time
from test_continuous_math import plan
from test_multiseason import datasets, plan as previous_plan


def probe_worker_network():
    blocked = []
    for action in [
        lambda: socket.getaddrinfo("127.0.0.1", 9),
        lambda: socket.socket(socket.AF_INET),
    ]:
        try:
            action()
        except AssertionError:
            blocked.append(True)
        else:
            blocked.append(False)
    a, b = socket.socketpair()
    a.close()
    b.close()
    return blocked


class ContinuousRecoveryTests(unittest.TestCase):
    def test_spawned_workers_forbid_network_but_allow_local_ipc(self):
        with ProcessPoolExecutor(
            max_workers=1,
            mp_context=get_context("spawn"),
            initializer=initialize_worker,
            initargs=(None,),
        ) as executor:
            self.assertEqual(executor.submit(probe_worker_network).result(timeout=30), [True, True])

    def test_bounded_parallel_execution_reproduces_every_trial_and_failure(self):
        d, _ = design(self.context["rows"], "evolving", scoring_season=2026)
        l = np.eye(len(d.names))[:2]
        p = {**self.plan, "simulation_scenarios": ["continuous_prior"]}
        before = d.gram.copy()
        children = {p.pid for p in active_children()}
        serial = calibration(d, l, previous_plan(), p, lambda _: None, lambda *_: None, workers=1)
        parallel = calibration(d, l, previous_plan(), p, lambda _: None, lambda *_: None, workers=2)
        self.assertEqual(serial, parallel)
        self.assertEqual({p.pid for p in active_children()}, children)
        capped = calibration(
            d,
            l,
            previous_plan(),
            {**p, "diagnostic_trial_cap": 1},
            lambda _: None,
            lambda *_: None,
            workers=1,
        )
        self.assertEqual(capped[0]["continuous_prior"]["requested_replicates"], 2)
        self.assertEqual(capped[0]["continuous_prior"]["attempted_replicates"], 1)
        self.assertEqual(capped[0]["continuous_prior"]["unattempted_replicates"], 1)
        self.assertEqual(capped[1]["continuous_prior"], [serial[1]["continuous_prior"][0]])
        np.testing.assert_array_equal(d.gram, before)
        with self.assertRaises(ValueError):
            calibration(d, l, previous_plan(), p, lambda _: None, lambda *_: None, workers=0)

    @classmethod
    def setUpClass(cls):
        data, first = datasets()
        parent, models, old = previous_experiment(
            data, first, cutoff=datetime(2026, 12, 1, tzinfo=timezone.utc), plan=previous_plan()
        )
        rows = []
        for y, d in data.items():
            rows.extend(prepare(d[0], d[1], season=y, low_week=1, high_week=18)[0])
        rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
        cls.current = [p for p in rows if p["game_id"].startswith("2026_")]
        parent.update(
            code_revision="a" * 40,
            input_reports={},
            evidence_cutoff="2026-12-01T00:00:00+00:00",
            source_provenance={},
        )
        cls.context = dict(
            parent=parent,
            models=models,
            rows=rows,
            current=cls.current,
            values=old["estimates"]["evolving"],
        )
        # Deliberately impossible numerical ESS: no test can promote this fixture.
        cls.plan = {
            **plan(),
            "simulation_replicates": 2,
            "sobol_powers": [7, 8],
            "minimum_effective_samples": 1e9,
            "numerical_proposal": "stratified_student_t5_v1",
        }
        cls.report, cls.models, cls.result = experiment(cls.context, cls.plan)

    def test_season_only_negative_nonduplicated_accounting_and_inherited_eligibility(self):
        values = self.result["estimates"]
        ledger = self.result["play_ledger"]
        self.assertEqual(len(ledger), len(self.current))
        self.assertTrue(all(p["game_id"].startswith("2026_") for p in ledger))
        self.assertTrue(any(p["qb_above_first_unit"] < 0 for p in ledger))
        self.assertAlmostEqual(
            sum(p["qb_above_first_unit"] for p in ledger),
            sum(v["benchmarks"]["first_unit"]["expected_points"] for v in values),
            places=10,
        )
        for v, parent in zip(values, self.context["values"]):
            self.assertEqual(v["qualification"], parent["qualification"])
            self.assertEqual(v["opportunities"], parent["opportunities"])
            self.assertFalse(v["numerical_valid"])
            self.assertFalse(v["uncertainty_calibrated"])
            self.assertFalse(v["ranking_ready"])
            self.assertEqual(
                set(v["benchmarks"]), {"first_unit", "equal_player", "opportunity_weighted"}
            )
            self.assertAlmostEqual(
                sum(g["expected_points"] for g in v["game_ledger"]),
                v["benchmarks"]["first_unit"]["expected_points"],
                places=10,
            )
        self.assertEqual(self.report["season"]["historical_opportunities_in_scoring_total"], 0)
        with self.assertRaisesRegex(ValueError, "numerically invalid"):
            predict_frozen(self.models["evolving"], self.current)
        bad = deepcopy(self.context)
        bad["rows"][0]["offense_epa"] += 1
        with self.assertRaisesRegex(ValueError, "parent design"):
            experiment(bad, self.plan)

    def test_failures_cannot_disappear_from_calibration_denominator(self):
        good = dict(
            replicate=0,
            numerical_valid=True,
            truth=[0.0, 2.0],
            mean=[0.0, 0.0],
            low=[-1.0, -1.0],
            high=[1.0, 1.0],
            mode_mean=[0.0, 0.0],
            mode_low=[-1.0, -1.0],
            mode_high=[1.0, 1.0],
        )
        report = summarize_trials(
            [
                good,
                {**good, "replicate": 1},
                dict(replicate=2, numerical_valid=False, error="singular"),
            ],
            3,
            2,
        )
        self.assertEqual(report["all_trial_coverage_bounds"], [1 / 3, 2 / 3])
        self.assertEqual(report["success_only_integrated"]["coverage"], 0.5)
        self.assertEqual(report["failed_replicates"], 1)
        self.assertFalse(report["all_numerically_valid"])
        self.assertFalse(report["passes_admission"])
        partial = summarize_trials([good, {"replicate": 1, "numerical_valid": False}], 4, 2)
        self.assertEqual(partial["attempted_replicates"], 2)
        self.assertEqual(partial["unattempted_replicates"], 2)
        self.assertEqual(partial["failed_replicates"], 1)
        self.assertEqual(partial["all_trial_coverage_bounds"], [1 / 8, 7 / 8])
        self.assertFalse(partial["all_numerically_valid"])
        for scenario in self.report["calibration"].values():
            self.assertEqual(scenario["requested_replicates"], 2)
            self.assertEqual(scenario["failed_replicates"], 2)
            self.assertEqual(scenario["all_trial_coverage_bounds"], [0.0, 1.0])

    def test_new_generator_reproducible_and_independent_of_observed_outcomes(self):
        rows = self.context["rows"]
        d, _ = design(rows, "evolving", scoring_season=2026)
        changed = deepcopy(rows)
        for p in changed:
            p["offense_epa"] += 1000
        other, _ = design(changed, "evolving", scoring_season=2026)
        for scenario in self.plan["simulation_scenarios"]:
            a, y = simulate(d, previous_plan(), self.plan, scenario)
            b, z = simulate(other, previous_plan(), self.plan, scenario)
            np.testing.assert_array_equal(a, b)
            np.testing.assert_array_equal(y, z)
            fresh, _ = simulate(
                d, previous_plan(), {**self.plan, "simulation_seed": 20261110}, scenario
            )
            if scenario != "fixed_year_changes":
                self.assertFalse(np.array_equal(a, fresh))
        for key, value in [
            ("simulation_replicates", True),
            ("sobol_powers", [7, 9]),
            ("scramble_seeds", [1, 1]),
            ("log_precision_sd", float("nan")),
            ("future_test", {}),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**self.plan, key: value})

    def test_replay_checks_artifact_hashes_and_recomputed_values_before_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            rid, saved = save(store, self.report, self.models, self.result, code_revision="b" * 40)
            with patch(
                "nfl_value.continuous_cli.run", return_value=(self.report, self.models, self.result)
            ):
                self.assertEqual(replay_experiment(None, None, None, store, rid), saved)
            changed = deepcopy(self.result)
            changed["estimates"][0]["benchmarks"]["first_unit"]["expected_points"] += 0.01
            with (
                patch(
                    "nfl_value.continuous_cli.run", return_value=(self.report, self.models, changed)
                ),
                self.assertRaisesRegex(ValueError, "numeric replay"),
            ):
                replay_experiment(None, None, None, store, rid)
            with (
                patch.object(store, "read", side_effect=ValueError("hash mismatch")),
                patch("nfl_value.continuous_cli.run") as run,
                self.assertRaisesRegex(ValueError, "hash mismatch"),
            ):
                replay_experiment(None, None, None, store, rid)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
