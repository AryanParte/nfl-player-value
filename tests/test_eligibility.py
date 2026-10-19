"""Season-window and evidence-gate tests using explicitly synthetic exposure."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.eligibility import GameExposure, ModuleStatus, SeasonExposure, qualify


START = datetime(2026, 9, 13, 17, tzinfo=timezone.utc)
VALIDATED = ModuleStatus(True, True, True, "synthetic validated test module")
EXPLORATORY = ModuleStatus(True, False, False, "defensive game-level association")


def season(role="QB", counts=(20, 20, 20), *, played=None, teams=None, team_snaps=None, unit=None):
    if played is None:
        played = [True] * len(counts)
    if teams is None:
        teams = ["ATL"] * len(counts)
    if team_snaps is None:
        team_snaps = [None] * len(counts)
    games = []
    for index, (count, participated, team, snaps) in enumerate(zip(counts, played, teams, team_snaps), 1):
        kickoff = START + timedelta(days=7 * (index - 1))
        game = CompletedTeamGame(f"2026_{index:02}_{team}_TB", team, kickoff, kickoff + timedelta(hours=3), "REG")
        games.append(GameExposure(game, participated, count, snaps))
    units = {"QB": "modeled_qb_plays", "RB": "carry_or_target_plays", "WR": "targets", "TE": "targets"}
    return SeasonExposure(
        "00-0000001", role, 2026, START + timedelta(days=120), tuple(games),
        unit or units.get(role, "defensive_snaps"), True,
    )


class EligibilityTests(unittest.TestCase):
    def test_exact_floor_and_three_game_requirement(self):
        for role, counts, threshold in (
            ("QB", (16, 17, 17), 50), ("RB", (8, 8, 9), 25),
            ("WR", (5, 5, 5), 15), ("TE", (3, 3, 4), 10),
        ):
            with self.subTest(role=role):
                result = qualify(season(role, counts), VALIDATED)
                self.assertTrue(result.main_qualified)
                self.assertEqual(result.minimum_opportunities, threshold)
                below = (counts[0] - 1,) + counts[1:]
                self.assertFalse(qualify(season(role, below), VALIDATED).participation_qualified)
        two_games = qualify(season(counts=(100, 100)), VALIDATED)
        self.assertFalse(two_games.main_qualified)
        self.assertIn("fewer_than_three_games", two_games.main_exclusion_reasons)

    def test_missed_games_raise_season_threshold_without_resetting_value_exposure(self):
        exposure = season(counts=(30, 30, 30, 0, 0, 0, 0), played=(True, True, True, False, False, False, False))
        result = qualify(exposure, VALIDATED)
        self.assertEqual(result.games_played, 3)
        self.assertEqual(result.completed_team_games, 7)
        self.assertEqual(result.minimum_opportunities, 98)
        self.assertFalse(result.participation_qualified)

    def test_all_opportunity_rates_progress_with_completed_team_games(self):
        for role, threshold in (("QB", 84), ("RB", 36), ("WR", 18), ("TE", 12)):
            with self.subTest(role=role):
                count = threshold // 3
                exposure = season(role, (count, count, count, 0, 0, 0), played=(True, True, True, False, False, False))
                result = qualify(exposure, VALIDATED)
                self.assertEqual(result.minimum_opportunities, threshold)
                self.assertTrue(result.main_qualified)

    def test_missed_defensive_games_remain_in_team_snap_denominator(self):
        exposure = season("EDGE", (30, 30, 30, 0, 0, 0), team_snaps=(100,) * 6, played=(True, True, True, False, False, False))
        result = qualify(exposure, EXPLORATORY)
        self.assertEqual(result.games_played, 3)
        self.assertEqual(result.team_snap_denominator, 600)
        self.assertEqual(result.minimum_opportunities, 120)
        self.assertFalse(result.participation_qualified)

    def test_trade_preserves_nonoverlapping_stint_exposure_and_rejects_duplicate_game(self):
        exposure = season(counts=(30, 30, 30, 0), played=(True, True, True, False), teams=("ATL", "ATL", "CAR", "CAR"))
        result = qualify(exposure, VALIDATED)
        self.assertEqual(result.completed_team_games, 4)
        self.assertEqual(result.opportunities, 90)
        self.assertEqual(result.minimum_opportunities, 56)
        with self.assertRaisesRegex(ValueError, "duplicate game"):
            replace(exposure, games=exposure.games + (exposure.games[0],))
        overlapping = replace(exposure.games[2].game, kickoff=exposure.games[1].game.kickoff, completed_at=exposure.games[1].game.completed_at)
        with self.assertRaisesRegex(ValueError, "overlapping"):
            replace(exposure, games=exposure.games[:2] + (replace(exposure.games[2], game=overlapping),))

    def test_snap_roles_use_correct_unit_and_season_denominator(self):
        for role, unit, counts, expected in (
            ("OT", "offensive_snaps", (47, 47, 47), 141),
            ("CB", "defensive_snaps", (47, 47, 47), 141),
            ("EDGE", "defensive_snaps", (27, 27, 27), 81),
        ):
            with self.subTest(role=role):
                result = qualify(season(role, counts, team_snaps=(134, 134, 134), unit=unit), VALIDATED)
                self.assertEqual(result.team_snap_denominator, 402)
                self.assertEqual(result.minimum_opportunities, expected)
                self.assertTrue(result.main_qualified)
        with self.assertRaisesRegex(ValueError, "opportunity_unit"):
            qualify(season("WR", (20, 20, 20), unit="offensive_snaps"), VALIDATED)

    def test_missing_denominators_and_future_or_incomplete_windows_fail_closed(self):
        missing = qualify(season("CB", (40, 40, 40)), VALIDATED)
        self.assertFalse(missing.participation_qualified)
        self.assertIn("team_snap_denominator_missing", missing.main_exclusion_reasons)
        exposure = season()
        incomplete = qualify(replace(exposure, denominator_complete=False), VALIDATED)
        self.assertFalse(incomplete.main_qualified)
        with self.assertRaisesRegex(ValueError, "not completed"):
            replace(exposure, cutoff=exposure.games[-1].game.kickoff)

    def test_defense_explorer_has_separate_validation_and_comparability_gates(self):
        exposure = season("EDGE", (30, 30, 30), team_snaps=(100, 100, 100))
        result = qualify(exposure, EXPLORATORY)
        self.assertTrue(result.participation_qualified)
        self.assertTrue(result.explorer_qualified)
        self.assertFalse(result.main_qualified)
        self.assertIn("attribution_not_validated", result.main_exclusion_reasons)
        self.assertIn("not_comparable_to_main", result.main_exclusion_reasons)
        self.assertFalse(qualify(exposure, replace(EXPLORATORY, source_coverage_complete=False)).explorer_qualified)
        self.assertTrue(qualify(exposure, VALIDATED).main_qualified)

    def test_partial_receiving_label_and_unsupported_specialists_are_explicit(self):
        receiving = qualify(season("WR", (5, 5, 5)), VALIDATED)
        self.assertIn("partial position coverage", receiving.scope_label)
        specialist = qualify(season("K", (10, 10, 10), unit="field_goal_attempts"), VALIDATED)
        self.assertFalse(specialist.main_qualified)
        self.assertIn("position_rule_not_validated", specialist.main_exclusion_reasons)

    def test_bounded_historical_grid_does_not_change_three_game_rule(self):
        exposure = season(counts=(13, 13, 12))
        self.assertTrue(qualify(exposure, VALIDATED, historical_threshold_multiplier=0.75).main_qualified)
        self.assertFalse(qualify(exposure, VALIDATED).main_qualified)
        stricter = qualify(exposure, VALIDATED, historical_threshold_multiplier=1.25)
        self.assertEqual(stricter.minimum_opportunities, 63)
        self.assertIn("historical-1.25x", stricter.policy_version)
        # 20% of 402 snaps is 80.4; scale to 100.5 then round to 101.
        # Rounding before scaling would incorrectly require 102.
        defensive = season("EDGE", (34, 34, 33), team_snaps=(134,) * 3)
        scaled = qualify(defensive, VALIDATED, historical_threshold_multiplier=1.25)
        self.assertEqual(scaled.minimum_opportunities, 101)
        self.assertTrue(scaled.participation_qualified)
        with self.assertRaises(ValueError):
            qualify(exposure, VALIDATED, historical_threshold_multiplier=0.9)
        self.assertFalse(qualify(season(counts=(40, 40)), VALIDATED, historical_threshold_multiplier=0.75).main_qualified)

    def test_invalid_exposure_is_rejected(self):
        exposure = season()
        with self.assertRaises(ValueError):
            replace(exposure.games[0], participated=False)
        with self.assertRaises(ValueError):
            replace(exposure.games[0], team_unit_snaps=1)
        with self.assertRaises(ValueError):
            replace(exposure, season=2025)
        with self.assertRaises(ValueError):
            replace(exposure, cutoff=exposure.cutoff.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
