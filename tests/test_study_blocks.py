"""Large known-answer cases retain every trial within the existing object cap."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.coarse_control_study import kernel_hash, load, save
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.study_blocks import checkpoint, put_case, read_case


def case(index=0):
    return dict(target=index, records=[dict(trial=i, payload="x" * 1800) for i in range(12)])


class StudyBlockTests(unittest.TestCase):
    def test_nested_case_storage_and_checkpoints_reconstruct_every_byte(self):
        plan = json.loads(Path("config/coarse-control-v2.json").read_text())
        result = dict(
            experiment="coarse-control-controls-v2", plan=plan, cases=[case(i) for i in range(5)]
        )
        with (
            tempfile.TemporaryDirectory() as path,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 12000),
            patch("nfl_value.coarse_control_study.validate_known"),
        ):
            output = SnapshotStore(path)
            witness = checkpoint(output, "a" * 40, "0", result["cases"][0])
            record = json.loads(output.read(witness))
            self.assertEqual(json_bytes(read_case(output, record["record_id"])), json_bytes(case()))
            rid, _ = save(output, result, "a" * 40, expected_kernel=kernel_hash())
            self.assertEqual(json_bytes(load(output, rid)[1]), json_bytes(result))
            self.assertTrue(
                all(p.stat().st_size <= 12000 for p in (Path(path) / "objects").iterdir())
            )
            with self.assertRaisesRegex(ValueError, "source changed"):
                save(output, result, "a" * 40, expected_kernel="0" * 64)

    def test_omitted_reordered_changed_and_corrupt_trials_fail(self):
        with (
            tempfile.TemporaryDirectory() as path,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 12000),
        ):
            output = SnapshotStore(path)
            rid = put_case(output, case())
            original = json.loads(output.read(rid))
            for change in ("omit", "reorder", "count", "start", "logical", "rows", "format"):
                bad = deepcopy(original)
                if change == "omit":
                    bad["blocks"].pop()
                elif change == "reorder":
                    bad["blocks"].reverse()
                elif change == "count":
                    bad["record_count"] += 1
                elif change == "start":
                    bad["blocks"][0]["start"] = True
                elif change == "logical":
                    bad["logical_sha256"] = "0" * 64
                elif change == "format":
                    bad["storage_format"] = "unknown"
                else:
                    rows = json.loads(output.read(bad["blocks"][0]["sha256"]))
                    rows[0]["payload"] = "changed"
                    bad["blocks"][0]["sha256"] = output.put(json_bytes(rows))
                with self.assertRaises(ValueError, msg=change):
                    read_case(output, output.put(json_bytes(bad)))
            (output.root / "objects" / original["blocks"][0]["sha256"]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                read_case(output, rid)

    def test_small_cases_are_unchanged_and_one_oversized_trial_cannot_bypass_cap(self):
        with (
            tempfile.TemporaryDirectory() as path,
            patch("nfl_value.ingestion.MAX_DOWNLOAD_BYTES", 4000),
        ):
            output = SnapshotStore(path)
            small = dict(records=[dict(trial=0, signed=-3)])
            rid = put_case(output, small)
            self.assertEqual(output.read(rid), json_bytes(small))
            with self.assertRaisesRegex(ValueError, "single trial"):
                put_case(output, dict(records=[dict(payload="x" * 5000)]))
            with self.assertRaisesRegex(ValueError, "nonempty trial list"):
                put_case(output, dict(payload="x" * 5000))


if __name__ == "__main__":
    unittest.main()
