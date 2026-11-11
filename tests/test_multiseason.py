"""Offline scientific contracts: historical information is not historical points."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline_cli import save
from nfl_value.defense_variance import diagnose
from nfl_value.ingestion import SnapshotStore
from nfl_value.multiseason import experiment, predict
from nfl_value.multiseason_cli import replay_experiment
from nfl_value.multiseason_control import controls
from nfl_value.multiseason_math import allocation_witness, contrast, design, validate_plan
from nfl_value.multiseason_simulation import simulate, summary
from nfl_value.qb_recovery import prepare
from test_defensive_model import fixture as defense_fixture
from test_qb_recovery import sample


def plan():
    p = json.loads(Path("config/multiseason-v1.json").read_text())
    p.update(precision_grid=[4.0, 400.0], simulation_replicates=4, quantile_iterations=24)
    return p


def datasets():
    data = {}
    for year in [2024, 2025, 2026]:
        ledger, evidence, first, games = sample(year)
        data[year] = ledger, evidence, games, {"synthetic": True}
    return data, first


class MultiSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.first = datasets()
        cls.cutoff = datetime(2026, 12, 1, tzinfo=timezone.utc)
        cls.report, cls.models, cls.results = experiment(
            cls.data, cls.first, cutoff=cls.cutoff, plan=plan()
        )

    def test_current_only_total_benchmarks_signed_accounting_and_eligibility_separation(self):
        report, models, result = self.report, self.models, self.results
        self.assertEqual(report["season"]["historical_opportunities_in_scoring_total"], 0)
        self.assertEqual(set(models), {"evolving", "persistent", "team", "qb_proxy"})
        for variant, values in result["estimates"].items():
            ledger = result["play_ledgers"][variant]
            self.assertEqual(len(ledger), report["season"]["plays"])
            self.assertTrue(all(p["game_id"].startswith("2026_") for p in ledger))
            self.assertTrue(any(p["observed_epa"] < 0 for p in ledger))
            self.assertTrue(any(p["qb_above_first_unit"] < 0 for p in ledger))
            self.assertAlmostEqual(
                sum(v["benchmarks"]["first_unit"]["expected_points"] for v in values),
                sum(p["qb_above_first_unit"] for p in ledger),
                places=10,
            )
            for v in values:
                self.assertFalse(v["ranking_ready"])
                self.assertEqual(
                    set(v["benchmarks"]), {"first_unit", "equal_player", "opportunity_weighted"}
                )
                self.assertAlmostEqual(
                    sum(g["expected_points"] for g in v["game_ledger"]),
                    v["benchmarks"]["first_unit"]["expected_points"],
                    places=10,
                )
            self.assertGreater(
                len(models[variant]["training_games"]), len({p["game_id"] for p in ledger})
            )
        self.assertFalse(report["ranking_ready"])
        self.assertEqual(
            report["evaluation"]["evolving"]["identification"]["nonestimable_contrasts"],
            report["season"]["players"],
        )

    def test_future_evaluation_is_frozen_and_keeps_unseen_qb(self):
        prepared, _ = prepare(
            self.data[2026][0], self.data[2026][1], season=2026, low_week=1, high_week=3
        )
        model = self.models["evolving"]
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            predict(model, prepared)
        future = deepcopy(prepared[0])
        future.update(
            game_id="2026_10_BUF_NYJ",
            week=10,
            scheduled_kickoff="2026-11-15T18:00:00+00:00",
            qb="00-9999999",
        )
        output, unseen = predict(model, [future])
        self.assertEqual(len(output), 1)
        self.assertEqual(unseen, {"innovation": 1, "qb": 1})
        self.assertEqual(model, before)
        broken = deepcopy(model)
        broken["coefficients"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "frozen model"):
            predict(broken, [future])
        broken = deepcopy(model)
        broken["names"][0] = broken["names"][1]
        with self.assertRaisesRegex(ValueError, "frozen model"):
            predict(broken, [future])
        future["week"] = 11
        with self.assertRaisesRegex(ValueError, "reserved"):
            predict(model, [future])

    def test_reserved_training_window_and_policy_validation_fail_closed(self):
        validate_plan(plan())
        for key, value in [
            ("scoring_season", 2025),
            ("simulation_replicates", True),
            ("noise_prior_shape", 0.5),
            ("precision_grid", [4.0, float("nan")]),
            ("primary", "qb_proxy"),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**plan(), key: value})
        p = plan()
        p["future_test"]["weeks"] = [3]
        with self.assertRaisesRegex(ValueError, "reserved future"):
            experiment(self.data, self.first, cutoff=self.cutoff, plan=p)

    def test_cold_benchmark_and_prediction_preserving_transition_alias(self):
        rows = []
        for year, d in self.data.items():
            rows.extend(prepare(d[0], d[1], season=year, low_week=1, high_week=3)[0])
        # A cross-year team switch links persistent QB effects, but each year
        # still has its own innovation/team allocation ambiguity.
        a, b = sorted({p["qb"] for p in rows})[:2]
        changed = deepcopy(rows)
        for p in changed:
            if p["game_id"].startswith("2025_"):
                p["qb"] = b if p["qb"] == a else a if p["qb"] == b else p["qb"]
        sizes = {}
        for variant in ["persistent", "evolving"]:
            d, _ = design(changed, variant, scoring_season=2026, extra_qbs=["00-9999999"])
            l = np.array([contrast(d.names, a, 100, {a: 0.5, "00-9999999": 0.5}, season=2026)])
            self.assertEqual(float(d.x[:, d.names.index("qb/00-9999999")].sum()), 0.0)
            witness = allocation_witness(d, changed, l, evolving=variant == "evolving")
            self.assertLess(witness["example"]["max_prediction_change_ep"], 1e-12)
            self.assertGreater(witness["example"]["max_absolute_contrast_change_ep"], 0)
            sizes[variant] = witness["connected_components"]
        self.assertGreater(sizes["evolving"], sizes["persistent"])

    def test_simulation_does_not_use_observed_outcomes_and_mcse_is_by_replicate(self):
        rows, _ = prepare(
            self.data[2026][0], self.data[2026][1], season=2026, low_week=1, high_week=3
        )
        d, _ = design(rows, "evolving", scoring_season=2026)
        for scenario in plan()["simulation_scenarios"]:
            beta, y = simulate(d, plan(), scenario)
            changed = deepcopy(rows)
            for p in changed:
                p["offense_epa"] = 10000.0
            other, _ = design(changed, "evolving", scoring_season=2026)
            bb, yy = simulate(other, plan(), scenario)
            np.testing.assert_array_equal(beta, bb)
            np.testing.assert_array_equal(y, yy)
        t = np.zeros((3, 4))
        low = np.array([[-1.0, 1.0, -1.0, 1.0]] * 3)
        high = low + 2
        s = summary(t, t, low, high)
        self.assertEqual(s["coverage"], 0.5)
        self.assertAlmostEqual(s["monte_carlo_se"], np.std([1.0, 0.0, 1.0, 0.0], ddof=1) / 2)

    def test_defense_pair_retains_population_but_loses_lineup_information(self):
        rich, degraded, _ = defense_fixture()
        report = diagnose(rich, degraded, plan())
        a, b = report["rich_play_lineups"], report["degraded_team_games"]
        self.assertEqual(a["weighted_plays"], b["weighted_plays"])
        self.assertGreater(a["residualized_defender_rank"], b["residualized_defender_rank"])
        self.assertFalse(a["ranking_ready"])
        self.assertFalse(b["ranking_ready"])
        self.assertLess(a["null_witness"]["max_row_prediction_change_ep"], 1e-7)
        self.assertLess(b["null_witness"]["max_row_prediction_change_ep"], 1e-7)
        degraded["team_games"][0]["defense_epa_total"] += 1
        with self.assertRaises(ValueError):
            diagnose(rich, degraded, plan())

    def test_fresh_controls_keep_primary_prior_and_use_distinct_known_innovation(self):
        p = plan()
        diagnostic = json.loads(Path("config/multiseason-control-v1.json").read_text())
        diagnostic["replicates"] = 4
        rows, _ = prepare(
            self.data[2026][0], self.data[2026][1], season=2026, low_week=1, high_week=3
        )
        d, _ = design(rows, "evolving", scoring_season=2026)
        players = sorted({row["qb"] for row in rows})
        l = np.array(
            [
                contrast(d.names, player, 10, {v: 1 / len(players) for v in players}, season=2026)
                for player in players
            ]
        )
        before = deepcopy(p)
        result = controls(d, l, p, diagnostic)
        self.assertEqual(p, before)
        self.assertEqual(result["known_precision_ratios"]["qb"], 36.0)
        self.assertEqual(result["known_precision_ratios"]["innovation"], 100.0)
        self.assertFalse(result["ranking_ready"])
        self.assertEqual(set(result["results"]), set(diagnostic["controls"]))
        with self.assertRaisesRegex(ValueError, "fresh"):
            controls(d, l, p, {**diagnostic, "seed": p["simulation_seed"]})

    def test_replay_checks_structure_numeric_results_and_artifact_hashes(self):
        report = {**self.report, "input_reports": {}, "evidence_cutoff": self.cutoff.isoformat()}
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            rid, saved = save(store, report, self.models, self.results, code_revision="a" * 40)
            with patch(
                "nfl_value.multiseason_cli.run", return_value=(report, self.models, self.results)
            ):
                self.assertEqual(replay_experiment(None, None, None, store, rid), saved)
            bad = deepcopy(self.results)
            bad["estimates"]["evolving"][0]["benchmarks"]["first_unit"]["expected_points"] += 0.01
            with (
                patch("nfl_value.multiseason_cli.run", return_value=(report, self.models, bad)),
                self.assertRaisesRegex(ValueError, "numeric replay"),
            ):
                replay_experiment(None, None, None, store, rid)
            # Hash mismatch is rejected before any expensive recalculation.
            with (
                patch.object(store, "read", side_effect=ValueError("hash mismatch")),
                patch("nfl_value.multiseason_cli.run") as rerun,
                self.assertRaisesRegex(ValueError, "hash mismatch"),
            ):
                replay_experiment(None, None, None, store, rid)
            rerun.assert_not_called()


if __name__ == "__main__":
    unittest.main()
