"""Offline QB recovery contracts: chronology, identities, cumulative ledgers, replay."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline_cli import save
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.qb_math import contrast, design
from nfl_value.qb_recovery import experiment, held_out, prepare, validate_plan
from nfl_value.qb_recovery_cli import replay_experiment
from nfl_value.qb_simulation import simulate, summarize
from test_contrasts import fixture
from test_qb_math import plan, rows


def sample(season):
    ledger, evidence, first, games = fixture()
    ledger = json.loads(json.dumps(ledger).replace("2025", str(season)))
    evidence = json.loads(json.dumps(evidence).replace("2025", str(season)))
    first = json.loads(json.dumps(first).replace("2025", str(season)))
    first["assignments"] = [a for a in first["assignments"] if a["role"] == "QB"]
    games = [
        replace(
            g,
            game_id=g.game_id.replace("2025", str(season)),
            kickoff=g.kickoff.replace(year=season),
            completed_at=g.completed_at.replace(year=season),
        )
        for g in games
    ]

    def other(value):
        text = json.dumps(value).replace("BUF", "KC").replace("NYJ", "DEN")
        for i in range(1, 9):
            text = text.replace(f"00-000000{i}", f"00-000010{i}")
        return json.loads(text)

    ledger["plays"] += other(ledger["plays"])
    for key in evidence:
        evidence[key] += other(evidence[key])
    first["assignments"] += other(first["assignments"])
    games += [
        replace(
            g,
            game_id=g.game_id.replace("BUF", "KC").replace("NYJ", "DEN"),
            team_id={"BUF": "KC", "NYJ": "DEN"}[g.team_id],
        )
        for g in games[:]
    ]
    rng = np.random.default_rng(season)
    for p in ledger["plays"]:
        p["offense_epa"] += float(rng.normal())
        p["context"].update(
            game_seconds_remaining=int(rng.integers(0, 3601)),
            score_differential=int(rng.integers(-28, 29)),
        )
    return ledger, evidence, first, games


def small_plan():
    p = plan()
    p.update(
        train_through_week=1,
        validation_through_week=2,
        test_through_week=3,
        transfer_train_through_week=1,
        simulation_replicates=2,
        bootstrap_replicates=16,
        optimizer_starts=[10.0],
    )
    return p


class QBRecoveryTests(unittest.TestCase):
    def test_invalid_plan_and_overlapping_training_fail(self):
        validate_plan(plan())
        for key, value in [
            ("simulation_replicates", True),
            ("simulation_noise_sd", float("nan")),
            ("historical_season", 2026),
            ("primary", "qb_proxy"),
            ("optimizer_starts", [0]),
            ("allow_retrospective", False),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**plan(), key: value})
        with self.assertRaisesRegex(ValueError, "chronology overlaps"):
            held_out(rows(), rows(), plan(), seed=1, progress=lambda _: None)

    def test_identity_exclusions_and_future_records_cannot_change_prefix(self):
        ledger, evidence, _, _ = sample(2024)
        before, _ = prepare(ledger, evidence, season=2024, low_week=1, high_week=1)
        future = deepcopy(evidence["player_games"][-1])
        evidence["player_games"].append(future)
        ledger["plays"][-1]["actors"]["dropback"] = "bad future identity"
        after, _ = prepare(ledger, evidence, season=2024, low_week=1, high_week=1)
        self.assertEqual(before, after)
        ledger, evidence, _, _ = sample(2024)
        selected = [p for p in ledger["plays"] if p["event_kind"] == "pass" and p["week"] == 1]
        selected[0]["actors"]["dropback"] = None
        selected[1]["issues"] = ["ambiguous_actor"]
        selected[2]["actors"]["dropback"] = selected[2]["actors"]["target"]
        result, audit = prepare(ledger, evidence, season=2024, low_week=1, high_week=1)
        self.assertEqual(audit["dropback_exclusions"]["ambiguous_or_missing_dropback_identity"], 2)
        self.assertEqual(audit["dropback_exclusions"]["non_qb_dropback"], 1)
        self.assertTrue(all(p["actors"]["target"] is None for p in result))
        self.assertTrue(any(p["offense_epa"] < 0 for p in result))
        for record in evidence["player_games"]:
            if record["source_position_role"] == "QB" and record["team"] == "BUF":
                record["issues"] = ["unresolved"]
        with self.assertRaisesRegex(ValueError, "missing from completed team games"):
            prepare(ledger, evidence, season=2024, low_week=1, high_week=1)

    def test_simulations_use_design_only_and_mcse_uses_replicates(self):
        d = design(rows(), "joint")
        p = small_plan()
        for scenario in p["scenarios"]:
            truth, y = simulate(d, p, scenario=scenario, replicate=0)
            again = simulate(d, p, scenario=scenario, replicate=0)
            np.testing.assert_array_equal(truth, again[0])
            np.testing.assert_array_equal(y, again[1])
            self.assertFalse(np.array_equal(y, simulate(d, p, scenario=scenario, replicate=1)[1]))
        s = summarize(
            [np.zeros(100), np.ones(100) * 3], [np.ones(100) * 2] * 2, replicates=2, failures=[]
        )
        self.assertEqual(s["coverage"], 0.5)
        self.assertEqual(s["monte_carlo_se"], 0.5)
        self.assertFalse(s["passes_admission"])
        self.assertFalse(
            summarize([], [], replicates=2, failures=[{"replicate": 0}])["valid_for_decision"]
        )

    def test_end_to_end_research_ledger_and_immutable_numerical_replay(self):
        historical, he, _, _ = sample(2024)
        current, ce, first, games = sample(2026)
        with patch(
            "urllib.request.OpenerDirector.open", side_effect=AssertionError("network forbidden")
        ):
            report, models, results = experiment(
                historical,
                current,
                he,
                ce,
                first,
                games,
                cutoff=datetime(2026, 12, 1, tzinfo=timezone.utc),
                plan=small_plan(),
            )
        self.assertFalse(report["ranking_ready"])
        self.assertEqual(report["season"]["games"], 6)
        self.assertEqual(report["season"]["identification"]["nonestimable_contrasts"], 4)
        for player in results["player_contrasts"]:
            self.assertEqual(player["games"], 3)
            self.assertEqual(
                set(player["benchmarks"]), {"first_unit", "equal_player", "opportunity_weighted"}
            )
            self.assertAlmostEqual(
                sum(g["expected_points"] for g in player["game_ledger"]),
                player["benchmarks"]["first_unit"]["expected_points"],
            )
            self.assertFalse(player["ranking_ready"])
        for p in results["evaluation"]["season"]:
            self.assertAlmostEqual(
                p["observed_epa"],
                p["qb_above_first_unit"]
                + p["benchmark_component"]
                + sum(v for k, v in p["components"].items() if k != "qb")
                + p["residual"],
            )
        self.assertTrue(
            report["season"]["allocation_witness"]["example"]["max_absolute_contrast_change_ep"] > 0
        )
        self.assertEqual(
            report["season"]["allocation_witness"]["example"]["max_prediction_change_ep"], 0
        )
        report.update(input_reports={}, evidence_cutoff="2026-12-01T00:00:00+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid, saved = save(store, report, models, results, code_revision="a" * 40)
            # Mathematical computation ran above; mock only source reconstruction here.
            with patch("nfl_value.qb_recovery_cli.run", return_value=(report, models, results)):
                self.assertEqual(replay_experiment(None, None, store, rid), saved)
                changed = deepcopy(saved)
                changed["season"]["plays"] += 1
                bad = store.put(json_bytes(changed), manifest=True)
                with self.assertRaises(ValueError):
                    replay_experiment(None, None, store, bad)
                store._path(saved["objects"]["models"]).write_bytes(b"corrupt")
                with self.assertRaises(ValueError):
                    replay_experiment(None, None, store, rid)

    def test_cold_benchmark_member_stays_in_contrast_without_qualification(self):
        d = design(rows(), "joint", extra_qbs=["00-9999999"])
        l = contrast(d.names, "00-0000001", 10, {"00-9999999": 0.5, "00-0000001": 0.5})
        self.assertEqual(l[d.names.index("qb/00-9999999")], -5)
        self.assertEqual(l[d.names.index("qb/00-0000001")], 5)


if __name__ == "__main__":
    unittest.main()
