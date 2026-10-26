"""Synthetic weekly evidence and whole dependency-chain offline replay."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.benchmarks import CompletedTeamGame
from nfl_value.ingestion import SnapshotStore, capture, json_bytes
from nfl_value.offensive_inputs import COUNT_NAMES, build_offensive_inputs, save_offensive_inputs
from nfl_value.roster_cli import main
from nfl_value.roster_inputs import (
    build_roster_inputs,
    join_roster_evidence,
    replay_roster_inputs,
    save_roster_inputs,
)
from nfl_value.source_audit import audit_csv
from nfl_value.sources import source_spec
from test_defense_inputs import REVISION, WHEN, Source, schedule
from test_ingestion import csv_gzip
from test_offensive_inputs import PASSER, RECEIVER, end_play, offensive_play


START = datetime(2025, 9, 7, 17, tzinfo=timezone.utc)
OBSERVED = datetime.fromisoformat(WHEN)


def roster(**changes):
    return {
        "season": "2025",
        "week": "1",
        "game_type": "REG",
        "team": "ATL",
        "gsis_id": PASSER,
        "espn_id": "1",
        "position": "QB",
        "depth_chart_position": "QB",
        "status": "ACT",
        "status_description_abbr": "A01",
        **changes,
    }


def team_game(week=1, team="ATL"):
    return CompletedTeamGame(
        f"2025_{week:02d}_{team}_TB", team, START + timedelta(weeks=week - 1), OBSERVED, "REG"
    )


def workload(player=PASSER, week=1, team="ATL"):
    counts = {
        k: int(k in {"dropbacks", "dropback_or_rush_plays", "on_ball_plays"}) for k in COUNT_NAMES
    }
    return {
        "player_id": player,
        "game_id": team_game(week, team).game_id,
        "team": team,
        "observed": counts,
        "context_outcome_complete": dict(counts),
    }


def join(rows, *, games=None, workloads=None):
    return join_roster_evidence(
        rows,
        season=2025,
        team_games=games if games is not None else [team_game()],
        season_teams=["ATL", "TB", "CAR"],
        workloads=workloads or [],
        retrieved_at=OBSERVED,
    )


class WeeklyRosterTests(unittest.TestCase):
    def audit(self, rows):
        return audit_csv(csv_gzip(rows), source_spec("weekly_rosters", 2025), observed_at=WHEN)

    def test_source_registry_and_schema_are_separate_from_annual_rosters(self):
        spec = source_spec("weekly_rosters", 2026)
        self.assertEqual(spec.filename, "roster_weekly_2026.csv.gz")
        self.assertEqual(spec.tag, "weekly_rosters")
        self.assertEqual(spec.license_id, "CC-BY-4.0")
        self.assertNotEqual(spec.schema_version, source_spec("rosters", 2026).schema_version)
        with self.assertRaisesRegex(ValueError, "2002"):
            source_spec("weekly_rosters", 2001)

    def test_invalid_season_week_type_team_duplicate_and_schema_fail(self):
        for changes in (
            {"season": "2026"},
            {"week": "0"},
            {"week": "19"},
            {"week": "1.0"},
            {"game_type": "PRE"},
            {"team": "Atlanta"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.audit([roster(**changes)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.audit([roster(), roster()])
        incomplete = roster()
        incomplete.pop("status")
        with self.assertRaisesRegex(ValueError, "required columns"):
            self.audit([incomplete])

    def test_missing_and_legacy_ids_remain_unlinked_and_coarse_positions_unresolved(self):
        rows = [
            roster(gsis_id="", position="DL", depth_chart_position="DE"),
            roster(gsis_id="legacy", espn_id="2", position="LB", depth_chart_position="OLB"),
        ]
        report = self.audit(rows)
        self.assertEqual(report["issue_counts"]["missing_gsis_id"], 1)
        self.assertEqual(report["issue_counts"]["noncanonical_gsis_id"], 1)
        evidence, _ = join(rows)
        self.assertEqual(evidence["player_games"], [])
        self.assertTrue(
            all(r["source_position_role"] is None for r in evidence["roster_observations"])
        )
        self.assertFalse(report["ranking_ready"])

    def test_statuses_and_zero_observations_do_not_invent_missed_games(self):
        for status in ("ACT", "RES", "CUT", "TRD", "DEV", "unknown"):
            with self.subTest(status=status):
                evidence, audit = join([roster(status=status)])
                row = evidence["player_games"][0]
                self.assertEqual(evidence["roster_observations"][0]["status"], status)
                self.assertFalse(row["observed_offensive_participation"])
                self.assertIsNone(row["offensive_opportunities"])
                self.assertFalse(evidence["qualification_denominator_complete"])
                self.assertFalse(evidence["roster_stints_verified"])
                self.assertEqual(audit["player_games_without_observed_offensive_participation"], 1)

    def test_exact_week_join_keeps_role_changes_and_never_fills_gaps_or_late_entry(self):
        rows = [roster(week="2", position="WR"), roster(week="4", position="TE")]
        evidence, audit = join(
            rows,
            games=[team_game(w) for w in range(1, 5)],
            workloads=[workload(week=w) for w in range(1, 5)],
        )
        self.assertEqual(
            [r["source_position_role"] for r in evidence["player_games"]], [None, "WR", None, "TE"]
        )
        self.assertEqual(audit["actor_issue_counts"]["missing_roster_record"], 2)
        self.assertEqual(audit["team_games_without_roster_rows"], 2)
        self.assertEqual(audit["actor_rows_with_resolved_role"], 2)

    def test_trade_and_bye_evidence_does_not_append_both_teams_entire_seasons(self):
        rows = [roster(), roster(week="2"), roster(week="3", team="CAR")]
        games = [team_game(1), team_game(3), team_game(1, "CAR"), team_game(3, "CAR")]
        evidence, _ = join(rows, games=games)
        self.assertEqual(
            [(r["week"], r["team"]) for r in evidence["player_games"]], [(1, "ATL"), (3, "CAR")]
        )
        self.assertFalse(evidence["qualification_denominator_complete"])

    def test_team_mismatch_dual_team_and_secondary_identity_conflicts_block_roles(self):
        cases = [
            ([roster(team="CAR")], "roster_team_mismatch"),
            ([roster(), roster(team="CAR")], "ambiguous_player_week"),
            ([roster(), roster(gsis_id=RECEIVER)], "conflicting_secondary_identity"),
        ]
        for rows, reason in cases:
            with self.subTest(reason=reason):
                evidence, _ = join(rows, workloads=[workload()])
                row = next(r for r in evidence["player_games"] if r["player_id"] == PASSER)
                self.assertIsNone(row["source_position_role"])
                self.assertIn(reason, row["issues"])

    def test_offensive_team_conflict_is_not_resolved_by_roster_agreement(self):
        game = team_game()
        other = {**workload(), "team": "TB"}
        evidence, audit = join(
            [roster()], games=[game, replace(game, team_id="TB")], workloads=[workload(), other]
        )
        self.assertTrue(all(r["source_position_role"] is None for r in evidence["player_games"]))
        self.assertEqual(audit["actor_issue_counts"]["offensive_player_game_team_conflict"], 2)

    def test_opaque_defensive_roles_and_postseason_rows_cannot_supply_regular_season_role(self):
        rows = [
            roster(position="DB", depth_chart_position="CB"),
            roster(game_type="POST", position="WR"),
        ]
        evidence, audit = join(rows, workloads=[workload()])
        self.assertIsNone(evidence["player_games"][0]["source_position_role"])
        self.assertEqual(audit["actor_issue_counts"], {"primary_position_unreviewed": 1})

    def test_order_independence_no_epa_allocation_and_source_availability_are_explicit(self):
        rows = [roster(), roster(gsis_id=RECEIVER, espn_id="2", position="WR")]
        counts = [workload(), workload(RECEIVER)]
        evidence, audit = join(rows, workloads=counts)
        self.assertEqual(
            (evidence, audit), join(list(reversed(rows)), workloads=list(reversed(counts)))
        )
        self.assertNotIn("epa", json.dumps(evidence))
        self.assertEqual(
            evidence["player_games"][0]["offensive_opportunities"]["observed"]["targets"], 0
        )
        self.assertEqual(audit["team_games_with_retrospective_roster_retrieval"], 1)
        self.assertTrue(
            all(not r["roster_retrieved_before_kickoff"] for r in evidence["player_games"])
        )
        self.assertFalse(evidence["ranking_ready"])

    def test_missing_roster_status_blocks_role_and_bad_count_schema_fails(self):
        evidence, audit = join([roster(status="")], workloads=[workload()])
        self.assertIsNone(evidence["player_games"][0]["source_position_role"])
        self.assertEqual(audit["actor_issue_counts"], {"missing_roster_status": 1})
        item = workload()
        item["context_outcome_complete"].pop("targets")
        with self.assertRaisesRegex(ValueError, "opportunity units"):
            join([roster()], workloads=[item])
        item = workload()
        item["context_outcome_complete"]["targets"] = 2
        with self.assertRaisesRegex(ValueError, "exceed"):
            join([roster()], workloads=[item])

    def test_bad_team_universe_duplicate_games_and_invalid_workloads_fail(self):
        with self.assertRaisesRegex(ValueError, "team outside"):
            join([roster(team="XYZ")])
        with self.assertRaisesRegex(ValueError, "duplicate completed"):
            join([roster()], games=[team_game(), team_game()])
        with self.assertRaisesRegex(ValueError, "duplicate offensive"):
            join([roster()], workloads=[workload(), workload()])
        with self.assertRaisesRegex(ValueError, "outside completed"):
            join([roster()], workloads=[workload(week=2)])
        for changes in ({"on_ball_plays": True}, {"on_ball_plays": 0}, {"targets": -1}):
            item = workload()
            item["observed"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                join([roster()], workloads=[item])


class RosterBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.raw, self.offensive, self.derived = (
            SnapshotStore(Path(temp.name) / name) for name in ("raw", "offensive", "derived")
        )
        self.ids = {}
        for kind, rows in (
            ("weekly_rosters", [roster(), roster(gsis_id=RECEIVER, espn_id="2", position="WR")]),
            ("schedules", [schedule()]),
            ("pbp", [offensive_play(), end_play()]),
        ):
            source = Source(kind, rows)
            self.ids[kind] = capture(
                self.raw, source.spec, code_revision=REVISION, fetch=source.fetch
            )[0]
        report, ledger = build_offensive_inputs(
            self.raw,
            schedules=self.ids["schedules"],
            pbp=self.ids["pbp"],
            cutoff=OBSERVED,
            code_revision=REVISION,
        )
        self.offensive_id, _ = save_offensive_inputs(self.offensive, report, ledger)

    def build(self, **changes):
        args = {
            "weekly_rosters": self.ids["weekly_rosters"],
            "offensive_report_id": self.offensive_id,
            "evidence_cutoff": OBSERVED + timedelta(days=1),
            "code_revision": REVISION,
            **changes,
        }
        return build_roster_inputs(self.raw, self.offensive, **args)

    def cli(self, *args):
        return main(
            [
                "--store",
                str(self.raw.root),
                "--offensive-store",
                str(self.offensive.root),
                "--output-store",
                str(self.derived.root),
                *args,
            ]
        )

    def test_build_and_replay_cli_verify_whole_archived_chain_without_network(self):
        with patch(
            "nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")
        ):
            with (
                patch("nfl_value.roster_cli.committed_revision", return_value=REVISION),
                redirect_stdout(io.StringIO()) as out,
            ):
                self.assertEqual(
                    self.cli(
                        "build",
                        "--weekly-rosters",
                        self.ids["weekly_rosters"],
                        "--offensive-report-id",
                        self.offensive_id,
                        "--evidence-cutoff",
                        (OBSERVED + timedelta(days=1)).isoformat(),
                    ),
                    0,
                )
            rid = json.loads(out.getvalue())["report_id"]
            report = replay_roster_inputs(self.raw, self.offensive, self.derived, rid)
            self.assertNotEqual(report["game_cohort_cutoff"], report["evidence_cutoff"])
            self.assertEqual(report["audit"]["actor_role_counts"], {"QB": 1, "WR": 1})
            self.assertFalse(report["ranking_ready"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(self.cli("replay", rid), 0)

    def test_wrong_kind_cutoff_revision_and_season_fail(self):
        for changes, message in (
            ({"weekly_rosters": self.ids["pbp"]}, "source kind"),
            ({"evidence_cutoff": OBSERVED - timedelta(days=1)}, "later than"),
            ({"code_revision": "dirty"}, "revision"),
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                self.build(**changes)
        from test_ingestion import FakeSource

        source = FakeSource(csv_gzip([roster(season="2026")]), "weekly_rosters")
        rid = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]
        with self.assertRaisesRegex(ValueError, "same season"):
            self.build(weekly_rosters=rid)

    def test_changed_report_evidence_and_corrupt_dependency_cannot_replay(self):
        report, evidence = self.build()
        _, saved = save_roster_inputs(self.derived, report, evidence)
        changes = [{**saved, "ranking_ready": True}, {**saved, "report_version": True}]
        altered = deepcopy(evidence)
        altered["player_games"][0]["source_position_role"] = "RB"
        changes.append({**saved, "objects": {"evidence": self.derived.put(json_bytes(altered))}})
        for changed in changes:
            rid = self.derived.put(json_bytes(changed), manifest=True)
            with self.subTest(changed=changed["objects"]), self.assertRaises(ValueError):
                replay_roster_inputs(self.raw, self.offensive, self.derived, rid)
        path = self.raw.root / "manifests" / f"{self.ids['weekly_rosters']}.json"
        path.write_text("{}\n")
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(
                self.cli("replay", self.derived.put(json_bytes(saved), manifest=True)), 1
            )
        self.assertIn("SHA-256", error.getvalue())


if __name__ == "__main__":
    unittest.main()
