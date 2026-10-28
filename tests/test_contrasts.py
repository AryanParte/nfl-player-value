"""Synthetic, offline contrasts: independent math, exposure and accounting."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nfl_value.baseline import ACTORS, actor_features, design, fit
from nfl_value.baseline_cli import assert_numerically_equal, save
from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.contrast_cli import replay_contrasts
from nfl_value.contrast_cohorts import exposure_diagnostic, make_cohorts
from nfl_value.contrast_math import (
    SCOPES,
    contrast_vector,
    fit_joint,
    summarize_contrast,
    validate_plan,
)
from nfl_value.contrasts import evaluate_fit, experiment
from nfl_value.ingestion import SnapshotStore, json_bytes
from test_baseline import play, plan as baseline_plan


def plan():
    return {
        "plan_version": 1,
        "windows": {"2025": [1, 2, 3]},
        "roles": list(SCOPES),
        "primary_actor_penalty": 1000.0,
        "actor_penalties": [10.0, 100.0, 1000.0],
        "context_penalty": 1.0,
        "team_penalty": 50.0,
        "qualification_multipliers": [0.75, 1.0, 1.25],
        "uncertainty": "conditional-gaussian-plugin-iid-v1",
        "exposure_policy": "full-observed-single-team-window-v1",
        "allow_retrospective": True,
    }


def fixture():
    """Two teams, four roles, known on-ball exposure; not real NFL observations."""
    rows, observations, player_games, assignments, games = [], [], [], [], []
    for week in (1, 2, 3):
        week_rows = [play(week=week, i=i) for i in range(1, 81)]
        for p in week_rows:
            side = p["play_id"] % 2
            if p["play_id"] % 8 in (0, 1):
                p["actors"] = {"dropback": None, "rusher": f"00-000000{5 + side}", "target": None}
                p["event_kind"] = "run"
            elif p["play_id"] % 8 in (2, 3):
                p["actors"]["target"] = f"00-000000{7 + side}"
        rows.extend(week_rows)
        kickoff = datetime.fromisoformat(week_rows[0]["scheduled_kickoff"])
        game_id = week_rows[0]["game_id"]
        for side, team in enumerate(("BUF", "NYJ")):
            games.append(
                CompletedTeamGame(
                    game_id, team, kickoff, kickoff + timedelta(hours=4), "REG", "exact"
                )
            )
            for role, start in (("QB", 1), ("WR", 3), ("RB", 5), ("TE", 7)):
                player = f"00-000000{start + side}"
                counts = {"dropback_or_rush_plays": 0, "carry_or_target_plays": 0, "targets": 0}
                for p in week_rows:
                    actors = actor_features(p)
                    counts["dropback_or_rush_plays"] += any(
                        f"{c}/{player}" in actors for c in ("dropback", "carry")
                    )
                    counts["carry_or_target_plays"] += any(
                        f"{c}/{player}" in actors for c in ("carry", "target")
                    )
                    counts["targets"] += f"target/{player}" in actors
                observations.append(
                    {
                        "player_id": player,
                        "game_type": "REG",
                        "week": week,
                        "team": team,
                        "source_position_role": role,
                        "issues": [],
                    }
                )
                player_games.append(
                    {
                        "player_id": player,
                        "game_id": game_id,
                        "team": team,
                        "source_position_role": role,
                        "issues": [],
                        "observed_offensive_participation": True,
                        "offensive_opportunities": {"observed": counts},
                    }
                )
                assignments.append(
                    {
                        "player_id": player,
                        "role": role,
                        "team_id": team,
                        "game_id": game_id,
                        "snapshot_at": (kickoff - timedelta(days=1)).isoformat(),
                    }
                )
    ledger = {
        "schema_version": 1,
        "opportunity_policy": "observed-offensive-pass-run-v1",
        "provenance": {"season": 2025},
        "ranking_ready": False,
        "plays": rows,
    }
    evidence = {"roster_observations": observations, "player_games": player_games}
    return ledger, evidence, {"assignments": assignments, "issues": []}, games


CUTOFF = datetime(2025, 12, 1, tzinfo=timezone.utc)


class ContrastMathTests(unittest.TestCase):
    def test_degenerate_residual_scale_is_not_falsely_precise_uncertainty(self):
        rows = fixture()[0]["plays"]
        for row in rows:
            row["offense_epa"] = 0.0
        with self.assertRaisesRegex(ValueError, "positive residual scale"):
            fit_joint(rows, {}, plan=plan(), actor_penalty=1000)

    def test_ridge_and_joint_covariance_against_independent_inverse(self):
        rows = fixture()[0]["plays"]
        model, covariance = fit_joint(rows, {}, plan=plan(), actor_penalty=10)
        x, names, _ = design(rows, "joint")
        d = np.array(
            [
                0
                if n == "context/intercept"
                else 10
                if n.split("/")[0] in ACTORS
                else 1
                if n.startswith(("context/", "observed_role/"))
                else 50
                for n in names
            ]
        )
        y = np.array([p["offense_epa"] for p in rows])
        inverse = np.linalg.inv(x.toarray().T @ x.toarray() + np.diag(d))
        mean = inverse @ x.T @ y
        residual = y - x @ mean
        np.testing.assert_allclose(model["coefficients"], mean, atol=1e-9)
        np.testing.assert_allclose(covariance, (residual @ residual / len(y)) * inverse, atol=1e-10)
        legacy = fit(rows, variant="joint", plan=baseline_plan(), actor_penalty=10)
        np.testing.assert_allclose(model["coefficients"], legacy["coefficients"], atol=1e-7)

    def test_shared_shift_self_membership_and_correlated_uncertainty(self):
        names = ["target/00-0000001", "target/00-0000002"]
        vector = contrast_vector(
            names,
            player="00-0000001",
            counts={"target": 10},
            weights={"00-0000001": 0.5, "00-0000002": 0.5},
        )
        np.testing.assert_equal(vector, [5, -5])
        mean, cov = np.array([-1.0, 2.0]), np.array([[4.0, 3.0], [3.0, 9.0]])
        actual = summarize_contrast(vector, mean, cov)
        self.assertEqual(actual["contrast_ep"], -15)
        self.assertAlmostEqual(actual["conditional_standard_error_ep"] ** 2, 175)
        self.assertEqual(actual, summarize_contrast(vector, mean + 17, cov))
        vector = contrast_vector(
            names, player="00-0000001", counts={"target": 10}, weights={"00-0000001": 1.0}
        )
        self.assertEqual(summarize_contrast(vector, mean, cov)["conditional_standard_error_ep"], 0)

    def test_unobserved_first_unit_parameter_retains_prior_uncertainty(self):
        model, covariance = fit_joint(
            fixture()[0]["plays"], {"QB": ["00-9999999"]}, plan=plan(), actor_penalty=10
        )
        i = model["features"].index("dropback/00-9999999")
        self.assertEqual(model["coefficients"][i], 0)
        self.assertIn("dropback/00-9999999", model["prior_only_actor_parameters"])
        self.assertGreater(covariance[i, i], 0)
        self.assertAlmostEqual(covariance[i, i], model["noise_variance_sse_over_n"] / 10)

    def test_invalid_math_and_plans_fail_closed(self):
        for key, value in (
            ("qualification_multipliers", [0.75, True, 1.25]),
            ("plan_version", True),
            ("primary_actor_penalty", 0),
            ("actor_penalties", [float("inf")]),
            ("windows", {"2025": [3, 2]}),
            ("allow_retrospective", 1),
        ):
            p = plan()
            p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan(p)
        with self.assertRaises(ValueError):
            contrast_vector(["target/x"], player="x", counts={"target": 1}, weights={"x": 0.5})
        with self.assertRaises(ValueError):
            contrast_vector([], player="x", counts={"target": 1}, weights={"x": 1.0})
        with self.assertRaises(ValueError):
            summarize_contrast(np.array([1.0]), np.array([1.0]), np.array([[-1.0]]))


class ContrastCohortTests(unittest.TestCase):
    def setUp(self):
        self.ledger, self.evidence, self.first, self.games = fixture()

    def cohorts(self):
        return make_cohorts(
            self.ledger["plays"], self.evidence, self.first, self.games, cutoff=CUTOFF
        )

    def exposure(self, cohorts, player="00-0000001", role="QB"):
        return exposure_diagnostic(
            player,
            role,
            cohorts,
            self.evidence,
            self.games,
            season=2025,
            week=3,
            cutoff=CUTOFF,
            multipliers=plan()["qualification_multipliers"],
        )

    def test_qualification_never_filters_cohort_and_three_games_is_required(self):
        c = self.cohorts()
        before = deepcopy(c["weights"])
        q = self.exposure(c)
        self.assertTrue(q["denominator_complete"])
        self.assertTrue(q["qualification_grid"]["1.0"]["participation_qualified"])
        self.assertTrue(
            all(not item["main_qualified"] for item in q["qualification_grid"].values())
        )
        self.assertEqual(c["weights"], before)
        self.games = self.games[:4]
        c = self.cohorts()
        q = self.exposure(c)
        self.assertTrue(
            all(not item["participation_qualified"] for item in q["qualification_grid"].values())
        )

    def test_gaps_trades_and_position_changes_do_not_create_denominators(self):
        for kind in ("gap", "trade", "position"):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == "gap":
                    self.evidence["player_games"][0]["observed_offensive_participation"] = False
                else:
                    self.evidence["roster_observations"][0][
                        "team" if kind == "trade" else "source_position_role"
                    ] = "KC" if kind == "trade" else "WR"
                q = self.exposure(self.cohorts())
                self.assertFalse(q["denominator_complete"])
                self.assertIsNone(q["qualification_grid"])

    def test_one_bad_first_unit_cell_blocks_role_without_changing_other_roles(self):
        self.first["assignments"].pop(0)  # missing BUF QB in week 1
        c = self.cohorts()
        self.assertNotIn("QB", c["weights"])
        self.assertTrue(c["audit"]["QB"]["blocked_reasons"])
        self.assertEqual(set(c["weights"]), {"RB", "WR", "TE"})

    def test_roster_mismatch_blocks_role_and_duplicate_join_fails(self):
        self.evidence["player_games"][0]["source_position_role"] = "WR"
        self.assertNotIn("QB", self.cohorts()["weights"])
        self.evidence["player_games"].append(self.evidence["player_games"][0])
        with self.assertRaisesRegex(ValueError, "duplicate roster"):
            self.cohorts()

    def test_zero_observation_starter_is_primary_only_and_not_precise_zero(self):
        for p in self.ledger["plays"]:
            if p["actors"]["target"] == "00-0000007":
                p["actors"]["target"] = None
        c = self.cohorts()
        self.assertEqual(c["weights"]["TE"]["first_unit"]["00-0000007"], 0.5)
        self.assertNotIn("00-0000007", c["weights"]["TE"]["equal_player"])
        self.assertEqual(c["weights"]["TE"]["opportunity_weighted"]["00-0000007"], 0)
        self.assertIn("00-0000007", c["audit"]["TE"]["first_unit_zero_opportunity_players"])

    def test_component_accounting_preserves_negative_and_unsupported_outcomes(self):
        p = self.ledger["plays"][0]
        p["issues"], p["offense_epa"] = ["ambiguous_actor"], -50.0
        self.evidence["player_games"][1]["issues"] = ["ambiguous_position"]
        c = self.cohorts()
        model, cov = fit_joint(
            self.ledger["plays"], c["candidates"], plan=plan(), actor_penalty=100
        )
        result = evaluate_fit(self.ledger["plays"], c, model, cov)
        for accounting in result["accounting"].values():
            self.assertLess(accounting["max_play_accounting_error"], 1e-9)
            self.assertLess(accounting["player_sum_error"], 1e-8)
            self.assertAlmostEqual(
                sum(accounting["totals_ep"].values()), accounting["observed_epa"]
            )
            self.assertLess(accounting["observed_epa"], 0)
        self.assertTrue(
            any(
                p["comparisons"] and p["comparisons"]["first_unit"]["contrast_ep"] < 0
                for p in result["players"]
            )
        )

    def test_self_target_components_and_scramble_count_unique_opportunities(self):
        p = self.ledger["plays"][0]
        p["actors"] = {"dropback": None, "rusher": "00-0000006", "target": "00-0000006"}
        p["event_kind"] = "pass"
        c = self.cohorts()
        counts = c["counts"][("RB", "00-0000006")]
        self.assertEqual(sum(counts.values()), len(c["opportunities"][("RB", "00-0000006")]) + 1)
        p["actors"] = {"dropback": "00-0000002", "rusher": "00-0000002", "target": None}
        p["event_kind"] = "scramble"
        c = self.cohorts()
        self.assertEqual(
            sum(c["counts"][("QB", "00-0000002")].values()),
            len(c["opportunities"][("QB", "00-0000002")]),
        )

    def test_missing_model_rows_does_not_equal_complete_source_coverage(self):
        self.ledger["plays"] = self.ledger["plays"][2:]
        q = self.exposure(self.cohorts())
        self.assertTrue(q["denominator_complete"])
        self.assertIn(
            "source_coverage_incomplete", q["qualification_grid"]["1.0"]["main_exclusion_reasons"]
        )

    def test_zero_targets_in_observed_carry_game_is_participation_not_absence(self):
        for row in self.ledger["plays"]:
            if row["week"] == 1 and row["actors"]["target"] == "00-0000003":
                row["actors"] = {"dropback": None, "rusher": "00-0000003", "target": None}
        for row in self.evidence["player_games"]:
            if row["player_id"] == "00-0000003" and "_01_" in row["game_id"]:
                row["offensive_opportunities"]["observed"]["targets"] = 0
        result = self.exposure(self.cohorts(), player="00-0000003", role="WR")
        self.assertTrue(result["denominator_complete"])
        self.assertEqual(result["qualification_grid"]["1.0"]["games_played"], 3)
        self.assertEqual(result["qualification_grid"]["1.0"]["opportunities"], 40)


class ContrastExperimentTests(unittest.TestCase):
    def run_fixture(self, fixture_data=None, experiment_plan=None):
        ledger, evidence, first, games = fixture_data or fixture()
        p = experiment_plan or plan()
        # Synthetic selections contain no global identity cross-check. Real CLI
        # tests below exercise prefix selection from archived chart rows.
        first_units = {str(w): first for w in p["windows"]["2025"]}
        return experiment(ledger, evidence, first_units, games, season=2025, cutoff=CUTOFF, plan=p)

    def test_future_changes_cannot_change_earlier_window(self):
        original = self.run_fixture()
        data = fixture()
        for row in data[0]["plays"]:
            if row["week"] == 3:
                row["offense_epa"] += 100
        for row in data[1]["roster_observations"]:
            if row["week"] == 3:
                row["source_position_role"] = "WR"
        data[2]["issues"].append(
            {"role": "QB", "game_id": "2025_03_BUF_NYJ", "reason": "late_problem"}
        )
        changed = self.run_fixture(data)
        self.assertEqual(original[0]["summary"]["1"], changed[0]["summary"]["1"])
        self.assertEqual(original[2]["1"], changed[2]["1"])
        self.assertNotEqual(original[2]["3"], changed[2]["3"])

    def test_incomplete_inventory_and_unavailable_window_fail(self):
        data = fixture()
        data[3].pop()
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.run_fixture(data)
        p = plan()
        p["windows"]["2025"] = [4]
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.run_fixture(experiment_plan=p)

    def test_replay_refits_numerically_and_detects_rehashed_corruption(self):
        # Only upstream orchestration is patched. The entire numerical experiment
        # is rerun, including coefficients, joint intervals and qualification.
        def rerun(*args, **kwargs):
            report, models, results = self.run_fixture(experiment_plan=kwargs["plan"])
            report.update(input_reports={"roster": "r", "offensive": "o"}, depth_charts="d")
            return report, models, results

        report, models, results = rerun(plan=plan())
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            rid, saved = save(store, report, models, results, code_revision="a" * 40)
            with patch("nfl_value.contrast_cli.run", side_effect=rerun):
                self.assertEqual(replay_contrasts(None, None, None, store, rid), saved)
                broken = deepcopy(models)
                next(iter(broken.values()))["coefficients"][0] += 0.01
                altered = deepcopy(saved)
                altered["objects"]["models"] = store.put(json_bytes(broken))
                bad_id = store.put(json_bytes(altered), manifest=True)
                with self.assertRaisesRegex(ValueError, "numeric replay differs"):
                    replay_contrasts(None, None, None, store, bad_id)
                # Valid hashes alone must not authorize a true admission flag.
                altered = deepcopy(saved)
                altered["ranking_ready"] = True
                bad_id = store.put(json_bytes(altered), manifest=True)
                with self.assertRaisesRegex(ValueError, "ranking_ready"):
                    replay_contrasts(None, None, None, store, bad_id)
        self.assertFalse(report["ranking_ready"])
        assert_numerically_equal(json.loads(json.dumps(results)), json.loads(json.dumps(results)))


if __name__ == "__main__":
    unittest.main()
