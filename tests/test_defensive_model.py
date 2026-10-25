"""Synthetic defense rotations expose what game aggregates cannot identify."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.defensive_model import (aggregate_plays, coefficient_agreement, design, experiment, features, fit,
    identification, metrics, paired_rmse_interval, predict, prepare_pair, selection_diagnostics, validate_plan, validate_rows)
from nfl_value.defensive_model_cli import replay_experiment, run, save
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256


RICH, DEGRADED = "rich_play_lineups", "degraded_team_games"


def plan():
    return {"plan_version": 1, "season": 2025, "train_through_week": 1, "validation_through_week": 2,
            "test_through_week": 3, "context_penalty": 1.0, "team_penalty": 50.0,
            "defender_penalties": [1.0, 10.0, 100.0], "solver_tolerance": 1e-10, "solver_iteration_limit": 20000,
            "bootstrap_replicates": 100, "seed": 7, "rank_relative_tolerance": 1e-10, "selection_smd_threshold": 0.1}


def fixture():
    plays = []
    all_teams = ("BUF", "NYJ", "KC", "DEN")
    for week in (1, 2, 3):
        for m in (0, 1):
            teams = all_teams[m*2:m*2+2]
            for i in range(24):
                offense, defense = teams[i % 2], teams[1 - i % 2]
                base = all_teams.index(defense) * 100
                rotation = (i // 2) % 2
                plays.append({"game_id": f"2025_{week:02}_{teams[0]}_{teams[1]}", "week": week, "play_id": i,
                    "scheduled_kickoff": (datetime(2025, 9, 1, tzinfo=timezone.utc) + timedelta(weeks=week, hours=m)).isoformat(),
                    "offense_team": offense, "defense_team": defense, "defense_epa": 0.8 * (2*rotation - 1) + 0.05*m,
                    "context": {"down": 1.0, "ydstogo": 10.0, "yardline_100": 50.0,
                                "game_seconds_remaining": 3000.0, "qtr": 1.0, "score_differential": 0.0},
                    "defense_players": [f"00-{base+j:07}" for j in range(1, 11)] + [f"00-{base+11+rotation:07}"],
                    "offense_players": [f"00-{1000+all_teams.index(offense)*100+j:07}" for j in range(11)]})
    return from_plays(plays)


def from_plays(plays):
    plays = sorted(plays, key=lambda p: (p["game_id"], p["play_id"]))
    provenance = {"source_receipts": {"pbp": "a"*64, "schedules": "b"*64, "participation": "c"*64},
                  "derived_participation_license": "CC-BY-SA-4.0", "attribution": "Synthetic fixture, not NFL data"}
    common = {"schema_version": 1, "season": 2025, "cohort_sha256": sha256(json_bytes([[p["game_id"], p["play_id"]] for p in plays])),
              "cohort_plays": len(plays), "game_ids": sorted({p["game_id"] for p in plays}), "ranking_ready": False,
              "provenance": provenance}
    rich = {**common, "view": RICH, "plays": plays}
    degraded = {**common, "view": DEGRADED, "team_games": aggregate_plays(plays)}
    ledger = {"schema_version": 1, "opportunity_policy": "observed-offensive-pass-run-v1",
              "provenance": {"season": 2025, **provenance},
              "plays": [{k: v for k, v in p.items() if k not in {"defense_epa", "defense_players", "offense_players"}} |
                        {"offense_epa": -p["defense_epa"], "context_outcome_complete": True} for p in plays]}
    return rich, degraded, ledger


def fitted(rows, view=RICH, variant="defender", penalty=1):
    return fit(rows, view=view, variant=variant, plan=plan(), defender_penalty=penalty)


class DefensiveModelTests(unittest.TestCase):
    def test_plan_fails_closed(self):
        for key, value in (("plan_version", True), ("context_penalty", 0), ("team_penalty", float("nan")),
                           ("seed", True), ("validation_through_week", 1), ("defender_penalties", [1, 1]),
                           ("rank_relative_tolerance", 1), ("bootstrap_replicates", 10001)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                p = plan()
                p[key] = value
                validate_plan(p)

    def test_pair_rejects_wrong_cohort_or_outcome_and_aggregate(self):
        r, d, _ = fixture()
        self.assertEqual(len(prepare_pair(r, d, 2025)[0]), 144)
        for change in (lambda x: x.update(cohort_sha256="f"*64),
                       lambda x: x["team_games"][0].update(defense_epa_mean=7),
                       lambda x: x["team_games"].pop(),
                       lambda x: x["team_games"][0]["context_mean"].update(ydstogo=11)):
            x = deepcopy(d)
            change(x)
            with self.assertRaises(ValueError):
                prepare_pair(r, x, 2025)

    def test_degraded_fit_rejects_rich_information_and_bad_weights(self):
        rows = fixture()[1]["team_games"]
        for change in (lambda p: p.update(defense_players=["00-0000001"]),
                       lambda p: p.update(play_id=1), lambda p: p.update(opportunities=0),
                       lambda p: p["defender_workloads"][0].update(fraction=0.001),
                       lambda p: p["defender_workloads"].append(p["defender_workloads"][0]),
                       lambda p: p["defender_workloads"].pop(),
                       lambda p: p["context_mean"].update(down=0)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                x = deepcopy(rows)
                change(x[0])
                fitted(x, DEGRADED)

    def test_invalid_rich_identity_and_context_fail_closed(self):
        for change in (lambda r: r.append(r[0]), lambda r: r[0]["defense_players"].pop(),
                       lambda r: r[0]["defense_players"].__setitem__(0, r[0]["offense_players"][0]),
                       lambda r: r[0]["context"].update(down=True), lambda r: r[0].update(defense_epa=float("nan")),
                       lambda r: r[0].update(week=4)):
            rows = fixture()[0]["plays"]
            change(rows)
            with self.assertRaises(ValueError):
                validate_rows(rows, RICH)

    def test_linear_features_commute_with_aggregation(self):
        rows = fixture()[0]["plays"]
        for i, p in enumerate(rows):
            p["context"].update(down=i % 4 + 1, ydstogo=i % 9 + 1, yardline_100=i % 95,
                                score_differential=i % 11 - 5, game_seconds_remaining=3600 - i)
        aggregate = aggregate_plays(rows)
        for game in aggregate:
            group = [p for p in rows if (p["game_id"], p["defense_team"]) == (game["game_id"], game["defense_team"])]
            f = features(game, DEGRADED, "defender")
            rich = [features(p, RICH, "defender") for p in group]
            for k in f:
                self.assertAlmostEqual(f[k], sum(d.get(k, 0) for d in rich) / len(group), places=12)

    def test_weighted_ridge_matches_dense_reference_with_unequal_game_sizes(self):
        rows = fixture()[0]["plays"]
        rows = [p for p in rows if p["week"] != 1 or p["play_id"] < 8]
        aggregate = aggregate_plays(rows)
        model = fitted(aggregate, DEGRADED)
        x, names, _ = design(aggregate, DEGRADED, "defender")
        penalties = [0 if n == "context/intercept" else 50 if "team/" in n else 1 for n in names]
        w = np.array([p["opportunities"] for p in aggregate])
        y = np.array([p["defense_epa_mean"] for p in aggregate])
        expected = np.linalg.solve((x.T @ x.multiply(w[:, None])).toarray() + np.diag(penalties), x.T @ (y*w))
        np.testing.assert_allclose(model["coefficients"], expected, atol=1e-7, rtol=1e-7)

    def test_rotation_information_can_disappear_completely(self):
        r, d, _ = fixture()
        rich = fitted(r["plays"])
        degraded = fitted(d["team_games"], DEGRADED)
        def contrast(model):
            coef = dict(zip(model["features"], model["coefficients"]))
            return coef["defender/00-0000012"] - coef["defender/00-0000011"]
        self.assertAlmostEqual(contrast(rich), 1.6, delta=0.1)
        self.assertAlmostEqual(contrast(degraded), 0, places=8)
        for p in r["plays"]:
            p["defense_players"][-1] = p["defense_players"][-1][:-1] + ("2" if p["defense_players"][-1].endswith("1") else "1")
        permuted = aggregate_plays(r["plays"])
        self.assertEqual(permuted, d["team_games"])
        self.assertEqual(degraded, fitted(permuted, DEGRADED))
        self.assertAlmostEqual(contrast(fitted(r["plays"])), -contrast(rich), places=7)

    def test_rank_and_identical_columns_expose_coappearance(self):
        r, d, _ = fixture()
        rich = identification(r["plays"], RICH, relative_tolerance=1e-10)
        degraded = identification(d["team_games"], DEGRADED, relative_tolerance=1e-10)
        self.assertEqual(rich["residualized_defender_rank"], 4)
        self.assertEqual(degraded["residualized_defender_rank"], 0)
        self.assertGreater(degraded["unidentified_linear_dimensions"], rich["unidentified_linear_dimensions"])
        self.assertEqual(degraded["defender_team_cosine_max"], 1)
        self.assertTrue(degraded["identical_defender_column_groups"])
        self.assertFalse(degraded["identification_validated"])

    def test_components_conserve_signed_outcome_without_repeated_full_credit(self):
        for rows, view in ((fixture()[0]["plays"], RICH), (fixture()[1]["team_games"], DEGRADED)):
            pred, audit = predict(fitted(rows, view), rows)
            self.assertLess(audit["max_row_accounting_error"], 1e-9)
            self.assertEqual(len(pred), 12)
            self.assertEqual(sum(p["opportunities"] for p in pred), 144)
            for p in pred:
                self.assertAlmostEqual(sum(p["components"].values()) + p["residual_mean"], p["observed_epa_mean"], places=9)

    def test_no_opponent_player_or_postplay_features(self):
        p = fixture()[0]["plays"][0]
        before = features(p, RICH, "defender")
        p.update(defense_epa=100, pressure=1, sacks=7, offense_players=["00-9999999"])
        self.assertEqual(before, features(p, RICH, "defender"))

    def test_unseen_defender_is_prior_prediction_and_reported(self):
        r = fixture()[0]["plays"]
        model = fitted(r)
        for p in r:
            if p["defense_team"] == "BUF":
                p["defense_players"][0] = "00-9999999"
        pred, audit = predict(model, r)
        self.assertNotIn("defender/00-9999999", model["features"])
        self.assertEqual(audit["unseen_feature_rows"]["defender"], 36)
        self.assertTrue(pred)

    def test_solver_failure_not_accepted(self):
        p = plan()
        p["solver_iteration_limit"] = 1
        with self.assertRaisesRegex(ValueError, "did not converge"):
            fit(fixture()[0]["plays"], view=RICH, variant="defender", plan=p, defender_penalty=1)

    def test_cluster_interval_checks_pairing_and_identical_predictions(self):
        pred = predict(fitted(fixture()[0]["plays"]), fixture()[0]["plays"])[0]
        result = paired_rmse_interval(pred, pred, seed=7, replicates=100)
        self.assertEqual(result["percentile_95_interval"], [0, 0])
        self.assertFalse(result["equivalence_test"])
        altered = deepcopy(pred)
        altered[0]["opportunities"] += 1
        with self.assertRaises(ValueError):
            paired_rmse_interval(pred, altered, seed=7, replicates=100)
        perfect = deepcopy(pred)
        for p in perfect:
            p["predicted_epa_mean"] = p["observed_epa_mean"]
        bad = deepcopy(perfect)
        for p in bad:
            p["predicted_epa_mean"] += 1
        self.assertEqual(paired_rmse_interval(bad, perfect, seed=7, replicates=100)["percentile_95_interval"], [1, 1])

    def test_test_outcomes_cannot_change_fits_or_penalty_selection(self):
        r, d, l = fixture()
        report, models, predictions = experiment(r, d, l, plan())
        for p in r["plays"]:
            if p["week"] == 3:
                p["defense_epa"] += 10
        r2, d2, l2 = from_plays(r["plays"])
        report2, models2, _ = experiment(r2, d2, l2, plan())
        self.assertEqual(models, models2)
        self.assertEqual(report["selected_defender_penalties"], report2["selected_defender_penalties"])
        self.assertNotEqual(report["evaluation"], report2["evaluation"])
        for k in ("ranking_ready", "individual_attribution_validated", "benchmark_contrasts_computed", "qualification_computed", "live_source_equivalence_validated"):
            self.assertFalse(report[k])
        self.assertFalse(coefficient_agreement(models["rich"]["defender"], models["degraded"]["defender"])["reference_is_ground_truth"])
        self.assertEqual(metrics(predictions["rich"]["defender"])["games"], 2)

    def test_chronological_overlap_and_empty_split_rejected(self):
        r, _, _ = fixture()
        for p in r["plays"]:
            if p["week"] == 2:
                p["scheduled_kickoff"] = "2025-08-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "overlaps"):
            experiment(*from_plays(r["plays"]), plan())
        with self.assertRaisesRegex(ValueError, "empty"):
            experiment(*from_plays([p for p in r["plays"] if p["week"] != 2]), plan())

    def test_selection_reports_removed_games_and_signed_epa(self):
        r, _, ledger = fixture()
        kept = [p for p in r["plays"] if p["week"] != 1]
        r2, _, _ = from_plays(kept)
        for p in ledger["plays"]:
            if p["week"] == 1:
                p["offense_epa"] += 2
        result = selection_diagnostics(r2, ledger, threshold=0.1)
        self.assertEqual(result["retained"]["plays"], 96)
        self.assertEqual(result["excluded"]["games"], 2)
        self.assertTrue(result["contrasts"]["defense_epa"]["flagged"])
        self.assertAlmostEqual(result["contrasts"]["defense_epa"]["excluded_mean"], -1.975)
        self.assertFalse(result["selection_is_ignorable"])

    def test_selection_rejects_mismatched_sources_sign_or_partial_games(self):
        for change in (lambda l: l["provenance"]["source_receipts"].update(pbp="d"*64),
                       lambda l: l["plays"][0].update(offense_epa=5), lambda l: l["plays"].pop(),
                       lambda l: l["plays"][0].update(context_outcome_complete=False),
                       lambda l: l["plays"][0].update(context_outcome_complete="true"),
                       lambda l: l["plays"].append({**l["plays"][0], "play_id": 999})):
            r, _, ledger = fixture()
            ledger = deepcopy(ledger)  # fixture shares provenance intentionally; isolate the corruption.
            change(ledger)
            with self.assertRaises(ValueError):
                selection_diagnostics(r, ledger, threshold=0.1)

    def test_cli_revalidates_sources_before_model_and_rejects_incomplete_coverage(self):
        report = {"report_version": 2, "game_coverage": {"coverage_complete": False}}
        with patch("nfl_value.defensive_model_cli.replay_defense_inputs", return_value=report) as defensive, \
             patch("nfl_value.defensive_model_cli.replay_offensive_inputs", return_value=report) as candidate:
            with self.assertRaisesRegex(ValueError, "reconciled"):
                run(None, None, None, defensive_report="d", candidate_report="c", plan=plan())
            defensive.assert_called_once()
            candidate.assert_called_once()

    def test_immutable_outputs_replay_and_retain_independent_provenance(self):
        r, d, l = fixture()
        report, models, predictions = experiment(r, d, l, plan())
        report["input_reports"] = {"defensive": "d", "candidate": "c"}
        report["source_provenance"] = {"derivative_license": "CC-BY-SA-4.0", "attribution": "Synthetic fixture"}
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            report_id, saved = save(store, report, models, predictions, code_revision="a"*40)
            for key in ("models", "predictions"):
                artifact = json.loads(store.read(saved["objects"][key]))
                self.assertEqual(artifact["source_provenance"], report["source_provenance"])
                self.assertEqual(artifact["plan"], plan())
                self.assertFalse(artifact["ranking_ready"])
            with patch("nfl_value.defensive_model_cli.run", return_value=(report, models, predictions)):
                self.assertEqual(replay_experiment(None, None, None, store, report_id), saved)
                altered = deepcopy(saved)
                altered["objects"]["predictions"] = saved["objects"]["models"]
                bad_id = store.put(json_bytes(altered), manifest=True)
                with self.assertRaisesRegex(ValueError, "structure"):
                    replay_experiment(None, None, None, store, bad_id)
                altered["environment"]["numpy"] = "unsupported"
                bad_id = store.put(json_bytes(altered), manifest=True)
                with self.assertRaisesRegex(ValueError, "versions"):
                    replay_experiment(None, None, None, store, bad_id)


if __name__ == "__main__":
    unittest.main()
