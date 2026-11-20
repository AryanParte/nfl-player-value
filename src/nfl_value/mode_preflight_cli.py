"""Offline mode preflight and independent reconstruction; no NFL command exists."""

import argparse
import json
from pathlib import Path
import socket
import sys

import numpy as np

from nfl_value.coarse_control_study import kernel_hash
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes
from nfl_value.mode_preflight import experiment, load, save


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=Path("config/mode-preflight-v1.json"))
    parser.add_argument("--offline", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("replay").add_argument("report_id")
    args = parser.parse_args(argv)
    if args.offline:

        def forbidden(*_args, **_kwargs):
            raise OSError("network disabled for offline preflight")

        socket.socket = socket.create_connection = socket.getaddrinfo = forbidden
    output = SnapshotStore(args.store)
    try:
        source = kernel_hash()
        expected = None
        if args.command == "replay":
            expected, previous = load(output, args.report_id)
            plan, revision = expected["plan"], expected["code_revision"]
        else:
            plan, revision = json.loads(args.plan.read_text()), committed_revision()
        result, timings = experiment(
            plan,
            progress=lambda s: print(s, file=sys.stderr, flush=True),
            checkpoint=lambda _key, case: output.put(json_bytes(case)),
        )
        rid, manifest = save(output, result, revision, source)
        if expected is not None and (
            rid != args.report_id
            or json_bytes(manifest) != json_bytes(expected)
            or json_bytes(result) != json_bytes(previous)
        ):
            raise ValueError("complete preflight failed independent reconstruction")
        print(
            json.dumps(
                dict(
                    report_id=rid,
                    screen_passed=result["screen_passed"],
                    numerical_certified=False,
                    ranking_ready=False,
                    timings=timings,
                ),
                indent=2,
            )
        )
    except (ValueError, OSError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        print(f"Mode preflight failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
