# Architecture

The initial product is a batch research pipeline and a static website. Python produces versioned artifacts; React/TypeScript renders them. An API service and database are unnecessary for the first release.

```text
permitted source releases / APIs
            |
            v
immutable raw bytes + provenance manifest
            |
            v
validated normalized tables and coverage report
            |
            v
baseline / attribution models + evaluation artifacts
            |
            v
immutable ranking snapshot + player JSON + release manifest
            |
            v
React / TypeScript static dashboard
```

## Boundaries

- **Ingestion:** fetch permitted sources, retain exact bytes, verify schemas, and record coverage. No hidden network calls inside model fitting.
- **Contracts:** stable player identifiers; roles; unique game/play keys; opportunity denominators; pregame membership evidence; completed-game and cutoff semantics.
- **Modeling:** transparent regularized baseline first; optional hierarchical fitting after measured improvement. Random seeds, dependency versions, model configuration, and training windows are recorded.
- **Evaluation:** historical chronological splits, benchmark/eligibility sensitivity, attribution stress tests, and separate defensive admission artifacts.
- **Publication:** validate a complete output bundle before atomically advancing the public latest pointer. Keep the last valid release on failure.
- **Presentation:** display values, intervals, model/benchmark labels, source freshness, scope limitations, and weekly histories. Numerical explanations originate in recorded model outputs, not LLM-generated scores.

Implemented boundaries now include benchmark/qualification contracts, immutable
source receipts, and offline [pregame inputs](PREGAME_INPUTS.md). The latter retain
the whole schedule/PBP reconciliation, formation-aware memberships, coverage
failures and retrospective-availability labels in a content-addressed diagnostic
report. The [defensive input layer](DEFENSE_INPUTS.md) now adds source-specific FTN
license provenance and paired rich-play/degraded-team-game objects with a common
cohort hash. All derivation/replay is offline; reports retain exclusions and
`ranking_ready=false`. No new runtime dependency was needed. Model fitting,
information-loss comparisons, publication and presentation remain unimplemented.

The [offensive input layer](OFFENSIVE_INPUTS.md) now supplies one observed EPA
outcome per play, actor links and per-player-game count unions, with unresolved
positions/stints explicitly flagged. It shares the preplay context parser with
the defensive layer. New pregame/defensive report version 2 uses clock-based
completion; replay dispatches old reports to their recorded rule. The change adds
no runtime dependency and does not allocate team outcomes to individuals.

## Snapshot and release contract

Each source manifest should record the source URL/release asset, retrieval time, upstream update time when supplied, content hash, size, schema version, license/provenance reference, and observed game/week coverage. Record compressed and decoded hashes when transformations make both relevant. An upstream modification timestamp alone is not a data version.

Each model release should identify its input manifest hashes, code commit, dependency lock, model and qualification policies, benchmark cohort/weights, seed, training cutoff, completed games, exclusion counts, diagnostics, and output hashes. Persist sufficient fitted state or reproducible instructions for an offline rerun.

Use immutable release IDs. Corrections create a new timestamped version linked to the superseded version. Preserve both the rankings originally published each week and later revised estimates; a chart must state which history it displays. Do not silently include late corrections, incomplete games, or unavailable feeds.

An ingestion failure does not turn missing observations into zero contribution. When an optional feed fails, only an explicitly validated fallback model may run; otherwise retain the last good snapshot and show the limitation.

## Engineering and production execution

GitHub is the permanent source of truth. Use a stable local clone, isolated Python/Node environments, `codex/` feature branches, tests, CI, self-review, and reviewable PRs. Never merge an automated development PR directly into `main`.

The authorized daily development run is **7:30 PM America/New_York**. It must inspect remote state and current roadmap before choosing work, preserve unfinished branches and changes, and acquire a repository-specific lock before mutation. An active lock or conflicting unfinished task is a reason to inspect or stop safely, not overwrite work. Separate paths, environments, caches, and ports protect the existing NFL Opponent Intelligence project. Host-level resource contention still needs attention; different start times alone cannot guarantee nonoverlap.

Production weekly refresh is a separate deployed workflow. It must not depend on the desktop app or a development agent being awake. Schedule after expected data availability with manual reruns and explicit freshness checks; scheduled CI is not a hard real-time guarantee. Read-only runs and mutating publication use appropriate independent locks/concurrency controls.

## Cost and deployment

Prefer standard public GitHub Actions runners for batch jobs and free static hosting for the frontend. Cache dependency downloads without relying on ephemeral CI caches as the permanent data archive. Immutable release assets may store permitted, size-bounded outputs and provenance; raw-data redistribution depends on source terms.

The operating budget is below **$100/month**, preferably near zero. No paid service, data subscription, storage expansion, or purchase may be enabled without explicit user approval. If free runtime or storage limits prevent a verified release, report the measured requirement and propose a concrete alternative.

Relevant operational references: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), and [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/). These are deployment candidates, not evidence that deployment has occurred.
