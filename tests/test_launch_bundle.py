"""Synthetic sources with real replay; compiled site assets are explicit fixtures."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from io import StringIO
import json
import shutil
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from nfl_value.admission import SOURCE_PATHS
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.launch_bundle import CHECK, MANIFEST, build_launch, restore_launch
from nfl_value.launch_cli import main
from nfl_value.readiness import POLICY
from nfl_value.recovery_io import encode_archive, file_index, read_archive
from nfl_value.refresh_candidate import replay_candidate
from nfl_value.review_bundle import (
    POLICY_PATH,
    REGISTRY_PATH,
    archive_bytes,
    bundle_files,
    review_inputs,
    stage_review,
)
from test_ingestion import REVISION
from test_readiness import CUTOFF
import test_readiness as readiness_fixture


class LaunchTests(unittest.TestCase):
    def setUp(self):
        # Reuse fixture setup, not inherited test methods or stubbed source replay.
        self.case = readiness_fixture.ReadinessTests(
            "test_real_candidate_chain_replays_offline_and_does_not_publish"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = self.case.root
        for relative in {
            *SOURCE_PATHS.values(),
            REGISTRY_PATH,
            POLICY_PATH,
            "web/package-lock.json",
        }:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(relative, target)
        # Canonical store layout, as used by the portable package.
        paths = (
            "data/raw/source-snapshots",
            "data/derived/offensive-inputs",
            "data/derived/defense-explorer",
            "data/derived/explorer-candidates",
        )
        for store, relative in zip(self.case.stores, paths):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if store.root.exists():
                store.root.rename(target)
            store.root = target
        _, _, self.cid = self.case.prepare()
        self.candidate = replay_candidate(*self.case.stores, self.cid)
        self.body = self.review(self.candidate["explorer_report"])
        self.pin = sha256(self.body)
        self.checked = CUTOFF + timedelta(minutes=1)
        self.destination = self.root / "restore"

    def review(self, report):
        files, meta = review_inputs(self.root, *self.case.stores[:3], report, REVISION)
        meta["toolchain"] = {"node": "v24.synthetic", "npm": "synthetic", "python": "synthetic"}
        dist = self.root / "fixture-dist"
        stage_review(dist, files)
        (dist / "assets").mkdir(exist_ok=True)
        (dist / "assets/fixture.js").write_text("/* synthetic compiler output */")
        (dist / "assets/fixture.css").write_text("body {color: white}")
        (dist / "index.html").write_text("Synthetic test site")
        return archive_bytes(bundle_files(dist, files, meta))

    def package(self, **updates):
        kwargs = dict(
            repository_root=self.root,
            store_root=self.root,
            review_body=self.body,
            review_hash=self.pin,
            candidate_id=self.cid,
            checked_at=self.checked,
            code_revision=REVISION,
        )
        return build_launch(**(kwargs | updates))

    def repack(self, files, **changes):
        manifest = json.loads(files[MANIFEST])
        manifest.update(changes)
        manifest["files"] = file_index({k: v for k, v in files.items() if k != MANIFEST})
        return encode_archive({**files, MANIFEST: json_bytes(manifest)})

    def test_exact_portable_replay_includes_candidate_and_frozen_recheck(self):
        # An unrelated store object is neither copied nor removed.
        unrelated = self.case.raw.put(b"unrelated object")
        with patch("socket.socket", side_effect=AssertionError("network")):
            body, manifest = self.package()
        self.assertEqual(self.package()[0], body)
        files = read_archive(body, sha256(body))
        self.assertNotIn(f"data/raw/source-snapshots/objects/{unrelated}", files)
        self.assertEqual(self.case.raw.read(unrelated), b"unrelated object")
        check = json.loads(files[CHECK])
        self.assertEqual(check["policy"], POLICY)
        self.assertEqual(check["cutoff"], self.checked.isoformat())
        self.assertNotEqual(manifest["checked_at"], manifest["game_cutoff"])
        self.assertIn(f"data/derived/explorer-candidates/manifests/{self.cid}.json", files)
        self.assertFalse(manifest["published"])
        self.assertFalse(manifest["ranking_ready"])
        # Remove original stores. Restoration must rely solely on staged bytes.
        (self.root / "data").rename(self.root / "hidden-original-data")
        with patch("socket.socket", side_effect=AssertionError("network")):
            result = restore_launch(self.root, body, sha256(body), self.destination)
        self.assertTrue(result["verified_at_recorded_time_only"])
        self.assertTrue(result["semantic_replay_verified"])
        for name, expected in files.items():
            self.assertEqual((self.destination / name).read_bytes(), expected)
        self.assertEqual(self.case.pointer.read_bytes(), b"prior public pointer is never touched")

    def test_previous_comparison_dependencies_and_attribution_are_retained(self):
        self.case.rows["pbp"][0]["epa"] = "1"
        corrected = self.case.capture("pbp")
        _, _, second_id = self.case.prepare(
            {**self.case.ids, "pbp": corrected}, previous_explorer=self.candidate["explorer_report"]
        )
        second = replay_candidate(*self.case.stores, second_id)
        reviewed = self.review(second["explorer_report"])
        body, _ = self.package(
            candidate_id=second_id, review_body=reviewed, review_hash=sha256(reviewed)
        )
        files = read_archive(body, sha256(body))
        self.assertIn(
            f"data/derived/defense-explorer/manifests/{self.candidate['explorer_report']}.json",
            files,
        )
        notice = files["ATTRIBUTION.md"].decode()
        self.assertIn("prior comparison", notice)
        self.assertIn(self.case.ids["pbp"], notice)
        self.assertIn(corrected, notice)
        result = restore_launch(self.root, body, sha256(body), self.destination)
        self.assertTrue(result["semantic_replay_verified"])

    def test_stale_or_backward_check_cannot_reuse_positive_original_decision(self):
        for checked in (CUTOFF - timedelta(seconds=1), CUTOFF + timedelta(days=1)):
            with (
                self.subTest(checked=checked),
                self.assertRaisesRegex(ValueError, "precede|sources not ready"),
            ):
                self.package(checked_at=checked)
        self.assertFalse(self.destination.exists())

    def test_wrong_site_snapshot_rejected_even_with_valid_new_hash(self):
        self.case.rows["pbp"][0]["epa"] = "1"
        corrected = self.case.capture("pbp")
        _, _, second = self.case.prepare({**self.case.ids, "pbp": corrected})
        with self.assertRaisesRegex(ValueError, "exact candidate"):
            self.package(candidate_id=second)

    def test_game_starting_after_candidate_blocks_later_packaging(self):
        kickoff = CUTOFF + timedelta(minutes=30)
        local = kickoff.astimezone(ZoneInfo("America/New_York"))
        row = self.case.rows["schedules"][1]
        row.update(gameday=local.strftime("%Y-%m-%d"), gametime=local.strftime("%H:%M"))
        schedules = self.case.capture("schedules")
        _, _, cid = self.case.prepare({**self.case.ids, "schedules": schedules})
        candidate = replay_candidate(*self.case.stores, cid)
        review = self.review(candidate["explorer_report"])
        with self.assertRaisesRegex(ValueError, "sources not ready.*game_coverage"):
            self.package(
                candidate_id=cid,
                review_body=review,
                review_hash=sha256(review),
                checked_at=kickoff + timedelta(minutes=1),
            )

    def test_corrupt_missing_candidate_or_prior_bytes_fail(self):
        path = self.case.candidates._path(self.cid, manifest=True)
        original = path.read_bytes()
        path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.package()
        path.unlink()
        with self.assertRaises(OSError):
            self.package()
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.package(review_body=self.body + b"corrupt")

    def test_changed_recheck_or_manifest_fails_semantic_replay(self):
        body, _ = self.package()
        original = read_archive(body, sha256(body))
        for field, value in (
            ("published", True),
            ("schema_version", True),
            ("game_cutoff", self.checked.isoformat()),
            ("explorer_report", "f" * 64),
        ):
            with self.subTest(field=field):
                changed = self.repack(original, **{field: value})
                with self.assertRaises(ValueError):
                    restore_launch(self.root, changed, sha256(changed), self.destination)
                self.assertFalse(self.destination.exists())
                self.assertEqual(list(self.root.glob(".launch-restore-*")), [])
        check = json.loads(original[CHECK])
        check["policy"]["required_sources"]["pbp"]["upstream_hours"] = 9999
        changed = self.repack({**original, CHECK: json_bytes(check)})
        with self.assertRaisesRegex(ValueError, "semantic replay"):
            restore_launch(self.root, changed, sha256(changed), self.destination)

    def test_missing_or_extra_allowed_store_member_is_not_silently_accepted(self):
        body, _ = self.package()
        original = read_archive(body, sha256(body))
        extra = b"unreferenced"
        extra_name = f"data/raw/source-snapshots/objects/{sha256(extra)}"
        missing = f"data/derived/explorer-candidates/manifests/{self.cid}.json"
        for files in (
            {**original, extra_name: extra},
            {k: v for k, v in original.items() if k != missing},
        ):
            changed = self.repack(files)
            with self.assertRaises((ValueError, OSError)):
                restore_launch(self.root, changed, sha256(changed), self.destination)
            self.assertFalse(self.destination.exists())

    def test_external_digest_unsafe_paths_and_rehashed_wrong_scope_fail(self):
        body, _ = self.package()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            restore_launch(self.root, body, "f" * 64, self.destination)
        files = read_archive(body, sha256(body))
        changed = self.repack({**files, "data/derived/calibration/no.json": b"{}"})
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            restore_launch(self.root, changed, sha256(changed), self.destination)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            encode_archive({"../escape": b"no"})

    def test_existing_destination_and_failed_rename_preserve_prior_files(self):
        body, _ = self.package()
        self.destination.mkdir()
        prior = self.destination / "prior"
        prior.write_bytes(b"saved")
        with self.assertRaisesRegex(ValueError, "already exist"):
            restore_launch(self.root, body, sha256(body), self.destination)
        self.assertEqual(prior.read_bytes(), b"saved")
        fresh = self.root / "fresh"
        with patch("nfl_value.launch_bundle.os.rename", side_effect=OSError("storage failure")):
            with self.assertRaises(OSError):
                restore_launch(self.root, body, sha256(body), fresh)
        self.assertFalse(fresh.exists())
        self.assertEqual(list(self.root.glob(".launch-restore-*")), [])
        self.assertEqual(prior.read_bytes(), b"saved")

    def test_cli_records_real_attempt_time_and_restore_does_not_renew_it(self):
        archive = self.root / "site.zip"
        archive.write_bytes(self.body)
        args = [
            "pack",
            self.cid,
            str(archive),
            "--sha256",
            self.pin,
            "--store-root",
            str(self.root),
            "--destination",
            str(self.root / "packages"),
        ]
        output = StringIO()
        with (
            patch("nfl_value.launch_cli.committed_revision", return_value=REVISION),
            patch("nfl_value.launch_cli.Path.cwd", return_value=self.root),
            patch("nfl_value.launch_cli.datetime") as clock,
            redirect_stdout(output),
        ):
            clock.now.return_value = self.checked
            self.assertEqual(main(args), 0)
            self.assertEqual(clock.now.call_count, 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["manifest"]["checked_at"], self.checked.isoformat())
        self.assertFalse(result["uploaded"])
        out = StringIO()
        with (
            patch("nfl_value.launch_cli.committed_revision", return_value=REVISION),
            patch("nfl_value.launch_cli.Path.cwd", return_value=self.root),
            redirect_stdout(out),
        ):
            self.assertEqual(
                main(
                    [
                        "restore",
                        result["archive"],
                        "--sha256",
                        result["archive_sha256"],
                        "--destination",
                        str(self.destination),
                    ]
                ),
                0,
            )
        self.assertTrue(json.loads(out.getvalue())["verified_at_recorded_time_only"])
        with (
            patch("nfl_value.launch_cli.committed_revision", side_effect=ValueError("dirty")),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(args), 1)
