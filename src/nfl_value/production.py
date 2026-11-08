"""Explorer release handoff and fresh publication gates; never admit CAVAA."""

from datetime import datetime, timezone
import re

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.launch_bundle import MANIFEST, _launch, build_launch, restore_launch
from nfl_value.recovery_io import decode_object, digest, read_archive, read_bounded
from nfl_value.review_bundle import safe_path, stage_review


PREFIX = "explorer-2026-"


def release_tag(pin):
    return PREFIX + digest(pin)


def tag_digest(tag):
    if not isinstance(tag, str) or not tag.startswith(PREFIX):
        raise ValueError("unsupported retained release tag")
    return digest(tag[len(PREFIX) :])


def record_for(body, previous_tag=None):
    """A retention record describes verified bytes, not a successful deployment."""
    if previous_tag is not None:
        tag_digest(previous_tag)
    pin = sha256(body)
    _, manifest = _launch(body, pin)
    return {
        "schema_version": 1,
        "kind": "retained_explorer_candidate",
        "tag": release_tag(pin),
        "archive_sha256": pin,
        "archive_bytes": len(body),
        "code_revision": manifest["packager_code_revision"],
        "candidate_id": manifest["candidate_id"],
        "explorer_report": manifest["explorer_report"],
        "game_cutoff": manifest["game_cutoff"],
        "previous_retained_tag": previous_tag,
        "ranking_ready": False,
    }


def read_release(directory, expected_pin=None):
    record = decode_object(read_bounded(safe_path(directory, "release.json")))
    pin = digest(record["archive_sha256"])
    if expected_pin is not None and pin != digest(expected_pin):
        raise ValueError("release disagrees with independently supplied archive pin")
    body = read_bounded(safe_path(directory, pin + ".zip"))
    if sha256(body) != pin or json_bytes(record) != json_bytes(
        record_for(body, record["previous_retained_tag"])
    ):
        raise ValueError("release record disagrees with archive")
    return body, record


def select_previous(pages, *, bootstrap=False):
    """No fallback on a malformed newest release or on a failed API request.

    The newest retained candidate may not have deployed. Its completed games
    still constrain the next candidate, which is conservative about coverage.
    """
    if not isinstance(pages, list) or any(not isinstance(p, list) for p in pages):
        raise ValueError("paginated release list required")
    releases = []
    for page in pages:
        for item in page:
            if not isinstance(item, dict) or not isinstance(item.get("tag_name"), str):
                raise ValueError("malformed release listing")
            if not item["tag_name"].startswith(PREFIX):
                continue
            tag_digest(item["tag_name"])
            if type(item.get("draft")) is not bool or type(item.get("id")) is not int:
                raise ValueError("malformed managed release")
            if not item["draft"]:
                releases.append(item)
    if not releases:
        if not bootstrap:
            raise ValueError("no retained Explorer; first manual run requires bootstrap")
        return None
    if bootstrap:
        raise ValueError("bootstrap cannot bypass an existing retained Explorer")
    if len({r["id"] for r in releases}) != len(releases):
        raise ValueError("duplicate release listing")
    return max(releases, key=lambda r: r["id"])["tag_name"]


def verify_release(
    repository_root,
    directory,
    destination,
    *,
    expected_pin=None,
    expected_revision=None,
    clock=None,
    site=None,
):
    """Restore, recheck at the real attempt time, then expose verified site files.

    Tests inject a clock; the public CLI has no historical-time override. A
    previous positive packaging decision never authorizes a later publication.
    """
    body, record = read_release(directory, expected_pin)
    if expected_revision is not None and (
        not re.fullmatch(r"[a-f0-9]{40}", expected_revision)
        or record["code_revision"] != expected_revision
    ):
        raise ValueError("release producer differs from workflow revision")
    restore_launch(repository_root, body, record["archive_sha256"], destination)
    manifest = decode_object((destination / MANIFEST).read_bytes())
    review_hash = manifest["review_archive_sha256"]
    review = read_bounded(destination / f"review/{review_hash}.zip")
    review_files = read_archive(review, review_hash)
    if (
        decode_object(review_files["review-manifest.json"])["code_revision"]
        != record["code_revision"]
    ):
        raise ValueError("site producer differs from release producer")
    checked_at = (clock or (lambda: datetime.now(timezone.utc)))()
    # Replays, checks the exact candidate/site, and rejects newly started games.
    build_launch(
        repository_root,
        destination,
        review,
        review_hash,
        record["candidate_id"],
        checked_at,
        record["code_revision"],
    )
    if site is not None:
        if site.exists() or site.is_symlink():
            raise ValueError("publication site destination must be new")
        files = review_files
        files["release.json"] = json_bytes(record)
        files["ATTRIBUTION.md"] = (destination / "ATTRIBUTION.md").read_bytes()
        stage_review(site, files)
    return {
        "archive_sha256": record["archive_sha256"],
        "checked_at": checked_at.isoformat(),
        "ready_for_explorer_deployment": True,
        "ranking_ready": False,
    }
