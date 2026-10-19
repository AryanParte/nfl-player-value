"""The lease must fail closed across processes and Git worktrees."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_lock import DirectoryLock, LockError, resolve_lock


ROOT = Path(__file__).resolve().parents[1]


class RunLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.lease = DirectoryLock(self.base / "development.lock")

    def test_claim_check_and_release_require_owner(self):
        owner = self.lease.claim("unit-test")
        self.assertEqual(self.lease.check(owner["token"])["run_id"], "unit-test")
        with self.assertRaises(LockError):
            self.lease.claim("overlap")
        with self.assertRaises(LockError):
            self.lease.release("0" * 64)
        self.lease.check(owner["token"])
        self.lease.release(owner["token"])
        self.assertFalse(self.lease.path.exists())
        next_owner = self.lease.claim("next-run")
        with self.assertRaises(LockError):
            self.lease.release(owner["token"])
        self.lease.check(next_owner["token"])

    def test_two_processes_cannot_claim_same_lease(self):
        code = (
            "import json,sys; from pathlib import Path; "
            "from scripts.run_lock import DirectoryLock; "
            "print(json.dumps(DirectoryLock(Path(sys.argv[1])).claim(sys.argv[2])))"
        )
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", code, str(self.lease.path), f"run-{index}"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(2)
        ]
        outputs = [process.communicate(timeout=10) for process in processes]
        self.assertEqual(sorted(process.returncode for process in processes), [0, 1])
        winner = next(
            json.loads(output[0])
            for process, output in zip(processes, outputs)
            if process.returncode == 0
        )
        self.lease.check(winner["token"])

    def test_failed_metadata_write_removes_only_own_claim(self):
        with patch("scripts.run_lock.json.dump", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.lease.claim("failed-write")
        self.assertFalse(self.lease.path.exists())
        self.lease.claim("retry")

    def test_incomplete_claim_requires_manual_recovery(self):
        self.lease.path.mkdir()
        with self.assertRaises(LockError):
            self.lease.inspect()
        with self.assertRaises(LockError):
            self.lease.claim("must-not-steal")
        # Simulates an operator confirming the owner has stopped, then moving
        # the entire stale directory aside. Age or a PID check is insufficient.
        archive = self.base / "confirmed-stopped-run"
        self.lease.path.rename(archive)
        self.lease.claim("recovered-run")
        self.assertTrue(archive.is_dir())

    def test_old_timestamp_and_missing_pid_do_not_expire_lease(self):
        owner = self.lease.claim("old-but-potentially-active")
        metadata = next(self.lease.path.iterdir())
        owner.update(created_at="2000-01-01T00:00:00+00:00", claim_process_id=-1)
        metadata.write_text(json.dumps(owner), encoding="utf-8")
        with self.assertRaises(LockError):
            self.lease.claim("must-not-steal")
        self.lease.check(owner["token"])

    def test_invalid_metadata_and_path_tokens_fail_closed(self):
        owner = self.lease.claim("valid-owner")
        with self.assertRaises(LockError):
            self.lease.release("../../other")
        metadata = next(self.lease.path.iterdir())
        metadata.write_text("{", encoding="utf-8")
        with self.assertRaises(LockError):
            self.lease.release(owner["token"])
        self.assertTrue(self.lease.path.exists())

    def test_cli_checks_origin_and_all_worktrees_share_lease(self):
        repo = self.base / "canonical"
        repo.mkdir()

        def git(*args):
            return subprocess.run(
                ["git", "-C", str(repo), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        git("init", "-b", "main")
        git("remote", "add", "origin", "https://github.com/example/wrong.git")
        with self.assertRaises(LockError):
            resolve_lock(repo)
        git("remote", "set-url", "origin", "https://github.com/AryanParte/nfl-player-value.git")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "Fixture")
        worktree = self.base / "linked"
        git("worktree", "add", "-b", "codex/test", str(worktree))
        main_lease = resolve_lock(repo)
        linked_lease = resolve_lock(worktree)
        self.assertEqual(main_lease.path.resolve(), linked_lease.path.resolve())
        owner = main_lease.claim("canonical-owner")
        with self.assertRaises(LockError):
            linked_lease.claim("linked-overlap")
        linked_lease.check(owner["token"])


if __name__ == "__main__":
    unittest.main()
