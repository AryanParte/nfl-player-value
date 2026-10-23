"""Synthetic fixtures exercise attribution failures as well as prediction recovery."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline import (actor_features, coappearance, design, experiment, features, fit, metrics,
                                paired_rmse_interval, predict, prepare_plays, validate_plan)
from nfl_value.baseline_cli import assert_numerically_equal, load_ledger, replay_experiment, save
from nfl_value.ingestion import SnapshotStore


def plan():
    return {"plan_version": 1, "historical_season": 2025, "transfer_season": 2026,
            "train_through_week": 1, "validation_through_week": 2, "test_through_week": 3,
            "context_penalty": 1.0, "team_penalty": 50.0, "actor_penalties": [1.0, 10.0, 100.0],
            "solver_tolerance": 1e-10, "solver_iteration_limit": 20000,
            "bootstrap_replicates": 100, "seed": 7}


def play(season=2025, week=1, i=1, *, matchup=0):
    teams = ("BUF", "NYJ") if matchup == 0 else ("KC", "DEN")
    return {"game_id": f"{season}_{week:02}_{teams[0]}_{teams[1]}", "play_id": i, "week": week,
            "scheduled_kickoff": (datetime(season, 9, 1, tzinfo=timezone.utc) + timedelta(weeks=week, hours=matchup)).isoformat(),
            "offense_team": teams[i % 2], "defense_team": teams[1 - i % 2], "event_kind": "pass",
            "context": {"down": i % 4 + 1, "ydstogo": i % 10 + 1, "yardline_100": i % 90 + 1,
                        "game_seconds_remaining": 3600 - i % 3000, "qtr": 1, "score_differential": i % 14 - 7},
            "offense_epa": (i % 5 - 2) * 0.5,
            "actors": {"dropback": f"00-000000{i % 2 + 1}", "rusher": None, "target": f"00-000000{i % 2 + 3}"},
            "context_outcome_complete": True, "issues": [], "target_observation": "recorded"}


def ledger(season):
    return {"schema_version": 1, "opportunity_policy": "observed-offensive-pass-run-v1",
            "provenance": {"season": season}, "ranking_ready": False,
            "plays": [play(season, week, i, matchup=m) for week in (1, 2, 3) for m in (0, 1) for i in range(1, 21)]}


class BaselineTests(unittest.TestCase):
    def test_penalties_and_split_plan_fail_closed(self):
        for key, value in (("context_penalty", 0), ("team_penalty", float("nan")), ("seed", True),
                           ("validation_through_week", 1), ("actor_penalties", [1, 1]), ("plan_version", True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                p = plan()
                p[key] = value
                validate_plan(p)

    def test_no_postplay_hardship_features(self):
        p = play()
        altered = deepcopy(p)
        altered.update(offense_epa=-100, event_kind="sack", target_observation="none_recorded")
        altered["pressure"] = 1
        altered["yards_gained"] = -50
        for variant in ("context", "team", "joint"):
            self.assertEqual(features(p, variant), features(altered, variant))

    def test_scramble_has_one_initiator_effect(self):
        p = play()
        p["actors"].update(rusher=p["actors"]["dropback"], target=None)
        p["event_kind"] = "scramble"
        self.assertEqual(actor_features(p), {"dropback/00-0000002": 1})
        p["actors"]["dropback"] = None
        self.assertEqual(actor_features(p), {"carry/00-0000002": 1})

    def test_actor_issues_preserve_negative_outcome_without_actor_assignment(self):
        data = ledger(2025)
        p = data["plays"][0]
        p["offense_epa"], p["issues"] = -7, ["aborted_actor_requires_review"]
        rows, audit = prepare_plays(data, season=2025)
        self.assertEqual(len(rows), 120)
        self.assertEqual(audit["actor_issue_plays_retained"], 1)
        self.assertEqual(actor_features(rows[0]), {})
        self.assertEqual(rows[0]["offense_epa"], -7)
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=10)
        pred, _ = predict(model, rows)
        self.assertEqual(sum(pred[0]["components"][k] for k in ("dropback", "carry", "target")), 0)
        self.assertAlmostEqual(sum(pred[0]["components"].values()) + pred[0]["residual"], -7)

    def test_missing_context_not_imputed_and_false_complete_claim_rejected(self):
        data = ledger(2025)
        data["plays"][0].update(context=None, context_outcome_complete=False)
        rows, audit = prepare_plays(data, season=2025)
        self.assertEqual(len(rows), 119)
        self.assertEqual(audit["excluded"], {"context_outcome_incomplete": 1})
        data["plays"][1]["offense_epa"] = float("nan")
        with self.assertRaises(ValueError):
            prepare_plays(data, season=2025)

    def test_duplicate_keys_identity_conflicts_and_season_mismatch_rejected(self):
        for mutation in (lambda d: d["plays"].append(d["plays"][0]),
                         lambda d: d["plays"][1]["actors"].update(dropback=d["plays"][0]["actors"]["dropback"]),
                         lambda d: d["provenance"].update(season=2024),
                         lambda d: d["plays"][0].update(week=2)):
            d = ledger(2025)
            mutation(d)
            with self.assertRaises(ValueError):
                prepare_plays(d, season=2025)

    def test_unseen_holdout_actor_does_not_enter_training_vocabulary(self):
        rows = ledger(2025)["plays"]
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=10)
        p = play(2026)
        p["actors"]["dropback"] = "00-9999999"
        out, audit = predict(model, [p])
        self.assertNotIn("dropback/00-9999999", model["features"])
        self.assertEqual(audit["unseen_feature_appearances"], {"dropback": 1})
        self.assertEqual(out[0]["components"]["dropback"], 0)

    def test_known_crossed_effects_recovered_in_synthetic_balanced_design(self):
        rows = []
        for i in range(800):
            p = play(i=i)
            q, r = (i // 100) % 2, (i // 200) % 2
            # Cross every context with every actor pair; do not alias QB to down.
            p["context"] = play(i=i % 100)["context"]
            p["actors"].update(dropback=f"00-000000{q + 1}", target=f"00-000000{r + 3}")
            p["offense_epa"] = 0.6 * (2*q - 1) + 0.3 * (2*r - 1)
            rows.append(p)
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=1)
        coef = dict(zip(model["features"], model["coefficients"]))
        self.assertAlmostEqual(coef["dropback/00-0000002"] - coef["dropback/00-0000001"], 1.2, delta=0.01)
        self.assertAlmostEqual(coef["target/00-0000004"] - coef["target/00-0000003"], 0.6, delta=0.01)
        self.assertLess(metrics(predict(model, rows)[0])["rmse"], 0.01)

    def test_perfect_coappearance_is_flagged_not_validated_by_ridge(self):
        rows = ledger(2025)["plays"]
        audit = coappearance(rows)
        self.assertEqual(len(audit["identical_actor_column_groups"]), 2)
        self.assertFalse(audit["identification_validated"])
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=10)
        coef = dict(zip(model["features"], model["coefficients"]))
        for group in audit["identical_actor_column_groups"]:
            self.assertAlmostEqual(coef[group[0]], coef[group[1]], places=8)

    def test_solver_iteration_limit_is_failure_not_accepted_fit(self):
        p = plan()
        p["solver_iteration_limit"] = 1
        with self.assertRaisesRegex(ValueError, "did not converge"):
            fit(ledger(2025)["plays"], variant="joint", plan=p, actor_penalty=10)

    def test_ridge_matches_dense_normal_equation_reference(self):
        rows = ledger(2025)["plays"]
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=10)
        x, names, _ = design(rows, "joint")
        penalties = [0 if n == "context/intercept" else 1 if n.startswith(("context/", "observed_role/")) else
                     50 if "team/" in n else 10 for n in names]
        expected = np.linalg.solve((x.T @ x).toarray() + np.diag(penalties), x.T @ np.array([p["offense_epa"] for p in rows]))
        np.testing.assert_allclose(model["coefficients"], expected, atol=1e-7, rtol=1e-7)

    def test_accounting_reconstructs_outcomes_and_retains_all_plays(self):
        rows = ledger(2025)["plays"]
        model = fit(rows, variant="joint", plan=plan(), actor_penalty=10)
        pred, audit = predict(model, rows)
        self.assertEqual(len(pred), len(rows))
        self.assertLess(audit["max_accounting_error"], 1e-9)
        for p, source in zip(pred, rows):
            self.assertAlmostEqual(sum(p["components"].values()) + p["residual"], source["offense_epa"], places=9)

    def test_missing_target_keeps_dropback_and_no_invented_target_effect(self):
        p = play()
        p["actors"]["target"] = None
        p["target_observation"] = "none_recorded"
        self.assertEqual(actor_features(p), {"dropback/00-0000002": 1})

    def test_role_ablation_does_not_know_actor_identity(self):
        original, renamed = play(), play()
        renamed["actors"].update(dropback="00-8888888", target="00-9999999")
        self.assertEqual(features(original, "role"), features(renamed, "role"))
        self.assertNotEqual(features(original, "joint"), features(renamed, "joint"))

    def test_exact_validation_tie_chooses_stronger_declared_penalty(self):
        h, t = ledger(2025), ledger(2026)
        for p in h["plays"] + t["plays"]:
            p["offense_epa"] = 0.0
        report, _, _ = experiment(h, t, plan())
        self.assertEqual(report["selected_actor_penalty"], 100)

    def test_test_outcomes_cannot_change_selection_or_fitted_state(self):
        historical, later = ledger(2025), ledger(2026)
        r1, m1, _ = experiment(historical, later, plan())
        for p in historical["plays"]:
            if p["week"] == 3:
                p["offense_epa"] += 100
        for p in later["plays"]:
            p["offense_epa"] -= 100
        r2, m2, _ = experiment(historical, later, plan())
        self.assertEqual(m1, m2)
        self.assertEqual(r1["validation"], r2["validation"])
        self.assertEqual(r1["selected_actor_penalty"], r2["selected_actor_penalty"])
        self.assertNotEqual(r1["evaluation"], r2["evaluation"])
        self.assertFalse(r1["ranking_ready"])
        self.assertFalse(r1["benchmark_contrasts_computed"])

    def test_reversed_rows_leave_fit_and_splits_unchanged(self):
        h, t = ledger(2025), ledger(2026)
        expected = experiment(h, t, plan())
        h["plays"].reverse()
        t["plays"].reverse()
        self.assertEqual(expected, experiment(h, t, plan()))

    def test_split_empty_or_overlapping_by_kickoff_rejected(self):
        h = ledger(2025)
        h["plays"] = [p for p in h["plays"] if p["week"] != 2]
        with self.assertRaisesRegex(ValueError, "empty"):
            experiment(h, ledger(2026), plan())
        h = ledger(2025)
        for p in h["plays"]:
            if p["week"] == 2:
                p["scheduled_kickoff"] = "2025-01-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "overlaps"):
            experiment(h, ledger(2026), plan())

    def test_cluster_bootstrap_paired_identical_models_zero_interval(self):
        rows = ledger(2025)["plays"]
        pred, _ = predict(fit(rows, variant="context", plan=plan(), actor_penalty=10), rows)
        out = paired_rmse_interval(pred, pred, seed=99, replicates=100)
        self.assertEqual(out["percentile_95_interval"], [0.0, 0.0])
        self.assertEqual(out["resampling_unit"], "game")
        with self.assertRaises(ValueError):
            paired_rmse_interval(pred, pred[::-1], seed=99, replicates=100)

    def test_bootstrap_negative_difference_means_candidate_improvement(self):
        rows = ledger(2025)["plays"]
        perfect = [{"game_id": p["game_id"], "play_id": p["play_id"], "offense_team": p["offense_team"],
                    "observed_epa": p["offense_epa"], "predicted_epa": p["offense_epa"]} for p in rows]
        poor = [{**p, "predicted_epa": p["observed_epa"] + 2} for p in perfect]
        result = paired_rmse_interval(perfect, poor, seed=1, replicates=100)
        self.assertEqual(result["percentile_95_interval"], [-2.0, -2.0])

    def test_saved_experiment_numeric_replay_and_corruption_detection(self):
        result = experiment(ledger(2025), ledger(2026), plan())
        report, models, preds = result
        report["input_reports"] = {"historical": "a" * 64, "transfer": "b" * 64}
        with tempfile.TemporaryDirectory() as folder:
            store = SnapshotStore(Path(folder))
            rid, saved = save(store, report, models, preds, code_revision="c" * 40)
            with patch("nfl_value.baseline_cli.run", return_value=result):
                self.assertEqual(saved, replay_experiment(store, store, store, rid))
                path = store._path(saved["objects"]["models"])
                path.write_text("corrupted")
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    replay_experiment(store, store, store, rid)

    def test_numeric_replay_rejects_changed_data_but_allows_roundoff(self):
        assert_numerically_equal({"a": [1.0]}, {"a": [1.0 + 1e-12]})
        for a, b in (([1.1], [1.0]), ([True], [1]), ({"a": 1}, {"b": 1}), ([1], [1, 2]), ([float("nan")], [0.0])):
            with self.assertRaises(ValueError):
                assert_numerically_equal(a, b)

    def test_incomplete_coverage_blocks_experiment_entry(self):
        with patch("nfl_value.baseline_cli.replay_offensive_inputs", return_value={"game_coverage": {"coverage_complete": False}}):
            with self.assertRaisesRegex(ValueError, "coverage"):
                load_ledger(None, None, "a" * 64)


if __name__ == "__main__":
    unittest.main()
