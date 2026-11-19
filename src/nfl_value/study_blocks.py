"""Bounded storage of complete trial records without changing numerical results."""

import json

from nfl_value.ingestion import json_bytes, sha256

FORMAT = "coarse-control-trial-blocks-v1"


def put_case(output, case):
    from nfl_value.ingestion import MAX_DOWNLOAD_BYTES

    body = json_bytes(case)
    if len(body) <= MAX_DOWNLOAD_BYTES:
        return output.put(body)
    records = case.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("oversized study case needs a nonempty trial list")
    blocks = []

    def put_block(start, rows):
        data = json_bytes(rows)
        if len(data) > MAX_DOWNLOAD_BYTES:
            if len(rows) == 1:
                raise ValueError("single trial exceeds unchanged object size limit")
            middle = len(rows) // 2
            put_block(start, rows[:middle])
            put_block(start + middle, rows[middle:])
        else:
            blocks.append(dict(start=start, count=len(rows), sha256=output.put(data)))

    for start in range(0, len(records), 64):
        put_block(start, records[start : start + 64])
    return output.put(
        json_bytes(
            dict(
                storage_format=FORMAT,
                header={k: v for k, v in case.items() if k != "records"},
                record_count=len(records),
                blocks=blocks,
                logical_sha256=sha256(body),
            )
        )
    )


def read_case(output, digest):
    value = json.loads(output.read(digest))
    if not isinstance(value, dict):
        raise ValueError("study case must be an object")
    if "storage_format" not in value:
        return value
    if (
        set(value) != {"storage_format", "header", "record_count", "blocks", "logical_sha256"}
        or value["storage_format"] != FORMAT
        or not isinstance(value["header"], dict)
        or "records" in value["header"]
        or "storage_format" in value["header"]
        or type(value["record_count"]) is not int
        or value["record_count"] < 1
        or not isinstance(value["blocks"], list)
        or not value["blocks"]
    ):
        raise ValueError("invalid trial block index")
    records = []
    for block in value["blocks"]:
        if (
            not isinstance(block, dict)
            or set(block) != {"start", "count", "sha256"}
            or type(block["start"]) is not int
            or block["start"] != len(records)
            or type(block["count"]) is not int
            or not 1 <= block["count"] <= 64
        ):
            raise ValueError("trial blocks must be contiguous, ordered and bounded")
        rows = json.loads(output.read(block["sha256"]))
        if not isinstance(rows, list) or len(rows) != block["count"]:
            raise ValueError("trial block count differs")
        records.extend(rows)
        if len(records) > value["record_count"]:
            raise ValueError("trial blocks exceed declared count")
    result = dict(value["header"], records=records)
    if (
        len(records) != value["record_count"]
        or sha256(json_bytes(result)) != value["logical_sha256"]
    ):
        raise ValueError("complete logical case does not reconstruct")
    return result


def checkpoint(output, revision, name, record):
    return output.put(
        json_bytes(
            dict(
                storage_format="coarse-control-checkpoint-v2",
                code_revision=revision,
                case=name,
                record_id=put_case(output, record),
            )
        )
    )
