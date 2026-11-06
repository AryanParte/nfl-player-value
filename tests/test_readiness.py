"""Synthetic full-inventory source/candidate tests with real offline replay.

Future fixture dates deliberately share one day to keep the fixture small; this
is not an NFL schedule, source download, or attribution-validation experiment.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.ingestion import Download, SnapshotStore, capture, json_bytes
from nfl_value.readiness import POLICY, TEAMS, assess_sources, replay_readiness, save_readiness
from nfl_value.readiness_cli import main
from nfl_value.refresh_candidate import prepare_candidate, replay_candidate
from test_ingestion import FakeSource, REVISION, WHEN, csv_gzip, roster
from test_offensive_inputs import offensive_play
from test_pregame_inputs import chart, schedule


CUTOFF = datetime.fromisoformat(WHEN)
GAME = "2026_01_ATL_TB"


def full_schedule():
    # Seventeen rounds, each of 32 teams once per round, no duplicate game IDs.
    teams = ["ATL", *[t for t in TEAMS if t not in {"ATL", "TB"}], "TB"]
    rows = []
    for week in range(1, 18):
        for away, home in zip(teams[:16], reversed(teams[16:])):
            rows.append(
                schedule(
                    game_id=f"2026_{week:02d}_{away}_{home}",
                    week=str(week),
                    away_team=away,
                    home_team=home,
                    gameday="2026-11-15",
                    away_score="",
                    home_score="",
                )
            )
        teams = [teams[0], teams[-1], *teams[1:-1]]
    rows[0] = schedule()
    return rows


def event(**changes):
    return offensive_play(
        game_id=GAME,
        season="2026",
        total_away_score="10",
        interception="0",
        sack_player_id="",
        half_sack_1_player_id="",
        half_sack_2_player_id="",
        interception_player_id="",
        **changes,
    )


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.raw, self.inputs, self.explorers, self.candidates = (
            SnapshotStore(self.root / name) for name in ("raw", "inputs", "explorers", "candidates")
        )
        self.stores = self.raw, self.inputs, self.explorers, self.candidates
        self.rows = {
            "schedules": full_schedule(),
            "pbp": [
                event(),
                event(play_id="2", sack="1", play_type_nfl="SACK", epa="-2", receiver_player_id=""),
                event(
                    play_id="99",
                    play_type="",
                    play_type_nfl="END_GAME",
                    epa="",
                    qtr="4",
                    quarter_seconds_remaining="0",
                ),
            ],
            "depth_charts": [
                row
                for team in TEAMS
                for dt in ("2026-09-13T07:00:00Z", "2026-10-19T07:00:00Z")
                for row in chart(team, dt=dt, defense=16)
            ],
            "rosters": [
                roster(
                    team=team,
                    gsis_id=f"00-{i + 1:07d}",
                    espn_id=str(i + 1),
                    full_name=f"Synthetic {i}",
                )
                for i, team in enumerate(TEAMS)
            ],
        }
        self.ids = {kind: self.capture(kind) for kind in POLICY["required_sources"]}
        self.pointer = self.root / "public/latest.json"
        self.pointer.parent.mkdir()
        self.pointer.write_bytes(b"prior public pointer is never touched")

    def capture(self, kind, *, fetched=WHEN, updated="2026-10-19T19:00:00Z"):
        source = FakeSource(csv_gzip(self.rows[kind]), kind)
        source.metadata["assets"][0]["updated_at"] = updated

        def fetch(url, maximum):
            value = source.fetch(url, maximum)
            return Download(value.body, fetched, value.headers)

        return capture(self.raw, source.spec, code_revision=REVISION, fetch=fetch)[0]

    def assess(self, ids=None, *, cutoff=CUTOFF):
        return assess_sources(
            self.raw, self.ids if ids is None else ids, cutoff=cutoff, code_revision=REVISION
        )

    def prepare(self, ids=None, **kwargs):
        return prepare_candidate(
            *self.stores,
            self.ids if ids is None else ids,
            cutoff=CUTOFF,
            code_revision=REVISION,
            **kwargs,
        )

    def test_complete_fresh_sources_preserve_separate_readiness_and_admission(self):
        report = self.assess()
        self.assertTrue(report["ready_for_explorer_build"])
        self.assertFalse(report["ranking_ready"])
        self.assertEqual(report["policy"], POLICY)
        self.assertEqual(report["schedule_inventory"]["regular_games"], 272)
        self.assertTrue(report["schedule_inventory"]["complete"])
        self.assertEqual({g["game_id"] for g in report["game_coverage"]["matched_games"]}, {GAME})
        self.assertEqual(len(report["game_coverage"]["not_due_game_ids"]), 271)
        self.assertEqual(set(report["latest_depth_by_team"]), set(TEAMS))

    def test_missing_source_is_not_zero_or_ready_and_no_model_build_occurs(self):
        for kind in self.ids:
            with (
                self.subTest(kind=kind),
                patch("nfl_value.refresh_candidate.build_offensive_inputs") as build,
            ):
                rid, report, candidate = self.prepare(
                    {k: v for k, v in self.ids.items() if k != kind}
                )
                self.assertIsNone(candidate)
                self.assertFalse(report["ready_for_explorer_build"])
                self.assertIn({"scope": kind, "reason": "missing_receipt"}, report["blockers"])
                self.assertEqual(replay_readiness(self.raw, self.candidates, rid), report)
                build.assert_not_called()

    def test_recent_retrieval_does_not_refresh_old_upstream_bytes(self):
        for kind, hours in (("schedules", 2), ("pbp", 96), ("rosters", 48), ("depth_charts", 48)):
            with self.subTest(kind=kind):
                exact = (CUTOFF - timedelta(hours=hours)).isoformat()
                rid = self.capture(kind, updated=exact)
                self.assertTrue(self.assess({**self.ids, kind: rid})["ready_for_explorer_build"])
                stale = (CUTOFF - timedelta(hours=hours, seconds=1)).isoformat()
                rid = self.capture(kind, updated=stale)
                report = self.assess({**self.ids, kind: rid})
                self.assertIn(
                    {"scope": kind, "reason": "upstream_update_too_old"}, report["blockers"]
                )
                self.assertEqual(report["source_checks"][kind]["retrieval_age_seconds"], 0)

    def test_retrieval_age_bound_and_future_evidence_are_separate(self):
        for hours, seconds, blocked in ((6, 0, False), (6, 1, True)):
            fetched = (CUTOFF - timedelta(hours=hours, seconds=seconds)).isoformat()
            rid = self.capture("pbp", fetched=fetched, updated=fetched)
            report = self.assess({**self.ids, "pbp": rid})
            self.assertEqual(
                {"scope": "pbp", "reason": "retrieval_too_old"} in report["blockers"], blocked
            )
        with self.assertRaisesRegex(ValueError, "after.*cutoff"):
            self.assess(cutoff=CUTOFF - timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.assess(cutoff=CUTOFF.replace(tzinfo=None))

    def test_fresh_asset_cannot_hide_stale_or_missing_team_depth(self):
        self.rows["depth_charts"] = [
            r
            for r in self.rows["depth_charts"]
            if not (r["team"] == "TB" and r["dt"].startswith("2026-10"))
        ]
        rid = self.capture("depth_charts")
        report = self.assess({**self.ids, "depth_charts": rid})
        self.assertIn(
            {"scope": "depth_charts:TB", "reason": "team_snapshot_too_old"}, report["blockers"]
        )
        self.rows["depth_charts"] = [r for r in self.rows["depth_charts"] if r["team"] != "TB"]
        rid = self.capture("depth_charts")
        report = self.assess({**self.ids, "depth_charts": rid})
        self.assertIn(
            {"scope": "depth_charts:TB", "reason": "missing_team_snapshot"}, report["blockers"]
        )

    def test_partial_schedule_and_roster_team_universes_fail_closed(self):
        self.rows["schedules"].pop()
        rid = self.capture("schedules")
        report = self.assess({**self.ids, "schedules": rid})
        self.assertTrue(report["game_coverage"]["coverage_complete"])
        self.assertFalse(report["ready_for_explorer_build"])
        self.assertIn(
            {"scope": "schedules", "reason": "regular_season_inventory_incomplete"},
            report["blockers"],
        )
        self.rows["rosters"].pop()
        rid = self.capture("rosters")
        self.assertIn(
            {"scope": "rosters", "reason": "team_universe_incomplete"},
            self.assess({**self.ids, "rosters": rid})["blockers"],
        )

    def test_duplicate_team_week_is_blocked_even_when_counts_match(self):
        row = self.rows["schedules"][-1]
        row["week"] = "18"
        row["game_id"] = f"2026_18_{row['away_team']}_{row['home_team']}"
        # Give one team another game in week 18 by moving a different matchup.
        other = next(
            r
            for r in self.rows["schedules"]
            if r["week"] == "16" and row["home_team"] in (r["home_team"], r["away_team"])
        )
        other["week"] = "18"
        other["game_id"] = f"2026_18_{other['away_team']}_{other['home_team']}"
        rid = self.capture("schedules")
        report = self.assess({**self.ids, "schedules": rid})
        self.assertEqual(report["schedule_inventory"]["regular_games"], 272)
        self.assertTrue(report["schedule_inventory"]["duplicate_team_weeks"])
        self.assertFalse(report["ready_for_explorer_build"])

    def test_started_missing_game_is_not_dropped_from_expected_coverage(self):
        row = self.rows["schedules"][1]
        row["gameday"] = "2026-10-19"
        row["gametime"] = "13:00"
        rid = self.capture("schedules")
        report = self.assess({**self.ids, "schedules": rid})
        self.assertFalse(report["ready_for_explorer_build"])
        self.assertEqual(
            report["game_coverage"]["unresolved_games"],
            [{"game_id": row["game_id"], "reason": "missing_pbp"}],
        )

    def test_scores_without_terminal_marker_do_not_mean_completed(self):
        self.rows["pbp"].pop()
        rid = self.capture("pbp")
        report = self.assess({**self.ids, "pbp": rid})
        self.assertFalse(report["ready_for_explorer_build"])
        self.assertEqual(report["game_coverage"]["matched_games"], [])

    def test_corrupt_raw_wrong_source_and_clock_schema_drift_are_errors(self):
        with self.assertRaisesRegex(ValueError, "kind/season"):
            self.assess({**self.ids, "pbp": self.ids["rosters"]})
        with self.assertRaisesRegex(ValueError, "four reviewed"):
            self.assess({**self.ids, "participation": "a" * 64})
        for row in self.rows["pbp"]:
            row.pop("qtr")
        bad = self.capture("pbp")
        with self.assertRaisesRegex(ValueError, "columns"):
            self.assess({**self.ids, "pbp": bad})
        original = json.loads(self.raw.read(self.ids["pbp"], manifest=True))
        (self.raw.root / "objects" / original["objects"]["raw"]).write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.assess()

    def test_readiness_replay_is_frozen_and_detects_rehashed_policy_changes(self):
        report = self.assess()
        rid = save_readiness(self.candidates, report)
        with patch("socket.socket", side_effect=AssertionError("network")):
            self.assertEqual(replay_readiness(self.raw, self.candidates, rid), report)
        # Freshness expires without altering the historical decision.
        self.assertFalse(self.assess(cutoff=CUTOFF + timedelta(days=1))["ready_for_explorer_build"])
        for change in (
            lambda r: r["policy"].update(version="invented"),
            lambda r: r.update(ready_for_explorer_build=1),
            lambda r: r.update(ranking_ready=True),
        ):
            bad = deepcopy(report)
            change(bad)
            bad_id = self.candidates.put(json_bytes(bad), manifest=True)
            with self.assertRaisesRegex(ValueError, "replay differs"):
                replay_readiness(self.raw, self.candidates, bad_id)

    def test_real_candidate_chain_replays_offline_and_does_not_publish(self):
        rid, report, cid = self.prepare()
        self.assertTrue(report["ready_for_explorer_build"])
        with patch("socket.socket", side_effect=AssertionError("network")):
            candidate = replay_candidate(*self.stores, cid)
        self.assertEqual(candidate["readiness_report"], rid)
        self.assertFalse(candidate["published"])
        self.assertFalse(candidate["ranking_ready"])
        self.assertEqual(candidate["coverage"]["completed_games"], 1)
        data = json.loads(self.explorers.read(candidate["explorer_snapshot"]))
        self.assertTrue(
            all(p["cavaa"] is None and p["defensive_snaps"] is None for p in data["players"])
        )
        offensive = json.loads(self.inputs.read(candidate["offensive_report"], manifest=True))
        self.assertEqual(offensive["opportunity_audit"]["observed_offense_epa_sum"], -0.5)
        self.assertEqual(self.pointer.read_bytes(), b"prior public pointer is never touched")

    def test_source_corrections_create_new_candidate_and_preserve_old_replay(self):
        _, _, first_id = self.prepare()
        first = replay_candidate(*self.stores, first_id)
        self.rows["pbp"][0]["epa"] = "1"
        corrected = self.capture("pbp")
        _, _, next_id = self.prepare(
            {**self.ids, "pbp": corrected}, previous_explorer=first["explorer_report"]
        )
        self.assertNotEqual(next_id, first_id)
        second = replay_candidate(*self.stores, next_id)
        self.assertEqual(second["previous_explorer"], first["explorer_report"])
        self.assertNotEqual(second["explorer_snapshot"], first["explorer_snapshot"])
        self.assertEqual(second["previous_comparison"]["added_game_ids"], [])
        self.assertEqual(
            second["previous_comparison"]["changed_existing_team_games"],
            [{"game_id": GAME, "team": "TB"}],
        )
        self.assertEqual(replay_candidate(*self.stores, first_id), first)
        self.assertEqual(self.pointer.read_bytes(), b"prior public pointer is never touched")

    def test_previous_game_removal_or_cutoff_regression_is_blocked(self):
        for changed in (
            {"cutoff": "2026-10-20T00:00:00+00:00", "team_games": []},
            {"cutoff": WHEN, "team_games": [{"game_id": "2026_01_BUF_NYJ"}]},
        ):
            previous = {"season": 2026, **changed}
            with patch("nfl_value.refresh_candidate.replay_explorer", return_value=({}, previous)):
                with self.assertRaisesRegex(ValueError, "regress|drops"):
                    self.prepare(previous_explorer="b" * 64)
        self.assertEqual(self.pointer.read_bytes(), b"prior public pointer is never touched")

    def test_build_failure_leaves_no_candidate_and_preserves_existing_pointer(self):
        with patch(
            "nfl_value.refresh_candidate.build_explorer",
            side_effect=ValueError("event identity mismatch"),
        ):
            with self.assertRaisesRegex(ValueError, "identity"):
                self.prepare()
        manifests = list((self.candidates.root / "manifests").glob("*.json"))
        self.assertEqual(len(manifests), 1)
        self.assertEqual(json.loads(manifests[0].read_bytes())["kind"], "explorer_source_readiness")
        self.assertEqual(self.pointer.read_bytes(), b"prior public pointer is never touched")

    def test_candidate_manifest_corruption_and_rehashed_substitution_fail(self):
        _, _, cid = self.prepare()
        good = replay_candidate(*self.stores, cid)
        for key, value in (
            ("cutoff", "2026-10-20T00:00:00+00:00"),
            ("published", True),
            ("explorer_snapshot", "f" * 64),
            ("readiness_policy_sha256", "f" * 64),
        ):
            bad = self.candidates.put(json_bytes({**good, key: value}), manifest=True)
            with self.assertRaisesRegex(ValueError, "replay differs"):
                replay_candidate(*self.stores, bad)
        (self.candidates.root / "manifests" / f"{cid}.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            replay_candidate(*self.stores, cid)

    def test_cli_missing_sources_has_blocked_exit_and_immutable_report(self):
        args = ["--candidate-store", str(self.candidates.root), "assess", "--cutoff", WHEN]
        output = StringIO()
        with (
            patch("nfl_value.readiness_cli.committed_revision", return_value=REVISION),
            redirect_stdout(output),
        ):
            self.assertEqual(main(args), 2)
        result = json.loads(output.getvalue())
        self.assertIsNone(result["candidate_id"])
        self.assertEqual(len(result["blockers"]), 4)
        with redirect_stdout(StringIO()):
            self.assertEqual(
                main(
                    [
                        "--candidate-store",
                        str(self.candidates.root),
                        "replay-readiness",
                        result["readiness_report"],
                    ]
                ),
                2,
            )
        with (
            redirect_stderr(StringIO()),
            patch(
                "nfl_value.readiness_cli.committed_revision", side_effect=ValueError("dirty source")
            ),
        ):
            self.assertEqual(main(args), 1)

    def test_cli_prepare_and_replay_do_not_claim_current_readiness(self):
        common = [
            "--raw-store",
            str(self.raw.root),
            "--input-store",
            str(self.inputs.root),
            "--explorer-store",
            str(self.explorers.root),
            "--candidate-store",
            str(self.candidates.root),
        ]
        args = common + ["prepare", "--cutoff", WHEN]
        for kind, rid in self.ids.items():
            args.extend(["--" + kind.replace("_", "-"), rid])
        out = StringIO()
        with (
            patch("nfl_value.readiness_cli.committed_revision", return_value=REVISION),
            redirect_stdout(out),
        ):
            self.assertEqual(main(args), 0)
        cid = json.loads(out.getvalue())["candidate_id"]
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(common + ["replay-candidate", cid]), 0)
        self.assertTrue(json.loads(out.getvalue())["verified_at_original_cutoff_only"])
        self.assertFalse(json.loads(out.getvalue())["published"])
