"""Production boundaries: real synthetic archive replay, fake GitHub transport."""

from contextlib import redirect_stderr
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.production import read_release, record_for, select_previous, verify_release
from nfl_value.production_cli import build, main, previous, retain
from test_ingestion import REVISION
import test_launch_bundle as launch_fixture


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.case = launch_fixture.LaunchTests(
            "test_exact_portable_replay_includes_candidate_and_frozen_recheck"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = self.case.root
        self.body, _ = self.case.package()
        self.pin = sha256(self.body)
        self.record = record_for(self.body)
        self.directory = self.root / "handoff"
        self.directory.mkdir()
        (self.directory / (self.pin + ".zip")).write_bytes(self.body)
        (self.directory / "release.json").write_bytes(json_bytes(self.record))
        self.destination = self.root / "verified"
        self.site = self.root / "served"

    def verify(self, **changes):
        args = dict(
            expected_pin=self.pin,
            expected_revision=REVISION,
            clock=lambda: self.case.checked + timedelta(minutes=1),
            site=self.site,
        )
        return verify_release(self.root, self.directory, self.destination, **(args | changes))

    def test_verify_replays_offline_stages_only_public_files_and_rechecks_now(self):
        with patch("socket.socket", side_effect=AssertionError("network")):
            result = self.verify()
        self.assertTrue(result["ready_for_explorer_deployment"])
        self.assertFalse(result["ranking_ready"])
        self.assertEqual(
            result["checked_at"], (self.case.checked + timedelta(minutes=1)).isoformat()
        )
        self.assertEqual(json.loads((self.site / "release.json").read_bytes()), self.record)
        self.assertEqual((self.site / "index.html").read_text(), "Synthetic test site")
        self.assertTrue((self.site / "ATTRIBUTION.md").is_file())
        self.assertFalse((self.site / "data/raw").exists())
        self.assertFalse((self.site / "launch-manifest.json").exists())
        self.assertEqual(
            self.case.case.pointer.read_bytes(), b"prior public pointer is never touched"
        )

    def test_delayed_publisher_rejects_stale_ready_package_without_staging(self):
        with self.assertRaisesRegex(ValueError, "sources not ready"):
            self.verify(clock=lambda: self.case.checked + timedelta(days=1))
        self.assertFalse(self.site.exists())
        # Stored original and canonical website remain unchanged.
        self.assertEqual(read_release(self.directory, self.pin)[0], self.body)
        self.assertEqual(
            self.case.case.pointer.read_bytes(), b"prior public pointer is never touched"
        )

    def test_existing_site_is_never_replaced(self):
        self.site.mkdir()
        pointer = self.site / "latest.json"
        pointer.write_bytes(b"last good")
        with self.assertRaisesRegex(ValueError, "must be new"):
            self.verify()
        self.assertEqual(pointer.read_bytes(), b"last good")

    def test_workflow_pin_and_revision_bind_handoff(self):
        for changes in ({"expected_pin": "f" * 64}, {"expected_revision": "f" * 40}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.verify(**changes)
            self.assertFalse(self.destination.exists())
            self.assertFalse(self.site.exists())

    def test_rehashed_wrong_metadata_extra_keys_and_corrupt_archive_fail(self):
        for changes in (
            {"ranking_ready": True},
            {"archive_bytes": True},
            {"candidate_id": "f" * 64},
            {"unexpected": 1},
        ):
            (self.directory / "release.json").write_bytes(json_bytes(self.record | changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                read_release(self.directory)
        (self.directory / "release.json").write_bytes(json_bytes(self.record))
        (self.directory / (self.pin + ".zip")).write_bytes(self.body + b"corruption")
        with self.assertRaises(ValueError):
            read_release(self.directory)

    def test_previous_uses_newest_retained_not_latest_or_draft_and_bootstrap_is_explicit(self):
        first = {"id": 3, "tag_name": self.record["tag"], "draft": False}
        second_tag = "explorer-2026-" + "a" * 64
        second = {"id": 4, "tag_name": second_tag, "draft": False}
        draft = {"id": 5, "tag_name": "explorer-2026-" + "b" * 64, "draft": True}
        self.assertEqual(select_previous([[draft, first], [second]]), second_tag)
        with self.assertRaisesRegex(ValueError, "bootstrap cannot bypass"):
            select_previous([[first]], bootstrap=True)
        with self.assertRaisesRegex(ValueError, "first manual"):
            select_previous([[]])
        self.assertIsNone(select_previous([[]], bootstrap=True))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            select_previous([[first, first]])
        with self.assertRaises(ValueError):
            select_previous([[first, second | {"tag_name": "explorer-2026-bad"}]])

    def fake_download(self, args):
        destination = Path(args[args.index("--dir") + 1])
        shutil.copyfile(self.directory / "release.json", destination / "release.json")
        shutil.copyfile(self.directory / (self.pin + ".zip"), destination / (self.pin + ".zip"))

    def test_previous_remote_recovery_replays_and_network_failure_cannot_bootstrap(self):
        def api(*args):
            if args[0] == "api":
                return json.dumps([[{"id": 1, "tag_name": self.record["tag"], "draft": False}]])
            self.fake_download(args)
            return ""

        workspace = self.root / "previous"
        with patch("nfl_value.production_cli.gh", side_effect=api):
            state = previous(self.root, workspace, bootstrap=False)
        self.assertEqual(state["explorer_report"], self.record["explorer_report"])
        self.assertTrue((workspace / "launch-manifest.json").exists())
        blocked = self.root / "network-failed"
        with patch(
            "nfl_value.production_cli.gh", side_effect=subprocess.CalledProcessError(1, "gh")
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                previous(self.root, blocked, bootstrap=True)
        self.assertFalse(blocked.exists())

    def test_retention_downloads_and_replays_before_releasing_draft(self):
        calls = []
        checks = []

        def api(*args):
            calls.append(args)
            if args[:2] == ("release", "download"):
                self.fake_download(args)
            return ""

        def verify(*args, **kwargs):
            checks.append(args[1])
            return verify_release(*args, **kwargs, clock=lambda: self.case.checked)

        with (
            patch("nfl_value.production_cli.gh", side_effect=api),
            patch("nfl_value.production_cli.verify_release", side_effect=verify),
        ):
            result = retain(self.root, self.directory, self.root / "remote", self.pin, REVISION)
        self.assertEqual([args[1] for args in calls], ["create", "download", "edit"])
        self.assertIn("--draft", calls[0])
        self.assertIn("--draft=false", calls[-1])
        self.assertNotIn("--clobber", str(calls))
        self.assertEqual(len(checks), 2)
        self.assertTrue(result["remote_download_replayed"])
        self.assertFalse(result["deployed"])

    def test_failed_remote_download_never_exposes_draft_or_edits_prior_release(self):
        calls = []

        def api(*args):
            calls.append(args)
            if args[:2] == ("release", "download"):
                raise subprocess.CalledProcessError(1, "gh")
            return ""

        def verify(*args, **kwargs):
            return verify_release(*args, **kwargs, clock=lambda: self.case.checked)

        with (
            patch("nfl_value.production_cli.gh", side_effect=api),
            patch("nfl_value.production_cli.verify_release", side_effect=verify),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            retain(self.root, self.directory, self.root / "remote", self.pin, REVISION)
        self.assertEqual([args[1] for args in calls], ["create", "download"])
        self.assertEqual(read_release(self.directory, self.pin)[0], self.body)

    def test_cli_rejects_wrong_validator_before_external_writes(self):
        with (
            patch("nfl_value.production_cli.committed_revision", return_value="e" * 40),
            patch("nfl_value.production_cli.gh", side_effect=AssertionError("no remote writes")),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(
                main(
                    [
                        "retain",
                        "--input",
                        str(self.directory),
                        "--destination",
                        str(self.destination),
                        "--sha256",
                        self.pin,
                        "--expected-revision",
                        REVISION,
                    ]
                ),
                1,
            )

    def test_capture_build_handoff_uses_cutoff_after_all_sources_and_preserves_prior(self):
        (self.root / "previous.json").write_bytes(
            json_bytes(
                {
                    "retained_tag": self.record["tag"],
                    "explorer_report": self.case.candidate["explorer_report"],
                }
            )
        )
        output = self.root / "built-release"
        captured = []

        def capture(store, spec, **kwargs):
            captured.append(spec.kind)
            self.assertEqual(spec.season, 2026)
            self.assertEqual(kwargs["code_revision"], REVISION)
            return self.case.case.ids[spec.kind], {}

        def review(root, report, *args, **kwargs):
            self.assertTrue(kwargs["isolated"])
            body = self.case.review(report)
            path = self.root / "compiled.zip"
            path.write_bytes(body)
            return {"archive": str(path), "archive_sha256": sha256(body)}

        def now(_zone):
            self.assertEqual(captured, ["pbp", "schedules", "depth_charts", "rosters"])
            return self.case.checked

        with (
            patch("nfl_value.production_cli.capture", side_effect=capture),
            patch("nfl_value.production_cli.build_review", side_effect=review),
            patch("nfl_value.production_cli.datetime") as clock,
            patch("nfl_value.production_cli.committed_revision", return_value=REVISION),
            patch("socket.socket", side_effect=AssertionError("network")),
        ):
            clock.now.side_effect = now
            record = build(self.root, self.root, output, REVISION)
        self.assertEqual(record["previous_retained_tag"], self.record["tag"])
        self.assertEqual(record["game_cutoff"], self.case.checked.isoformat())
        self.assertEqual(read_release(output)[1], record)
        result = verify_release(
            self.root,
            output,
            self.destination,
            clock=lambda: self.case.checked,
            expected_revision=REVISION,
        )
        self.assertTrue(result["ready_for_explorer_deployment"])

    def test_failed_capture_or_stale_inputs_cannot_create_release_output(self):
        (self.root / "previous.json").write_bytes(
            json_bytes({"retained_tag": None, "explorer_report": None})
        )
        output = self.root / "blocked-release"
        with (
            patch("nfl_value.production_cli.capture", side_effect=OSError("source offline")),
            self.assertRaises(OSError),
        ):
            build(self.root, self.root, output, REVISION)
        self.assertFalse(output.exists())

        def capture(store, spec, **kwargs):
            return self.case.case.ids[spec.kind], {}

        with (
            patch("nfl_value.production_cli.capture", side_effect=capture),
            patch("nfl_value.production_cli.datetime") as clock,
            patch(
                "nfl_value.production_cli.build_review", side_effect=AssertionError("blocked build")
            ),
        ):
            clock.now.return_value = self.case.checked + timedelta(days=1)
            with self.assertRaisesRegex(ValueError, "sources not ready"):
                build(self.root, self.root, output, REVISION)
        self.assertFalse(
            json.loads((self.root / "readiness.json").read_bytes())["ready_for_explorer_build"]
        )
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
