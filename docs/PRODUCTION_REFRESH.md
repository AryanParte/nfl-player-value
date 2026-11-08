# Explorer production refresh

The `Refresh and publish Defense Explorer` workflow implements independent
source capture, verification, release retention and GitHub Pages deployment.
It is **Explorer-only**: observed events, team context, missingness and the pinned
17-module non-admission registry. It does not calculate or publish CAVAA rankings.
The first-unit benchmark, cumulative ledger and scientific admission requirements
are unchanged. A successful deployment cannot substitute for attribution evidence.

## Activation and access

PRs #18 and #19 were merged by the owner on November 7; merged main CI passed.
A subsequent inspection found no production run, a signed-out browser and a
Pages Site not found response. Activation remains unverified. In this repository's
Settings → Pages, choose **GitHub Actions** as the publishing source. Configure
the `github-pages` environment for main only. No custom domain, secret or paid
service is required for a public repository. This document does not claim those
settings have been configured or that deployment has succeeded.

Run the workflow on **main**, setting `bootstrap=true` for the first release only.
Bootstrap fails if any public managed Explorer release already exists. All later
manual runs use the default `false`. Scheduled runs use `false` and fail closed
until the first retained release exists. The workflow runs Tuesdays and Fridays
at **16:17 UTC** (11:17 EST / 12:17 EDT), after Monday/Thursday games. GitHub may
delay scheduled runs; this is not a freshness SLA. It never changes the separate
7:30 PM America/New_York Codex automation or the other NFL project's workflow.

The GitHub connector available during development cannot upload binary release
assets, dispatch a new workflow, or configure Pages. The hosted workflow uses
GitHub's installed `gh` and ephemeral `GITHUB_TOKEN`; no local token is copied.
Only the canonical repository's main ref can run either job. There is no PR or
`pull_request_target` trigger. Checkout credentials are not persisted. The build
has read-only repository access; only the publisher receives contents/Pages/OIDC
write scopes. No package installation or npm build runs in that privileged job.

## Transaction and provenance

1. Restore the newest public `explorer-2026-<full archive SHA-256>` release across
   paginated GitHub results. Drafts do not count; malformed/missing assets fail
   instead of falling back to an older convenient release. Semantic replay verifies
   the archive in a new private directory. This previous **retained** candidate may
   not have deployed; it conservatively constrains coverage in the next candidate.
2. Capture the four reviewed 2026 sources and choose a cutoff after all retrievals.
   Apply existing freshness, completed-game, source and missingness contracts.
   Preserve every game from the previous candidate. Build in isolation from
   committed code, with locked Node 24 dependencies, and package the replay closure.
3. Restore and recheck the exact package, then test its actual site on desktop and
   mobile Chromium at a project subpath. These tests intercept no data requests.
   Ordinary PR CI remains offline and uses its existing synthetic browser suite.
4. Pass the archive hash as a job output independently of the transferred files.
   The publisher binds that hash and the workflow commit to the archive, site and
   `release.json`. Replay and a fresh source check precede any remote write.
5. Create a new draft prerelease with the package and retention record. Download
   both from GitHub into a different directory, compare their exact bytes, replay
   again and recheck freshness. Only then expose the release as a public prerelease.
   No public release, tag or asset is overwritten or deleted. `--clobber` is absent.
6. Upload only the verified site files, source attribution and retention record to
   Pages. Recheck source readiness immediately before requesting deployment. The
   source check has an explicit time; it cannot certify later source corrections
   or guarantee the precise instant GitHub activates the deployment.

Workflow concurrency serializes the entire transaction without cancelling a
running publication. A failed build/gate/upload never requests Pages deployment,
so the last deployed site remains served. Hosting deployment is a GitHub-managed
operation; its failure and final activation still require hosted verification.
Published archive releases are retention evidence, **not deployment receipts**.
`release.json` says `ranking_ready=false` and never asserts deployment success.
Follow the Actions run/environment result to determine what actually deployed.

## Recovery and costs

If capture is incomplete or feeds are stale, inspect the readiness diagnostic and
rerun the complete workflow after the sources recover. Never weaken the gates.
A failed draft upload is preserved for operator diagnosis; it is not selected as
the previous release. A new full run creates a new time-addressed package. Do not
rerun only the publisher against an already retained tag: duplicate creation
deliberately fails. A failed deployment after successful retention leaves that
archive intact; the next refresh uses its completed-game set.

No automated destructive rollback is provided. Old releases retain recoverable
bytes, but replaying them does not renew freshness. Recovery of an old public view
must be explicitly labeled archival; normal publication requires a fresh capture
and current-time checks. Admin deletion or out-of-band deployments are outside
this workflow's guarantees. Code/policy changes that cannot replay the prior
release need a reviewed migration; they must not silently bootstrap new history.

Artifacts used only for job handoff expire after 7 days; failure diagnostics after
14; Pages artifacts after 1. Public GitHub releases provide the durable retained
copies (no automatic expiry in this workflow). They are immutable by workflow
policy, not protected against repository administrators. Each package contains its
current/prior Explorer closure, not every historical research store. All past
release packages must remain retained. The current archive bound is 128 MiB;
growth must fail explicitly before adopting a reviewed larger/chunked format.

No new Python/npm dependency is required. The hosted run adds one Python 3.13
validation/build job and a stdlib-only publishing job with 30/20-minute limits.
There is no purchase, paid upgrade or deployment credential. Public-repository
standard runners and Pages target zero recurring cost; monitor retention growth
and account limits, and never opt into paid capacity automatically.

Local production-boundary tests use synthetic source archives and a fake GitHub
transport. They verify error paths and ordering, not actual hosted permissions,
network storage, or Pages atomic activation. The first live workflow must verify
the off-machine restore, public URL, content hash, mobile behavior and failure
preservation before those operational capabilities are claimed complete.

Official references: [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[release creation](https://cli.github.com/manual/gh_release_create),
[workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
