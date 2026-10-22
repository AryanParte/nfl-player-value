"""Synthetic football scenarios; these tests do not validate player attribution."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.first_unit import require_role_assignments, select_first_units
from nfl_value.ingestion import Download, SnapshotStore, capture, json_bytes
from nfl_value.pregame_cli import main
from nfl_value.pregame_inputs import build_inputs, replay_inputs, require_benchmark_inputs
from nfl_value.schedules import audit_schedule_rows, reconcile_game_coverage
from test_ingestion import FakeSource, REVISION, WHEN, csv_gzip, play


def time(value):
    return datetime.fromisoformat(value)


CUTOFF = time(WHEN)


def schedule(**changes):
    row = {"game_id": "2026_01_ATL_TB", "season": "2026", "game_type": "REG", "week": "1", "gameday": "2026-09-13", "gametime": "13:00", "away_team": "ATL", "home_team": "TB", "away_score": "10", "home_score": "7"}
    row.update(changes)
    return row


def plays():
    return [play(home_team="TB", away_team="ATL", total_home_score="7", total_away_score="10", qtr="4", quarter_seconds_remaining="30"), play(play_id="2", play_type_nfl="END_GAME", epa="", home_team="TB", away_team="ATL", total_home_score="7", total_away_score="10", qtr="4", quarter_seconds_remaining="0")]


def game(team="ATL", game_id="2026_01_ATL_TB", kickoff="2026-09-13T17:00:00+00:00"):
    return CompletedTeamGame(game_id, team, time(kickoff), CUTOFF, "REG")


def chart(team="ATL", dt="2026-09-13T07:00:00Z", defense=None):
    # Synthetic IDs, actual documented/observed 3WR formation slot conventions.
    slots = [(1, "WR", 1), (2, "WR", 2), (3, "LT", 1), (4, "LG", 1), (5, "C", 1), (6, "RG", 1), (7, "RT", 1), (8, "WR", 3), (9, "QB", 1), (10, "TE", 1), (11, "RB", 1)]
    groups = [(21, "3WR 1TE", slots)]
    if defense:
        positions = ["LDE", "LDT", "RDT", "RDE", "WLB", "MLB", "SLB", "LCB", "SS", "FS", "RCB", "NB"] if defense == 16 else ["LDE", "NT", "RDE", "WLB", "LILB", "RILB", "SLB", "LCB", "SS", "FS", "RCB", "NB"]
        groups.append((defense, "Base 4-3 D" if defense == 16 else "Base 3-4 D", [(i, p, 1) for i, p in enumerate(positions, 1)]))
    offset = 0 if team == "ATL" else 1000
    return [dict(dt=dt, team=team, gsis_id=f"00-{offset + group * 100 + slot:07d}", espn_id=str(offset + group * 100 + slot), pos_grp_id=str(group), pos_grp=name, pos_slot=str(slot), pos_rank=str(rank), pos_abb=pos) for group, name, members in groups for slot, pos, rank in members]


class ScheduleTests(unittest.TestCase):
    def reconcile(self, rows=None, schedules=None):
        inventory = audit_schedule_rows(schedules or [schedule()], season=2026)["games"]
        return reconcile_game_coverage(inventory, plays() if rows is None else rows, cutoff=CUTOFF, observed_at=CUTOFF)

    def test_schedule_capture_preserves_all_seasons_and_replays(self):
        source = FakeSource(csv_gzip([schedule(), schedule(game_id="2025_01_ATL_TB", season="2025", gameday="2025-09-07")]), "schedules")
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            rid, receipt = capture(store, source.spec, code_revision=REVISION, fetch=source.fetch)
            from nfl_value.ingestion import replay
            self.assertEqual(replay(store, rid), receipt)
            self.assertEqual(receipt["audit"]["rows"], 2)
            self.assertEqual(receipt["audit"]["selected_rows"], 1)

    def test_eastern_kickoff_observes_daylight_saving(self):
        summer = audit_schedule_rows([schedule()], season=2026)["games"]["2026_01_ATL_TB"]
        winter = audit_schedule_rows([schedule(gameday="2026-11-08")], season=2026)["games"]["2026_01_ATL_TB"]
        self.assertEqual(summer["scheduled_kickoff"], "2026-09-13T17:00:00+00:00")
        self.assertEqual(winter["scheduled_kickoff"], "2026-11-08T18:00:00+00:00")

    def test_schedule_rejects_inconsistent_identity_keys_and_scores(self):
        for changed in (schedule(game_id="2026_02_ATL_TB"), schedule(home_team="ATL"), schedule(away_score=""), schedule(away_score="-1"), schedule(gametime="TBD"), schedule(game_type="PRE"), schedule(gameday="2024-09-13")):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                audit_schedule_rows([changed], season=2026)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit_schedule_rows([schedule(), schedule()], season=2026)
        with self.assertRaisesRegex(ValueError, "no games"):
            audit_schedule_rows([schedule()], season=2025)

    def test_terminal_marker_and_matching_scores_establish_observation_bound(self):
        result = self.reconcile()
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["matched_games"][0]["completion_observed_by"], WHEN)
        self.assertNotIn("completed_at", result["matched_games"][0])

    def test_score_or_zero_clock_alone_is_not_completion(self):
        rows = plays()[:1]
        rows[0]["game_seconds_remaining"] = "0"
        self.assertFalse(self.reconcile(rows)["coverage_complete"])
        rows = plays()
        rows[-1]["game_seconds_remaining"] = "293"  # Overtime can end early.
        self.assertTrue(self.reconcile(rows)["coverage_complete"])

    def test_duplicate_or_nonterminal_end_markers_are_unresolved(self):
        for extra in (play(play_id="3", play_type_nfl="END_GAME"), play(play_id="3")):
            self.assertEqual(self.reconcile(plays() + [extra])["unresolved_games"][0]["reason"], "missing_or_nonterminal_end_marker")

    def test_score_disagreement_or_missing_scores_blocks_game(self):
        self.assertEqual(self.reconcile(schedules=[schedule(home_score="8")])["unresolved_games"][0]["reason"], "score_disagreement")
        self.assertEqual(self.reconcile(schedules=[schedule(home_score="", away_score="")])["unresolved_games"][0]["reason"], "missing_schedule_scores")
        rows = plays()
        rows[-1]["total_home_score"] = ""
        self.assertFalse(self.reconcile(rows)["coverage_complete"])

    def test_missing_due_game_is_not_silently_dropped(self):
        missing = schedule(game_id="2026_02_ATL_TB", week="2", gameday="2026-09-20")
        result = self.reconcile(schedules=[schedule(), missing])
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(len(result["matched_games"]), 1)
        self.assertEqual(result["unresolved_games"], [{"game_id": missing["game_id"], "reason": "missing_pbp"}])

    def test_future_tbd_and_postseason_games_are_excluded(self):
        later = schedule(game_id="2026_10_ATL_TB", week="10", gameday="2026-11-15", gametime="", away_score="", home_score="")
        post = schedule(game_id="2026_19_ATL_TB", week="19", game_type="WC", gameday="2027-01-16")
        result = self.reconcile(schedules=[schedule(), later, post])
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["not_due_game_ids"], [later["game_id"]])
        self.assertEqual(result["excluded_postseason_game_ids"], [post["game_id"]])
        self.assertFalse(self.reconcile(schedules=[schedule(gametime="")])["coverage_complete"])

    def test_unexpected_game_team_or_future_pbp_fails(self):
        rows = plays()
        rows[-1]["home_team"] = "ATL"
        with self.assertRaisesRegex(ValueError, "teams disagree"):
            self.reconcile(rows)
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.reconcile(schedules=[schedule(game_id="2026_02_ATL_TB", week="2")])
        with self.assertRaisesRegex(ValueError, "not started"):
            self.reconcile(schedules=[schedule(gameday="2026-11-15")])


class FirstUnitTests(unittest.TestCase):
    def select(self, rows=None, games=None, roles=("WR",), **kwargs):
        return select_first_units(chart() if rows is None else rows, games or [game()], requested_roles=roles, **kwargs)

    def test_three_receivers_use_ranks_one_two_three(self):
        result = self.select()
        members = require_role_assignments(result, "WR")
        self.assertEqual({m.player_id for m in members}, {"00-0002101", "00-0002102", "00-0002108"})
        self.assertEqual([a["source_ranks"] for a in result["assignments"]], [[1], [2], [3]])

    def test_latest_snapshot_strictly_before_kickoff_is_selected(self):
        earlier = chart(dt="2026-09-12T07:00:00Z")
        latest = chart()
        post = chart(dt="2026-09-13T17:00:00Z")
        latest[0]["gsis_id"], latest[0]["espn_id"] = "00-0999999", "999999"
        result = self.select(post + latest + earlier)
        self.assertIn("00-0999999", {a.player_id for a in require_role_assignments(result, "WR")})
        self.assertEqual(result["selections"][0]["age_seconds"], 36000)

    def test_invalid_latest_snapshot_does_not_fall_back(self):
        latest = [r for r in chart() if r["pos_slot"] != "2"]
        result = self.select(chart(dt="2026-09-12T07:00:00Z") + latest)
        self.assertFalse(result["role_coverage_complete"]["WR"])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            require_role_assignments(result, "WR")

    def test_backup_does_not_fill_missing_starter_slot(self):
        rows = chart()
        rows[1]["pos_rank"] = "5"
        self.assertFalse(self.select(rows)["role_coverage_complete"]["WR"])

    def test_missing_legacy_or_ambiguous_ids_are_not_name_matched(self):
        for bad_id in ("", "NA", "ABC123456"):
            rows = chart()
            rows[0]["gsis_id"] = bad_id
            self.assertEqual(self.select(rows)["issues"][0]["reason"], "unresolved_player_identity")
        rows = chart()
        rows.append({**rows[0], "gsis_id": "00-0999999", "espn_id": "999999"})
        self.assertFalse(self.select(rows)["role_coverage_complete"]["WR"])

    def test_stale_missing_and_boundary_age(self):
        rows = chart(dt="2026-09-10T17:00:00Z")
        self.assertTrue(self.select(rows)["role_coverage_complete"]["WR"])
        rows = chart(dt="2026-09-10T16:59:59Z")
        self.assertEqual(self.select(rows)["issues"][0]["reason"], "stale_snapshot")
        self.assertEqual(self.select([])["issues"][0]["reason"], "no_pregame_snapshot")
        with self.assertRaises(ValueError):
            self.select(max_age=timedelta(0))

    def test_one_missing_team_blocks_whole_positional_population(self):
        report = self.select(games=[game(), game("TB")])
        self.assertEqual(len(report["assignments"]), 3)
        with self.assertRaises(ValueError):
            require_role_assignments(report, "WR")
        self.assertFalse(self.select(chart(), roles=("CB",))["role_coverage_complete"]["CB"])

    def test_traded_player_changes_team_without_resetting_identity(self):
        first = chart()
        second = chart("TB", "2026-09-20T07:00:00Z")
        second[8]["gsis_id"], second[8]["espn_id"] = first[8]["gsis_id"], first[8]["espn_id"]
        games = [game(), game("TB", "2026_02_TB_NYJ", "2026-09-20T17:00:00+00:00")]
        members = require_role_assignments(self.select(first + second, games, roles=("QB",)), "QB")
        self.assertEqual({a.team_id for a in members}, {"ATL", "TB"})
        self.assertEqual(len({a.player_id for a in members}), 1)

    def test_byes_do_not_add_a_synthetic_game_or_exposure(self):
        # Only declared schedule games become cells. Charts do not imply snaps,
        # missed-game participation, late-signing dates, or games during byes.
        result = self.select(chart() + chart(dt="2026-09-20T07:00:00Z"), roles=("QB",))
        self.assertEqual(result["expected_team_game_cells"], 1)
        self.assertNotIn("opportunities", result["assignments"][0])

    def test_both_teams_and_conflicting_identity_are_rejected(self):
        rows = chart() + chart("TB")
        rows[11 + 8]["gsis_id"], rows[11 + 8]["espn_id"] = rows[8]["gsis_id"], rows[8]["espn_id"]
        result = self.select(rows, [game(), game("TB")], roles=("QB",))
        self.assertIn("player_on_both_teams", {i["reason"] for i in result["issues"]})
        rows[-3]["gsis_id"] = "00-0999999"
        result = self.select(rows, [game(), game("TB")], roles=("QB",))
        self.assertIn("conflicting_player_identity", {i["reason"] for i in result["issues"]})

    def test_unknown_formation_position_and_duplicate_slot_fail_closed(self):
        for field, value in (("pos_grp_id", "99"), ("pos_slot", "99"), ("pos_abb", "TE"), ("pos_grp", "New formation")):
            rows = chart()
            rows[0][field] = value
            self.assertFalse(self.select(rows)["role_coverage_complete"]["WR"])
        rows = chart()
        rows[1]["gsis_id"] = rows[0]["gsis_id"]
        self.assertIn("same_player_in_multiple_slots", {i["reason"] for i in self.select(rows)["issues"]})

    def test_defensive_roles_depend_on_formation_not_de_abbreviation_alone(self):
        for formation, role, player in ((16, "EDGE", "00-0001601"), (15, "IDL", "00-0001501")):
            result = self.select(chart(defense=formation), roles=(role,))
            self.assertIn(player, {a.player_id for a in require_role_assignments(result, role)})
            self.assertFalse(result["ranking_ready"])

    def test_nickel_duplicate_is_counted_once_but_not_treated_as_lineup(self):
        rows = chart(defense=16)
        rows[-1]["gsis_id"], rows[-1]["espn_id"] = rows[-5]["gsis_id"], rows[-5]["espn_id"]
        result = self.select(rows, roles=("CB",))
        self.assertEqual(len(require_role_assignments(result, "CB")), 2)
        self.assertIn([8, 12], [a["slots"] for a in result["assignments"]])

    def test_ambiguous_defensive_formation_blocks_defensive_roles(self):
        rows = chart(defense=16) + [r for r in chart(defense=15) if r["pos_grp_id"] == "15"]
        result = self.select(rows, roles=("EDGE", "QB"))
        self.assertFalse(result["role_coverage_complete"]["EDGE"])
        self.assertTrue(result["role_coverage_complete"]["QB"])


class InputBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = SnapshotStore(Path(self.temp.name) / "raw")
        self.derived = SnapshotStore(Path(self.temp.name) / "derived")
        fixtures = {"schedules": [schedule()], "pbp": plays(), "depth_charts": chart() + chart("TB")}
        self.ids = {}
        for kind, rows in fixtures.items():
            fake = FakeSource(csv_gzip(rows), kind)
            self.ids[kind], _ = capture(self.raw, fake.spec, code_revision=REVISION, fetch=fake.fetch)

    def build(self, **changes):
        args = dict(self.ids, cutoff=CUTOFF, code_revision=REVISION)
        args.update(changes)
        return build_inputs(self.raw, **args)

    def test_offline_build_replay_and_cli_are_reproducible(self):
        with patch("nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")):
            report = self.build()
            rid = self.derived.put(json_bytes(report), manifest=True)
            self.assertEqual(replay_inputs(self.raw, self.derived, rid), report)
            self.assertTrue(report["game_coverage"]["coverage_complete"])
            self.assertEqual(len(require_role_assignments(report["first_unit"], "WR")), 6)
            self.assertFalse(report["ranking_ready"])
            self.assertEqual(report["historical_availability"]["team_games_using_retrospectively_retrieved_depth"], 2)
            with self.assertRaisesRegex(ValueError, "retrospective"):
                require_benchmark_inputs(report, "WR")
            games, members = require_benchmark_inputs(report, "WR", allow_retrospective=True)
            self.assertEqual((len(games), len(members)), (2, 6))
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--store", str(self.raw.root), "--output-store", str(self.derived.root), "replay", rid]), 0)
            self.assertFalse(json.loads(output.getvalue())["ranking_ready"])

    def test_cutoff_cannot_backdate_later_source_retrieval(self):
        with self.assertRaisesRegex(ValueError, "after cutoff"):
            self.build(cutoff=time("2026-09-14T00:00:00Z"))

    def test_receipt_evidence_must_finish_before_cutoff(self):
        fake = FakeSource(csv_gzip([schedule()]), "schedules")

        def fetch(url, max_bytes):
            result = fake.fetch(url, max_bytes)
            return Download(result.body, "2026-10-19T20:01:00Z" if url == fake.spec.license_url else WHEN, result.headers)

        rid, _ = capture(self.raw, fake.spec, code_revision=REVISION, fetch=fetch)
        with self.assertRaisesRegex(ValueError, "after cutoff"):
            self.build(schedules=rid)

    def test_wrong_source_kind_and_tampered_report_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "kind"):
            self.build(pbp=self.ids["depth_charts"])
        report = self.build()
        report["ranking_ready"] = True
        rid = self.derived.put(json_bytes(report), manifest=True)
        with self.assertRaisesRegex(ValueError, "differs"):
            replay_inputs(self.raw, self.derived, rid)

    def test_new_required_headers_are_checked_before_derivation(self):
        rows = chart()
        for row in rows:
            del row["pos_grp"]
        fake = FakeSource(csv_gzip(rows), "depth_charts")
        rid, _ = capture(self.raw, fake.spec, code_revision=REVISION, fetch=fake.fetch)
        with self.assertRaisesRegex(ValueError, "requires columns"):
            self.build(depth_charts=rid)

    def test_missing_pbp_game_produces_diagnostic_not_empty_valid_board(self):
        fake = FakeSource(csv_gzip([schedule(), schedule(game_id="2026_02_ATL_TB", week="2", gameday="2026-09-20")]), "schedules")
        rid, _ = capture(self.raw, fake.spec, code_revision=REVISION, fetch=fake.fetch)
        report = self.build(schedules=rid)
        self.assertFalse(report["game_coverage"]["coverage_complete"])
        self.assertFalse(report["ranking_ready"])
        with self.assertRaisesRegex(ValueError, "game coverage"):
            require_benchmark_inputs(report, "WR", allow_retrospective=True)

    def test_benchmark_gate_requires_all_teams_and_complete_role_cells(self):
        report = self.build()
        report["season_team_ids"].append("KC")
        with self.assertRaisesRegex(ValueError, "team universe"):
            require_benchmark_inputs(report, "QB", allow_retrospective=True)
        report = self.build()
        report["first_unit"]["assignments"] = [a for a in report["first_unit"]["assignments"] if a["team_id"] == "ATL"]
        with self.assertRaisesRegex(ValueError, "team-game cells"):
            require_benchmark_inputs(report, "QB", allow_retrospective=True)


if __name__ == "__main__":
    unittest.main()
