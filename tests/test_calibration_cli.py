"""Network-blocked calibration replay through real archived contrast reconstruction."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import unittest
from unittest.mock import patch

from nfl_value import calibration_cli, contrast_cli
from nfl_value.baseline_cli import save
from nfl_value.ingestion import SnapshotStore, json_bytes
import test_contrast_cli as archives
from test_calibration import plan


class CalibrationCliTests(unittest.TestCase):
    def setUp(self):
        # Synthetic archives with network blockers; only source capture/replay
        # boundaries are stubbed. Contrast construction and replay are real.
        archives.ContrastCliTests.setUp(self)
        upstream = archives.ContrastCliTests.run_experiment(self)
        self.contrasts = self.output
        self.cid, self.upstream = save(self.contrasts, *upstream, code_revision="a" * 40)
        self.output = SnapshotStore(self.root / "calibration")

    def run_experiment(self, **changes):
        args = {"contrast_report": self.cid, "plan": plan(), **changes}
        return calibration_cli.run(self.raw, self.offensive, self.rosters, self.contrasts, **args)

    def test_cli_build_replay_and_rehashed_tampering_preserve_original(self):
        arguments = []
        for name, store in (
            ("raw", self.raw),
            ("offensive", self.offensive),
            ("roster", self.rosters),
            ("contrast", self.contrasts),
            ("output", self.output),
        ):
            arguments += [f"--{name}-store", str(store.root)]
        plan_path = self.root / "calibration-plan.json"
        plan_path.write_bytes(json_bytes(plan()))

        def invoke(args, expected=0):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = calibration_cli.main(arguments + args)
            self.assertEqual(code, expected, err.getvalue())
            return json.loads(out.getvalue()) if not code else err.getvalue()

        with patch("nfl_value.calibration_cli.committed_revision", return_value="b" * 40):
            built = invoke(["build", "--contrast-report", self.cid, "--plan", str(plan_path)])
        rid = built["report_id"]
        self.assertFalse(built["ranking_ready"])
        self.assertEqual(invoke(["replay", rid]), built)
        original = self.output.read(rid, manifest=True)
        saved = json.loads(original)
        altered = deepcopy(saved)
        results = json.loads(self.output.read(saved["objects"]["predictions"]))
        key = "fixed_signal_game/penalty-1000"
        results[key]["players"][0]["intervals"]["conditional_gaussian"]["coverage"] = -1.0
        altered["objects"]["predictions"] = self.output.put(json_bytes(results))
        bad_id = self.output.put(json_bytes(altered), manifest=True)
        self.assertIn("coverage", invoke(["replay", bad_id], 1))
        for field, value in (
            ("experiment_version", True),
            ("ranking_ready", True),
            ("environment", {"numpy": "wrong", "scipy": "wrong"}),
        ):
            wrong = {**saved, field: value}
            invoke(["replay", self.output.put(json_bytes(wrong), manifest=True)], 1)
        self.assertEqual(self.output.read(rid, manifest=True), original)
        self.assertEqual(invoke(["replay", rid]), built)

    def test_corrupted_upstream_artifact_is_not_accepted_as_design(self):
        object_id = self.upstream["objects"]["models"]
        self.contrasts._path(object_id).write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
            self.run_experiment()

    def test_missing_window_and_changed_penalty_policy_fail(self):
        changed = plan()
        changed["windows"]["2025"] = 6
        with self.assertRaisesRegex(ValueError, "window absent"):
            self.run_experiment(plan=changed)
        changed = plan()
        changed["primary_actor_penalty"] = 10.0
        with self.assertRaisesRegex(ValueError, "preserve.*penalty"):
            self.run_experiment(plan=changed)

    def test_actual_outcome_change_does_not_generate_synthetic_truth_or_select_cohorts(self):
        before = self.run_experiment()
        inputs = json.loads(
            self.offensive.read(self.roster_report["offensive_report_id"], manifest=True)
        )
        ledger = json.loads(self.offensive.read(inputs["objects"]["ledger"]))
        for row in ledger["plays"]:
            row["offense_epa"] = row["offense_epa"] * 4 - 8
        inputs["objects"]["ledger"] = self.offensive.put(json_bytes(ledger))
        oid = self.offensive.put(json_bytes(inputs), manifest=True)
        roster = {**self.roster_report, "offensive_report_id": oid}
        rid = self.rosters.put(json_bytes(roster), manifest=True)
        upstream = contrast_cli.run(
            self.raw,
            self.offensive,
            self.rosters,
            roster_report=rid,
            depth_charts=self.depth_id,
            evidence_cutoff=self.upstream["evidence_cutoff"],
            plan=self.upstream["plan"],
        )
        cid, _ = save(self.contrasts, *upstream, code_revision="c" * 40)
        after = self.run_experiment(contrast_report=cid)
        self.assertEqual(before[2], after[2])
        self.assertNotEqual(before[1]["design_rows_sha256"], after[1]["design_rows_sha256"])

    def test_prefix_slice_excludes_later_outcomes_before_design_validation(self):
        changed = plan()
        changed["windows"]["2025"] = 1
        report, diagnostics, _ = self.run_experiment(plan=changed)
        self.assertEqual(report["summary"]["completed_games"], 1)
        self.assertEqual(report["summary"]["modeled_plays"], 80)
        self.assertEqual(report["week"], 1)
        self.assertTrue(all(p["unique_opportunities"] <= 40 for p in diagnostics["contrast_order"]))


if __name__ == "__main__":
    unittest.main()
