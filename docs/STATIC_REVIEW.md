# Archived static review bundles

The dashboard exposes the [November 2 module decisions](ADMISSION.md) alongside
the Defense Explorer. All 17 contribution modules remain unadmitted, with scope,
seven validation gates and links to the exact reviewed evidence. This is an
exploratory product for inspecting evidence and missing measurement, not a
published MVP ranking. Accounting checks alone do not validate player attribution.

The browser fetches the exact registry bytes pinned in
`web/src/release-policy.json`, verifies SHA-256, then applies a strict Zod contract.
The backend verifies the registry's 13 source references before export. Evidence
links use the pinned Git revision, never moving main. A missing/corrupt registry
shows an error, not assumed admission or fabricated scores. Explorer and registry
loads fail independently, with independent retries. The November 2 review date
does not advance the Explorer's October 22 game cutoff.

## Build from committed code and retained inputs

From the canonical repository root, with the development lease held, Python
3.11+ and the installed Node 24 toolchain:

```sh
# Install the committed frontend lockfile once if dependencies are absent.
npm --prefix web ci --ignore-scripts --no-fund
mkdir -p work
PYTHONPATH=src .venv/bin/python -m nfl_value.review_cli \
  497f59523ffd5f608937d82dda6a5d2abf1a8621d92ba7031df94b3a1f605435 \
  > work/review-build.json
```

The report ID identifies the archived Week 6 Explorer. It requires the local
source/derived stores recorded in `docs/audits/2026-10-25-defense-explorer.json`;
Git alone does not contain those bytes. The command accepts explicit store paths
but never downloads missing inputs. Missing archives fail explicitly.

The command checks committed frontend/config/model code, verifies the decision
registry and evidence-link revision, replays the complete Explorer source chain,
and requires observed 2026 data with every player CAVAA/snap estimate null. It
checks Node 24 and the installed npm dependency tree, stages immutable public
objects before the atomic local `data/latest.json` pointer, and runs TypeScript
and Vite from this checkout. Use `npm ci` when restoring dependencies; `npm ls`
checks the installed tree but is not a cryptographic audit of package contents.
The command rechecks source cleanliness and the built data bytes before creating
an immutable `artifacts/review-bundles/<sha256>.zip`.

The archive contains `index.html`, built JS/CSS, the single selected Explorer
object and pointer, the reviewed registry, and `review-manifest.json`. It excludes
raw source downloads, old unreferenced exports, local credentials and development
dependencies. Original local objects are preserved. The manifest records file
hashes/sizes, code/toolchain/npm-lock versions, source receipts, review version,
coverage and the original game cutoff. `ranking_ready` is always false.

ZIP entry order, timestamps, permissions and compression are fixed; repeat builds
with the recorded code, inputs and toolchain should produce the same bytes.
Compare the returned archive SHA-256 with the reviewed audit, rather than computing
a new expected digest from an untrusted candidate. The ZIP hash covers the
manifest too. Hash identity is not scientific validation or a trusted signature.
Restore/extract only the verified archive into a new directory, then serve it
over localhost or HTTPS; `file://` cannot supply the browser fetch/crypto contract.
The build uses relative asset paths, including for a static subdirectory.

## Boundaries and failure behavior

This command does not run the test suite, so `make check` and the Chromium suite
remain required before the review artifact is accepted. The small offline tests
stub raw replay at its validated boundary; real archived replay is separately
recorded in the dated audit. No ordinary CI job needs a live NFL download.

Staging rejects mismatched immutable bytes and path/symlink escapes. Source or
evidence failure happens before staging. A staging-write failure leaves the prior
local pointer; a compiler failure may leave newly verified staged data but creates
no new review archive. Existing archives are never overwritten. **No hosted
publication pointer exists or changes.** These local protections are not a claim
of production rollback or durable off-machine retention.

No production source-readiness/freshness policy, independent scheduled refresh,
hosting, durable raw snapshot retention or admitted CAVAA ranking is provided by
this unit. Packaging archived evidence must not be presented as weekly live
coverage. A future ranking publisher still needs the release gates in
[CI.md](CI.md), including defensible position admission, complete source coverage,
validated uncertainty and retention of every original weekly release.
