"""Synthetic observed evidence; fixtures are never presented as NFL findings."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.defense_explorer import (UNAVAILABLE, build_explorer, event_credits, export_explorer,
                                      observed_explorer, replay_explorer, save_explorer)
from nfl_value.ingestion import SnapshotStore, json_bytes


def fixture():
    gid = "2026_01_BUF_NYJ"
    games = {"coverage_complete": True, "matched_games": [{"game_id": gid, "week": 1, "home_team": "NYJ", "away_team": "BUF"}]}
    plays = [{"game_id": gid, "play_id": i, "offense_team": "NYJ" if i < 4 else "BUF",
              "defense_team": "BUF" if i < 4 else "NYJ", "event_kind": "sack" if i <= 2 else "pass",
              "offense_epa": -1.0 if i <= 2 else 0.5} for i in range(1, 5)]
    chart = {"assignments": [{"game_id": gid, "team_id": "BUF", "role": "EDGE", "player_id": "00-0000001", "espn_id": "11"},
                             {"game_id": gid, "team_id": "NYJ", "role": "CB", "player_id": "00-0000004", "espn_id": "14"}], "issues": []}
    events = [{"game_id": gid, "play_id": str(i), "sack": "1" if i <= 2 else "0", "interception": "1" if i == 3 else "0",
               "sack_player_id": "00-0000001" if i == 1 else "NA", "half_sack_1_player_id": "00-0000001" if i == 2 else "NA",
               "half_sack_2_player_id": "00-0000002" if i == 2 else "NA", "interception_player_id": "00-0000003" if i == 3 else "NA"} for i in range(1, 5)]
    roster = [{"gsis_id": f"00-{i:07}", "espn_id": str(i+10), "full_name": f"Synthetic Player {i}"} for i in range(1, 5)]
    return {"plays": plays}, games, chart, events, roster


def payload():
    return {"schema_version": 1, "kind": "defense_explorer", "data_mode": "synthetic", "ranking_ready": False,
            "season": 2026, "cutoff": "2026-10-22T23:50:38+00:00", "code_revision": "a"*40,
            "scope": "Synthetic test observations; not real NFL data.",
            "provenance": {"offensive_report": "a"*64, "source_receipts": {k: "b"*64 for k in ("pbp", "schedules", "rosters", "depth_charts")},
                "sources": [{"kind": k, "fetched_at": "2026-10-22T22:00:00+00:00", "updated_at": "2026-10-22T21:00:00+00:00",
                             "source_url": "https://github.com/nflverse/nflverse-data", "license_id": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/", "attribution": "Synthetic test fixture"}
                            for k in ("pbp", "schedules", "rosters", "depth_charts")],
                "opportunity_policy": "observed-offensive-pass-run-v1", "chart_policy": "espn-formation-slots-2025-v1",
                "retrospective_chart_team_games": 2, "name_policy": "Synthetic fixture"}, **observed_explorer(*fixture())}


class ExplorerTests(unittest.TestCase):
    def test_build_rejects_future_or_wrong_season_sources_before_chart_derivation(self):
        report = {"objects": {"ledger": "a"*64}, "source_receipts": {"pbp": "b"*64, "schedules": "c"*64},
                  "cutoff": "2026-10-22T23:50:38+00:00", "season": 2026}
        receipts = [{"source": {"kind": kind, "season": 2026},
                     "retrieval": {"data": "2026-10-22T22:00:00+00:00"}}
                    for kind in ("pbp", "schedules", "depth_charts", "rosters")]
        for future in (True, False):
            changed = deepcopy(receipts)
            if future:
                changed[-1]["retrieval"]["data"] = "2026-10-23T00:00:00+00:00"
            else:
                changed[-1]["source"]["season"] = 2025
            with tempfile.TemporaryDirectory() as tmp:
                inputs = SnapshotStore(Path(tmp))
                report["objects"]["ledger"] = inputs.put(json_bytes({}))
                with patch("nfl_value.defense_explorer.replay_offensive_inputs", return_value=report), \
                        patch("nfl_value.defense_explorer.replay", side_effect=changed), \
                        patch("nfl_value.defense_explorer.build_inputs") as chart:
                    with self.assertRaisesRegex(ValueError, "cutoff" if future else "season"):
                        build_explorer(None, inputs, offensive_report="d"*64, depth_charts="e"*64,
                                       rosters="f"*64, code_revision="a"*40)
                    chart.assert_not_called()

    def test_shared_frontend_fixture_matches_python_contract(self):
        self.assertEqual(json.loads(Path("web/tests/fixture.json").read_text()), payload())

    def test_export_rejects_unadmitted_numeric_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp)/"store")
            p = payload()
            p["players"][0]["cavaa"] = 40
            rid, _ = save_explorer(store, p)
            with self.assertRaisesRegex(ValueError, "unadmitted"):
                export_explorer(store, rid, Path(tmp)/"public")
            self.assertFalse((Path(tmp)/"public/latest.json").exists())

    def test_solo_and_split_sacks_conserve_one_credit_per_event(self):
        data = observed_explorer(*fixture())
        players = {p["player_id"]: p for p in data["players"]}
        self.assertEqual(players["00-0000001"]["sack_credits"], 1.5)
        self.assertEqual(players["00-0000002"]["sack_credits"], 0.5)
        self.assertEqual(sum(p["interceptions"] for p in players.values()), 1)
        self.assertEqual(data["audit"]["unallocated_flagged_events"], {"sacks": 0, "interceptions": 0})
        self.assertEqual(players["00-0000004"]["event_games"], 0)
        self.assertEqual(players["00-0000004"]["chart_games"], 1)
        self.assertTrue(all(p["cavaa"] is None and p["defensive_snaps"] is None for p in players.values()))

    def test_ambiguous_event_preserves_outcome_and_unallocated_credit(self):
        args = fixture()
        args[3][1]["half_sack_2_player_id"] = "00-0000001"
        data = observed_explorer(*args)
        self.assertEqual(data["audit"]["unallocated_flagged_events"]["sacks"], 1)
        self.assertEqual(data["coverage"]["included_plays"], 4)
        self.assertEqual(next(g for g in data["team_games"] if g["team"] == "BUF")["defense_epa"], 1.5)
        self.assertEqual(len(data["audit"]["event_issues"]), 1)

    def test_invalid_ids_unknown_flags_and_conflicting_events_not_invented(self):
        row = fixture()[3][0]
        for changes in ({"sack_player_id": "bad"}, {"sack": "NA"}, {"sack": "0"},
                        {"interception": "1", "interception_player_id": "00-0000003"},
                        {"half_sack_1_player_id": "00-0000002"}):
            with self.subTest(changes=changes):
                credits, reasons = event_credits({**row, **changes}, "sack")
                self.assertEqual(credits, {"sacks": {}, "interceptions": {}})
                self.assertTrue(reasons)
        self.assertEqual(event_credits(row, "aborted")[0]["sacks"], {})

    def test_events_outside_included_cohort_never_enter_totals(self):
        args = fixture()
        args[3].append({**args[3][0], "game_id": "2026_02_BUF_NYJ"})
        args[3].append({**args[3][0], "play_id": "99"})
        self.assertEqual(observed_explorer(*args)["audit"]["allocated_credits"]["sacks"], 2)

    def test_duplicate_and_missing_event_keys_fail_closed(self):
        for mutate in (lambda x: x.append(x[0]), lambda x: x.pop()):
            args = fixture()
            mutate(args[3])
            with self.assertRaises(ValueError):
                observed_explorer(*args)

    def test_entire_conflicted_chart_cell_withheld_not_partial(self):
        args = fixture()
        args[2]["issues"].append({"game_id": "2026_01_BUF_NYJ", "team_id": "NYJ", "role": "CB", "reason": "ambiguous_unit_role", "slot": None})
        data = observed_explorer(*args)
        self.assertNotIn("00-0000004", [p["player_id"] for p in data["players"]])
        self.assertEqual(next(c for c in data["coverage"]["role_cells"] if c["role"] == "CB")["blocked_cells"], 1)

    def test_no_name_guessing_or_roster_position_role_inference(self):
        for mutate in (lambda x: x.append({**x[0], "full_name": "Different Person"}),
                       lambda x: x[0].update(espn_id="999"),
                       lambda x: x[1].update(espn_id="11"), lambda x: x.pop(0)):
            args = fixture()
            mutate(args[4])
            data = observed_explorer(*args)
            p = next(p for p in data["players"] if p["player_id"] == "00-0000001")
            self.assertIsNone(p["name"])
            self.assertEqual(p["roles"], ["EDGE"])
        args = fixture()
        args[4][1]["position"] = "DE"
        self.assertEqual(next(p for p in observed_explorer(*args)["players"] if p["player_id"] == "00-0000002")["roles"], [])

    def test_negative_team_epa_retained_missing_epa_not_zero(self):
        args = fixture()
        data = observed_explorer(*args)
        self.assertEqual(next(g for g in data["team_games"] if g["team"] == "NYJ")["defense_epa"], -0.5)
        args[0]["plays"][0]["offense_epa"] = None
        data = observed_explorer(*args)
        group = next(g for g in data["team_games"] if g["team"] == "BUF")
        self.assertIsNone(group["defense_epa"])
        self.assertEqual((group["included_plays"], group["epa_observed_plays"]), (3, 2))

    def test_unresolved_completion_and_opposing_team_identity_rejected(self):
        args = fixture()
        args[1]["coverage_complete"] = False
        with self.assertRaises(ValueError):
            observed_explorer(*args)
        args = fixture()
        args[2]["assignments"][1].update(player_id="00-0000001")
        with self.assertRaisesRegex(ValueError, "both teams"):
            observed_explorer(*args)

    def test_trade_evidence_accumulates_without_claiming_stints_or_games_played(self):
        args = fixture()
        second = deepcopy(args[2]["assignments"][0])
        second.update(game_id="2026_02_BUF_NYJ", team_id="NYJ")
        args[2]["assignments"].append(second)
        args[1]["matched_games"].append({"game_id": second["game_id"], "week": 2, "home_team": "BUF", "away_team": "NYJ"})
        p = next(p for p in observed_explorer(*args)["players"] if p["player_id"] == second["player_id"])
        self.assertEqual(p["teams"], ["BUF", "NYJ"])
        self.assertEqual(p["chart_games"], 2)
        self.assertNotIn("games_played", p)
        self.assertIn("qualification", UNAVAILABLE)

    def test_export_retains_old_objects_and_rejects_corrupted_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, out = SnapshotStore(Path(tmp)/"store"), Path(tmp)/"public"
            p = payload()
            rid, report = save_explorer(store, p)
            export_explorer(store, rid, out)
            self.assertEqual(json.loads((out/"latest.json").read_text())["snapshot_id"], report["object"])
            self.assertEqual((out/(report["object"]+".json")).read_bytes(), json_bytes(p))
            p["scope"] += " Corrected."
            second, report2 = save_explorer(store, p)
            export_explorer(store, second, out)
            self.assertTrue((out/(report["object"]+".json")).exists())
            (out/(report2["object"]+".json")).write_text("corrupt")
            with self.assertRaises(ValueError):
                export_explorer(store, second, out)
            self.assertEqual(json.loads((out/"latest.json").read_text())["snapshot_id"], report2["object"])

    def test_replay_compares_exact_payload_and_export_failure_preserves_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, out = SnapshotStore(Path(tmp)/"store"), Path(tmp)/"public"
            p = payload()
            rid, _ = save_explorer(store, p)
            with patch("nfl_value.defense_explorer.build_explorer", return_value=p):
                self.assertEqual(replay_explorer(None, None, store, rid)[1], p)
            with patch("nfl_value.defense_explorer.build_explorer", return_value={**p, "season": 2025}):
                with self.assertRaisesRegex(ValueError, "differs"):
                    replay_explorer(None, None, store, rid)
            export_explorer(store, rid, out)
            before = (out/"latest.json").read_bytes()
            with patch("nfl_value.defense_explorer.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    export_explorer(store, rid, out)
            self.assertEqual(before, (out/"latest.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
