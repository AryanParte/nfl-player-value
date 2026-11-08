"""Explicit legacy 2024 roster capture, restricted to retrospective research.

GitHub did not publish digests for this March 2025 asset. Do not fabricate one
or weaken ordinary ingestion. Pin its ID/version, archive both metadata reads,
hash the bytes locally, and distinguish integrity from an upstream checksum.
"""

from dataclasses import asdict
import json
import re

from nfl_value.ingestion import _check_license, fetch_public, json_bytes, sha256
from nfl_value.source_audit import audit_csv, aware_time
from nfl_value.sources import source_spec

POLICY = "retrospective-2024-weekly-roster-local-hash-v1"
ASSET_ID = 237398166
UPDATED_AT = "2025-03-14T07:16:06Z"


def asset(metadata):
    spec = source_spec("weekly_rosters", 2024)
    release = json.loads(metadata)
    matches = [a for a in release["assets"] if a["name"] == spec.filename]
    if release["tag_name"] != spec.tag or len(matches) != 1:
        raise ValueError("legacy roster release/asset mismatch")
    a = matches[0]
    if (
        type(a["id"]) is not int
        or type(a["size"]) is not int
        or a["id"] != ASSET_ID
        or a["updated_at"] != UPDATED_AT
        or a.get("digest") is not None
        or a["browser_download_url"] != spec.download_url
        or a["size"] != 699786
    ):
        raise ValueError("legacy roster version changed; new reviewed source policy required")
    return {k: a[k] for k in ("id", "name", "updated_at", "size", "browser_download_url", "digest")}


def capture_legacy(store, *, code_revision, fetch=fetch_public):
    if not re.fullmatch(r"[0-9a-f]{40}", code_revision):
        raise ValueError("committed revision required")
    spec = source_spec("weekly_rosters", 2024)
    before = fetch(spec.metadata_url, 4 * 1024 * 1024)
    version = asset(before.body)
    data = fetch(spec.download_url, version["size"])
    after = fetch(spec.metadata_url, 4 * 1024 * 1024)
    if version != asset(after.body) or len(data.body) != version["size"]:
        raise ValueError("legacy roster changed during capture")
    audit = audit_csv(data.body, spec, observed_at=data.fetched_at)
    license_record = fetch(spec.license_url, 256 * 1024)
    _check_license(license_record.body, spec)
    times = [aware_time(record.fetched_at) for record in (before, data, after, license_record)]
    if times != sorted(times) or times[0] < aware_time(UPDATED_AT):
        raise ValueError("invalid legacy retrieval chronology")
    saved = {
        "policy": POLICY,
        "code_revision": code_revision,
        "source": asdict(spec),
        "asset": version,
        "upstream_sha256_available": False,
        "research_only": True,
        "ranking_ready": False,
        "audit": audit,
        "retrieval": {
            "before": before.fetched_at,
            "data": data.fetched_at,
            "after": after.fetched_at,
            "license": license_record.fetched_at,
        },
        "objects": {
            "before": store.put(before.body),
            "raw": store.put(data.body),
            "after": store.put(after.body),
            "license": store.put(license_record.body),
        },
    }
    receipt_id = store.put(json_bytes(saved), manifest=True)
    replay_legacy(store, receipt_id)
    return receipt_id, saved


def replay_legacy(store, receipt_id):
    saved = json.loads(store.read(receipt_id, manifest=True))
    if (
        saved["policy"] != POLICY
        or saved["source"] != asdict(source_spec("weekly_rosters", 2024))
        or saved["research_only"] is not True
        or saved["ranking_ready"] is not False
        or saved["upstream_sha256_available"] is not False
        or not re.fullmatch(r"[0-9a-f]{40}", saved["code_revision"])
    ):
        raise ValueError("invalid legacy research receipt")
    times = [aware_time(saved["retrieval"][k]) for k in ("before", "data", "after", "license")]
    if times != sorted(times) or times[0] < aware_time(UPDATED_AT):
        raise ValueError("invalid legacy retrieval chronology")
    before = asset(store.read(saved["objects"]["before"]))
    after = asset(store.read(saved["objects"]["after"]))
    body = store.read(saved["objects"]["raw"])
    if before != after or before != saved["asset"] or len(body) != before["size"]:
        raise ValueError("legacy roster version mismatch")
    _check_license(store.read(saved["objects"]["license"]), source_spec("weekly_rosters", 2024))
    if (
        audit_csv(body, source_spec("weekly_rosters", 2024), observed_at=saved["retrieval"]["data"])
        != saved["audit"]
    ):
        raise ValueError("legacy roster audit replay mismatch")
    if sha256(json_bytes(saved)) != receipt_id:
        raise ValueError("noncanonical legacy manifest")
    return saved
