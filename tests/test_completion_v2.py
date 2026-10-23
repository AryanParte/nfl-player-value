"""Synthetic event-order counterexamples, not score-only finality inference."""

import unittest

from nfl_value.schedules import CLOCK_COMPLETION, LEGACY_COMPLETION, audit_schedule_rows, reconcile_game_coverage
from test_pregame_inputs import CUTOFF, plays, schedule


class ClockCompletionTests(unittest.TestCase):
    def setUp(self):
        self.rows = plays()
        self.inventory = audit_schedule_rows([schedule()], season=2026)["games"]

    def run_policy(self, policy=CLOCK_COMPLETION):
        return reconcile_game_coverage(self.inventory, self.rows, cutoff=CUTOFF, observed_at=CUTOFF, policy_version=policy)

    def reason(self):
        result = self.run_policy()
        self.assertFalse(result["coverage_complete"])
        return result["unresolved_games"][0]["reason"]

    def test_higher_id_for_earlier_timeout_or_kneel_is_accepted_only_by_v2(self):
        for kind, clock in (("TIMEOUT", "3"), ("RUSH", "33")):
            self.rows = plays() + [{**plays()[0], "play_id": "3", "play_type_nfl": kind, "quarter_seconds_remaining": clock}]
            with self.subTest(kind=kind):
                self.assertTrue(self.run_policy()["coverage_complete"])
                self.assertFalse(self.run_policy(LEGACY_COMPLETION)["coverage_complete"])

    def test_row_order_is_irrelevant_and_old_policy_is_still_replayable(self):
        expected = self.run_policy()
        self.rows.reverse()
        self.assertEqual(expected, self.run_policy())
        self.assertEqual(self.run_policy(LEGACY_COMPLETION)["policy_version"], LEGACY_COMPLETION)

    def test_event_later_than_marker_fails_even_with_smaller_numeric_id(self):
        self.rows = [{**plays()[0], "qtr": "5", "quarter_seconds_remaining": "100"}, plays()[1]]
        self.assertEqual(self.reason(), "event_after_end_marker_clock")

    def test_early_overtime_finish_is_valid_without_zero_clock(self):
        self.rows[0].update(qtr="5", quarter_seconds_remaining="300")
        self.rows[1].update(qtr="5", quarter_seconds_remaining="293")
        self.assertTrue(self.run_policy()["coverage_complete"])
        self.rows.append({**self.rows[0], "play_id": "3", "quarter_seconds_remaining": "292"})
        self.assertEqual(self.reason(), "event_after_end_marker_clock")

    def test_regulation_or_early_quarter_marker_cannot_end_with_remaining_time(self):
        for quarter, clock in (("4", "1"), ("3", "0")):
            with self.subTest(quarter=quarter):
                self.rows[-1].update(qtr=quarter, quarter_seconds_remaining=clock)
                self.assertEqual(self.reason(), "invalid_end_marker_clock")

    def test_equal_clock_after_marker_is_ambiguous(self):
        self.rows.append({**plays()[0], "play_id": "3", "quarter_seconds_remaining": "0"})
        self.assertEqual(self.reason(), "ambiguous_event_at_end_marker_clock")

    def test_comment_can_lack_clock_but_timed_event_cannot(self):
        self.rows.append({**plays()[0], "play_id": "3", "qtr": "", "quarter_seconds_remaining": "", "play_type_nfl": "COMMENT"})
        self.assertTrue(self.run_policy()["coverage_complete"])
        self.rows[-1]["play_type_nfl"] = "TIMEOUT"
        self.assertEqual(self.reason(), "missing_or_invalid_event_clock")

    def test_invalid_clocks_fail_instead_of_fabricating_order(self):
        for field, value in (("qtr", "6"), ("qtr", "NA"), ("quarter_seconds_remaining", "-1"), ("quarter_seconds_remaining", "901")):
            with self.subTest(field=field, value=value):
                self.rows = plays()
                self.rows[0][field] = value
                self.assertEqual(self.reason(), "missing_or_invalid_event_clock")

    def test_missing_duplicate_marker_or_score_disagreement_still_blocks(self):
        self.rows.pop()
        self.assertEqual(self.reason(), "missing_or_duplicate_end_marker")
        self.rows = plays() + [{**plays()[1], "play_id": "3"}]
        self.assertEqual(self.reason(), "missing_or_duplicate_end_marker")
        self.rows = plays()
        self.rows[-1]["total_home_score"] = "8"
        self.assertEqual(self.reason(), "score_disagreement")

    def test_zero_clock_without_marker_and_unsupported_policy_are_rejected(self):
        self.rows[-1]["play_type_nfl"] = "END_QUARTER"
        self.assertEqual(self.reason(), "missing_or_duplicate_end_marker")
        with self.assertRaisesRegex(ValueError, "unsupported completion"):
            self.run_policy("future-policy")


if __name__ == "__main__":
    unittest.main()
