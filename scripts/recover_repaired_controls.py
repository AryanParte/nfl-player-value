"""Recover all completed controls after the aggregate exceeded the object cap.

No numerical trial is rerun or relabeled. The receipt distinguishes the producing
kernel from packaging, and recovery proves that only save/load code changed.
"""

import argparse
import ast
import json
from pathlib import Path
import socket
import subprocess

from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.repaired_functional import kernel_hash, load, save, validate_known

PRODUCER = "3774295badc90b699fc0b4433dd23f16df80ec27"
PRODUCING_KERNEL = "0bf3bd28b50d3f4176b3a4effe4388dd1d62a0a15bbd4edb31678fb47419170d"
CHECKPOINTS = [
    "3890b042ae5d962f52cdf454090625d12e3866ac9b101b949992e34d0aa029ea",
    "7523ed09f2f45c64b8b3e77086b31db3e61bda2e892ae64f89d7fbede8e19a0b",
    "9deae104e8115db70eac934c002f7faf2d7e35a3b12ada6843387ad3f6ab7ae1",
    "ca4d094c9808acaa44fd5e52f8cbf8c2ccf090b300a965dc9a204226896d2861",
    "346627611dfab8b16a125fc40914fca5be5a112f8f924989321df2f019c5370f",
]


def unchanged_computation(original, current):
    if set(original) != set(current):
        raise ValueError("statistical package module set changed")
    for name, source in original.items():
        if name == "repaired_functional.py":

            def computational_tree(body):
                tree = ast.parse(body)
                tree.body = [
                    n
                    for n in tree.body
                    if not (isinstance(n, ast.FunctionDef) and n.name in ("save", "load"))
                ]
                return ast.dump(tree, include_attributes=False)

            if computational_tree(source) != computational_tree(current[name]):
                raise ValueError("computational syntax changed beyond save/load")
        elif source != current[name]:
            raise ValueError(f"computational module changed: {name}")


def verify_source():
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", PRODUCER, "--", "src/nfl_value"], text=True
    ).splitlines()
    original = {
        Path(p).name: subprocess.check_output(["git", "show", f"{PRODUCER}:{p}"])
        for p in files
        if Path(p).parent == Path("src/nfl_value") and p.endswith(".py")
    }
    if sha256(json_bytes({n: sha256(v) for n, v in original.items()})) != PRODUCING_KERNEL:
        raise ValueError("original producing kernel fingerprint differs")
    current = {p.name: p.read_bytes() for p in Path("src/nfl_value").glob("*.py")}
    unchanged_computation(original, current)


def recover(directory):
    verify_source()
    executing_kernel, revision = kernel_hash(), committed_revision()
    output = SnapshotStore(directory)
    cases = []
    for i, digest in enumerate(CHECKPOINTS):
        checkpoint = json.loads(output.read(digest))
        if (
            set(checkpoint) != {"code_revision", "case", "record"}
            or checkpoint["code_revision"] != PRODUCER
            or checkpoint["case"] != str(i)
            or checkpoint["record"]["target"] != i
        ):
            raise ValueError("checkpoint producing revision or complete case order differs")
        cases.append(checkpoint["record"])
    result = dict(
        experiment="repaired-functional-controls-v1",
        plan=json.loads(Path("config/repaired-functional-v2.json").read_text()),
        cases=cases,
        controls_passed=all(c["decision"]["passed"] for c in cases),
        nfl_data_used=False,
        calibration_completed=False,
        ranking_ready=False,
    )
    validate_known(result)
    report, manifest = save(output, result, revision, expected_kernel=executing_kernel)
    loaded, restored = load(output, report)
    if json_bytes(loaded) != json_bytes(manifest) or json_bytes(restored) != json_bytes(result):
        raise ValueError("complete indexed study failed logical replay")
    receipt = dict(
        kind="repaired-functional-storage-recovery-v1",
        producing_revision=PRODUCER,
        producing_kernel_sha256=PRODUCING_KERNEL,
        packaging_revision=revision,
        packaging_kernel_sha256=executing_kernel,
        computation_check="all_modules_unchanged_except_save_load_syntax",
        checkpoints=CHECKPOINTS,
        logical_study_sha256=sha256(json_bytes(result)),
        report_id=report,
        same_declared_draws=True,
        ranking_ready=False,
    )
    receipt_id = output.put(json_bytes(receipt), manifest=True)
    return dict(
        report_id=report, recovery_receipt=receipt_id, controls_passed=result["controls_passed"]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store", type=Path)
    args = parser.parse_args()

    def forbidden(*_args, **_kwargs):
        raise OSError("network disabled for checkpoint recovery")

    socket.socket = socket.create_connection = socket.getaddrinfo = forbidden
    print(json.dumps(recover(args.store), indent=2))


if __name__ == "__main__":
    main()
