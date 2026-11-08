"""Synthetic replay boundary tests; no live downloads or production admission."""

from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from nfl_value.admission import SOURCE_PATHS
from nfl_value.defense_explorer import save_explorer
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.review_bundle import (
    POLICY_PATH,
    REGISTRY_PATH,
    archive_bytes,
    bundle_files,
    read_policy,
    review_inputs,
    save_archive,
    stage_review,
)
from nfl_value.review_cli import build_review, build_workspace, main
from test_defense_explorer import payload


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for relative in {
            *SOURCE_PATHS.values(),
            REGISTRY_PATH,
            POLICY_PATH,
            "web/package-lock.json",
        }:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(relative, target)
        self.output = SnapshotStore(self.root / "objects")
        self.data = payload()
        # Simulate the replay boundary only. These observations remain synthetic.
        self.data["data_mode"] = "observed"
        self.report_id, self.report = save_explorer(self.output, self.data)
        self.replay = patch(
            "nfl_value.review_bundle.replay_explorer", return_value=(self.report, self.data)
        )
        self.mock_replay = self.replay.start()
        self.addCleanup(self.replay.stop)

    def inputs(self):
        return review_inputs(self.root, None, None, self.output, self.report_id, "a" * 40)

    def dist(self, files):
        dist = self.root / "dist"
        stage_review(dist, files)
        (dist / "assets").mkdir(exist_ok=True)
        (dist / "assets/test.js").write_text("/* synthetic compiled asset */")
        (dist / "assets/test.css").write_text(":root { color: white; }")
        (dist / "index.html").write_text('<script type="module" src="./assets/test.js"></script>')
        return dist

    def test_manifest_preserves_game_cutoff_separately_from_later_decision(self):
        files, metadata = self.inputs()
        self.assertEqual(metadata["game_cutoff"], self.data["cutoff"])
        self.assertEqual(metadata["decided_at"], "2026-11-02T19:53:56+00:00")
        self.assertFalse(metadata["ranking_ready"])
        self.assertEqual(metadata["explorer_report"], self.report_id)
        dist = self.dist(files)
        (dist / "data/old-unreferenced.json").write_text("preserved but not packaged")
        (dist / ".env").write_text("not public")
        result = bundle_files(dist, files, metadata)
        manifest = json.loads(result["review-manifest.json"])
        self.assertEqual(set(manifest["files"]), set(result) - {"review-manifest.json"})
        for name, entry in manifest["files"].items():
            self.assertEqual(entry, {"sha256": sha256(result[name]), "bytes": len(result[name])})
        self.assertNotIn("data/old-unreferenced.json", result)
        self.assertNotIn(".env", result)
        self.assertTrue((dist / "data/old-unreferenced.json").exists())

    def test_registry_and_bound_evidence_corruption_fail_before_replay(self):
        for relative in (REGISTRY_PATH, SOURCE_PATHS["defense_evidence"]):
            with self.subTest(relative=relative):
                target = self.root / relative
                original = target.read_bytes()
                target.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    self.inputs()
                self.mock_replay.assert_not_called()
                target.write_bytes(original)

    def test_policy_requires_strict_version_and_committed_pins(self):
        target = self.root / POLICY_PATH
        original = read_policy(self.root)
        for key, value in (
            ("schema_version", True),
            ("registry_sha256", ""),
            ("registry_revision", "main"),
            ("unknown", 0),
        ):
            target.write_bytes(json_bytes({**original, key: value}))
            with self.assertRaises(ValueError):
                read_policy(self.root)

    def test_synthetic_wrong_season_or_fabricated_scores_never_stage(self):
        for update in ({"data_mode": "synthetic"}, {"season": 2025}, {"ranking_ready": True}):
            with self.subTest(update=update):
                changed = {**self.data, **update}
                rid, report = save_explorer(self.output, changed)
                self.mock_replay.return_value = report, changed
                with self.assertRaisesRegex(ValueError, "observed"):
                    review_inputs(self.root, None, None, self.output, rid, "a" * 40)
        changed = deepcopy(self.data)
        changed["players"][0]["cavaa"] = 0
        rid, report = save_explorer(self.output, changed)
        self.mock_replay.return_value = report, changed
        with self.assertRaisesRegex(ValueError, "observed"):
            review_inputs(self.root, None, None, self.output, rid, "a" * 40)

    def test_replay_failure_leaves_existing_pointer_and_archives_untouched(self):
        files, _ = self.inputs()
        stage_review(self.root / "web/public", files)
        pointer = self.root / "web/public/data/latest.json"
        before = pointer.read_bytes()
        self.mock_replay.side_effect = ValueError("replay differs")
        with self.assertRaisesRegex(ValueError, "replay differs"):
            self.inputs()
        self.assertEqual(pointer.read_bytes(), before)
        self.assertFalse((self.root / "artifacts").exists())

    def test_bad_immutable_object_and_failed_write_preserve_local_pointer(self):
        files, _ = self.inputs()
        public = self.root / "web/public"
        stage_review(public, files)
        pointer = public / "data/latest.json"
        before = pointer.read_bytes()
        new_files = {**files, "data/extra.json": b"new", "data/latest.json": b"changed"}
        with patch("nfl_value.review_bundle._publish_bytes", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                stage_review(public, new_files)
        self.assertEqual(pointer.read_bytes(), before)
        name = f"data/{self.report['object']}.json"
        (public / name).write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "immutable"):
            stage_review(public, {**files, "data/latest.json": b"changed"})
        self.assertEqual(pointer.read_bytes(), before)

    def test_built_registry_snapshot_or_pointer_mismatch_prevents_archive(self):
        files, metadata = self.inputs()
        dist = self.dist(files)
        for name, body in files.items():
            (dist / name).write_bytes(body + b" ")
            with self.assertRaisesRegex(ValueError, "built data differs"):
                bundle_files(dist, files, metadata)
            (dist / name).write_bytes(body)
        (dist / "assets/test.js").unlink()
        with self.assertRaisesRegex(ValueError, "JavaScript"):
            bundle_files(dist, files, metadata)

    def test_symlink_and_unsafe_asset_paths_are_rejected(self):
        files, metadata = self.inputs()
        dist = self.dist(files)
        outside = self.root / "other"
        outside.write_bytes(b"untrusted")
        target = dist / "assets/test.js"
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            bundle_files(dist, files, metadata)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            stage_review(dist, {"../outside": b"no"})
        target.unlink()
        target.write_bytes(b"original")
        (dist / "assets/.env").write_bytes(b"no")
        with self.assertRaisesRegex(ValueError, "unexpected static asset"):
            bundle_files(dist, files, metadata)

    def test_archive_is_deterministic_checks_every_file_and_never_overwrites(self):
        files, metadata = self.inputs()
        packaged = bundle_files(self.dist(files), files, metadata)
        first = archive_bytes(packaged)
        self.assertEqual(first, archive_bytes(dict(reversed(list(packaged.items())))))
        with zipfile.ZipFile(BytesIO(first)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), sorted(packaged))
            for name, body in packaged.items():
                self.assertEqual(archive.read(name), body)
        target = save_archive(self.root / "archives", first)
        self.assertEqual(target.name, f"{sha256(first)}.zip")
        self.assertEqual(save_archive(target.parent, first), target)
        target.write_bytes(b"corrupted saved release")
        with self.assertRaisesRegex(ValueError, "immutable review archive"):
            save_archive(target.parent, first)
        self.assertEqual(target.read_bytes(), b"corrupted saved release")

    def test_cli_rejects_dirty_frontend_before_replay_or_build(self):
        with (
            patch("nfl_value.review_cli.committed_revision", return_value="a" * 40),
            patch("nfl_value.review_cli.subprocess.check_output", return_value="?? web/src/new.ts"),
            patch("nfl_value.review_cli.subprocess.run") as build,
        ):
            with self.assertRaisesRegex(ValueError, "commit web"):
                build_review(
                    self.root, self.report_id, None, None, self.output, self.root / "archives"
                )
        build.assert_not_called()
        self.mock_replay.assert_not_called()

    def test_cli_rebuilds_and_propagates_failure_without_creating_archive(self):
        def git(args, **kwargs):
            if args[0] == "node":
                return "v24.19.0"
            if args[0] == "npm":
                return "11.11.1"
            if args[1] == "status":
                return ""
            return (self.root / args[2].split(":", 1)[1]).read_bytes()

        def build(*args, **kwargs):
            if "ls" in args[0]:
                return
            files, _ = self.inputs()
            self.dist(files).rename(self.root / "web/dist")

        with (
            patch("nfl_value.review_cli.committed_revision", return_value="a" * 40),
            patch("nfl_value.review_cli.subprocess.check_output", side_effect=git),
            patch("nfl_value.review_cli.subprocess.run", side_effect=build) as compiler,
        ):
            result = build_review(
                self.root, self.report_id, None, None, self.output, self.root / "archives"
            )
            self.assertFalse(result["ranking_ready"])
            compiler.assert_called_with(
                ["npm", "--prefix", "web", "run", "build"],
                cwd=self.root,
                check=True,
                stdout=sys.stderr,
            )
            self.assertEqual(compiler.call_count, 2)
            saved = Path(result["archive"]).read_bytes()

            def fail_build(args, **kwargs):
                if "ls" not in args:
                    raise OSError("compiler unavailable")

            compiler.side_effect = fail_build
            with self.assertRaises(OSError):
                build_review(
                    self.root, self.report_id, None, None, self.output, self.root / "archives"
                )
            self.assertEqual(Path(result["archive"]).read_bytes(), saved)
            self.assertEqual(len(list((self.root / "archives").iterdir())), 1)

    def test_unsupported_toolchain_or_mismatched_evidence_link_fails_before_staging(self):
        for bad_link in (True, False):

            def commands(args, **kwargs):
                if args[0] == "node":
                    return "v22.0.0"
                if args[1] == "status":
                    return ""
                return (
                    b"corrupt" if bad_link else (self.root / args[2].split(":", 1)[1]).read_bytes()
                )

            with (
                patch("nfl_value.review_cli.committed_revision", return_value="a" * 40),
                patch("nfl_value.review_cli.subprocess.check_output", side_effect=commands),
                patch("nfl_value.review_cli.stage_review") as stage,
            ):
                with self.assertRaisesRegex(ValueError, "evidence link" if bad_link else "Node 24"):
                    build_review(
                        self.root, self.report_id, None, None, self.output, self.root / "archives"
                    )
                stage.assert_not_called()

    def test_cli_failure_has_nonzero_exit(self):
        with (
            patch(
                "nfl_value.review_cli.build_review", side_effect=ValueError("invalid saved inputs")
            ),
            patch("sys.stderr"),
        ):
            self.assertEqual(main(["a" * 64]), 1)

    def test_isolated_workspace_copies_tracked_only_and_cleans_on_failure(self):
        modules = self.root / "web/node_modules"
        modules.mkdir()
        public = self.root / "web/public/data"
        public.mkdir(parents=True)
        (public / "latest.json").write_bytes(b"prior pointer")
        (self.root / "web/.env").write_bytes(b"not a build input")
        with patch(
            "nfl_value.review_cli.subprocess.check_output", return_value=b"web/package-lock.json\0"
        ):
            with self.assertRaisesRegex(OSError, "compile failed"):
                with build_workspace(self.root, True) as staging:
                    self.assertNotEqual(staging, self.root)
                    self.assertEqual(
                        (staging / "web/package-lock.json").read_bytes(),
                        (self.root / "web/package-lock.json").read_bytes(),
                    )
                    self.assertFalse((staging / "web/.env").exists())
                    self.assertFalse((staging / "web/public").exists())
                    self.assertEqual((staging / "web/node_modules").resolve(), modules)
                    raise OSError("compile failed")
        self.assertEqual((public / "latest.json").read_bytes(), b"prior pointer")
        self.assertFalse(staging.exists())
        self.assertEqual(list((self.root / "work").iterdir()), [])
