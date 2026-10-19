# NFL Player Value engineering instructions

## Scope and authority

- Canonical repository: https://github.com/AryanParte/nfl-player-value.
- Stable local clone: `/Users/aryanparte/Documents/Codex/projects/nfl-player-value`.
- This product is independent of `nfl-opponent-intelligence`. Never edit that
  project's files, branches, automation, caches, ports, or configuration.
- User approved implementation on October 18, 2026. Target launch: November 7.
- No paid datasets, services, purchases, or paid account upgrades without explicit
  approval. Target near-zero recurring cost; $100/month is a ceiling, not spending
  authorization. Do not create filler commits.

## Scientific contract

Read `docs/METHODOLOGY.md`, `docs/EVALUATION.md`, `ROADMAP.md`, and `STATUS.md`
before selecting work. CAVAA is cumulative 2026 expected points above the
first-unit positional benchmark under comparable observed context. Equal-player
and opportunity-weighted benchmarks are required sensitivity analyses.

Keep benchmark membership independent of leaderboard eligibility. Preserve
negative games and historical weekly publications. No recency discount on the
season ledger. No full play EPA awarded independently to multiple teammates,
arbitrary position multipliers, score-derived eligibility, or invented scores.
Statistical predictions are observational estimates, not demonstrated causality.

Defense is a required workstream: historical information-loss experiment and
Defense Explorer. Unsupported contributions remain missing with reasons, never
zero or fabricated ranks. A position enters the unified leaderboard only after
its measurement and comparability gates pass. Partial on-ball value must be
labeled; targets are not a complete measure of receiving value.

## Safe daily workflow

Follow `docs/DAILY_WORKFLOW.md`. Acquire the common-Git-directory run lock before
mutating the repository; retain its token until completion. A manual turn and a
scheduled run follow the same lock. Never remove a lock merely because it is old.
If another owner is active, leave its checkout alone and report the blocker.
Delegated agents operate under the parent's lease with disjoint file ownership.

Inspect status, origin, branches, recent commits, GitHub PRs/reviews/CI and roadmap
before work. Fetch without resetting local changes. Preserve unfinished work.
Use `codex/` branches and reviewable PRs; never merge PRs, enable auto-merge, push
implementation to main, or force-push. The only direct main commit was the empty
repository bootstrap. If prerequisite work is awaiting review, continue a
coherent existing PR or use an explicitly documented stacked PR.

Implement one meaningful unit, add appropriate tests, run `make check`, inspect
the complete diff, fix defects, rerun affected checks, and update `STATUS.md`,
`ROADMAP.md`, and `docs/learning/YYYY-MM-DD.md`. Commit and push verified work,
open/update a PR and report it. Explain what changed, why, statistical concepts,
verification, limitations, review focus, and next steps. Do not claim checks or
experiments ran when only their design exists.

## Engineering conventions

Python batch computation and immutable versioned outputs; React/TypeScript
dashboard. Add complexity only when validated. Current core uses Python 3.11+
stdlib; any new dependency must have a documented purpose, compatible license,
and reproducible version policy. Use deterministic seeds for experiments.

Keep downloaded source data and generated artifacts out of normal Git history.
Capture source URL, fetched timestamp, source update time if supplied, bytes hash,
schema, license, game coverage, code revision, model settings and cutoff. Never
silently treat missing observations as zero. Offline tests use synthetic fixtures
clearly labeled as such. Live source audits are separate from offline CI.

Production weekly refresh must run independently of Codex development. Local
development schedules require this computer and the app to be running; record
failures honestly and do not weaken publication checks to meet a deadline.
