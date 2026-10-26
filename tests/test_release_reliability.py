"""Offline replay/export regressions; synthetic fixtures are not admission evidence.

Model integration begins at validated input reports. Only raw-source replay is
stubbed; CLI parsing, hashed reads/writes, solvers, selection and replay are real.
Existing ingestion/input suites exercise the raw receipt and reconciliation layer.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value import baseline_cli, defensive_model_cli, explorer_cli
from nfl_value.defense_explorer import export_explorer, save_explorer
from nfl_value.ingestion import SnapshotStore, json_bytes
from test_baseline import ledger, plan as offensive_plan
from test_defense_explorer import payload
from test_defensive_model import fixture, plan as defensive_plan


def read_validated_report(_raw, store, report_id):
    return json.loads(store.read(report_id, manifest=True))


class ReplayIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = SnapshotStore(self.root / "inputs")
        self.output = SnapshotStore(self.root / "output")
        # No live downloads, even if a future integration change adds a fetch.
        for target in ("socket.socket.connect", "urllib.request.OpenerDirector.open"):
            blocker = patch(
                target, side_effect=AssertionError("offline tests must not use the network")
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        for target in (
            "nfl_value.baseline_cli.replay_offensive_inputs",
            "nfl_value.defensive_model_cli.replay_offensive_inputs",
            "nfl_value.defensive_model_cli.replay_defense_inputs",
        ):
            boundary = patch(target, side_effect=read_validated_report)
            boundary.start()
            self.addCleanup(boundary.stop)

    def input_report(self, data):
        report = {
            "report_version": 2,
            "objects": {"ledger": self.inputs.put(json_bytes(data))},
            "game_coverage": {"coverage_complete": True},
            "opportunity_audit": {"player_game_team_conflicts": []},
            "code_revision": "a" * 40,
            "cutoff": "2026-10-22T00:00:00+00:00",
            "source_receipts": {"pbp": "b" * 64},
            "source_attribution": "Synthetic test fixture",
        }
        return self.inputs.put(json_bytes(report), manifest=True)

    def arguments(self):
        return [
            "--raw-store",
            str(self.root / "raw"),
            "--input-store",
            str(self.inputs.root),
            "--output-store",
            str(self.output.root),
        ]

    def invoke(self, module, args, expected=0):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = module.main(args)
        self.assertEqual(code, expected, stderr.getvalue())
        return json.loads(stdout.getvalue()) if code == 0 else stderr.getvalue()

    def build_offense(self):
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(json_bytes(offensive_plan()))
        args = self.arguments() + [
            "build",
            "--historical-report",
            self.input_report(ledger(2025)),
            "--transfer-report",
            self.input_report(ledger(2026)),
            "--plan",
            str(plan_path),
        ]
        with patch("nfl_value.baseline_cli.committed_revision", return_value="a" * 40):
            summary = self.invoke(baseline_cli, args)
        return summary["report_id"], json.loads(
            self.output.read(summary["report_id"], manifest=True)
        )

    def test_offense_cli_rebuilds_saved_models_and_predictions_offline(self):
        rid, saved = self.build_offense()
        replayed = self.invoke(baseline_cli, self.arguments() + ["replay", rid])
        self.assertEqual(replayed["objects"], saved["objects"])
        self.assertFalse(replayed["ranking_ready"])
        self.assertIn("source_provenance", saved)

    def test_valid_hash_is_insufficient_for_altered_coefficients_or_prediction_components(self):
        rid, saved = self.build_offense()
        for kind in ("models", "predictions"):
            with self.subTest(kind=kind):
                artifact = json.loads(self.output.read(saved["objects"][kind]))
                if kind == "models":
                    artifact["joint"]["coefficients"][0] += 1.0
                else:
                    # Keep predicted total and observed EPA intact: allocation must also replay.
                    artifact["historical_test"]["joint"][0]["components"]["target"] += 1.0
                changed = deepcopy(saved)
                changed["objects"][kind] = self.output.put(json_bytes(artifact))
                bad_id = self.output.put(json_bytes(changed), manifest=True)
                error = self.invoke(baseline_cli, self.arguments() + ["replay", bad_id], expected=1)
                self.assertIn("numeric replay differs", error)
        # Failed verification cannot invalidate the previous immutable experiment.
        self.invoke(baseline_cli, self.arguments() + ["replay", rid])

    def test_wrong_environment_tolerance_or_input_identity_cannot_replay(self):
        _, saved = self.build_offense()
        changes = (
            ("experiment_version", True, "unsupported"),
            ("environment", {**saved["environment"], "numpy": "0.0.0"}, "versions"),
            ("replay_tolerance", {"absolute": 1.0, "relative": 1.0}, "tolerance"),
            ("input_reports", {**saved["input_reports"], "transfer": "f" * 64}, "failed"),
        )
        for key, value, message in changes:
            with self.subTest(key=key):
                changed = {**saved, key: value}
                bad_id = self.output.put(json_bytes(changed), manifest=True)
                self.assertIn(
                    message,
                    self.invoke(baseline_cli, self.arguments() + ["replay", bad_id], expected=1),
                )

    def test_team_mapping_conflict_fails_before_model_fit_or_save(self):
        rid = self.input_report(ledger(2025))
        report = json.loads(self.inputs.read(rid, manifest=True))
        report["opportunity_audit"]["player_game_team_conflicts"] = ["synthetic-conflict"]
        rid = self.inputs.put(json_bytes(report), manifest=True)
        with patch("nfl_value.baseline_cli.experiment") as fit:
            with self.assertRaisesRegex(ValueError, "team conflict"):
                baseline_cli.run(
                    None,
                    self.inputs,
                    historical_report=rid,
                    transfer_report=rid,
                    plan=offensive_plan(),
                )
            fit.assert_not_called()
        self.assertFalse(self.output.root.exists())

    def test_defensive_cli_replays_fit_and_rejects_mismatched_provenance_envelope(self):
        rich, degraded, candidates = fixture()
        report = {
            "report_version": 2,
            "game_coverage": {"coverage_complete": True},
            "objects": {
                k: self.inputs.put(json_bytes(v))
                for k, v in (("rich", rich), ("degraded", degraded))
            },
            "derived_participation_license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "Synthetic test fixture",
        }
        defensive_id = self.inputs.put(json_bytes(report), manifest=True)
        candidate_id = self.input_report(candidates)
        args = self.arguments() + ["--candidate-store", str(self.inputs.root)]
        plan_path = self.root / "plan.json"
        plan_path.write_bytes(json_bytes(defensive_plan()))
        with patch("nfl_value.defensive_model_cli.committed_revision", return_value="a" * 40):
            summary = self.invoke(
                defensive_model_cli,
                args
                + [
                    "build",
                    "--defensive-report",
                    defensive_id,
                    "--candidate-report",
                    candidate_id,
                    "--plan",
                    str(plan_path),
                ],
            )
        rid = summary["report_id"]
        self.invoke(defensive_model_cli, args + ["replay", rid])
        saved = json.loads(self.output.read(rid, manifest=True))
        changed = {**saved, "experiment_version": True}
        bad_id = self.output.put(json_bytes(changed), manifest=True)
        self.assertIn(
            "unsupported defensive experiment",
            self.invoke(defensive_model_cli, args + ["replay", bad_id], expected=1),
        )
        envelope = json.loads(self.output.read(saved["objects"]["models"]))
        envelope["source_provenance"]["derivative_license"] = "MIT"
        changed = deepcopy(saved)
        changed["objects"]["models"] = self.output.put(json_bytes(envelope))
        bad_id = self.output.put(json_bytes(changed), manifest=True)
        self.assertIn(
            "derivative_license",
            self.invoke(defensive_model_cli, args + ["replay", bad_id], expected=1),
        )
        self.invoke(defensive_model_cli, args + ["replay", rid])

    def test_replay_comparison_rejects_nonfinite_values_even_when_matching(self):
        for value in (float("inf"), -float("inf"), float("nan")):
            for actual, expected in ((value, value), (value, 0.0), (0.0, value)):
                with self.subTest(actual=actual, expected=expected):
                    with self.assertRaisesRegex(ValueError, r"root.coefficient\[0\]"):
                        baseline_cli.assert_numerically_equal(
                            {"coefficient": [actual]}, {"coefficient": [expected]}
                        )


class ExportFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = SnapshotStore(self.root / "store")
        self.destination = self.root / "public"
        self.data = payload()
        self.rid, self.report = save_explorer(self.store, self.data)
        export_explorer(self.store, self.rid, self.destination)
        self.before = {p.name: p.read_bytes() for p in self.destination.iterdir()}

    def assert_previous_publication_unchanged(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.destination.iterdir()}, self.before)

    def test_direct_export_rejects_manifest_payload_disagreement_before_publication(self):
        for key, value in (
            ("code_revision", "b" * 40),
            ("offensive_report", "c" * 64),
            ("depth_charts", "d" * 64),
            ("rosters", "e" * 64),
            ("ranking_ready", True),
            ("report_version", True),
        ):
            with self.subTest(key=key):
                bad_id = self.store.put(json_bytes({**self.report, key: value}), manifest=True)
                with self.assertRaises(ValueError):
                    export_explorer(self.store, bad_id, self.destination)
                self.assert_previous_publication_unchanged()

    def test_invalid_export_schema_never_advances_pointer(self):
        for key, value in (
            ("schema_version", True),
            ("schema_version", 2),
            ("kind", "ranking"),
            ("ranking_ready", True),
        ):
            with self.subTest(key=key):
                bad_id, _ = save_explorer(self.store, {**self.data, key: value})
                with self.assertRaises(ValueError):
                    export_explorer(self.store, bad_id, self.destination)
                self.assert_previous_publication_unchanged()

    def test_write_flush_failure_keeps_old_pointer_and_removes_staging_file(self):
        new_id, _ = save_explorer(
            self.store, {**self.data, "scope": "Synthetic corrected evidence"}
        )
        with patch(
            "nfl_value.defense_explorer.os.fsync", side_effect=OSError("synthetic disk failure")
        ):
            with self.assertRaisesRegex(OSError, "disk failure"):
                export_explorer(self.store, new_id, self.destination)
        self.assert_previous_publication_unchanged()

    def test_archive_flush_failure_preserves_objects_and_receipts_without_partial_files(self):
        before = {p: p.read_bytes() for p in self.store.root.rglob("*") if p.is_file()}
        for manifest in (False, True):
            with self.subTest(manifest=manifest):
                with patch(
                    "nfl_value.ingestion.os.fsync", side_effect=OSError("synthetic archive failure")
                ):
                    with self.assertRaisesRegex(OSError, "archive failure"):
                        self.store.put(
                            json_bytes({"synthetic": "new receipt or object"}), manifest=manifest
                        )
                self.assertEqual(
                    {p: p.read_bytes() for p in self.store.root.rglob("*") if p.is_file()}, before
                )
                self.assertEqual(self.store.read(self.report["object"]), json_bytes(self.data))

    def test_cli_requires_successful_reconstruction_before_export(self):
        args = [
            "--output-store",
            str(self.store.root),
            "export",
            self.rid,
            "--destination",
            str(self.destination),
        ]
        # Snapshot hashes are valid but the reconstructed evidence disagrees.
        with (
            patch(
                "nfl_value.defense_explorer.build_explorer",
                return_value={**self.data, "season": 2025},
            ),
            patch("nfl_value.explorer_cli.export_explorer") as publish,
            redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(explorer_cli.main(args), 1)
            publish.assert_not_called()
            self.assertIn("replay differs", errors.getvalue())
        self.assert_previous_publication_unchanged()
        # The verified path still succeeds and exports the expected bytes.
        with (
            patch("nfl_value.defense_explorer.build_explorer", return_value=self.data),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(explorer_cli.main(args), 0)
        self.assert_previous_publication_unchanged()

    def test_cli_corrupted_manifest_fails_without_reconstruction_or_export(self):
        self.store._path(self.rid, manifest=True).write_text("corrupted")
        with (
            patch("nfl_value.defense_explorer.build_explorer") as build,
            redirect_stderr(io.StringIO()) as errors,
        ):
            result = explorer_cli.main(
                [
                    "--output-store",
                    str(self.store.root),
                    "export",
                    self.rid,
                    "--destination",
                    str(self.destination),
                ]
            )
            self.assertEqual(result, 1)
            self.assertIn("SHA-256", errors.getvalue())
            build.assert_not_called()
        self.assert_previous_publication_unchanged()

    def test_missing_evidence_does_not_replace_last_valid_export(self):
        with (
            patch(
                "nfl_value.defense_explorer.build_explorer",
                side_effect=FileNotFoundError("missing archived receipt"),
            ),
            redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(
                explorer_cli.main(
                    [
                        "--output-store",
                        str(self.store.root),
                        "export",
                        self.rid,
                        "--destination",
                        str(self.destination),
                    ]
                ),
                1,
            )
            self.assertIn("missing archived receipt", errors.getvalue())
        self.assert_previous_publication_unchanged()


if __name__ == "__main__":
    unittest.main()
