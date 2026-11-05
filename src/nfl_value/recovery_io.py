"""Bounded, deterministic archive IO for the Explorer recovery contract."""

from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import stat
import zipfile

from nfl_value.admission import _invalid_constant, _unique_object
from nfl_value.defense_explorer import _publish_bytes
from nfl_value.ingestion import sha256
from nfl_value.review_bundle import safe_path


MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ENTRIES = 128


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("a trusted full SHA-256 digest is required")
    return value


def decode_object(body):
    value = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def read_bounded(path):
    safe_path(path.parent, path.name)
    with path.open("rb") as handle:
        body = handle.read(MAX_ARCHIVE_BYTES + 1)
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError("recovery archive exceeds size limit")
    return body


def safe_name(name):
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", name)
        or str(PurePosixPath(name)) != name
        or ".." in PurePosixPath(name).parts
    ):
        raise ValueError("unsafe archive member path")


def read_archive(body, expected_sha256):
    """Check the external pin before decoding; never extract through ZIP APIs."""
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError("recovery archive exceeds size limit")
    if sha256(body) != digest(expected_sha256):
        raise ValueError("archive SHA-256 mismatch")
    with zipfile.ZipFile(BytesIO(body)) as archive:
        infos = archive.infolist()
        if not 1 <= len(infos) <= MAX_ENTRIES:
            raise ValueError("invalid archive entry count")
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError("duplicate archive member")
        if sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
            raise ValueError("archive expansion exceeds size limit")
        for info in infos:
            safe_name(info.filename)
            if (
                info.compress_type != zipfile.ZIP_STORED
                or info.flag_bits & 1
                or info.is_dir()
                or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
            ):
                raise ValueError("only unencrypted regular stored files are supported")
        return {info.filename: archive.read(info) for info in infos}


def file_index(files):
    return {
        name: {"sha256": sha256(body), "bytes": len(body)} for name, body in sorted(files.items())
    }


def check_index(files, index):
    if not isinstance(index, dict) or index.keys() != files.keys():
        raise ValueError("archive file inventory mismatch")
    for name, body in files.items():
        entry = index[name]
        if (
            not isinstance(entry, dict)
            or entry.keys() != {"sha256", "bytes"}
            or type(entry["bytes"]) is not int
            or entry["bytes"] != len(body)
            or digest(entry["sha256"]) != sha256(body)
        ):
            raise ValueError(f"archive file hash/size mismatch: {name}")


def encode_archive(files):
    if not 1 <= len(files) <= MAX_ENTRIES or sum(map(len, files.values())) > MAX_ARCHIVE_BYTES:
        raise ValueError("recovery archive exceeds size/count limit")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, body in sorted(files.items()):
            safe_name(name)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body)
    body = buffer.getvalue()
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError("recovery archive including metadata exceeds size limit")
    return body


def save_recovery(destination, body):
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError("recovery archive exceeds size limit")
    target = safe_path(destination, f"{sha256(body)}.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if read_bounded(target) != body:
            raise ValueError("existing immutable recovery archive disagrees")
    else:
        _publish_bytes(target, body, replace=False)
    return target
