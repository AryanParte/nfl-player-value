"""The historical exception never creates an upstream checksum or production receipt."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.ingestion import Download, SnapshotStore, json_bytes, replay, resolve_asset
from nfl_value.research_roster import ASSET_ID, UPDATED_AT, asset, capture_legacy, replay_legacy
from nfl_value.sources import source_spec
from test_ingestion import csv_gzip


class LegacyRosterTests(unittest.TestCase):
    def source(self):
        spec = source_spec("weekly_rosters", 2024)
        row = dict(
            season="2024",
            week="1",
            game_type="REG",
            team="BUF",
            gsis_id="00-0000001",
            espn_id="1",
            position="QB",
            depth_chart_position="QB",
            status="ACT",
            status_description_abbr="A",
        )
        compressed = csv_gzip([row])
        raw = compressed + bytes(699786 - len(compressed))
        meta = {
            "tag_name": spec.tag,
            "assets": [
                {
                    "id": ASSET_ID,
                    "name": spec.filename,
                    "size": len(raw),
                    "digest": None,
                    "updated_at": UPDATED_AT,
                    "browser_download_url": spec.download_url,
                }
            ],
        }

        def fetch(url, max_bytes=None):
            body = (
                json_bytes(meta)
                if url == spec.metadata_url
                else raw
                if url == spec.download_url
                else b"Attribution 4.0 International\nSynthetic fixture"
            )
            return Download(body, "2026-11-07T20:00:00+00:00", {})

        return spec, meta, fetch

    def test_offline_replay_and_explicit_integrity_limits(self):
        spec, meta, fetch = self.source()
        with self.assertRaisesRegex(ValueError, "published SHA-256"):
            resolve_asset(json_bytes(meta), spec)
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            rid, saved = capture_legacy(store, code_revision="a" * 40, fetch=fetch)
            with patch(
                "urllib.request.OpenerDirector.open",
                side_effect=AssertionError("network forbidden"),
            ):
                self.assertEqual(replay_legacy(store, rid), saved)
            self.assertIsNone(saved["asset"]["digest"])
            self.assertFalse(saved["upstream_sha256_available"])
            self.assertFalse(saved["ranking_ready"])
            with self.assertRaises(KeyError):
                replay(store, rid)
            altered = deepcopy(saved)
            altered["audit"]["rows"] += 1
            bad = store.put(json_bytes(altered), manifest=True)
            with self.assertRaisesRegex(ValueError, "audit replay mismatch"):
                replay_legacy(store, bad)
            path = store._path(saved["objects"]["raw"])
            path.write_bytes(b"corruption")
            with self.assertRaises(ValueError):
                replay_legacy(store, rid)

    def test_changed_asset_or_wrong_historical_version_is_rejected(self):
        _, meta, _ = self.source()
        for key, value in [
            ("id", 12),
            ("updated_at", "2026-11-07T20:00:00Z"),
            ("digest", "sha256:" + "a" * 64),
            ("size", 1),
        ]:
            changed = deepcopy(meta)
            changed["assets"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                asset(json_bytes(changed))
        changed = deepcopy(meta)
        changed["assets"].append(changed["assets"][0])
        with self.assertRaises(ValueError):
            asset(json_bytes(changed))

    def test_invalid_retrieval_chronology_publishes_no_receipt(self):
        spec, _, original = self.source()

        def fetch(url, max_bytes=None):
            value = original(url)
            return (
                Download(value.body, "2026-11-06T20:00:00+00:00", {})
                if url == spec.license_url
                else value
            )

        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            with self.assertRaisesRegex(ValueError, "chronology"):
                capture_legacy(store, code_revision="a" * 40, fetch=fetch)
            self.assertFalse((Path(tmp) / "manifests").exists())
            self.assertFalse((Path(tmp) / "objects").exists())

    def test_changed_during_capture_does_not_publish(self):
        spec, meta, original = self.source()
        calls = 0

        def fetch(url, max_bytes=None):
            nonlocal calls
            if url == spec.metadata_url:
                calls += 1
                changed = deepcopy(meta)
                if calls > 1:
                    changed["assets"][0]["updated_at"] = "2026-11-07T20:00:00Z"
                return Download(json_bytes(changed), "2026-11-07T20:00:00+00:00", {})
            return original(url)

        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(Path(tmp))
            with self.assertRaises(ValueError):
                capture_legacy(store, code_revision="a" * 40, fetch=fetch)
            self.assertFalse((Path(tmp) / "manifests").exists())
