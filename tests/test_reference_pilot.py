"""Accounting, stress selection, failures, provenance and replay are separate gates."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline_cli import save
from nfl_value.ingestion import SnapshotStore
from nfl_value.multiseason import experiment as previous_experiment
from nfl_value.qb_recovery import prepare
from nfl_value.reference_cli import replay_pilot
from nfl_value.reference_pilot import CASES, experiment, prepare_case, season_outputs, validate_plan
from nfl_value.source_audit import aware_time
from test_multiseason import datasets, plan as previous_plan
from test_variance_reference import plan


class ReferencePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, first = datasets()
        parent, models, result = previous_experiment(
            data, first, cutoff=datetime(2026, 12, 1, tzinfo=timezone.utc), plan=previous_plan()
        )
        rows = []
        for year, d in data.items():
            rows.extend(prepare(d[0], d[1], season=year, low_week=1, high_week=18)[0])
        rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
        cls.context = dict(
            parent=parent,
            models=models,
            rows=rows,
            current=[r for r in rows if r["game_id"].startswith("2026_")],
            values=result["estimates"]["evolving"],
        )
        cls.model_plan = json.loads(
            Path("config/continuous-variance-diagnostic-v1.json").read_text()
        )
        cls.continuous_parent = dict(
            plan=cls.model_plan,
            code_revision="a" * 40,
            source_provenance={},
            input_reports={},
            evidence_cutoff="2026-11-08T02:47:32+00:00",
            season=parent["season"],
        )

    def test_every_case_retained_after_declared_numerical_failure(self):
        p = {**plan(), "maximum_target_evaluations_per_case": 1}
        report, models, outputs, _ = experiment(self.context, self.continuous_parent, p)
        self.assertEqual(list(report["cases"]), CASES)
        self.assertTrue(
            all(r["status"] == "failed" and r["budget_exhausted"] for r in report["cases"].values())
        )
        self.assertFalse(report["numerical_pilot_passed"])
        self.assertFalse(report["calibration_completed"])
        self.assertFalse(report["ranking_ready"])
        self.assertEqual(models, {})
        self.assertEqual(outputs, {})

    def test_signed_season_only_accounting_retains_benchmarks_and_qualification(self):
        d, _, l, _, matrices = prepare_case(self.context, self.model_plan, "real_evolving")
        m = self.context["models"]["evolving"]
        fit = dict(
            coefficient_mean=np.array(m["coefficients"]),
            game_mean=np.array([m["game_coefficients"][g] for g in d.game_names]),
        )
        means = l @ fit["coefficient_mean"]
        summaries = {0.0: dict(mean=means, low=means - 2, high=means + 2)}
        values, ledger, error = season_outputs(self.context, d, fit, summaries, matrices, False)
        self.assertLess(error, 1e-10)
        self.assertEqual(len(ledger), len(self.context["current"]))
        self.assertTrue(all(p["game_id"].startswith("2026_") for p in ledger))
        self.assertTrue(any(v["benchmarks"]["first_unit"]["expected_points"] < 0 for v in values))
        for v, old in zip(values, self.context["values"]):
            self.assertEqual(v["qualification"], old["qualification"])
            self.assertEqual(v["opportunities"], old["opportunities"])
            self.assertFalse(
                v["numerical_valid"] or v["uncertainty_calibrated"] or v["ranking_ready"]
            )
            self.assertEqual(
                set(v["benchmarks"]), {"first_unit", "equal_player", "opportunity_weighted"}
            )
        changed = deepcopy(self.context)
        changed["rows"][0]["offense_epa"] += 0.1
        with self.assertRaisesRegex(ValueError, "frozen original"):
            prepare_case(changed, self.model_plan, "real_evolving")

    def test_plan_and_replay_do_not_hide_failed_cases_or_changed_outputs(self):
        for key, value in [
            ("cases", CASES[:-1]),
            ("maximum_seconds_total", 3601),
            ("maximum_target_evaluations_per_case", True),
            ("prior_mass_per_axis", 1),
            ("future_test", {}),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**plan(), key: value})
        p = {**plan(), "maximum_target_evaluations_per_case": 1}
        report, models, result, _ = experiment(self.context, self.continuous_parent, p)
        with tempfile.TemporaryDirectory() as folder:
            store = SnapshotStore(folder)
            rid, saved = save(store, report, models, result, code_revision="b" * 40)
            with patch("nfl_value.reference_cli.run", return_value=(report, models, result, {})):
                self.assertEqual(replay_pilot(None, store, rid)[0], saved)
            bad = deepcopy(report)
            bad["cases"].pop(CASES[-1])
            with (
                patch("nfl_value.reference_cli.run", return_value=(bad, models, result, {})),
                self.assertRaises(ValueError),
            ):
                replay_pilot(None, store, rid)
            with (
                patch.object(store, "read", side_effect=ValueError("hash mismatch")),
                patch("nfl_value.reference_cli.run") as run,
                self.assertRaisesRegex(ValueError, "hash mismatch"),
            ):
                replay_pilot(None, store, rid)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
