#!/usr/bin/env python3
"""Hold a repository-wide development lease across separate agent tool calls.

The directory is the atomic claim. The random token belongs to one run, not a
process: a PID or timestamp cannot establish whether a Codex run has stopped.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


CANONICAL_ORIGINS = {
    "https://github.com/AryanParte/nfl-player-value.git",
    "git@github.com:AryanParte/nfl-player-value.git",
}
LOCK_NAME = "nfl-player-value-development.lock"
TOKEN_PATTERN = re.compile(r"[0-9a-f]{64}")


class LockError(RuntimeError):
    """The lease is held, malformed, or cannot be verified safely."""


class DirectoryLock:
    """Small filesystem API; CLI callers must resolve the Git common directory."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _owner_path(self, token: str) -> Path:
        if not TOKEN_PATTERN.fullmatch(token):
            raise LockError("Invalid owner token.")
        return self.path / f"owner-{token}.json"

    def claim(self, run_id: str) -> dict:
        if not run_id.strip() or len(run_id) > 200:
            raise LockError("Run ID must contain 1–200 characters.")
        token = secrets.token_hex(32)
        owner_path = self._owner_path(token)
        owner = {
            "schema_version": 1,
            "token": token,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "claim_process_id": os.getpid(),
        }
        try:
            self.path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise LockError("Development lease already exists; do not steal it.") from exc
        try:
            with owner_path.open("x", encoding="utf-8") as handle:
                json.dump(owner, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            # Clean up only this failed claim. A killed process may leave a
            # directory behind; future claims fail closed until manual recovery.
            owner_path.unlink(missing_ok=True)
            self.path.rmdir()
            raise
        return owner

    def inspect(self) -> dict:
        if self.path.is_symlink() or not self.path.is_dir():
            raise LockError("No valid development lease directory exists.")
        paths = list(self.path.iterdir())
        if len(paths) != 1 or not paths[0].name.startswith("owner-"):
            raise LockError("Lease metadata is incomplete or unexpected; recover manually.")
        path = paths[0]
        if path.is_symlink():
            raise LockError("Lease metadata must not be a symbolic link.")
        try:
            owner = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LockError("Lease metadata cannot be read safely.") from exc
        if (
            not isinstance(owner, dict)
            or owner.get("schema_version") != 1
            or not isinstance(owner.get("token"), str)
            or not isinstance(owner.get("run_id"), str)
            or not isinstance(owner.get("created_at"), str)
            or not isinstance(owner.get("claim_process_id"), int)
        ):
            raise LockError("Lease metadata has an invalid schema.")
        if self._owner_path(owner["token"]) != path:
            raise LockError("Lease token and metadata filename disagree.")
        return owner

    def check(self, token: str) -> dict:
        self._owner_path(token)
        owner = self.inspect()
        if not secrets.compare_digest(owner["token"], token):
            raise LockError("This run does not own the development lease.")
        return owner

    def release(self, token: str) -> None:
        self.check(token)
        # Each owner has a different filename. A duplicate release cannot
        # unlink a later owner's metadata even if a new claim has intervened.
        self._owner_path(token).unlink()
        self.path.rmdir()


def resolve_lock(repo: Path) -> DirectoryLock:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    if git("config", "--get", "remote.origin.url") not in CANONICAL_ORIGINS:
        raise LockError("Origin is not the canonical AryanParte/nfl-player-value repository.")
    common_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    return DirectoryLock(common_dir / LOCK_NAME)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    claim = commands.add_parser("claim")
    claim.add_argument("--run-id", required=True)
    commands.add_parser("status")
    for command in ("check", "release"):
        subcommand = commands.add_parser(command)
        subcommand.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    try:
        lease = resolve_lock(args.repo)
        if args.command == "claim":
            result = lease.claim(args.run_id)
        elif args.command == "release":
            lease.release(args.token)
            result = {"released": True}
        else:
            owner = lease.check(args.token) if args.command == "check" else lease.inspect()
            result = {key: value for key, value in owner.items() if key != "token"}
        print(json.dumps(result, sort_keys=True))
    except (LockError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Development lease failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
