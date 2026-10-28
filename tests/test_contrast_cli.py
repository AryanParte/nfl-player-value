"""Real CLI/selector/fitting/replay on synthetic archives; only upstream replay is stubbed."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value import contrast_cli
from nfl_value.ingestion import SnapshotStore, json_bytes
from test_contrasts import CUTOFF, fixture, plan
from test_ingestion import csv_gzip


def read_report(_raw, _offensive, store, report_id):
    return json.loads(store.read(report_id, manifest=True))


class ContrastCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.raw, self.offensive, self.rosters, self.output = (
            SnapshotStore(self.root / name) for name in ("raw", "offensive", "rosters", "output")
        )
        for target in ("socket.socket.connect", "urllib.request.OpenerDirector.open"):
            blocker = patch(
                target, side_effect=AssertionError("offline integration cannot use network")
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        for target, replacement in (
            ("nfl_value.contrast_cli.replay_roster_inputs", read_report),
            (
                "nfl_value.contrast_cli.replay",
                lambda store, rid: json.loads(store.read(rid, manifest=True)),
            ),
        ):
            stub = patch(target, side_effect=replacement)
            stub.start()
            self.addCleanup(stub.stop)
        ledger, evidence, _, games = fixture()
        depth_rows = []
        for game in games:
            side = ("BUF", "NYJ").index(game.team_id)
            for slot, position, rank, player_number in (
                (9, "QB", 1, 1 + side),
                (11, "RB", 1, 5 + side),
                (10, "TE", 1, 7 + side),
                (1, "WR", 1, 3 + side),
                (2, "WR", 2, 9 + side),
                (8, "WR", 3, 11 + side),
            ):
                player = f"00-{player_number:07d}"
                depth_rows.append(
                    {
                        "dt": (game.kickoff - timedelta(days=1)).isoformat(),
                        "team": game.team_id,
                        "gsis_id": player,
                        "espn_id": str(player_number),
                        "pos_grp_id": "21",
                        "pos_grp": "3WR 1TE",
                        "pos_slot": str(slot),
                        "pos_rank": str(rank),
                        "pos_abb": position,
                    }
                )
                if player_number > 8:
                    evidence["player_games"].append(
                        {
                            "player_id": player,
                            "game_id": game.game_id,
                            "team": game.team_id,
                            "source_position_role": "WR",
                            "issues": [],
                            "observed_offensive_participation": False,
                            "offensive_opportunities": None,
                        }
                    )
        self.depth_rows = depth_rows
        schedule = self.raw.put(json_bytes({"audit": {"teams": ["BUF", "NYJ"]}}), manifest=True)
        coverage = {
            "coverage_complete": True,
            "matched_games": [
                {
                    "game_id": g.game_id,
                    "away_team": "BUF",
                    "home_team": "NYJ",
                    "scheduled_kickoff": g.kickoff.isoformat(),
                    "completion_observed_by": g.completed_at.isoformat(),
                }
                for g in games
                if g.team_id == "BUF"
            ],
        }
        upstream = {
            "objects": {"ledger": self.offensive.put(json_bytes(ledger))},
            "game_coverage": coverage,
            "source_receipts": {"schedules": schedule},
        }
        oid = self.offensive.put(json_bytes(upstream), manifest=True)
        self.roster_report = {
            "season": 2025,
            "evidence_cutoff": CUTOFF.isoformat(),
            "game_cohort_cutoff": CUTOFF.isoformat(),
            "game_coverage_complete": True,
            "source_attribution": {"pbp": "synthetic"},
            "audit": {"team_games_with_retrospective_roster_retrieval": 6},
            "offensive_report_id": oid,
            "objects": {"evidence": self.rosters.put(json_bytes(evidence))},
        }
        self.roster_id = self.rosters.put(json_bytes(self.roster_report), manifest=True)
        self.receipt = {
            "source": {
                "kind": "depth_charts",
                "season": 2025,
                "license_id": "synthetic",
                "license_url": "https://example.test/terms",
                "attribution": "synthetic",
            },
            "retrieval": {"data": CUTOFF.isoformat()},
            "objects": {"raw": self.raw.put(csv_gzip(depth_rows))},
        }
        self.depth_id = self.raw.put(json_bytes(self.receipt), manifest=True)

    def run_experiment(self, **changes):
        args = {
            "roster_report": self.roster_id,
            "depth_charts": self.depth_id,
            "evidence_cutoff": CUTOFF.isoformat(),
            "plan": plan(),
        }
        args.update(changes)
        return contrast_cli.run(self.raw, self.offensive, self.rosters, **args)

    def test_cli_build_replay_uses_archives_and_preserves_last_good_artifact(self):
        arguments = [
            "--raw-store",
            str(self.raw.root),
            "--offensive-store",
            str(self.offensive.root),
            "--roster-store",
            str(self.rosters.root),
            "--output-store",
            str(self.output.root),
        ]
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(json_bytes(plan()))

        def invoke(args, expected=0):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = contrast_cli.main(args)
            self.assertEqual(code, expected, err.getvalue())
            return json.loads(out.getvalue()) if not code else err.getvalue()

        with patch("nfl_value.contrast_cli.committed_revision", return_value="b" * 40):
            built = invoke(
                arguments
                + [
                    "build",
                    "--roster-report",
                    self.roster_id,
                    "--depth-charts",
                    self.depth_id,
                    "--evidence-cutoff",
                    CUTOFF.isoformat(),
                    "--plan",
                    str(plan_path),
                ]
            )
        rid = built["report_id"]
        self.assertEqual(invoke(arguments + ["replay", rid]), built)
        self.assertEqual(built["summary"]["3"]["benchmark_ready_roles"], ["QB", "RB", "TE", "WR"])
        saved = json.loads(self.output.read(rid, manifest=True))
        original_bytes = self.output.read(rid, manifest=True)
        result = json.loads(self.output.read(saved["objects"]["predictions"]))
        result["3"]["qualification"][0]["denominator_complete"] = False
        changed = deepcopy(saved)
        changed["objects"]["predictions"] = self.output.put(json_bytes(result))
        bad_id = self.output.put(json_bytes(changed), manifest=True)
        self.assertIn("denominator_complete", invoke(arguments + ["replay", bad_id], 1))
        self.assertEqual(self.output.read(rid, manifest=True), original_bytes)
        self.assertEqual(invoke(arguments + ["replay", rid]), built)

    def test_future_depth_identity_conflict_cannot_contaminate_earlier_selection(self):
        before = self.run_experiment()
        rows = deepcopy(self.depth_rows)
        latest = max(row["dt"] for row in rows)
        for row in rows:
            if row["dt"] == latest and row["gsis_id"] == "00-0000001":
                row["espn_id"] = "98765"
        changed = deepcopy(self.receipt)
        changed["objects"]["raw"] = self.raw.put(csv_gzip(rows))
        after = self.run_experiment(depth_charts=self.raw.put(json_bytes(changed), manifest=True))
        self.assertEqual(before[2]["1"], after[2]["1"])
        self.assertEqual(before[2]["2"], after[2]["2"])
        self.assertNotEqual(before[2]["3"], after[2]["3"])
        self.assertFalse(after[2]["3"]["cohorts"]["QB"]["benchmark_ready"])

    def test_wrong_sources_cutoffs_and_incomplete_coverage_fail(self):
        for changed_source in (
            {**self.receipt["source"], "kind": "pbp"},
            {**self.receipt["source"], "season": 2026},
        ):
            rid = self.raw.put(
                json_bytes({**self.receipt, "source": changed_source}), manifest=True
            )
            with self.assertRaisesRegex(ValueError, "kind/season"):
                self.run_experiment(depth_charts=rid)
        with self.assertRaisesRegex(ValueError, "after contrast cutoff"):
            self.run_experiment(evidence_cutoff=(CUTOFF - timedelta(seconds=1)).isoformat())
        rid = self.rosters.put(
            json_bytes({**self.roster_report, "game_coverage_complete": False}), manifest=True
        )
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.run_experiment(roster_report=rid)


if __name__ == "__main__":
    unittest.main()
