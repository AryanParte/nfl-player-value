"""Synthetic contract tests; no NFL performance is claimed by these fixtures."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from nfl_value.benchmarks import (
    CompletedTeamGame,
    FirstUnitAssignment,
    PlayerPrediction,
    calculate_benchmarks,
)


START = datetime(2026, 9, 13, 17, tzinfo=timezone.utc)
CUTOFF = START + timedelta(days=30)
A, B, BACKUP = "00-0000001", "00-0000002", "00-0000003"


def game(week, team="ATL", opponent="TB"):
    kickoff = START + timedelta(days=7 * (week - 1))
    return CompletedTeamGame(f"2026_{week:02}_{team}_{opponent}", team, kickoff, kickoff + timedelta(hours=3), "REG")


def assignment(player_id, team_game, role="QB"):
    return FirstUnitAssignment(player_id, role, team_game.team_id, team_game.game_id, team_game.kickoff - timedelta(hours=1))


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        # ATL has two completed games, CAR has one: teams retain equal weight.
        self.games = (game(1), game(2), game(1, "CAR", "NO"))
        self.predictions = (
            PlayerPrediction(A, "QB", 0.4, 100),
            PlayerPrediction(B, "QB", 0.0, 100),
            PlayerPrediction(BACKUP, "QB", -2.0, 1),
        )
        self.assignments = (
            assignment(A, self.games[0]),
            assignment(A, self.games[1]),
            assignment(B, self.games[2]),
        )

    def calculate(self, **overrides):
        arguments = dict(
            role="QB", predictions=self.predictions, assignments=self.assignments,
            team_games=self.games, expected_team_ids=("ATL", "CAR"), cutoff=CUTOFF,
        )
        arguments.update(overrides)
        return calculate_benchmarks(**arguments)

    def test_team_weight_and_tiny_backup_sensitivities(self):
        result = self.calculate()
        self.assertEqual(dict(result.first_unit.player_weights), {A: 0.5, B: 0.5})
        self.assertAlmostEqual(result.first_unit.expected_points, 0.2)
        self.assertAlmostEqual(result.equal_player.expected_points, -1.6 / 3)
        self.assertAlmostEqual(result.opportunity_weighted.expected_points, 38 / 201)
        # The backup is not discarded by an MVP participation threshold.
        self.assertIn(BACKUP, dict(result.equal_player.player_weights))
        for estimate in (result.first_unit, result.equal_player, result.opportunity_weighted):
            self.assertAlmostEqual(sum(dict(estimate.player_weights).values()), 1)

    def test_first_unit_membership_changes_receive_game_weights(self):
        changed = self.assignments[:1] + (assignment(BACKUP, self.games[1]),) + self.assignments[2:]
        result = self.calculate(assignments=changed)
        self.assertEqual(dict(result.first_unit.player_weights), {A: 0.25, B: 0.5, BACKUP: 0.25})

    def test_multiple_first_unit_players_split_role_cell_and_zero_usage_is_valid(self):
        predictions = (
            PlayerPrediction(A, "WR", 4, 20),
            PlayerPrediction(B, "WR", 16, 0),
        )
        games = (game(1),)
        result = self.calculate(
            role="WR", predictions=predictions, team_games=games, expected_team_ids=("ATL",),
            assignments=(assignment(A, games[0], "WR"), assignment(B, games[0], "WR")),
        )
        # Average model predictions (4 + 16)/2, not squared mean features (2+4)/2.
        self.assertEqual(result.first_unit.expected_points, 10)
        self.assertEqual(result.equal_player.expected_points, 4)
        self.assertNotIn(B, dict(result.equal_player.player_weights))
        self.assertEqual(result.opportunity_weighted.expected_points, 4)

    def test_missing_team_game_role_or_prediction_fails_closed(self):
        cases = (
            {"assignments": self.assignments[:-1]},
            {"expected_team_ids": ("ATL", "CAR", "NYG")},
            {"predictions": self.predictions[:1]},
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.calculate(**case)

    def test_at_kickoff_and_future_information_rejected(self):
        leaked = replace(self.assignments[0], snapshot_at=self.games[0].kickoff)
        with self.assertRaisesRegex(ValueError, "strictly before"):
            self.calculate(assignments=(leaked,) + self.assignments[1:])
        with self.assertRaisesRegex(ValueError, "not completed"):
            self.calculate(cutoff=self.games[1].completed_at - timedelta(microseconds=1))
        # Completion exactly at the publication cutoff is eligible.
        self.calculate(cutoff=self.games[1].completed_at)

    def test_role_mixing_duplicate_records_and_empty_opportunity_pool_rejected(self):
        cases = (
            {"predictions": (replace(self.predictions[0], role="RB"),) + self.predictions[1:]},
            {"predictions": self.predictions + (self.predictions[0],)},
            {"assignments": self.assignments + (self.assignments[0],)},
            {"team_games": self.games + (self.games[0],)},
            {"predictions": tuple(replace(p, opportunities=0) for p in self.predictions)},
            {"cutoff": CUTOFF.replace(tzinfo=None)},
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.calculate(**case)

    def test_order_does_not_change_output(self):
        self.assertEqual(
            self.calculate(),
            self.calculate(predictions=self.predictions[::-1], assignments=self.assignments[::-1], team_games=self.games[::-1]),
        )

    def test_invalid_identifier_nonfinite_prediction_and_ambiguous_role(self):
        for change in ({"player_id": "Player Name"}, {"expected_points": float("nan")}, {"role": "OL"}, {"opportunities": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.predictions[0], **change)

    def test_preseason_postseason_and_invalid_regular_weeks_rejected(self):
        for change in (
            {"season_type": "PRE"}, {"season_type": "POST"},
            {"game_id": "2026_00_ATL_TB"}, {"game_id": "2026_19_ATL_TB"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.games[0], **change)


if __name__ == "__main__":
    unittest.main()
