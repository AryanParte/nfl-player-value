"""Synthetic opportunity accounting and versioned input tests."""

from contextlib import redirect_stdout
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.defense_inputs import build_defense_inputs, replay_defense_inputs, save_defense_inputs
from nfl_value.ingestion import SnapshotStore, capture, json_bytes
from nfl_value.offensive_cli import main
from nfl_value.offensive_inputs import build_offensive_inputs, offensive_ledger, replay_offensive_inputs, save_offensive_inputs
from nfl_value.pregame_inputs import build_inputs, replay_inputs
from test_defense_inputs import GAME, REVISION, WHEN, Source, part, play, schedule
from test_pregame_inputs import chart, plays as pregame_plays, schedule as pregame_schedule
from test_ingestion import FakeSource, csv_gzip


PASSER, RUNNER, RECEIVER = "00-0000001", "00-0000002", "00-0000003"
GAMES = [{"game_id": GAME, "week": 1, "scheduled_kickoff": "2025-09-07T17:00:00+00:00", "away_team": "ATL", "home_team": "TB"}]


def offensive_play(**changes):
    return {**play(), "qb_dropback": "1", "qb_scramble": "0", "rush_attempt": "0", "pass_attempt": "1", "sack": "0", "aborted_play": "0",
            "passer_player_id": PASSER, "rusher_player_id": "", "receiver_player_id": RECEIVER, **changes}


def run_play(**changes):
    return offensive_play(play_type="run", play_type_nfl="RUSH", qb_dropback="0", rush_attempt="1", pass_attempt="0", passer_player_id="", rusher_player_id=RUNNER, receiver_player_id="", **changes)


def end_play():
    return offensive_play(play_id="99", play_type="", play_type_nfl="END_GAME", qtr="4", quarter_seconds_remaining="0", epa="")


class LedgerTests(unittest.TestCase):
    def ledger(self, rows):
        return offensive_ledger(rows, completed_games=GAMES)

    def test_epa_is_one_team_outcome_not_copied_to_actor_workloads(self):
        ledger, audit = self.ledger([offensive_play()])
        self.assertEqual(audit["observed_offense_epa_sum"], 1.5)
        self.assertEqual(ledger["plays"][0]["actors"], {"dropback": PASSER, "rusher": None, "target": RECEIVER})
        self.assertNotIn("epa", json.dumps(ledger["observed_player_games"]))
        self.assertEqual(audit["observed_players"], 2)

    def test_sack_negative_value_is_retained_and_is_a_dropback(self):
        ledger, audit = self.ledger([offensive_play(sack="1", play_type_nfl="SACK", receiver_player_id="", epa="-4")])
        self.assertEqual(ledger["plays"][0]["event_kind"], "sack")
        self.assertEqual(audit["observed_offense_epa_sum"], -4)
        self.assertEqual(ledger["observed_player_games"][0]["observed"]["dropbacks"], 1)
        self.assertEqual(ledger["observed_player_games"][0]["observed"]["targets"], 0)

    def test_scramble_union_is_one_play_not_two(self):
        row = run_play()
        row.update(qb_dropback="1", qb_scramble="1", rusher_player_id=PASSER)
        ledger, _ = self.ledger([row])
        counts = ledger["observed_player_games"][0]["observed"]
        self.assertEqual(counts["dropbacks"], 1)
        self.assertEqual(counts["rushes"], 1)
        self.assertEqual(counts["dropback_or_rush_plays"], 1)
        self.assertEqual(counts["on_ball_plays"], 1)

    def test_nondropback_run_does_not_assume_roster_position(self):
        ledger, _ = self.ledger([run_play()])
        self.assertEqual(ledger["plays"][0]["event_kind"], "non_dropback_run")
        self.assertFalse(ledger["player_positions_verified"])
        self.assertFalse(ledger["qualification_denominator_complete"])
        self.assertNotIn("role", ledger["observed_player_games"][0])

    def test_self_target_cannot_double_count_unique_on_ball_plays(self):
        ledger, _ = self.ledger([offensive_play(receiver_player_id=PASSER)])
        counts = ledger["observed_player_games"][0]["observed"]
        self.assertEqual(counts["dropbacks"], 1)
        self.assertEqual(counts["targets"], 1)
        self.assertEqual(counts["on_ball_plays"], 1)

    def test_missing_target_is_explicit_not_an_invented_receiver(self):
        ledger, audit = self.ledger([offensive_play(receiver_player_id="")])
        self.assertEqual(audit["passes_without_recorded_target"], 1)
        self.assertEqual(ledger["plays"][0]["target_observation"], "none_recorded")
        self.assertEqual(audit["observed_players"], 1)

    def test_missing_actor_and_aborted_play_do_not_remove_negative_team_epa(self):
        ledger, audit = self.ledger([offensive_play(passer_player_id="", epa="-3"), run_play(play_id="2", aborted_play="1", epa="-2")])
        self.assertEqual(audit["observed_offense_epa_sum"], -5)
        self.assertEqual(len(ledger["plays"]), 2)
        self.assertEqual(audit["plays_with_actor_issues"], 2)
        self.assertEqual(ledger["plays"][1]["actors"], {"dropback": None, "rusher": None, "target": None})

    def test_invalid_identity_or_flags_are_visible_and_not_guessed(self):
        for change, reason in (({"passer_player_id": "legacy"}, "noncanonical_passer_player_id"),
                               ({"qb_dropback": ""}, "unknown_event_flag"), ({"qb_scramble": "1"}, "inconsistent_event_flags"),
                               ({"qb_kneel": ""}, "unknown_exclusion_flag")):
            with self.subTest(change=change):
                ledger, audit = self.ledger([offensive_play(**change)])
                self.assertIn(reason, audit["issue_counts"])
                self.assertEqual(len(ledger["plays"]), 1)
                self.assertIsNone(ledger["plays"][0]["actors"]["dropback"])

    def test_missing_context_and_epa_stay_missing_with_separate_workload_counts(self):
        for field, value in (("down", "NA"), ("epa", "NA"), ("epa", "nan")):
            with self.subTest(field=field, value=value):
                ledger, audit = self.ledger([offensive_play(**{field: value})])
                self.assertEqual(audit["candidate_plays"], 1)
                self.assertEqual(audit["context_outcome_complete_plays"], 0)
                for item in ledger["observed_player_games"]:
                    self.assertEqual(item["observed"]["on_ball_plays"], 1)
                    self.assertEqual(item["context_outcome_complete"]["on_ball_plays"], 0)

    def test_postseason_kneel_spike_conversion_no_play_and_unfinished_game_excluded(self):
        rows = [offensive_play(), offensive_play(play_id="2", qb_kneel="1"), offensive_play(play_id="3", qb_spike="1"),
                offensive_play(play_id="4", two_point_attempt="1"), offensive_play(play_id="5", play_type="no_play"),
                offensive_play(game_id="2025_19_ATL_TB", season_type="POST"), offensive_play(game_id="2025_02_ATL_TB")]
        ledger, audit = self.ledger(rows)
        self.assertEqual(len(ledger["plays"]), 1)
        self.assertEqual(sum(audit["excluded_pbp_counts"].values()), 6)

    def test_duplicate_keys_and_wrong_team_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate offensive"):
            self.ledger([offensive_play(), offensive_play()])
        with self.assertRaisesRegex(ValueError, "teams disagree"):
            self.ledger([offensive_play(defteam="NYJ")])

    def test_cross_team_actor_conflicts_are_reported(self):
        _, audit = self.ledger([offensive_play(), offensive_play(play_id="2", posteam="TB", defteam="ATL")])
        self.assertEqual({x["player_id"] for x in audit["player_game_team_conflicts"]}, {PASSER, RECEIVER})

    def test_reordering_preserves_ledger_and_cumulative_negative_games(self):
        other = {**GAMES[0], "game_id": "2025_02_ATL_TB", "week": 2, "scheduled_kickoff": "2025-09-14T17:00:00Z"}
        rows = [offensive_play(epa="-3"), offensive_play(game_id=other["game_id"], epa="2")]
        a = offensive_ledger(rows, completed_games=GAMES + [other])
        b = offensive_ledger(list(reversed(rows)), completed_games=GAMES + [other])
        self.assertEqual(a, b)
        self.assertEqual(a[1]["observed_offense_epa_sum"], -1)
        self.assertEqual(a[1]["observed_player_game_rows"], 4)


class InputBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.raw = SnapshotStore(Path(temp.name) / "raw")
        self.derived = SnapshotStore(Path(temp.name) / "derived")
        self.ids = {}
        for kind, rows in (("schedules", [schedule()]), ("pbp", [offensive_play(), end_play()]), ("participation", [part()])):
            source = Source(kind, rows)
            self.ids[kind] = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]

    def build(self, **changes):
        ids = {kind: self.ids[kind] for kind in ("schedules", "pbp")}
        return build_offensive_inputs(self.raw, **{**ids, **changes}, cutoff=datetime.fromisoformat(WHEN), code_revision=REVISION)

    def test_realistic_bundle_and_cli_replay_are_offline(self):
        report, ledger = self.build()
        rid, saved = save_offensive_inputs(self.derived, report, ledger)
        self.assertEqual(report["game_coverage"]["policy_version"], "clock-marker-schedule-v2")
        self.assertEqual(ledger["provenance"]["source_attribution"]["pbp"]["license_id"], "CC-BY-4.0")
        with patch("nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")):
            self.assertEqual(replay_offensive_inputs(self.raw, self.derived, rid), saved)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--store", str(self.raw.root), "--output-store", str(self.derived.root), "replay", rid]), 0)
            self.assertFalse(json.loads(output.getvalue())["ranking_ready"])

    def test_tampered_ledger_and_report_are_detected(self):
        report, ledger = self.build()
        _, saved = save_offensive_inputs(self.derived, report, ledger)
        changed = {**saved, "objects": {"ledger": self.derived.put(json_bytes({**ledger, "plays": []}))}}
        rid = self.derived.put(json_bytes(changed), manifest=True)
        with self.assertRaisesRegex(ValueError, "replay differs"):
            replay_offensive_inputs(self.raw, self.derived, rid)
        rid = self.derived.put(json_bytes({**saved, "ranking_ready": True}), manifest=True)
        with self.assertRaisesRegex(ValueError, "replay differs"):
            replay_offensive_inputs(self.raw, self.derived, rid)

    def test_wrong_kind_future_evidence_or_missing_required_fields_fail(self):
        with self.assertRaisesRegex(ValueError, "source kind"):
            self.build(pbp=self.ids["schedules"])
        with self.assertRaisesRegex(ValueError, "after cutoff"):
            build_offensive_inputs(self.raw, schedules=self.ids["schedules"], pbp=self.ids["pbp"], cutoff=datetime.fromisoformat("2026-10-20T00:00:00Z"), code_revision=REVISION)
        row, end = offensive_play(), end_play()
        for r in (row, end):
            r.pop("qb_scramble")
        source = Source("pbp", [row, end])
        rid = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]
        with self.assertRaisesRegex(ValueError, "require columns"):
            self.build(pbp=rid)

    def test_defensive_v1_and_v2_replay_with_recorded_policy(self):
        for version in (1, 2):
            with self.subTest(version=version):
                report, rich, reduced = build_defense_inputs(self.raw, **self.ids, cutoff=datetime.fromisoformat(WHEN), code_revision=REVISION, report_version=version)
                rid, saved = save_defense_inputs(self.derived, report, rich, reduced)
                self.assertEqual(replay_defense_inputs(self.raw, self.derived, rid), saved)
                self.assertTrue(report["game_coverage"]["policy_version"].endswith(f"v{version}"))

    def test_pregame_v1_and_v2_replay_with_recorded_policy(self):
        ids = {}
        for kind, rows in (("schedules", [pregame_schedule()]), ("pbp", pregame_plays()), ("depth_charts", chart() + chart("TB"))):
            source = FakeSource(csv_gzip(rows), kind)
            ids[kind] = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]
        for version in (1, 2):
            report = build_inputs(self.raw, **ids, cutoff=datetime.fromisoformat(WHEN), code_revision=REVISION, report_version=version)
            rid = self.derived.put(json_bytes(report), manifest=True)
            self.assertEqual(replay_inputs(self.raw, self.derived, rid), report)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            build_inputs(self.raw, **ids, cutoff=datetime.fromisoformat(WHEN), code_revision=REVISION, report_version=3)


if __name__ == "__main__":
    unittest.main()
