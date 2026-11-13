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

## Execute one substantial coherent deliverable

1. Claim the lease and inspect `AGENTS.md`, `ROADMAP.md`, current project status, and recent learning reports. Inspect `git status`, branches, and worktrees before doing anything that could overwrite local changes.
2. Check ownership, fetch the canonical remote safely, and inspect recent commits, open PRs, review feedback, and CI results. Do not reset, clean, force-push, or overwrite unfinished work. Do not pull over a dirty tree. Resolve uncertainty about ownership before changing another run's work.
3. Put the scoring model on the critical path. Read `docs/MILESTONES.md`, select a substantial model-centered deliverable, and pause optional infrastructure except concrete blockers. Inspect PR status rather than assuming a pending merge; continue independent modeling work on a coherent branch or documented stack. A missing merge is not authorization to merge or to stop useful model work.
4. Work on a `codex/` feature branch. A modeling deliverable includes implementation, meaningful bounded experiments, failure analysis, justified fixes/alternatives, verification and a documented decision. One component, commit or negative result is not an automatic stopping point. Use multiple reviewable commits and continue through recoverable problems within capacity. Freeze alternatives and validation rules before evaluating new results; never tune on already inspected tests. Keep fitting offline, preserve provenance and distinguish absence from zero.
5. Critically review the actual diff. Check statistical estimands, time leakage, double-counting, source licenses, reproducibility, missing-data behavior, and truthful UI labeling where relevant. Fix discovered defects and rerun affected checks. Do not turn those checks into filler documentation when they are inapplicable to the change.
6. Update the roadmap, project status/next task, and a dated learning report. Commit only reviewed files, push the feature branch, and open or update a reviewable PR. Never merge or push directly to `main`. The initial empty-repository bootstrap is a one-time exception handled during repository creation, not permission for future direct pushes.
7. Report the PR link, verification evidence, unresolved uncertainties, and next priority. Release the lease even after a recoverable failure. If a tool failure prevents release, report the held lease and run ID so recovery can be deliberate.

For active recovery evidence, read `docs/DENSITY_HOLDOUT_RESULTS.md` and its frozen
plans; preserve all earlier failures. Five known-answer coverage gates pass, but
the archived numerical pilot retains one pass and four failures. Stabilization
improves average density overlap but does not guarantee functional accuracy or
stable individual pilots. The real QB check remains 0.014228 SD / 0.001308 CDF
against unchanged 0.01 / 0.001 limits; no confidence set establishes primary bias.
The failed prior-stress factorization reproduces at a 9.66e-24 precision, below
matrix roundoff scale. Next freeze a target-preserving conditional-solver
repair/equivalence study with exact-alias/weak-precision known answers. Do not
substitute zero likelihood, add arbitrary jitter, change priors or select another
seed to erase the failure. Retain the original artifacts, then diagnose remaining
primary/reference disagreement with independent declared randomizations/budgets.
Recompute failure decompositions from raw replicates in the declared prior-setting
order; sorted JSON keys are not the integrand's functional order.
Do not automatically enlarge primary samples or call reused cases fresh validation.
Weight-based effective counts describe concentration, not independent observations.
Shared conditional code remains a limitation. Exact replay is not calibration;
failed/unattempted trials remain visible. No module is admitted by numerical
coverage or by successful Explorer deployment.
The 64-per-scenario calibration remains unfinished. Keep attempted
failures distinct from unattempted trials, both in the requested denominator;
success-only coverage never certifies the complete study. Preserve the sealed
Week 10 window and saved model versions.
Passing matched-prior coverage or avoiding a severe-undercoverage flag is not
general calibration. Known-variance controls use unavailable synthetic knowledge;
never install their ratios or wider intervals as an NFL uncertainty fix. New
failure-analysis hypotheses require new preregistered draws, not a rerun selected
to improve the previous result.

An independently useful partial milestone is acceptable when genuinely blocked or
capacity-limited, with the remaining work explicit. It is not permission to stop
at a proposal, small component or first failed experiment. Unverified code is not
complete. If identification prevents a defensible ranking, diagnose the failure,
evaluate the bounded alternatives and preserve the defensive workstream. Never
invent a score or relax validation to manufacture progress.

## Learning report contents

Lead each report with the scoring/product milestone: implemented behavior, evidence
that passes, remaining blockers and next concrete action. Distinguish implementation,
software verification and scientific validation. Then explain decisions, concepts,
actual experiments/failures, uncertainty, review focus and PR. Do not optimize or
report success primarily in lines, commits or test counts. No completion percentage
without a measured backlog basis and uncertainty; the previous “60% remaining”
claim is not an established estimate. Never fabricate activity.

## Production refresh is independent

The deployed weekly ranking refresh must operate independently of this Codex development heartbeat. It consumes completed games, records exact source versions/cutoffs, computes reproducible outputs, and preserves prior weekly snapshots. A delayed development run must not stop publication of already validated production models. The merged Explorer production workflow has separate concurrency, retention and publication controls; its hosted activation remains unverified. It does not yet publish CAVAA rankings.

The 7:30 PM development schedule is separated from the existing Opponent Intelligence 8:00 AM schedule. Distinct repositories, environments, caches, and ports prevent accidental cross-project changes. The time difference reduces routine contention, but a long run can still overlap: inspect active work and defer expensive local fitting when the machine is busy. Never alter the other project's schedule or workspace as a workaround.

## October 23, 2026 scheduling exception

The owner requested the October 23 unit immediately instead of at 7:30 PM.
That run is recorded in the October 23 learning report. The existing automation
was updated through the app to start October 24, 2026 at 7:30 PM America/New_York,
retaining its daily recurrence, prompt and target chat. This skips only the
October 23 occurrence; there is no duplicate automation or permanent time change.
The other project's automation was not edited. This note records the exception,
not a recurring instruction to reschedule future runs.
