# Explorer recovery archives

The recovery command retains the exact inputs needed to replay an archived
Explorer, together with its existing [static review ZIP](STATIC_REVIEW.md).
It provides a portable artifact and verified local restoration. It does not
upload, deploy, refresh data, admit player scores, or publish a ranking pointer.

Version 1 is deliberately limited to the reviewed 2026 play-by-play, schedules,
depth-chart and roster source chain. It does not back up historical participation,
weekly-roster, model-fitting or calibration stores. Those research bytes still
need separate retention. Arbitrary recursive directory backups could disclose
unrelated files or combine incompatible redistribution terms.

## Pack the exact dependency set

Hold the repository development lease. Run from committed Python source at the
canonical repository root; the command refuses dirty `src` or `pyproject.toml`.
It needs Python 3.11+ and the stdlib only. No Node build or model fitting is run.

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.recovery_cli pack \
  artifacts/review-bundles/ffcffe5dfdde266274203407fc36e18e01d81206aff0736089372be36e09cffb.zip \
  --sha256 ffcffe5dfdde266274203407fc36e18e01d81206aff0736089372be36e09cffb
```

`--store-root` defaults to this checkout and may point to a previously restored
directory. The recorder collects only successfully verified reads during the
existing full source/ledger/Explorer replay. It rechecks the pinned admission
registry and evidence, npm lock, saved public objects, coverage, original game
cutoff and null CAVAA fields. Extra local objects are neither copied nor deleted.

The hash-named ZIP under `artifacts/recovery/` contains:

- Original source objects, archived licenses, receipts and derived objects in
  their existing content-addressed store paths.
- The exact saved `review/<sha256>.zip`, preserving its producer and toolchain.
- `ATTRIBUTION.md`, including source URLs, timestamps, hashes, credits, archived
  license locations and the distinction between raw and transformed data.
- `recovery-manifest.json`, with every member hash/size, packager revision,
  review/report identities, unchanged game cutoff and `ranking_ready=false`.

The ZIP is deterministic for identical inputs and packager revision. Fixed
ordering, timestamps, permissions and no compression avoid environment-dependent
compression bytes. Both encoded and expanded sizes are limited to 128 MiB, with
at most 128 entries. Existing immutable archives are verified, never overwritten.
Generated ZIPs remain outside ordinary Git history; commit their audit/digests.

## Restore into a new directory

Use an independently trusted digest from the committed dated audit. A checksum
computed from a candidate download itself does not authenticate that download.
Use a clean checkout containing the recorded packager code and pinned evidence;
future changed policy/registry bytes may correctly reject this older archive.
Keep the development lease while restoring under this repository.

```sh
# Replace both SHA256 occurrences with the digest in the committed recovery audit.
PYTHONPATH=src .venv/bin/python -m nfl_value.recovery_cli restore \
  --archive artifacts/recovery/SHA256.zip --sha256 SHA256 \
  --destination work/restored-explorer
```

For a future retained release asset, replace `--archive` with `--url` using the
canonical repository's exact hash-named download URL. The downloader accepts
only `https://github.com/AryanParte/nfl-player-value/releases/download/TAG/SHA256.zip`,
with no query/fragment or credentials, and reuses bounded HTTPS redirect checks.
The network branch is fixture-tested; no real remote asset is claimed until its
upload and separate download/restore have been recorded.

The external ZIP digest is checked before decoding. Duplicate members/JSON keys,
non-finite JSON, altered inventories, malformed paths, symlinks, directories,
compressed/encrypted entries and out-of-scope members fail explicitly. The
restorer writes a private sibling staging directory, reruns full semantic replay
using only those restored stores, and compares the exact dependency set and
attribution before renaming it to the requested destination. The recovery manifest
is retained alongside the files. Existing destinations, including empty ones,
are refused; failure removes only this operation's staging directory. Never
restore over the canonical stores or an earlier restored release.

The sibling rename gives local atomic visibility under the cooperative repository
lease. It is not distributed concurrency, power-loss durability, a production
publication pointer, or a rollback system. Restoring checks saved compiler asset
bytes, not a fresh frontend compilation; rebuilding the site is a separate static
review step. No existing public pointer is advanced, and original stores remain
untouched.

## Retention destination and rights

GitHub Releases is the proposed off-machine destination for these hash-named
artifacts. GitHub documents up to 1,000 assets per release and each asset below
2 GiB; our 128 MiB bound is much smaller. This uses the canonical repository and
avoids an additional paid service or large data in Git history. Retain old assets
and do not replace a hash-named file. [GitHub release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

Ordinary releases can be edited/deleted by authorized users. GitHub's separate
immutable-release feature has not been enabled here; content hashes detect changes
but do not prevent deletion. A release upload is not a backup guarantee. Record
the release/asset URL and digest, then download and restore independently before
calling remote retention verified. [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).

The four admitted source kinds have archived CC-BY-4.0 records. Keep attribution,
license links/text and the description of transformations with redistributed data;
the software's MIT license does not replace the data license. The v1 packer
rejects other seasons/source families/license identifiers rather than assuming
one policy covers historical FTN participation or commercial data.
[CC-BY-4.0 terms](https://creativecommons.org/licenses/by/4.0/deed.en).

No remote upload is currently completed: the connected GitHub tool has no binary
release-asset upload, the available browser is signed out, and no authenticated
release-upload CLI is available. The prepared local archive remains at risk from
machine loss until access permits upload and the remote restore check succeeds.
Do not bypass this by checking source binaries into Git. This access limitation
does not justify delaying independent source-readiness or deployment preparation.

## Verification limits

Offline CI exercises deterministic synthetic dependencies through the real
registry, review and archive validators, stubbing raw replay at its boundary.
It tests integrity, allowlists, missing/extra dependencies, replay failures,
write/rename failures and preservation of existing work. The dated real audit
separately tests the actual NFL chain with networking blocked.

Recovering the same observations is reproducibility evidence, not evidence of
correct individual attribution. All 17 modules remain unadmitted. Week 6 coverage
and the October 22 cutoff stay fixed; a November restore date adds no games.
First-unit CAVAA, benchmark sensitivities and eligibility policies are unchanged.
Production readiness, durable retention for all research stores, deployment,
independent refresh and an admissible ranking model remain unfinished.
