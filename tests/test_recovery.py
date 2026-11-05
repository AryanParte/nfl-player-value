"""Synthetic raw replay boundary; real registry/review/archive and IO validation.

No NFL downloads. The dated real archive audit separately verifies end-to-end
replay; these fixtures do not establish scientific validity or admission.
"""

from copy import deepcopy
from io import BytesIO, StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from nfl_value.defense_explorer import save_explorer
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.recovery import (
    ATTRIBUTION,
    MANIFEST,
    STORES,
    RecordingStore,
    build_recovery,
    restore_recovery,
    verified_closure,
)
from nfl_value.recovery_cli import main
from nfl_value.recovery_io import (
    check_index,
    decode_object,
    encode_archive,
    file_index,
    read_archive,
    read_bounded,
    save_recovery,
)
from nfl_value.review_bundle import review_inputs
from test_defense_explorer import payload


REVISION = "a" * 40


def mutate_archive(body, transform, *, update_index=True):
    files = read_archive(body, sha256(body))
    manifest = decode_object(files.pop(MANIFEST))
    transform(files, manifest)
    if update_index:
        manifest["files"] = file_index(files)
    return encode_archive({**files, MANIFEST: json_bytes(manifest)})


class ArchiveIOTests(unittest.TestCase):
    def test_fixed_metadata_order_and_external_hash(self):
        files = {"z/item": b"negative: -2", "a": b"0"}
        body = encode_archive(files)
        self.assertEqual(body, encode_archive(dict(reversed(list(files.items())))))
        self.assertEqual(read_archive(body, sha256(body)), files)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            read_archive(body + b"changed", sha256(body))
        with self.assertRaisesRegex(ValueError, "trusted full"):
            read_archive(body, "short")
        with self.assertRaises(zipfile.BadZipFile):
            read_archive(b"truncated", sha256(b"truncated"))

    def test_duplicate_member_is_rejected(self):
        buffer = BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("duplicate", b"a")
                archive.writestr("duplicate", b"b")
        body = buffer.getvalue()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            read_archive(body, sha256(body))

    def test_traversal_links_directories_and_compression_rejected(self):
        cases = [
            (name, 0o100644, zipfile.ZIP_STORED)
            for name in ("../escape", "/absolute", "a/../b", "a//b", "a\\b")
        ] + [
            ("link", 0o120777, zipfile.ZIP_STORED),
            ("directory/", 0o040755, zipfile.ZIP_STORED),
            ("compressed", 0o100644, zipfile.ZIP_DEFLATED),
        ]
        for name, mode, compression in cases:
            with self.subTest(name=name):
                buffer = BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    info.compress_type = compression
                    archive.writestr(info, b"bad")
                body = buffer.getvalue()
                with self.assertRaises(ValueError):
                    read_archive(body, sha256(body))

    def test_bounded_bytes_and_entry_count(self):
        body = encode_archive({"one": b"a", "two": b"b"})
        with patch("nfl_value.recovery_io.MAX_ARCHIVE_BYTES", len(body) - 1):
            with self.assertRaisesRegex(ValueError, "size limit"):
                read_archive(body, sha256(body))
        with patch("nfl_value.recovery_io.MAX_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "entry count"):
                read_archive(body, sha256(body))
            with self.assertRaisesRegex(ValueError, "size/count"):
                encode_archive({"one": b"a", "two": b"b"})

    def test_json_and_index_strictness(self):
        for invalid in (b'{"x":1,"x":2}', b'{"x":NaN}', b"[]"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                decode_object(invalid)
        files = {"one": b"a"}
        for change in (
            lambda x: x.clear(),
            lambda x: x["one"].update(bytes=True),
            lambda x: x["one"].update(sha256="f" * 64),
            lambda x: x["one"].update(extra=1),
        ):
            index = file_index(files)
            change(index)
            with self.assertRaises(ValueError):
                check_index(files, index)

    def test_immutable_archive_and_bounded_local_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            body = encode_archive({"a": b"a"})
            target = save_recovery(root, body)
            self.assertEqual(target, save_recovery(root, body))
            with patch("nfl_value.recovery_io.MAX_ARCHIVE_BYTES", len(body) - 1):
                with self.assertRaisesRegex(ValueError, "size limit"):
                    read_bounded(target)
            target.write_bytes(b"corrupt existing artifact")
            with self.assertRaisesRegex(ValueError, "immutable"):
                save_recovery(root, body)
            self.assertEqual(target.read_bytes(), b"corrupt existing artifact")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symbolic"):
                read_bounded(link)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.repository = Path.cwd()
        self.stores = [SnapshotStore(self.root / name) for name in STORES]
        raw, inputs, output = self.stores
        self.receipts = {}
        for kind in ("pbp", "schedules", "depth_charts", "rosters"):
            license_id = raw.put(b"Synthetic test license bytes, not source data")
            data_id = raw.put(f"Synthetic {kind}, not real NFL data".encode())
            receipt = {
                "source": {
                    "kind": kind,
                    "season": 2026,
                    "license_id": "CC-BY-4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "attribution": "Synthetic fixture only",
                },
                "asset": {
                    "browser_download_url": f"https://github.com/example/{kind}",
                    "updated_at": "2026-10-22T21:00:00+00:00",
                },
                "retrieval": {"data": "2026-10-22T22:00:00+00:00"},
                "objects": {"raw": data_id, "license": license_id},
            }
            self.receipts[kind] = raw.put(json_bytes(receipt), manifest=True)
        self.input_id = inputs.put(b"Synthetic derived ledger with negative outcomes: -2")
        self.unrelated = raw.put(b"Do not package unrelated local objects")
        self.data = payload()
        # Only simulate observed mode at raw replay's boundary. No production data.
        self.data["data_mode"] = "observed"
        self.data["provenance"]["source_receipts"] = self.receipts
        self.report_id, _ = save_explorer(output, self.data)

        def replay(raw, inputs, output, report_id):
            # Exercise actual RecordingStore reads under both original and
            # restored roots, rather than returning data from the original root.
            for receipt_id in self.receipts.values():
                receipt = decode_object(raw.read(receipt_id, manifest=True))
                for object_id in receipt["objects"].values():
                    raw.read(object_id)
            inputs.read(self.input_id)
            report = decode_object(output.read(report_id, manifest=True))
            return report, decode_object(output.read(report["object"]))

        replay_patch = patch("nfl_value.review_bundle.replay_explorer", side_effect=replay)
        self.replay = replay_patch.start()
        self.addCleanup(replay_patch.stop)
        files, metadata = review_inputs(self.repository, *self.stores, self.report_id, REVISION)
        files.update({"index.html": b"Synthetic", "assets/a.js": b"// test", "assets/a.css": b""})
        self.review_files = files
        self.review_manifest = {
            **metadata,
            "toolchain": {"python": "3.13", "node": "v24.0.0", "npm": "11.0.0"},
            "files": file_index(files),
        }
        self.review = encode_archive(
            {**files, "review-manifest.json": json_bytes(self.review_manifest)}
        )
        self.body, self.manifest = self.pack()
        self.destination = self.root / "restored"

    def pack(self, review=None):
        review = self.review if review is None else review
        return build_recovery(self.repository, self.root, review, sha256(review), REVISION)

    def restore(self, body=None):
        body = self.body if body is None else body
        return restore_recovery(self.repository, body, sha256(body), self.destination)

    def assert_unpublished(self):
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".recovery-*")), [])

    def test_exact_closure_deterministic_restore_without_original_stores(self):
        self.assertEqual(self.body, self.pack()[0])
        files = read_archive(self.body, sha256(self.body))
        self.assertNotIn(f"{STORES[0]}/objects/{self.unrelated}", files)
        # Remove access to original roots. Only candidate restored inputs can pass.
        (self.root / "data").rename(self.root / "original-hidden")
        result = self.restore()
        self.assertTrue(result["semantic_replay_verified"])
        self.assertFalse(result["ranking_ready"])
        self.assertEqual(result["game_cutoff"], self.data["cutoff"])
        self.assertEqual(result["files_restored"], len(files))
        for name, body in files.items():
            self.assertEqual((self.destination / name).read_bytes(), body)
        notice = (self.destination / ATTRIBUTION).read_text()
        self.assertIn("CC-BY-4.0", notice)
        self.assertIn("retained unchanged", notice)
        self.assertIn("Synthetic fixture only", notice)

    def test_changed_saved_public_data_and_provenance_fail_before_pack(self):
        for mutate in (
            lambda f, m: f.update({"data/latest.json": b"{}"}),
            lambda f, m: m.update(game_cutoff="2026-11-04T00:00:00+00:00"),
            lambda f, m: m.update(ranking_ready=True),
            lambda f, m: m.update(schema_version=True),
            lambda f, m: m["coverage"].update(included_plays=4.0),
            lambda f, m: m.update(toolchain={}),
            lambda f, m: m.update(unreviewed=True),
            lambda f, m: f.update({"assets/private.txt": b"private"}),
            lambda f, m: f.pop("assets/a.js"),
        ):
            files, metadata = deepcopy(self.review_files), deepcopy(self.review_manifest)
            mutate(files, metadata)
            metadata["files"] = file_index(files)
            bad = encode_archive({**files, "review-manifest.json": json_bytes(metadata)})
            with self.assertRaises(ValueError):
                self.pack(bad)

    def test_valid_manifest_whitespace_is_retained_byte_for_byte(self):
        files = read_archive(self.body, sha256(self.body))
        files[MANIFEST] += b"\n"
        self.restore(encode_archive(files))
        self.assertEqual((self.destination / MANIFEST).read_bytes(), files[MANIFEST])

    def test_unadmitted_score_rejected_by_real_review_contract(self):
        self.data["players"][0]["cavaa"] = 2
        report_id, _ = save_explorer(self.stores[2], self.data)
        with self.assertRaisesRegex(ValueError, "unadmitted"):
            review_inputs(self.repository, *self.stores, report_id, REVISION)

    def test_recording_rejects_corrupt_object_read_only_write_and_parent_link(self):
        store = RecordingStore(self.stores[1].root, STORES[1])
        store.read(self.input_id)
        store.read(self.input_id)
        self.assertEqual(len(store.files), 1)
        with self.assertRaisesRegex(ValueError, "read-only"):
            store.put(b"never write")
        target = self.stores[1].root / "objects" / self.input_id
        target.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
            store.read(self.input_id)
        link = self.root / "linked-store"
        link.symlink_to(self.stores[0].root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            RecordingStore(link, STORES[0]).read(self.receipts["pbp"], manifest=True)

    def test_archive_hash_failure_creates_no_destination(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            restore_recovery(
                self.repository, self.body + b"corrupt", sha256(self.body), self.destination
            )
        self.assert_unpublished()

    def test_missing_and_extra_dependencies_fail_even_with_rehashed_manifest(self):
        member = f"{STORES[1]}/objects/{self.input_id}"
        for mutate in (
            lambda f, m: f.pop(member),
            lambda f, m: f.update({f"{STORES[0]}/objects/{sha256(b'extra')}": b"extra"}),
            lambda f, m: f.update({member: b"corrupt ledger"}),
            lambda f, m: f.update({ATTRIBUTION: b"license removed"}),
        ):
            with self.assertRaises((ValueError, FileNotFoundError)):
                self.restore(mutate_archive(self.body, mutate))
            self.assert_unpublished()

    def test_manifest_hash_size_policy_and_cutoff_mismatch_fail(self):
        for mutate in (
            lambda f, m: m.update(game_cutoff="2026-11-04T00:00:00+00:00"),
            lambda f, m: m.update(explorer_report="f" * 64),
            lambda f, m: m.update(policy="unsupported"),
            lambda f, m: m.update(schema_version=True),
            lambda f, m: m.update(ranking_ready=True),
            lambda f, m: m.update(packager_code_revision="main"),
            lambda f, m: m["files"][ATTRIBUTION].update(bytes=0),
        ):
            with self.assertRaises(ValueError):
                self.restore(mutate_archive(self.body, mutate, update_index=False))
            self.assert_unpublished()

    def test_unreviewed_members_and_missing_notice_fail(self):
        for mutate in (
            lambda f, m: f.update({"secrets.txt": b"not permitted"}),
            lambda f, m: f.pop(ATTRIBUTION),
        ):
            with self.assertRaises(ValueError):
                self.restore(mutate_archive(self.body, mutate))
            self.assert_unpublished()

    def test_license_scope_is_explicit_not_general_research_redistribution(self):
        store = RecordingStore(self.stores[0].root, STORES[0])
        from nfl_value.recovery import _notice

        with self.assertRaisesRegex(ValueError, "source family"):
            _notice(store, {"participation": "b" * 64})
        receipt = decode_object(store.read(self.receipts["pbp"], manifest=True))
        for field, value in (("license_id", "CC-BY-SA-4.0"), ("season", 2025)):
            changed = deepcopy(receipt)
            changed["source"][field] = value
            rid = self.stores[0].put(json_bytes(changed), manifest=True)
            with self.assertRaisesRegex(ValueError, "2026 CC-BY"):
                _notice(store, {**self.receipts, "pbp": rid})

    def test_existing_destination_preserved_even_when_empty(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(ValueError, "already exist"):
            self.restore()
        (self.destination / "last-good").write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "already exist"):
            self.restore()
        self.assertEqual((self.destination / "last-good").read_bytes(), b"preserve")

    def test_replay_failure_and_rename_failure_remove_only_owned_staging(self):
        other = self.root / ".recovery-unrelated"
        other.mkdir()
        for target, error in (
            ("nfl_value.recovery.verified_closure", ValueError("cannot replay")),
            ("nfl_value.recovery.os.fsync", OSError("write failure")),
            ("nfl_value.recovery.os.rename", OSError("disk error")),
        ):
            with patch(target, side_effect=error), self.assertRaises(type(error)):
                self.restore()
            self.assertFalse(self.destination.exists())
            self.assertEqual(list(self.root.glob(".recovery-*")), [other])

    def test_destination_appearing_during_replay_is_preserved(self):
        def appearing(*args):
            result = verified_closure(*args)
            self.destination.mkdir()
            return result

        with patch("nfl_value.recovery.verified_closure", side_effect=appearing):
            with self.assertRaisesRegex(ValueError, "appeared"):
                self.restore()
        self.assertTrue(self.destination.is_dir())
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(list(self.root.glob(".recovery-*")), [])

    def test_cli_pack_and_restore_record_provenance_without_publishing(self):
        saved = self.root / "review.zip"
        saved.write_bytes(self.review)
        out = StringIO()
        with patch("nfl_value.recovery_cli.committed_revision", return_value=REVISION):
            with patch("sys.stdout", out):
                code = main(
                    [
                        "pack",
                        str(saved),
                        "--sha256",
                        sha256(self.review),
                        "--store-root",
                        str(self.root),
                        "--destination",
                        str(self.root / "archives"),
                    ]
                )
            self.assertEqual(code, 0)
            packed = json.loads(out.getvalue())
            self.assertFalse(packed["uploaded"])
            out = StringIO()
            with patch("sys.stdout", out):
                code = main(
                    [
                        "restore",
                        "--archive",
                        packed["archive"],
                        "--sha256",
                        packed["archive_sha256"],
                        "--destination",
                        str(self.destination),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["validator_code_revision"], REVISION)

    def test_cli_download_canonical_url_and_external_pin(self):
        pin = sha256(self.body)
        prefix = "https://github.com/AryanParte/nfl-player-value/releases/download/"
        url = f"{prefix}explorer-archive/{pin}.zip"
        with (
            patch("nfl_value.recovery_cli.committed_revision", return_value=REVISION),
            patch(
                "nfl_value.recovery_cli.fetch_public", return_value=SimpleNamespace(body=self.body)
            ) as fetch,
            patch("sys.stderr", StringIO()),
            patch("sys.stdout", StringIO()),
        ):
            for invalid in (
                url.replace("AryanParte", "someone"),
                url + "?token=bad",
                url.replace("explorer-archive", ".."),
            ):
                self.assertEqual(
                    main(
                        [
                            "restore",
                            "--url",
                            invalid,
                            "--sha256",
                            pin,
                            "--destination",
                            str(self.destination),
                        ]
                    ),
                    1,
                )
                fetch.assert_not_called()
            fetch.return_value = SimpleNamespace(body=self.body + b"changed")
            self.assertEqual(
                main(
                    [
                        "restore",
                        "--url",
                        url,
                        "--sha256",
                        pin,
                        "--destination",
                        str(self.destination),
                    ]
                ),
                1,
            )
            self.assert_unpublished()
            fetch.return_value = SimpleNamespace(body=self.body)
            self.assertEqual(
                main(
                    [
                        "restore",
                        "--url",
                        url,
                        "--sha256",
                        pin,
                        "--destination",
                        str(self.destination),
                    ]
                ),
                0,
            )
            self.assertEqual(fetch.call_args.args[0], url)

    def test_cli_dirty_code_guard_precedes_io(self):
        with (
            patch(
                "nfl_value.recovery_cli.committed_revision", side_effect=ValueError("dirty source")
            ),
            patch("nfl_value.recovery_cli.read_bounded") as read,
            patch("sys.stderr", StringIO()),
        ):
            self.assertEqual(main(["pack", "absent.zip", "--sha256", "a" * 64]), 1)
            read.assert_not_called()
