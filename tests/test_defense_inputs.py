"""Synthetic fixtures only; live FTN evidence is a separate recorded audit."""

from contextlib import redirect_stdout
import csv
from datetime import datetime
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.defense_cli import main
from nfl_value.defense_inputs import build_defense_inputs, paired_cohort, replay_defense_inputs, save_defense_inputs
from nfl_value.ingestion import Download, SnapshotStore, capture, json_bytes, replay, sha256
from nfl_value.participation import inspect_lineup
from nfl_value.source_audit import audit_csv
from nfl_value.sources import source_spec


WHEN = "2026-10-21T23:32:30+00:00"
REVISION = "a" * 40
GAME = "2025_01_ATL_TB"
AWAY = [f"00-{i:07d}" for i in range(1, 12)]
HOME = [f"00-{i:07d}" for i in range(12, 23)]


def part(**changes):
    row = {"nflverse_game_id": GAME, "play_id": "1", "possession_team": "ATL",
           "offense_players": ";".join(AWAY), "defense_players": ";".join(HOME),
           "players_on_play": ";".join(AWAY + HOME), "n_offense": "11", "n_defense": "11"}
    return {**row, **changes}


def play(**changes):
    row = {"game_id": GAME, "play_id": "1", "season": "2025", "season_type": "REG", "week": "1",
           "play_type": "pass", "play_type_nfl": "PASS", "posteam": "ATL", "defteam": "TB", "epa": "1.5",
           "down": "1", "ydstogo": "10", "yardline_100": "75", "game_seconds_remaining": "3500", "qtr": "1", "quarter_seconds_remaining": "800",
           "score_differential": "0", "qb_kneel": "0", "qb_spike": "0", "two_point_attempt": "0",
           "home_team": "TB", "away_team": "ATL", "total_home_score": "7", "total_away_score": "3"}
    return {**row, **changes}


def schedule():
    return {"game_id": GAME, "season": "2025", "game_type": "REG", "week": "1", "gameday": "2025-09-07",
            "gametime": "13:00", "away_team": "ATL", "home_team": "TB", "away_score": "3", "home_score": "7"}


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


class Source:
    def __init__(self, kind, rows):
        self.spec = source_spec(kind, 2025)
        self.raw = csv_bytes(rows)
        if self.spec.filename.endswith(".gz"):
            self.raw = gzip.compress(self.raw, mtime=0)
        self.license = (b"Attribution-ShareAlike 4.0 International" if kind == "participation" else b"Attribution 4.0 International") + b"\nSynthetic fixture"
        self.declaration = b"Synthetic declaration: https://creativecommons.org/licenses/by-sa/4.0/ FTN Data via nflverse 2023 onwards post-season games"
        self.metadata = {"tag_name": self.spec.tag, "assets": [{"id": 123, "name": self.spec.filename, "size": len(self.raw),
                         "digest": f"sha256:{sha256(self.raw)}", "updated_at": "2026-02-10T18:54:08Z", "browser_download_url": self.spec.download_url}]}

    def fetch(self, url, bound):
        data = {self.spec.metadata_url: json_bytes(self.metadata), self.spec.download_url: self.raw,
                self.spec.license_url: self.license, self.spec.license_declaration_url: self.declaration}[url]
        if len(data) > bound:
            raise ValueError("size limit")
        return Download(data, WHEN, {})


class ParticipationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = SnapshotStore(Path(temp.name))
        self.source = Source("participation", [part()])

    def capture(self):
        return capture(self.store, self.source.spec, code_revision=REVISION, fetch=self.source.fetch)

    def test_ftn_terms_and_declaration_are_archived_and_replayed_offline(self):
        rid, receipt = self.capture()
        self.assertEqual(receipt["manifest_version"], 2)
        self.assertEqual(receipt["source"]["license_id"], "CC-BY-SA-4.0")
        self.assertEqual(receipt["source"]["attribution"], "FTN Data via nflverse")
        self.assertEqual(self.store.read(receipt["objects"]["license_declaration"]), self.source.declaration)
        with patch("nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")):
            self.assertEqual(replay(self.store, rid), receipt)
        self.assertEqual(receipt["audit"]["valid_lineup_rows"], 1)

    def test_generic_license_cannot_silently_replace_ftn_terms(self):
        self.source.license = b"Attribution 4.0 International"
        with self.assertRaisesRegex(ValueError, "license changed"):
            self.capture()
        self.assertFalse((self.store.root / "manifests").exists())

    def test_changed_or_missing_source_declaration_blocks_capture(self):
        self.source.declaration = b"All rights reserved"
        with self.assertRaisesRegex(ValueError, "declaration changed"):
            self.capture()
        self.assertFalse((self.store.root / "manifests").exists())

    def test_declaration_integrity_policy_and_version_are_checked_on_replay(self):
        _, receipt = self.capture()
        cases = [{**receipt, "manifest_version": 1}, {**receipt, "license_declaration_url": "https://example.com"},
                 {**receipt, "objects": {**receipt["objects"], "license_declaration": self.store.put(b"changed")}},
                 {**receipt, "retrieval": {**receipt["retrieval"], "license_declaration": "2026-01-01T00:00:00Z"}}]
        for changed in cases:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                replay(self.store, self.store.put(json_bytes(changed), manifest=True))

    def test_unreviewed_historical_and_current_seasons_fail_closed(self):
        for year in (2022, 2026):
            with self.subTest(year=year), self.assertRaises(ValueError):
                source_spec("participation", year)

    def test_bad_lineup_is_preserved_in_audit_without_inventing_ids(self):
        self.source = Source("participation", [part(defense_players=";".join(HOME[:-1] + ["NA"]))])
        _, receipt = self.capture()
        self.assertEqual(receipt["audit"]["rows"], 1)
        self.assertEqual(receipt["audit"]["valid_lineup_rows"], 0)
        self.assertEqual(receipt["audit"]["lineup_issue_counts"]["defense_players:noncanonical_or_missing_id"], 1)

    def test_duplicate_keys_and_invalid_game_identity_fail(self):
        for rows in ([part(), part()], [part(nflverse_game_id="2024_01_ATL_TB")], [part(possession_team="NYJ")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                audit_csv(csv_bytes(rows), self.source.spec, observed_at=WHEN)

    def test_lineup_count_identity_overlap_and_union_checks(self):
        cases = [part(n_defense="10"), part(defense_players=";".join(HOME[:-1])),
                 part(defense_players=";".join(HOME[:-1] + [HOME[0]])),
                 part(defense_players=";".join(HOME[:-1] + [AWAY[0]])),
                 part(players_on_play=";".join(AWAY + HOME[:-1] + ["00-9999999"]))]
        for row in cases:
            with self.subTest(row=row):
                self.assertTrue(inspect_lineup(row)[1])
        self.assertEqual(inspect_lineup(part())[1], [])


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.plays = [play(), play(play_id="2", posteam="TB", defteam="ATL", epa="-0.5", play_type="run")]
        self.parts = [part(), part(play_id="2", possession_team="TB", offense_players=";".join(HOME), defense_players=";".join(AWAY))]
        self.games = [{"game_id": GAME, "week": 1, "scheduled_kickoff": "2025-09-07T17:00:00+00:00", "away_team": "ATL", "home_team": "TB"}]

    def pair(self):
        return paired_cohort(iter(self.plays), iter(self.parts), season=2025, completed_games=self.games)

    def test_views_share_exact_cohort_and_signed_team_outcome(self):
        rich, reduced, audit = self.pair()
        self.assertEqual(audit["paired_games"], 1)
        self.assertEqual(rich["cohort_sha256"], reduced["cohort_sha256"])
        self.assertEqual(rich["cohort_plays"], 2)
        self.assertEqual([p["defense_epa"] for p in rich["plays"]], [-1.5, 0.5])
        self.assertEqual(sum(g["defense_epa_total"] for g in reduced["team_games"]), -1)
        for team_game in reduced["team_games"]:
            self.assertEqual(sum(p["fraction"] for p in team_game["defender_workloads"]), 11)
            self.assertEqual(team_game["opportunities"], 1)

    def test_degraded_view_contains_no_play_lineups_pressure_or_offense_player_ids(self):
        _, reduced, _ = self.pair()
        encoded = json.dumps(reduced)
        for forbidden in ('"play_id"', '"plays"', '"offense_players"', '"defense_players"', '"was_pressure"', '"route"', '"time_to_throw"'):
            self.assertNotIn(forbidden, encoded)

    def test_missing_participation_blocks_whole_game_in_both_views(self):
        self.parts.pop()
        rich, reduced, audit = self.pair()
        self.assertEqual(audit["rejection_counts"]["missing_participation"], 1)
        self.assertEqual(audit["matched_plays_removed_by_whole_game_gate"], 1)
        self.assertEqual(rich["plays"], [])
        self.assertEqual(reduced["team_games"], [])
        self.assertFalse(audit["games"][GAME]["paired"])

    def test_wrong_possession_or_pbp_team_or_lineup_blocks_game(self):
        for field, value in (("possession_team", "TB"), ("n_defense", "10"), ("defense_players", "")):
            with self.subTest(field=field):
                self.parts[0] = part(**{field: value})
                self.assertEqual(self.pair()[2]["paired_games"], 0)
        self.parts[0] = part()
        self.plays[0] = play(defteam="NYJ")
        self.assertIn("pbp_team_mismatch", self.pair()[2]["rejection_counts"])

    def test_missing_or_invalid_preplay_context_or_target_blocks_game(self):
        for field, value in (("down", "NA"), ("ydstogo", "-1"), ("qtr", "6"), ("epa", "nan"),
                             ("game_seconds_remaining", "inf"), ("qb_spike", "")):
            with self.subTest(field=field):
                self.plays[0] = play(**{field: value})
                self.assertEqual(self.pair()[2]["paired_games"], 0)

    def test_sack_and_scramble_are_single_pass_or_run_records(self):
        self.plays[0]["play_type_nfl"] = "SACK"
        self.plays[1]["play_type_nfl"] = "RUSH"
        self.assertEqual(self.pair()[2]["paired_plays"], 2)

    def test_excluded_events_and_postseason_cannot_enter_or_block_regular_cohort(self):
        self.plays += [play(play_id="3", qb_kneel="1"), play(play_id="4", qb_spike="1"),
                       play(play_id="5", two_point_attempt="1"), play(play_id="6", play_type="no_play"),
                       play(game_id="2025_19_ATL_TB", season_type="POST")]
        self.parts.append(part(play_id="999"))
        _, _, audit = self.pair()
        self.assertEqual(audit["paired_plays"], 2)
        self.assertEqual(audit["excluded_pbp_counts"]["kneel_spike_or_two_point"], 3)
        self.assertEqual(audit["excluded_pbp_counts"]["postseason"], 1)
        self.assertEqual(audit["participation_without_pbp"], [{"game_id": GAME, "play_id": 999}])

    def test_duplicate_keys_are_rejected_in_either_feed(self):
        self.plays.append(play())
        with self.assertRaisesRegex(ValueError, "duplicate PBP"):
            self.pair()
        self.plays.pop()
        self.parts.append(part())
        with self.assertRaisesRegex(ValueError, "duplicate participation"):
            self.pair()

    def test_opportunities_are_team_specific_and_fraction_uses_accepted_play_denominator(self):
        self.plays.append(play(play_id="3", epa="-1"))
        new_defense = HOME[:-1] + ["00-0000023"]
        self.parts.append(part(play_id="3", defense_players=";".join(new_defense), players_on_play=";".join(AWAY + new_defense)))
        _, reduced, _ = self.pair()
        tb = next(g for g in reduced["team_games"] if g["defense_team"] == "TB")
        self.assertEqual(tb["opportunities"], 2)
        self.assertEqual(tb["defense_epa_total"], -0.5)
        workload = {p["player_id"]: p["fraction"] for p in tb["defender_workloads"]}
        self.assertEqual(workload[HOME[-1]], 0.5)
        self.assertEqual(workload["00-0000023"], 0.5)

    def test_reordering_inputs_preserves_outputs(self):
        first = self.pair()
        self.plays.reverse()
        self.parts.reverse()
        self.assertEqual(first, self.pair())

    def test_single_sided_or_unreconciled_game_cannot_be_paired(self):
        self.plays.pop()
        self.assertEqual(self.pair()[2]["paired_games"], 0)
        self.games = []
        self.assertEqual(self.pair()[2]["excluded_pbp_counts"]["game_not_reconciled_complete"], 1)


class BundleTests(unittest.TestCase):
    def setUp(self):
        fixture = CohortTests()
        fixture.setUp()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.raw = SnapshotStore(Path(temp.name) / "raw")
        self.derived = SnapshotStore(Path(temp.name) / "derived")
        self.ids = {}
        fixtures = {"pbp": fixture.plays + [play(play_id="99", play_type="", play_type_nfl="END_GAME", epa="", qtr="4", quarter_seconds_remaining="0")],
                    "participation": fixture.parts, "schedules": [schedule()]}
        for kind, rows in fixtures.items():
            source = Source(kind, rows)
            self.ids[kind] = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]

    def build(self, **changes):
        return build_defense_inputs(self.raw, **{**self.ids, **changes}, cutoff=datetime.fromisoformat(WHEN), code_revision=REVISION)

    def test_bundle_replays_offline_and_cli_exposes_no_ranking(self):
        report, rich, reduced = self.build()
        self.assertFalse(report["experiment_run"])
        self.assertEqual(report["historical_availability"], "retrospectively_retrieved_postseason_participation")
        self.assertEqual(rich["provenance"]["derived_participation_license"], "CC-BY-SA-4.0")
        rid, saved = save_defense_inputs(self.derived, report, rich, reduced)
        with patch("nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")):
            self.assertEqual(replay_defense_inputs(self.raw, self.derived, rid), saved)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--store", str(self.raw.root), "--output-store", str(self.derived.root), "replay", rid]), 0)
            self.assertFalse(json.loads(output.getvalue())["ranking_ready"])

    def test_missing_completion_evidence_is_visible_and_produces_no_pairs(self):
        source = Source("pbp", [play()])
        rid = capture(self.raw, source.spec, code_revision=REVISION, fetch=source.fetch)[0]
        report, rich, _ = self.build(pbp=rid)
        self.assertFalse(report["game_coverage"]["coverage_complete"])
        self.assertEqual(rich["plays"], [])

    def test_kind_and_future_receipts_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "source kind"):
            self.build(pbp=self.ids["participation"])
        with self.assertRaisesRegex(ValueError, "after cutoff"):
            build_defense_inputs(self.raw, **self.ids, cutoff=datetime.fromisoformat("2026-10-20T00:00:00Z"), code_revision=REVISION)

    def test_tampered_derived_object_or_report_does_not_replay(self):
        report, rich, reduced = self.build()
        _, saved = save_defense_inputs(self.derived, report, rich, reduced)
        changed = {**saved, "objects": {**saved["objects"], "rich": self.derived.put(json_bytes({**rich, "plays": []}))}}
        bad_id = self.derived.put(json_bytes(changed), manifest=True)
        with self.assertRaisesRegex(ValueError, "object replay differs"):
            replay_defense_inputs(self.raw, self.derived, bad_id)
        changed = {**saved, "policy": "silently changed"}
        bad_id = self.derived.put(json_bytes(changed), manifest=True)
        with self.assertRaisesRegex(ValueError, "report replay differs"):
            replay_defense_inputs(self.raw, self.derived, bad_id)


if __name__ == "__main__":
    unittest.main()
