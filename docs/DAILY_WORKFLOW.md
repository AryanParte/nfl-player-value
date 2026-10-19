# Daily development workflow

The canonical repository is [AryanParte/nfl-player-value](https://github.com/AryanParte/nfl-player-value). Its stable local clone is `/Users/aryanparte/Documents/Codex/projects/nfl-player-value`. The separate Codex development heartbeat runs at **7:30 PM America/New_York daily** when the local execution environment is available. The existing NFL Opponent Intelligence project and its automation are independent and must not be changed.

GitHub is the permanent source of truth. A scheduled run reads current repository state and this roadmap rather than assuming yesterday's task remains unfinished. The November 7, 2026 launch target takes priority over optional features. Recurring costs must remain below $100/month, preferably zero; no purchase or paid service may be enabled without explicit user approval.

## Acquire one lease for the entire run

Before any repository mutation, run:

```sh
cd /Users/aryanparte/Documents/Codex/projects/nfl-player-value
python3 scripts/run_lock.py claim --run-id YYYY-MM-DD-development
```

Retain the returned random `token` privately for the duration of this run. It is a local coordination secret, not a GitHub credential. Do not commit it or include it in reports or PRs. Use the exact returned value when checking ownership:

```sh
python3 scripts/run_lock.py check --token TOKEN_FROM_CLAIM
```

Check ownership before each group of mutations, including fetches, branch changes, edits, Git writes, and pushes. A successful claim persists across separate terminal/tool calls; a short-lived shell process ending does not release it. Keep the lease until tests, review, documentation, push, PR creation/update, and the learning report are complete. Release it in a final cleanup step:

```sh
python3 scripts/run_lock.py release --token TOKEN_FROM_CLAIM
```

The CLI verifies the exact canonical GitHub origin (HTTPS or SSH), then puts the atomic directory lease in Git's common directory. Every linked worktree of this clone therefore shares the lease. Do not create an independent clone to bypass an existing lease. Subagents may perform explicitly delegated work under the parent run's lease; only the owner manages Git operations and releases it. Give subagents disjoint file ownership.

If claiming or checking fails, perform no repository mutation. Read-only diagnosis is allowed. Report a blocked run if another owner is still working; do not produce a filler commit. A lock is advisory and relies on every agent following this protocol. It does not serialize unrelated repositories or limit aggregate machine/account resource use.

## Recovery after an interrupted run

`python3 scripts/run_lock.py status` shows the run ID, creation time, and claim-process ID without printing the token. There is deliberately no expiry or automatic lock stealing. The recorded PID belongs to the short-lived claim command, so its absence does **not** establish that the agent has stopped. Age alone does not establish this either.

If the owning run is conclusively stopped and its token is available, release normally. Otherwise a human operator must first confirm the owning Codex run and any delegated writers have stopped and inspect unfinished changes. Obtain the common directory with `git rev-parse --path-format=absolute --git-common-dir`, then move its `nfl-player-value-development.lock` directory to a unique archival name in that same directory. Preserve the archived metadata for diagnosis; never run an age-based deletion job. Only then claim a new lease. Missing or malformed metadata also requires this recovery procedure; it is not permission to steal a lease.

## Execute one coherent engineering unit

1. Claim the lease and inspect `AGENTS.md`, `ROADMAP.md`, current project status, and recent learning reports. Inspect `git status`, branches, and worktrees before doing anything that could overwrite local changes.
2. Check ownership, fetch the canonical remote safely, and inspect recent commits, open PRs, review feedback, and CI results. Do not reset, clean, force-push, or overwrite unfinished work. Do not pull over a dirty tree. Resolve uncertainty about ownership before changing another run's work.
3. Select the highest-priority unfinished task that fits the launch scope. Prefer finishing or repairing an existing coherent PR to duplicating it. With an unmerged foundation PR, continue its branch for a coherent extension or use an explicitly stacked PR with the correct feature-branch base. A missing merge is not authorization to merge.
4. Work on a `codex/` feature branch. Implement a meaningful unit, add tests for material behavior and failure cases, and run required checks. Keep model fitting and historical experiments offline. Preserve provenance and distinguish absent data from zero contribution.
5. Critically review the actual diff. Check statistical estimands, time leakage, double-counting, source licenses, reproducibility, missing-data behavior, and truthful UI labeling where relevant. Fix discovered defects and rerun affected checks. Do not turn those checks into filler documentation when they are inapplicable to the change.
6. Update the roadmap, project status/next task, and a dated learning report. Commit only reviewed files, push the feature branch, and open or update a reviewable PR. Never merge or push directly to `main`. The initial empty-repository bootstrap is a one-time exception handled during repository creation, not permission for future direct pushes.
7. Report the PR link, verification evidence, unresolved uncertainties, and next priority. Release the lease even after a recoverable failure. If a tool failure prevents release, report the held lease and run ID so recovery can be deliberate.

An independently useful partial unit is acceptable when a larger task is too broad. Unverified code must not be presented as complete. If data or identification limits prevent a defensible ranking, expose the coverage limitation and continue the required defensive workstream rather than inventing scores.

## Learning report contents

Each daily report explains what was built and why it matters; the engineering decisions; the statistical/ML ideas the owner should understand; the checks actually performed and their results; remaining uncertainty; what to review; and the next task. Record meaningful failures as well as successes. Never fabricate activity or add empty commits to satisfy a daily target.

## Production refresh is independent

The deployed weekly ranking refresh must operate independently of this Codex development heartbeat. It consumes completed games, records exact source versions/cutoffs, computes reproducible outputs, and preserves prior weekly snapshots. A delayed development run must not stop publication of already validated production models. Production workflow concurrency and atomic publication need their own controls when that workstream is implemented.

The 7:30 PM development schedule is separated from the existing Opponent Intelligence 8:00 AM schedule. Distinct repositories, environments, caches, and ports prevent accidental cross-project changes. The time difference reduces routine contention, but a long run can still overlap: inspect active work and defer expensive local fitting when the machine is busy. Never alter the other project's schedule or workspace as a workaround.
