"""Content-addressed source receipts and offline integrity/audit replay."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from nfl_value.source_audit import audit_csv, aware_time
from nfl_value.sources import SourceSpec, source_spec


MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}")
ALLOWED_HOSTS = {"api.github.com", "github.com", "raw.githubusercontent.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com", "creativecommons.org"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _allowed_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("source URL must use HTTPS on an approved public data host")


class _Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class Download:
    body: bytes
    fetched_at: str
    headers: dict[str, str]


def fetch_public(url: str, max_bytes: int = MAX_DOWNLOAD_BYTES) -> Download:
    """No credentials, bounded reads, approved HTTPS redirects; no signed URL log."""
    _allowed_url(url)
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_DOWNLOAD_BYTES:
        raise ValueError("invalid download size bound")
    request = Request(url, headers={"User-Agent": "nfl-player-value/0.1 source audit", "Accept-Encoding": "identity"})
    with build_opener(_Redirects()).open(request, timeout=60) as response:
        _allowed_url(response.url)
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("source exceeds download size limit")
        headers = {key: response.headers[key] for key in ("ETag", "Last-Modified", "Content-Type") if key in response.headers}
    return Download(body, datetime.now(timezone.utc).isoformat(), headers)


def resolve_asset(metadata: bytes, spec: SourceSpec) -> dict:
    release = json.loads(metadata)
    if release.get("tag_name") != spec.tag:
        raise ValueError("release tag does not match selected source")
    matches = [asset for asset in release["assets"] if asset["name"] == spec.filename]
    if len(matches) != 1:
        raise ValueError(f"expected one exact asset {spec.filename!r}; found {len(matches)}")
    asset = matches[0]
    if asset["browser_download_url"] != spec.download_url:
        raise ValueError("asset download URL does not match the source registry")
    if type(asset["id"]) is not int or asset["id"] <= 0:
        raise ValueError("invalid GitHub asset ID")
    if type(asset["size"]) is not int or not 0 < asset["size"] <= MAX_DOWNLOAD_BYTES:
        raise ValueError("invalid or excessive asset size")
    digest = asset.get("digest", "")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or not HASH.fullmatch(digest[7:]):
        raise ValueError("source asset needs a published SHA-256 digest")
    aware_time(asset["updated_at"])
    return {key: asset[key] for key in ("id", "name", "size", "digest", "updated_at", "browser_download_url")}


class SnapshotStore:
    """Append-only by convention; every read rechecks the requested content hash."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, digest: str, *, manifest: bool = False) -> Path:
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("expected a lowercase SHA-256 identifier")
        return self.root / ("manifests" if manifest else "objects") / (digest + (".json" if manifest else ""))

    def put(self, body: bytes, *, manifest: bool = False) -> str:
        if len(body) > MAX_DOWNLOAD_BYTES:
            raise ValueError("stored object exceeds size limit")
        digest = sha256(body)
        path = self._path(digest, manifest=manifest)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Publish only a fully written object; hard link provides no-clobber
        # semantics even if two independent writers address identical bytes.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            staging = Path(handle.name)
            try:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            except BaseException:
                staging.unlink(missing_ok=True)
                raise
        try:
            try:
                os.link(staging, path)
            except FileExistsError:
                pass
        finally:
            staging.unlink(missing_ok=True)
        if self.read(digest, manifest=manifest) != body:
            raise ValueError("existing content-addressed object disagrees with input")
        return digest

    def read(self, digest: str, *, manifest: bool = False) -> bytes:
        path = self._path(digest, manifest=manifest)
        if path.is_symlink():
            raise ValueError("content-addressed objects cannot be symbolic links")
        with path.open("rb") as handle:
            body = handle.read(MAX_DOWNLOAD_BYTES + 1)
        if len(body) > MAX_DOWNLOAD_BYTES:
            raise ValueError("stored object exceeds size limit")
        if sha256(body) != digest:
            raise ValueError(f"stored object failed SHA-256 verification: {digest}")
        return body


def capture(store: SnapshotStore, spec: SourceSpec, *, code_revision: str, fetch=fetch_public) -> tuple[str, dict]:
    """Resolve, download, validate, then publish one immutable source receipt.

    No latest/ranking pointer is advanced. A mutable URL changing between metadata
    resolution and download fails its hash check rather than creating a mixed run.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("code_revision must be a full Git commit SHA")
    if spec != source_spec(spec.kind, spec.season):
        raise ValueError("source does not match the reviewed registry")
    metadata = fetch(spec.metadata_url, 4 * 1024 * 1024)
    asset = resolve_asset(metadata.body, spec)
    source = fetch(spec.download_url, asset["size"])
    if len(source.body) != asset["size"] or sha256(source.body) != asset["digest"][7:]:
        raise ValueError("download does not match resolved asset size/SHA-256; retry from metadata")
    if aware_time(asset["updated_at"]) > aware_time(source.fetched_at):
        raise ValueError("source update time is later than retrieval")
    audit = audit_csv(source.body, spec, observed_at=source.fetched_at)
    license_record = fetch(spec.license_url, 256 * 1024)
    if not aware_time(metadata.fetched_at) <= aware_time(source.fetched_at) <= aware_time(license_record.fetched_at):
        raise ValueError("retrieval timestamps must be timezone-aware and ordered")
    _check_license(license_record.body, spec)
    declaration = None
    if spec.license_declaration_url:
        declaration = fetch(spec.license_declaration_url, 256 * 1024)
        if aware_time(declaration.fetched_at) < aware_time(license_record.fetched_at):
            raise ValueError("license declaration retrieval precedes license retrieval")
        _check_declaration(declaration.body)
    objects = {
        "raw": store.put(source.body),
        "release_metadata": store.put(metadata.body),
        "license": store.put(license_record.body),
    }
    receipt = {
        "manifest_version": 2 if declaration else 1,
        "code_revision": code_revision,
        "source": asdict(spec),
        "asset": asset,
        "retrieval": {"data": source.fetched_at, "metadata": metadata.fetched_at, "license": license_record.fetched_at},
        "http_headers": source.headers,
        "objects": objects,
        "audit": audit,
    }
    if declaration:
        receipt["objects"]["license_declaration"] = store.put(declaration.body)
        receipt["retrieval"]["license_declaration"] = declaration.fetched_at
        receipt["license_declaration_url"] = spec.license_declaration_url
    receipt_id = store.put(json_bytes(receipt), manifest=True)
    return receipt_id, receipt


def replay(store: SnapshotStore, receipt_id: str) -> dict:
    """Read only local objects. Verify provenance, bytes, and regenerated audit."""
    receipt = json.loads(store.read(receipt_id, manifest=True))
    if receipt["manifest_version"] not in {1, 2}:
        raise ValueError("unsupported manifest version")
    if not re.fullmatch(r"[0-9a-f]{40}", receipt["code_revision"]):
        raise ValueError("invalid recorded code revision")
    retrieval = receipt["retrieval"]
    if not aware_time(retrieval["metadata"]) <= aware_time(retrieval["data"]) <= aware_time(retrieval["license"]):
        raise ValueError("invalid recorded retrieval chronology")
    if aware_time(receipt["asset"]["updated_at"]) > aware_time(retrieval["data"]):
        raise ValueError("recorded source update time is later than retrieval")
    spec = source_spec(receipt["source"]["kind"], receipt["source"]["season"])
    if receipt["source"] != asdict(spec):
        raise ValueError("stored source schema/policy differs from this replay implementation")
    if receipt["manifest_version"] != (2 if spec.license_declaration_url else 1):
        raise ValueError("source requires its matching license provenance version")
    if spec.license_declaration_url:
        if receipt["license_declaration_url"] != spec.license_declaration_url:
            raise ValueError("license declaration URL disagrees with source registry")
        if aware_time(retrieval["license_declaration"]) < aware_time(retrieval["license"]):
            raise ValueError("invalid license declaration chronology")
        _check_declaration(store.read(receipt["objects"]["license_declaration"]))
    metadata = store.read(receipt["objects"]["release_metadata"])
    if resolve_asset(metadata, spec) != receipt["asset"]:
        raise ValueError("receipt asset disagrees with saved release metadata")
    raw = store.read(receipt["objects"]["raw"])
    if len(raw) != receipt["asset"]["size"] or sha256(raw) != receipt["asset"]["digest"][7:]:
        raise ValueError("saved raw bytes disagree with asset metadata")
    license_record = store.read(receipt["objects"]["license"])
    _check_license(license_record, spec)
    audit = audit_csv(raw, spec, observed_at=receipt["retrieval"]["data"])
    if audit != receipt["audit"]:
        raise ValueError("replayed audit differs from receipt; use the recorded code revision")
    return receipt


def _check_license(body: bytes, spec: SourceSpec):
    header = b"Attribution-ShareAlike 4.0 International" if spec.license_id == "CC-BY-SA-4.0" else b"Attribution 4.0 International"
    if not body.startswith(header):
        raise ValueError("declared source license changed; review before ingesting")


def _check_declaration(body: bytes):
    # Archive the actual declaration as well as the legal text. These tripwires
    # flag source-policy changes; they are not a legal compatibility judgment.
    if not all(marker in body for marker in (
        b"https://creativecommons.org/licenses/by-sa/4.0/",
        b"FTN Data via nflverse", b"2023 onwards", b"post-season games",
    )):
        raise ValueError("participation license declaration changed; review before ingesting")
