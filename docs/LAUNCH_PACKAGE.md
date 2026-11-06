# Portable Explorer launch package

The launch package joins a verified refresh candidate, its compiled static website,
and every source/derived byte required to replay both the candidate and its prior
comparison. It also records a new source-readiness assessment at packaging time.
It is an unpublished exploratory artifact, not an admitted MVP leaderboard.

## Prepare the website without changing the staged site

Hold the development lease and use committed code and installed locked dependencies.
Capture the four current sources and prepare a candidate with the
[readiness CLI](SOURCE_READINESS.md), retaining the previous Explorer reference.
Read its exact `explorer_report` from the candidate manifest. Then run:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.review_cli EXPLORER_REPORT --isolated
```

The optional isolated mode copies only tracked frontend files into a temporary
directory under `work/`, links the already-checked installed dependency directory,
and runs the existing TypeScript/Vite build there. Ignored `.env`, old public data,
dist and cache files are not copied. The canonical `web/public/data/latest.json`
and `web/dist` are untouched by this build, including on compilation failure.
Temporary source/output files are removed after success or failure. Shared
installed dependencies are not copied or reinstalled. This is build isolation,
not a sandbox for executing untrusted compiler plugins.

The saved review ZIP retains its existing format and original game cutoff. The
earlier non-isolated command and recovery-v1 archives remain compatible. Verify
the actual site in a browser and run `make check` and the Chromium suite; the
packager does not substitute for those checks.

## Package the candidate and exact replay inputs

Use the independently recorded digest returned by the review build:

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.launch_cli pack \
  CANDIDATE_ID artifacts/review-bundles/REVIEW_SHA256.zip --sha256 REVIEW_SHA256
```

The command uses the actual UTC packaging-attempt time, with no historical-cutoff
override. It replays the candidate, reassesses its sources under the frozen age and
game-coverage policy, and verifies that the saved website matches that exact
candidate. A stale source, newly started unresolved game, wrong site, corrupted
input or missing prior dependency rejects the package. Recapture and rebuild when
readiness fails; do not backdate the check or override the policy.

The hash-named ZIP under `artifacts/launch/` contains:

- The original four source families, receipts, offensive ledgers, Explorer objects,
  candidate manifest and readiness report actually read during verified replay.
- The prior Explorer's exact dependencies when used for comparison. This is one
  comparison dependency set, not retention of every historical weekly release.
- The unchanged `review/REVIEW_SHA256.zip` and both source sets' attribution/licenses.
- `checks/source-readiness.json`, evaluated at packaging-attempt time, and a strict
  `launch-manifest.json` with exact hashes, sizes, candidate, code and time references.

Only the reviewed 2026 CC-BY-4.0 input families are permitted. Unrelated stores,
credentials and local files are excluded. Size/count limits reuse recovery IO:
128 MiB and 128 regular uncompressed entries. A larger valid candidate must fail
explicitly and receive a reviewed storage decision, not silently omit dependencies.

## Restore independently

```sh
PYTHONPATH=src .venv/bin/python -m nfl_value.launch_cli restore \
  artifacts/launch/LAUNCH_SHA256.zip --sha256 LAUNCH_SHA256 \
  --destination work/restored-launch
```

Use a digest from a trusted committed audit or separately verified build output,
not one computed from an untrusted download itself. Retain the recorded code and
locked dependencies in Git. The external checksum and complete file inventory
are verified before writing. Full candidate/site replay and the original packaging
check are recomputed using only restored stores in a private sibling directory.
The result must reproduce the entire package byte-for-byte before that directory
is renamed into place. Existing destinations are refused; failures remove only
this operation's temporary files. No raw network request or compiler build occurs
during restoration. Browser testing of the saved compiled assets remains separate.

**Restore does not renew freshness.** `verified_at_recorded_time_only=true` makes
that explicit. The candidate's game cutoff and the later packaging check are
different timestamps; neither is a claim that data are current when viewed later.
Changing the packaging check time changes the package hash intentionally.

## Remaining deployment boundary

This command does not upload assets, deploy a site, schedule refreshes, establish
remote durability or update a public pointer. A future publisher must check
freshness at its own attempt time, bind the actual last-good reference, retain all
prior releases, and atomically publish only fully verified output. A copied ZIP
or CI artifact alone is not durable retention or rollback testing. The package
does not contain historical model/participation research stores.

All CAVAA/snap estimates remain null and all 17 modules remain unadmitted. Data
integrity, browser functionality and reproducibility do not repair attribution or
uncertainty-calibration failures. An exploratory launch does not complete the
unified MVP-ranking objective.
