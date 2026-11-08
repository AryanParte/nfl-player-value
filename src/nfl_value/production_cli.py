"""GitHub-native Explorer refresh, immutable retention and publication checks.

Only `retain` needs contents:write. Capture/build and previous-release recovery
have no publication authority. No command changes a development automation.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, capture, json_bytes
from nfl_value.launch_bundle import LAUNCH_STORES, build_launch, restore_launch
from nfl_value.production import (
    read_release,
    record_for,
    select_previous,
    tag_digest,
    verify_release,
)
from nfl_value.recovery_io import read_bounded, save_recovery
from nfl_value.refresh_candidate import prepare_candidate, replay_candidate
from nfl_value.review_cli import build_review
from nfl_value.sources import source_spec


REPOSITORY = "AryanParte/nfl-player-value"


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def download(tag, destination):
    pin = tag_digest(tag)
    destination.mkdir(parents=True, exist_ok=False)
    gh(
        "release",
        "download",
        tag,
        "--repo",
        REPOSITORY,
        "--dir",
        str(destination),
        "--pattern",
        "release.json",
        "--pattern",
        pin + ".zip",
    )
    return read_release(destination, pin)


def previous(root, workspace, *, bootstrap):
    pages = json.loads(
        gh("api", "--paginate", "--slurp", f"repos/{REPOSITORY}/releases?per_page=100")
    )
    tag = select_previous(pages, bootstrap=bootstrap)
    explorer = None
    if tag is None:
        workspace.mkdir(parents=True, exist_ok=False)
    else:
        body, record = download(tag, workspace.with_name(workspace.name + "-download"))
        restore_launch(root, body, tag_digest(tag), workspace)
        explorer = record["explorer_report"]
    state = {"retained_tag": tag, "explorer_report": explorer}
    (workspace / "previous.json").write_bytes(json_bytes(state))
    return state


def build(root, workspace, output, revision):
    if output.exists():
        raise ValueError("production output must be a new directory")
    state = json.loads((workspace / "previous.json").read_bytes())
    stores = [SnapshotStore(workspace / name) for name in LAUNCH_STORES]
    ids = {}
    for kind in ("pbp", "schedules", "depth_charts", "rosters"):
        ids[kind], _ = capture(stores[0], source_spec(kind, 2026), code_revision=revision)
    cutoff = datetime.now(timezone.utc)
    _, readiness, cid = prepare_candidate(
        *stores,
        ids,
        cutoff=cutoff,
        code_revision=revision,
        previous_explorer=state["explorer_report"],
    )
    (workspace / "readiness.json").write_bytes(json_bytes(readiness))
    if cid is None:
        raise ValueError("sources not ready: " + str(readiness["blockers"]))
    candidate = replay_candidate(*stores, cid)
    reviewed = build_review(
        root, candidate["explorer_report"], *stores[:3], workspace / "reviews", isolated=True
    )
    body, _ = build_launch(
        root,
        workspace,
        read_bounded(Path(reviewed["archive"])),
        reviewed["archive_sha256"],
        cid,
        datetime.now(timezone.utc),
        revision,
    )
    if committed_revision() != revision:
        raise ValueError("producer changed during refresh")
    record = record_for(body, state["retained_tag"])
    save_recovery(output, body)
    (output / "release.json").write_bytes(json_bytes(record))
    return record


def retain(root, directory, destination, pin, revision):
    """Publish a NEW archive release only after independent download/replay.

    Never edit an existing public release or overwrite assets. A failed upload
    leaves a draft for diagnosis; reruns use new time-addressed packages/tags.
    """
    body, record = read_release(directory, pin)
    if record["code_revision"] != revision:
        raise ValueError("release producer differs from workflow revision")
    # No mutations until local replay + a real-time source recheck succeeds.
    verify_release(
        root,
        directory,
        destination.with_name(destination.name + "-preflight"),
        expected_pin=pin,
        expected_revision=revision,
    )
    notes = directory / "release-notes.md"
    notes.write_text(
        "Exploratory observations, not CAVAA rankings. All modules remain unadmitted.\n\n"
        f"Game cutoff: {record['game_cutoff']}\n\nArchive SHA-256: `{pin}`\n\n"
        "This immutable retention record does not certify successful Pages deployment. "
        "See the workflow run for deployment status. Preserve the source attribution "
        "and licenses inside the archive.\n"
    )
    tag = record["tag"]
    gh(
        "release",
        "create",
        tag,
        str(directory / (pin + ".zip")),
        str(directory / "release.json"),
        "--repo",
        REPOSITORY,
        "--target",
        revision,
        "--draft",
        "--prerelease",
        "--latest=false",
        "--title",
        "2026 Defense Explorer " + pin[:12],
        "--notes-file",
        str(notes),
    )
    downloaded, remote_record = download(tag, destination)
    if downloaded != body or remote_record != record:
        raise ValueError("remote assets differ from verified local release")
    verify_release(
        root,
        destination,
        destination.with_name(destination.name + "-replayed"),
        expected_pin=pin,
        expected_revision=revision,
    )
    gh(
        "release",
        "edit",
        tag,
        "--repo",
        REPOSITORY,
        "--draft=false",
        "--prerelease",
        "--latest=false",
    )
    return {"retained_tag": tag, "remote_download_replayed": True, "deployed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prev = commands.add_parser("previous")
    prev.add_argument("--workspace", required=True, type=Path)
    prev.add_argument("--bootstrap", action="store_true")
    prepare = commands.add_parser("build")
    prepare.add_argument("--workspace", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path)
    for name in ("verify", "retain"):
        command = commands.add_parser(name)
        command.add_argument("--input", required=True, type=Path)
        command.add_argument("--destination", required=True, type=Path)
        command.add_argument("--sha256", required=True)
        command.add_argument("--expected-revision", required=True)
        if name == "verify":
            command.add_argument("--site", type=Path)
    args = parser.parse_args(argv)
    try:
        revision = committed_revision()
        root = Path.cwd()
        if args.command == "previous":
            result = previous(root, args.workspace, bootstrap=args.bootstrap)
        elif args.command == "build":
            result = build(root, args.workspace, args.output, revision)
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
                    handle.write(f"sha256={result['archive_sha256']}\n")
        else:
            if args.expected_revision != revision:
                raise ValueError("validator checkout differs from workflow revision")
            if args.command == "retain":
                result = retain(root, args.input, args.destination, args.sha256, revision)
            else:
                result = verify_release(
                    root,
                    args.input,
                    args.destination,
                    expected_pin=args.sha256,
                    expected_revision=revision,
                    site=args.site,
                )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        csv.Error,
        zipfile.BadZipFile,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Explorer production step failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
