"""Offline, immutable repaired-target study; never publishes player scores."""

import argparse
import json
from pathlib import Path
import socket
import sys

import numpy as np

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.repaired_functional import (
    archive,
    kernel_hash,
    known,
    load,
    save,
    validate_archive,
    validate_known,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-store", type=Path, default=Path("data/derived/repaired-functional-controls")
    )
    parser.add_argument(
        "--controls-store", type=Path, default=Path("data/derived/repaired-functional-controls")
    )
    parser.add_argument("--offline", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("known")
    for command in ("replay", "archive", "replay-archive"):
        sub.add_parser(command).add_argument("report_id")
    args = parser.parse_args(argv)
    if args.offline:

        def forbidden(*_args, **_kwargs):
            raise OSError("network disabled for offline reconstruction")

        socket.socket = socket.create_connection = socket.getaddrinfo = forbidden
    output = SnapshotStore(args.output_store)
    controls = SnapshotStore(args.controls_store)
    progress = lambda s: print(s, file=sys.stderr, flush=True)
    try:
        executing_kernel = kernel_hash()
        expected = None
        if args.command.startswith("replay"):
            expected, old_result = load(output, args.report_id)
            revision = expected["code_revision"]
        else:
            revision = committed_revision()
        if args.command in ("known", "replay"):
            plan = (
                expected["plan"]
                if expected
                else json.loads(Path("config/repaired-functional-v1.json").read_text())
            )
            result, timings = known(
                plan,
                progress,
                lambda name, r: output.put(
                    json_bytes(dict(code_revision=revision, case=name, record=r))
                ),
            )
            validate_known(result)
        else:
            control_id = old_result["control_report"] if expected else args.report_id
            result, timings = archive(
                controls,
                control_id,
                progress,
                lambda name, r: output.put(
                    json_bytes(dict(code_revision=revision, case=name, record=r))
                ),
            )
            validate_archive(result)
        rid, manifest = save(output, result, revision, expected_kernel=executing_kernel)
        if expected and (
            rid != args.report_id
            or json_bytes(manifest) != json_bytes(expected)
            or json_bytes(result) != json_bytes(old_result)
        ):
            raise ValueError("complete independent study does not reproduce byte-for-byte")
        print(
            json.dumps(
                dict(
                    report_id=rid,
                    controls_passed=result.get("controls_passed"),
                    numerical_pilot_passed=result.get("numerical_pilot_passed"),
                    timings=timings,
                    ranking_ready=False,
                ),
                indent=2,
            ),
            flush=True,
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Repaired functional study failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
