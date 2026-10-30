"""Offline archive orchestration and numerical replay of synthetic transitions."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value import transition_cli
from nfl_value.baseline_cli import save
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.transitions import PLAN
from test_transitions import fixture


class TransitionCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.raw, self.offensive, self.rosters, self.baseline, self.output = (
            SnapshotStore(self.root / n)
            for n in ("raw", "offensive", "rosters", "baseline", "output")
        )
        ledgers, evidence, games, report, models, predictions = fixture()
        self.roster_ids, inputs = {}, {}
        for label, key in (("historical_test", "historical"), ("transfer_test", "transfer")):
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
                    for g in games[label]
                    if g.team_id == "BUF"
                ],
            }
            oid = self.offensive.put(
                json_bytes(
                    {
                        "game_coverage": coverage,
                        "objects": {"ledger": self.offensive.put(json_bytes(ledgers[label]))},
                    }
                ),
                manifest=True,
            )
            inputs[key] = oid
            self.roster_ids[label] = self.rosters.put(
                json_bytes(
                    {
                        "offensive_report_id": oid,
                        "game_coverage_complete": True,
                        "objects": {"evidence": self.rosters.put(json_bytes(evidence[label]))},
                        "game_cohort_cutoff": "2026-10-22T23:50:38+00:00",
                        "evidence_cutoff": "2026-10-26T23:00:00+00:00",
                        "source_attribution": {"fixture": "synthetic retrospective evidence"},
                    }
                ),
                manifest=True,
            )
        self.bid, self.baseline_report = save(
            self.baseline,
            {**report, "input_reports": inputs},
            models,
            predictions,
            code_revision="a" * 40,
        )
        # Only upstream source/baseline replay boundaries are stubbed here.
        # Transition fitting diagnostics, hashes, joins and saved replay are real;
        # the real full-chain offline experiment is a separate bounded audit.
        for name, effect in (
            (
                "nfl_value.transition_cli.replay_experiment",
                lambda raw, inputs, store, rid: json.loads(store.read(rid, manifest=True)),
            ),
            (
                "nfl_value.transition_cli.replay_roster_inputs",
                lambda raw, inputs, store, rid: json.loads(store.read(rid, manifest=True)),
            ),
        ):
            p = patch(name, side_effect=effect)
            p.start()
            self.addCleanup(p.stop)
        for name in ("socket.socket.connect", "urllib.request.OpenerDirector.open"):
            p = patch(name, side_effect=AssertionError("offline test attempted network"))
            p.start()
            self.addCleanup(p.stop)

    def run_experiment(self, **changes):
        return transition_cli.run(
            self.raw,
            self.offensive,
            self.rosters,
            self.baseline,
            **{
                "baseline_report": self.bid,
                "roster_reports": self.roster_ids,
                "plan": deepcopy(PLAN),
                **changes,
            },
        )

    def test_cli_replays_and_rejects_rehashed_tampering_without_changing_original(self):
        args = []
        for name, store in (
            ("raw", self.raw),
            ("offensive", self.offensive),
            ("roster", self.rosters),
            ("baseline", self.baseline),
            ("output", self.output),
        ):
            args.extend([f"--{name}-store", str(store.root)])
        path = self.root / "plan.json"
        path.write_bytes(json_bytes(PLAN))

        def invoke(command, expected=0):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = transition_cli.main(args + command)
            self.assertEqual(code, expected, err.getvalue())
            return json.loads(out.getvalue()) if code == 0 else err.getvalue()

        with patch("nfl_value.transition_cli.committed_revision", return_value="b" * 40):
            built = invoke(
                [
                    "build",
                    "--baseline-report",
                    self.bid,
                    "--historical-roster-report",
                    self.roster_ids["historical_test"],
                    "--transfer-roster-report",
                    self.roster_ids["transfer_test"],
                    "--plan",
                    str(path),
                ]
            )
        rid = built["report_id"]
        original = self.output.read(rid, manifest=True)
        self.assertEqual(invoke(["replay", rid]), built)
        saved = json.loads(original)
        cases = json.loads(self.output.read(saved["objects"]["predictions"]))
        cases["transfer_test"]["cases"][0]["identity_swap_diagnostic"][
            "new_minus_prior_on_current_dropbacks_ep"
        ] += 1
        changed = {
            **saved,
            "objects": {**saved["objects"], "predictions": self.output.put(json_bytes(cases))},
        }
        self.assertIn(
            "numeric replay differs",
            invoke(["replay", self.output.put(json_bytes(changed), manifest=True)], 1),
        )
        for field, value in (
            ("ranking_ready", True),
            ("experiment_version", True),
            ("environment", {"numpy": "wrong", "scipy": "wrong"}),
            ("replay_tolerance", {"absolute": 1, "relative": 1}),
        ):
            with self.subTest(field=field):
                invoke(
                    ["replay", self.output.put(json_bytes({**saved, field: value}), manifest=True)],
                    1,
                )
        self.assertEqual(self.output.read(rid, manifest=True), original)
        self.assertEqual(invoke(["replay", rid]), built)

    def test_source_hash_mismatch_and_different_offensive_cohort_fail(self):
        roster = json.loads(self.rosters.read(self.roster_ids["transfer_test"], manifest=True))
        changed = {**roster, "offensive_report_id": "0" * 64}
        bad = self.rosters.put(json_bytes(changed), manifest=True)
        with self.assertRaisesRegex(ValueError, "offensive reports differ"):
            self.run_experiment(roster_reports={**self.roster_ids, "transfer_test": bad})
        self.rosters._path(roster["objects"]["evidence"]).write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
            self.run_experiment()

    def test_incomplete_source_coverage_fails_before_analysis(self):
        roster = json.loads(self.rosters.read(self.roster_ids["transfer_test"], manifest=True))
        bad = self.rosters.put(
            json_bytes({**roster, "game_coverage_complete": False}), manifest=True
        )
        with self.assertRaisesRegex(ValueError, "complete reconciled game coverage"):
            self.run_experiment(roster_reports={**self.roster_ids, "transfer_test": bad})

    def test_evidence_cutoff_does_not_promote_historical_availability_or_game_cutoff(self):
        report, _, _ = self.run_experiment()
        p = report["source_provenance"]["transfer_test"]
        self.assertFalse(p["historically_available_evidence_validated"])
        self.assertLess(p["game_cohort_cutoff"], p["evidence_cutoff"])
        self.assertFalse(report["ranking_ready"])
        self.assertFalse(report["individual_attribution_validated"])


if __name__ == "__main__":
    unittest.main()
