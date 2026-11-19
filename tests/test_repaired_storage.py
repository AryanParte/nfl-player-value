"""Bounded transport checks; statistical validation has separate known-answer tests."""

from copy import deepcopy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.repaired_functional import load, save


class RepairedStorageTests(unittest.TestCase):
    def fixture(self):
        return dict(
            experiment="repaired-functional-controls-v1",
            plan=json.loads(Path("config/repaired-functional-v2.json").read_text()),
            cases=[dict(target=i, payload=str(i) * 10000) for i in range(5)],
        )

    def test_large_case_index_reconstructs_exact_bytes_without_raising_object_cap(self):
        result = self.fixture()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 20000),
            patch("nfl_value.repaired_functional.validate_known"),
        ):
            output = SnapshotStore(directory)
            rid, manifest = save(output, result, "a" * 40)
            index = json.loads(output.read(manifest["objects"]["study"]))
            self.assertEqual(index["storage_format"], "repaired-functional-case-index-v1")
            self.assertTrue(
                all(p.stat().st_size <= 20000 for p in (output.root / "objects").iterdir())
            )
            self.assertEqual(json_bytes(load(output, rid)[1]), json_bytes(result))
            self.assertEqual(save(output, result, "a" * 40)[0], rid)
            with self.assertRaisesRegex(ValueError, "size limit"):
                output.put(json_bytes(result))

    def test_incomplete_reordered_duplicate_and_corrupted_shards_fail(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 20000),
            patch("nfl_value.repaired_functional.validate_known"),
        ):
            output = SnapshotStore(directory)
            rid, m = save(output, self.fixture(), "a" * 40)
            original = json.loads(output.read(m["objects"]["study"]))
            for mutation in ("omit", "reorder", "duplicate", "logical"):
                index, manifest = deepcopy(original), deepcopy(m)
                if mutation == "omit":
                    index["cases"].pop()
                elif mutation == "reorder":
                    index["cases"].reverse()
                elif mutation == "duplicate":
                    index["cases"][1] = index["cases"][0]
                else:
                    index["logical_sha256"] = "0" * 64
                manifest["objects"]["study"] = output.put(json_bytes(index))
                bad = output.put(json_bytes(manifest), manifest=True)
                with self.assertRaisesRegex(ValueError, "index|logical"):
                    load(output, bad)
            first = output.root / "objects" / original["cases"][0][1]
            first.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
                load(output, rid)
            first.unlink()
            with self.assertRaises(FileNotFoundError):
                load(output, rid)

    def test_recovery_proof_rejects_any_computational_change(self):
        check = runpy.run_path("scripts/recover_repaired_controls.py", run_name="recovery_test")[
            "unchanged_computation"
        ]
        old = {
            "repaired_functional.py": b"def save(): return 1\ndef load(): return 2\ndef known(): return 3\n",
            "model.py": b"value = 4\n",
        }
        allowed = {
            **old,
            "repaired_functional.py": old["repaired_functional.py"].replace(
                b"return 1", b"return 5"
            ),
        }
        check(old, allowed)
        for changed in (
            {**allowed, "model.py": b"value = 5\n"},
            {**allowed, "new_model.py": b"value = 6\n"},
            {
                **allowed,
                "repaired_functional.py": allowed["repaired_functional.py"].replace(
                    b"return 3", b"return 6"
                ),
            },
        ):
            with self.assertRaisesRegex(ValueError, "computational|module set"):
                check(old, changed)


if __name__ == "__main__":
    unittest.main()
