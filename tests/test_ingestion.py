"""Offline synthetic source fixtures; no live network or NFL model assertions."""

from contextlib import redirect_stdout
import csv
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.ingestion import Download, SnapshotStore, capture, fetch_public, json_bytes, replay, resolve_asset, sha256
from nfl_value.ingest_cli import main
from nfl_value.source_audit import audit_csv
from nfl_value.sources import source_spec


WHEN = "2026-10-19T20:00:00+00:00"
REVISION = "a" * 40


def csv_gzip(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return gzip.compress(buffer.getvalue().encode(), mtime=0)


def play(**changes):
    row = {"game_id": "2026_01_ATL_TB", "play_id": "1", "season": "2026", "season_type": "REG", "week": "1", "play_type_nfl": "PASS", "epa": "0.25"}
    row.update(changes)
    return row


def roster(**changes):
    row = {"season": "2026", "team": "ATL", "gsis_id": "00-0000001", "espn_id": "123", "position": "QB", "week": "1"}
    row.update(changes)
    return row


def depth(**changes):
    row = {"dt": "2026-09-10T07:00:00Z", "team": "ATL", "gsis_id": "00-0000001", "espn_id": "123", "pos_grp_id": "1", "pos_slot": "1", "pos_rank": "1", "pos_abb": "QB"}
    row.update(changes)
    return row


class FakeSource:
    def __init__(self, raw=None, kind="pbp"):
        self.spec = source_spec(kind, 2026)
        self.raw = raw if raw is not None else csv_gzip([play(), play(play_id="2", play_type_nfl="END_GAME", epa="")])
        self.metadata = {
            "tag_name": self.spec.tag,
            "assets": [{"id": 123, "name": self.spec.filename, "size": len(self.raw), "digest": f"sha256:{sha256(self.raw)}", "updated_at": "2026-10-19T19:00:00Z", "browser_download_url": self.spec.download_url}],
        }
        self.license = b"Attribution 4.0 International\nSynthetic license fixture.\n"
        self.calls = []

    def fetch(self, url, max_bytes):
        self.calls.append(url)
        responses = {self.spec.metadata_url: json_bytes(self.metadata), self.spec.download_url: self.raw, self.spec.license_url: self.license}
        body = responses[url]
        if len(body) > max_bytes:
            raise ValueError("download exceeds requested size")
        return Download(body, WHEN, {"ETag": '"synthetic"'})


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SnapshotStore(Path(self.temp.name))
        self.source = FakeSource()

    def capture(self, source=None):
        source = source or self.source
        return capture(self.store, source.spec, code_revision=REVISION, fetch=source.fetch)

    def test_capture_is_deterministic_and_replay_is_offline(self):
        receipt_id, receipt = self.capture()
        again, _ = self.capture()
        self.assertEqual(receipt_id, again)
        self.assertEqual(receipt["objects"]["raw"], sha256(self.source.raw))
        self.assertEqual(receipt["audit"]["missing_fields"]["epa"], 1)
        self.assertEqual(receipt["audit"]["games"]["2026_01_ATL_TB"]["end_game_markers"], 1)
        self.assertFalse(receipt["audit"]["ranking_ready"])
        with patch("nfl_value.ingestion.build_opener", side_effect=AssertionError("network attempted")):
            self.assertEqual(replay(self.store, receipt_id), receipt)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--store", str(self.store.root), "replay", receipt_id]), 0)
            self.assertEqual(json.loads(output.getvalue())["receipt_id"], receipt_id)

    def test_source_corrections_preserve_original_receipt(self):
        first_id, first = self.capture()
        revised = FakeSource(csv_gzip([play(epa="0.5")]))
        new_id, new = self.capture(revised)
        self.assertNotEqual(first_id, new_id)
        self.assertNotEqual(first["objects"]["raw"], new["objects"]["raw"])
        self.assertEqual(replay(self.store, first_id), first)
        self.assertEqual(replay(self.store, new_id), new)
        self.assertEqual(len(list((self.store.root / "manifests").glob("*.json"))), 2)

    def test_mutation_between_metadata_and_download_fails_without_receipt(self):
        self.source.raw = self.source.raw[:-1] + bytes([self.source.raw[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, "size/SHA-256"):
            self.capture()
        self.assertFalse((self.store.root / "manifests").exists())

    def test_corrupt_or_missing_objects_are_detected_and_never_overwritten(self):
        receipt_id, receipt = self.capture()
        raw_path = self.store.root / "objects" / receipt["objects"]["raw"]
        raw_path.write_bytes(b"damaged")
        with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
            replay(self.store, receipt_id)
        with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
            self.store.put(self.source.raw)
        self.assertEqual(raw_path.read_bytes(), b"damaged")
        raw_path.unlink()
        with self.assertRaises(FileNotFoundError):
            replay(self.store, receipt_id)

    def test_license_change_or_download_failure_publishes_no_receipt(self):
        self.source.license = b"Changed terms"
        with self.assertRaisesRegex(ValueError, "license changed"):
            self.capture()
        with self.assertRaises(OSError):
            capture(self.store, self.source.spec, code_revision=REVISION, fetch=lambda *args: (_ for _ in ()).throw(OSError("outage")))
        self.assertFalse((self.store.root / "manifests").exists())

    def test_missing_ambiguous_unhashed_or_wrong_source_asset_fails(self):
        good = self.source.metadata
        cases = []
        cases.append({**good, "assets": []})
        cases.append({**good, "assets": good["assets"] * 2})
        cases.append({**good, "tag_name": "wrong"})
        for field, value in [("digest", None), ("size", True), ("browser_download_url", "https://example.com/data")]:
            cases.append({**good, "assets": [{**good["assets"][0], field: value}]})
        for metadata in cases:
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                resolve_asset(json_bytes(metadata), self.source.spec)

    def test_future_source_metadata_and_invalid_gzip_publish_no_receipt(self):
        self.source.metadata["assets"][0]["updated_at"] = "2026-10-20T20:00:00Z"
        with self.assertRaisesRegex(ValueError, "later than retrieval"):
            self.capture()
        with self.assertRaises(OSError):
            self.capture(FakeSource(b"not gzip"))
        self.assertFalse((self.store.root / "manifests").exists())

    def test_replay_verifies_saved_metadata_license_and_audit(self):
        receipt_id, receipt = self.capture()
        for key in ("release_metadata", "license"):
            bad = {**receipt, "objects": {**receipt["objects"], key: self.store.put(b"wrong")}}
            bad_id = self.store.put(json_bytes(bad), manifest=True)
            with self.subTest(key=key), self.assertRaises((ValueError, KeyError)):
                replay(self.store, bad_id)
        changed = {**receipt, "audit": {**receipt["audit"], "rows": 999}}
        changed_id = self.store.put(json_bytes(changed), manifest=True)
        with self.assertRaisesRegex(ValueError, "audit differs"):
            replay(self.store, changed_id)
        self.assertEqual(replay(self.store, receipt_id), receipt)

    def test_hash_paths_and_source_registry_are_not_arbitrary(self):
        for unsafe in ("../secret", "A" * 64, "", "a" * 63):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                self.store.read(unsafe)
        for kind, year in (("pff", 2026), ("depth_charts", 2024), ("pbp", True)):
            with self.subTest(kind=kind, year=year), self.assertRaises(ValueError):
                source_spec(kind, year)

    def test_atomic_write_failure_does_not_publish_partial_object(self):
        with patch("nfl_value.ingestion.os.link", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.store.put(b"complete object")
        self.assertEqual(list((self.store.root / "objects").iterdir()), [])

    def test_http_scope_and_byte_limits_are_enforced_without_network(self):
        with patch("nfl_value.ingestion.build_opener") as opener:
            for url in ("http://github.com/file", "https://example.com/file", "https://github.com:8443/file", "https://user:password@github.com/file"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    fetch_public(url)
            opener.assert_not_called()
            response = io.BytesIO(b"oversize")
            response.url = self.source.spec.download_url
            response.headers = {}
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(ValueError, "download size limit"):
                fetch_public(self.source.spec.download_url, 4)

    def test_corrupt_manifest_and_oversize_local_object_fail(self):
        receipt_id, _ = self.capture()
        path = self.store.root / "manifests" / f"{receipt_id}.json"
        path.write_text('{}\n')
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            replay(self.store, receipt_id)
        digest = self.store.put(b"12345")
        with patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "size limit"):
                self.store.read(digest)


class SourceAuditTests(unittest.TestCase):
    def audit(self, kind, rows):
        return audit_csv(csv_gzip(rows), source_spec(kind, 2026), observed_at=WHEN)

    def test_missing_ids_are_reported_not_invented(self):
        for kind, row in [("rosters", roster(gsis_id="")), ("depth_charts", depth(gsis_id=""))]:
            report = self.audit(kind, [row])
            self.assertEqual(report["missing_fields"]["gsis_id"], 1)
            self.assertEqual(report["teams"], ["ATL"])
            self.assertFalse(report["ranking_ready"])

    def test_legacy_ids_are_preserved_but_not_declared_canonical(self):
        report = self.audit("depth_charts", [depth(gsis_id="ABC123456")])
        self.assertEqual(report["invalid_fields"]["noncanonical_gsis_id"], 1)
        self.assertEqual(report["missing_fields"]["gsis_id"], 0)
        self.assertFalse(report["ranking_ready"])

    def test_repeated_player_on_distinct_depth_snapshots_is_preserved(self):
        report = self.audit("depth_charts", [depth(), depth(dt="2026-09-11T07:00:00Z")])
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["depth_timestamps"]["count"], 2)

    def test_duplicate_source_keys_and_malformed_columns_are_rejected(self):
        for kind, row in [("pbp", play()), ("rosters", roster()), ("depth_charts", depth())]:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "duplicate source key"):
                self.audit(kind, [row, row])
        for body in (b"game_id,game_id\na,a\n", b"wrong\nvalue\n"):
            with self.assertRaises(ValueError):
                audit_csv(gzip.compress(body), source_spec("pbp", 2026), observed_at=WHEN)
        row = play()
        malformed = gzip.decompress(csv_gzip([row])) + b"a,b\n"
        with self.assertRaisesRegex(ValueError, "ragged"):
            audit_csv(gzip.compress(malformed), source_spec("pbp", 2026), observed_at=WHEN)

    def test_future_depth_timestamps_and_naive_times_are_rejected(self):
        for timestamp in ("2026-10-20T07:00:00Z", "2026-10-19T07:00:00"):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                self.audit("depth_charts", [depth(dt=timestamp)])

    def test_incomplete_and_postseason_games_are_not_promoted(self):
        rows = [play(), play(game_id="2026_19_CAR_NO", week="19", season_type="POST", play_type_nfl="END_GAME")]
        report = self.audit("pbp", rows)
        self.assertEqual(report["games"]["2026_01_ATL_TB"]["end_game_markers"], 0)
        self.assertEqual(report["games"]["2026_19_CAR_NO"]["season_type"], "POST")
        self.assertFalse(report["ranking_ready"])

    def test_season_key_and_identity_errors_fail(self):
        cases = [("pbp", play(season="2025")), ("pbp", play(week="2")), ("pbp", play(play_id="-1")), ("pbp", play(epa="NaN")), ("pbp", play(epa="inf")), ("pbp", play(epa="text")), ("depth_charts", depth(pos_rank="0"))]
        for kind, row in cases:
            with self.subTest(kind=kind, row=row), self.assertRaises(ValueError):
                self.audit(kind, [row])

    def test_empty_and_oversized_decoded_sources_fail(self):
        raw = csv_gzip([play()])
        header_only = gzip.decompress(raw).splitlines(keepends=True)[0]
        with self.assertRaisesRegex(ValueError, "empty source"):
            audit_csv(gzip.compress(header_only), source_spec("pbp", 2026), observed_at=WHEN)
        with patch("nfl_value.source_audit.MAX_DECODED_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "size limit"):
                audit_csv(raw, source_spec("pbp", 2026), observed_at=WHEN)


if __name__ == "__main__":
    unittest.main()
