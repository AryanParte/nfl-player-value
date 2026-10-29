"""Deterministic synthetic transition evidence, not NFL injury labels."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
import unittest

from nfl_value.baseline import fit, predict, prepare_plays
from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.transitions import (
    PLAN,
    case,
    experiment,
    summarize,
    target_mix_distance,
    validate_plan,
)
from test_baseline import play, plan as baseline_plan


def fixture():
    ledgers, evidence, games = {}, {}, {}
    for label, season, weeks in (
        ("historical_test", 2025, (1, 2, 3, 4, 5)),
        ("transfer_test", 2026, (1, 2, 3)),
    ):
        rows, observations, inventory = [], [], []
        for week in weeks:
            batch = [play(season, week, i) for i in range(1, 41)]
            for p in batch:
                if p["offense_team"] == "BUF" and week in (2, 4, 5):
                    p["actors"]["dropback"] = "00-0000005"
                p["offense_epa"] += 0.3 if week == 2 else -0.4 * week
            rows.extend(batch)
            kickoff = datetime.fromisoformat(batch[0]["scheduled_kickoff"])
            for team, players in (("BUF", (1, 3, 5)), ("NYJ", (2, 4))):
                inventory.append(
                    CompletedTeamGame(
                        batch[0]["game_id"],
                        team,
                        kickoff,
                        kickoff + timedelta(hours=4),
                        "REG",
                        "exact",
                    )
                )
                for player in players:
                    identity = f"00-000000{player}"
                    observations.append(
                        {
                            "player_id": identity,
                            "game_id": batch[0]["game_id"],
                            "team": team,
                            "source_position_role": "WR" if player in (3, 4) else "QB",
                            "issues": [],
                            "observed_offensive_participation": any(
                                identity in p["actors"].values() for p in batch
                            ),
                        }
                    )
        ledgers[label] = {
            "schema_version": 1,
            "opportunity_policy": "observed-offensive-pass-run-v1",
            "provenance": {"season": season},
            "ranking_ready": False,
            "plays": rows,
        }
        evidence[label] = {"player_games": observations}
        games[label] = inventory
    training = [p for p in ledgers["historical_test"]["plays"] if p["week"] <= 2]
    p = baseline_plan()
    p["actor_penalties"] = [1000.0]
    models = {v: fit(training, variant=v, plan=p, actor_penalty=1000.0) for v in ("joint", "role")}
    baseline = {
        "selected_actor_penalty": 1000.0,
        "split_games": {
            label: sorted(
                {p["game_id"] for p in ledger["plays"] if label == "transfer_test" or p["week"] > 2}
            )
            for label, ledger in ledgers.items()
        },
    }
    data = [ledgers, evidence, games, baseline, models, {}]
    refresh_predictions(data)
    return data


def refresh_predictions(data):
    ledgers, _, _, baseline, models, predictions = data
    for label, ledger in ledgers.items():
        rows, _ = prepare_plays(
            {
                **ledger,
                "plays": [
                    p for p in ledger["plays"] if p["game_id"] in baseline["split_games"][label]
                ],
            },
            season=ledger["provenance"]["season"],
        )
        predictions[label] = {v: predict(m, rows)[0] for v, m in models.items()}


def run(data):
    return experiment(*data, plan=deepcopy(PLAN))


class TransitionTests(unittest.TestCase):
    def test_known_mix_distances_and_missing_is_not_zero(self):
        self.assertEqual(target_mix_distance({"a": 8, "b": 2}, {"a": 4, "b": 1}), 0)
        self.assertEqual(target_mix_distance({"a": 10}, {"a": 5, "b": 5}), 0.5)
        self.assertEqual(target_mix_distance({"a": 10}, {"b": 10}), 1)
        self.assertIsNone(target_mix_distance({}, {"b": 10}))

    def test_negative_outcomes_reconcile_and_known_identity_swap_is_not_team_epa(self):
        data = fixture()
        report, panels, results = run(data)
        self.assertFalse(report["ranking_ready"])
        first = results["historical_test"]["cases"][0]
        self.assertAlmostEqual(first["observed_change_epa_per_play"], -0.4)
        self.assertAlmostEqual(sum(first["joint_component_changes_epa_per_play"].values()), -0.4)
        before, after = [p for p in panels["historical_test"]["team_games"] if p["team"] == "BUF"][
            :2
        ]
        analytical = case(
            before,
            after,
            coefficients={"dropback/00-0000001": 0.5, "dropback/00-0000005": -0.25},
            training_counts=Counter({"dropback/00-0000001": 20, "dropback/00-0000005": 20}),
            roster={},
        )
        self.assertEqual(
            analytical["identity_swap_diagnostic"]["new_minus_prior_on_current_dropbacks_ep"], -15
        )
        self.assertEqual(analytical["previous_leader_current_dropbacks"], 0)
        self.assertFalse(analytical["previous_leader_current_roster"]["record_present"])
        self.assertIsNone(
            analytical["previous_leader_current_roster"]["observed_offensive_participation"]
        )
        self.assertFalse(analytical["injury_absence_verified"])
        self.assertFalse(analytical["causal_effect_estimated"])

    def test_outcomes_do_not_select_cases_or_reestimate_frozen_effects(self):
        data = fixture()
        original = run(data)
        fitted = deepcopy(data[4])
        for p in data[0]["transfer_test"]["plays"]:
            p["offense_epa"] = p["offense_epa"] * 10 - 20
        refresh_predictions(data)
        changed = run(data)
        for label in PLAN["evaluation_labels"]:
            keys = lambda result: [
                (
                    c["team"],
                    c["previous_game_id"],
                    c["current_game_id"],
                    c["groups"],
                    c["identity_swap_diagnostic"],
                )
                for c in result[2][label]["cases"]
            ]
            self.assertEqual(keys(original), keys(changed))
        self.assertEqual(data[4], fitted)
        self.assertNotEqual(
            original[0]["summary"]["transfer_test"], changed[0]["summary"]["transfer_test"]
        )

    def test_bad_middle_game_blocks_both_adjacent_pairs_without_skipping(self):
        for defect in ("context", "identity", "actor_issue", "aborted"):
            data = fixture()
            row = next(
                p
                for p in data[0]["historical_test"]["plays"]
                if p["week"] == 4 and p["offense_team"] == "BUF"
            )
            if defect == "context":
                row.update(context=None, context_outcome_complete=False)
            elif defect == "identity":
                data[1]["historical_test"]["player_games"] = [
                    r
                    for r in data[1]["historical_test"]["player_games"]
                    if not (r["game_id"] == row["game_id"] and r["player_id"] == "00-0000005")
                ]
            elif defect == "actor_issue":
                row["issues"] = ["ambiguous_actor"]
            else:
                row["event_kind"] = "aborted"
            refresh_predictions(data)
            with self.subTest(defect=defect):
                _, _, results = run(data)
                self.assertEqual(
                    [c["team"] for c in results["historical_test"]["cases"]], ["NYJ", "NYJ"]
                )
                self.assertEqual(len(results["historical_test"]["excluded_pairs"]), 2)

    def test_bye_preserves_adjacency_and_no_training_endpoint_is_used(self):
        data = fixture()
        omitted = "2025_04_BUF_NYJ"
        data[3]["split_games"]["historical_test"].remove(omitted)
        data[2]["historical_test"] = [g for g in data[2]["historical_test"] if g.game_id != omitted]
        refresh_predictions(data)
        cases = run(data)[2]["historical_test"]["cases"]
        self.assertEqual(len(cases), 2)
        self.assertTrue(
            all(
                c["previous_game_id"] == "2025_03_BUF_NYJ"
                and c["current_game_id"] == "2025_05_BUF_NYJ"
                for c in cases
            )
        )

    def test_split_qb_and_non_qb_trick_actors_cannot_be_leaders(self):
        for role in ("QB", "WR"):
            data = fixture()
            for p in data[0]["transfer_test"]["plays"]:
                if (
                    p["week"] == 2
                    and p["offense_team"] == "BUF"
                    and (role == "WR" or p["play_id"] % 4 == 0)
                ):
                    p["actors"]["dropback"] = "00-0000003"
            for r in data[1]["transfer_test"]["player_games"]:
                if r["player_id"] == "00-0000003":
                    r["source_position_role"] = role
            refresh_predictions(data)
            with self.subTest(role=role):
                panel = next(
                    p
                    for p in run(data)[1]["transfer_test"]["team_games"]
                    if p["team"] == "BUF" and p["week"] == 2
                )
                self.assertFalse(panel["case_eligible"])
                self.assertIn("no_unique_qb_leader", panel["blocked_reasons"])

    def test_untrained_identity_is_null_not_zero_and_empty_targets_are_unknown(self):
        data = fixture()
        for p in data[0]["transfer_test"]["plays"]:
            if p["week"] == 2 and p["offense_team"] == "BUF":
                p["actors"]["dropback"] = "00-0000009"
            if p["offense_team"] == "NYJ":
                p["actors"]["target"] = None
        data[1]["transfer_test"]["player_games"].append(
            {
                "player_id": "00-0000009",
                "game_id": "2026_02_BUF_NYJ",
                "team": "BUF",
                "source_position_role": "QB",
                "issues": [],
                "observed_offensive_participation": True,
            }
        )
        refresh_predictions(data)
        cases = run(data)[2]["transfer_test"]["cases"]
        for c in cases:
            if c["team"] == "BUF":
                self.assertIsNone(
                    c["identity_swap_diagnostic"]["new_minus_prior_on_current_dropbacks_ep"]
                )
                self.assertIn(
                    "dropback/00-0000009", c["identity_swap_diagnostic"]["untrained_features"]
                )
            else:
                self.assertIsNone(c["target_mix_total_variation"])
                self.assertIn("qb_retained_target_mix_unknown", c["groups"])

    def test_temporal_and_artifact_cohort_mismatches_fail(self):
        for defect in (
            "overlap",
            "future",
            "training_hash",
            "prediction_order",
            "inventory",
            "duplicate_roster",
        ):
            data = fixture()
            if defect == "overlap":
                data[3]["split_games"]["historical_test"].append("2025_02_BUF_NYJ")
            elif defect == "future":
                for p in data[0]["transfer_test"]["plays"]:
                    p["scheduled_kickoff"] = "2025-01-01T00:00:00+00:00"
            elif defect == "training_hash":
                data[4]["role"]["training_rows_sha256"] = "0" * 64
            elif defect == "prediction_order":
                data[5]["transfer_test"]["joint"].reverse()
            elif defect == "inventory":
                data[2]["transfer_test"].pop()
            else:
                data[1]["transfer_test"]["player_games"].append(
                    data[1]["transfer_test"]["player_games"][0]
                )
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                run(data)

    def test_component_corruption_is_not_hidden_in_summary(self):
        data = fixture()
        data[5]["transfer_test"]["joint"][0]["components"]["dropback"] += 1
        with self.assertRaisesRegex(ValueError, "component accounting"):
            run(data)

    def test_team_omission_range_is_sensitivity_and_empty_groups_are_missing(self):
        cases = run(fixture())[2]["transfer_test"]["cases"]
        for c in cases:
            c["models"]["role"]["absolute_change_error"] = 1
            c["models"]["joint"]["absolute_change_error"] = 0 if c["team"] == "BUF" else 3
        summary = summarize(cases)
        self.assertEqual(summary["joint_minus_role_mae"], 0.5)
        self.assertEqual(summary["leave_one_offense_team_out_range"], [-1, 2])
        self.assertFalse(summary["range_is_confidence_interval"])
        self.assertIsNone(summarize(cases[:1])["leave_one_offense_team_out_range"])
        self.assertIsNone(summarize([])["joint_minus_role_mae"])

    def test_plan_is_frozen_and_boolean_does_not_equal_version_one(self):
        for key, value in (
            ("plan_version", True),
            ("minimum_team_dropbacks", 1),
            ("actor_penalty", 10.0),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_plan({**PLAN, key: value})


if __name__ == "__main__":
    unittest.main()
