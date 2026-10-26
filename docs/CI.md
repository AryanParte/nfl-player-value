# CI, regression evidence and release gates

The existing GitHub Actions pipeline remains the single PR CI system. Ordinary
PR tests use synthetic fixtures and archived-data interfaces, without downloading
NFL data. Dependency installation and optional security audits need the network.
No workflow receives deployment secrets or repository write permission, and
checkout does not retain Git credentials. The separate Codex development schedule
is unchanged.

## Three validation levels

| Level | Implemented checks | When |
| --- | --- | --- |
| Fast PR CI | Python 3.11/3.12/3.13 unittest matrix; installed-package smoke test; Ruff; branch/statement coverage; compileall/whitespace; Node 24 locked install; Prettier, Vitest, TypeScript, Vite build; eight Chromium scenarios | PRs and pushes to main |
| Optional checks | `Optional dependency audit`: pip-audit and npm audit, including development dependencies; existing bounded historical experiment CLIs run separately from CI | Manual dispatch; rerun before launch or dependency changes |
| Publication gates | Current source/experiment replay and local Defense Explorer export safeguards; the remaining ranking-release acceptance contract below | Production ranking refresh is **not implemented** |

Both workflows have timeouts, read-only permissions, concurrency controls and
SHA-pinned actions. The audit has no cron and creates no new Codex automation.
GitHub rulesets/required-check settings were not changed or claimed verified.

## Local checks and diagnostics

```sh
.venv/bin/python -m pip install --upgrade 'pip==26.2.2'
.venv/bin/python -m pip install '.[model,quality]'
make check PYTHON=.venv/bin/python
make coverage PYTHON=.venv/bin/python
# When diagnosing a failed coverage run, preserve its failure and still render:
make coverage-report PYTHON=.venv/bin/python
npm --prefix web run test:e2e
```

[Ruff](https://docs.astral.sh/ruff/linter/) 0.17.2 (MIT) finds syntax/name errors,
unused imports and selected high-signal bugs across `src`, `scripts` and `tests`.
Formatting is introduced incrementally: `PYTHON_FORMAT_FILES` in the Makefile
currently checks the substantially edited baseline CLI and new reliability tests.
Expand that list when substantially editing other modules; this is not a claim
that all legacy Python is formatter-clean. Explicit project configuration avoids
inheriting unrelated parent-directory lint settings. Two existing unused imports
were removed. No pytest migration was needed.

[coverage.py](https://coverage.readthedocs.io/en/latest/branch.html) 7.17.0
(Apache-2.0) measures which statements and branch destinations ran. Before this
unit, 186 tests covered **86.61%** combined, **87.67%** statements and **84.23%**
branches. The 199-test suite measures **90.15%**, **92.08%** and **85.78%** respectively
on local Python 3.13.2. Source scope includes every Python module and `run_lock.py`,
including unexecuted CLIs; no files were excluded to raise the percentage.
Coverage remains informational: a numerical threshold would not establish that
CAVAA allocates shared outcomes correctly. Missing branches remain review targets.

HTML, XML and JSON reports are under ignored `artifacts/coverage/`; CI retains a
separate artifact per Python version for 14 days and puts a table in the run
summary, including when tests fail. Tests use the source tree for coverage; the
separate installed-package smoke check remains outside the checkout.

Playwright retains HTML/JUnit results plus failure traces/screenshots for 14 days,
even after test failures. `forbidOnly` prevents an accidentally focused test from
silently excluding the suite. Retries remain zero, the worker count remains one,
and the isolated test server cannot reuse an existing server. npm downloads are
cached; Chromium installs with OS dependencies remain explicit, avoiding a browser
cache whose saved binary would not supply Linux libraries. Reports and generated
coverage files are ignored by Git. CI artifacts are diagnostics, **not durable NFL
snapshot storage**.

Static type checking was considered but deferred: the highest-risk boundaries are
currently nested JSON dictionaries validated at runtime. A checker permitting
those dictionaries as `Any` would miss the failures addressed here; tightening all
schemas now would expand this unit substantially. Introduce typed model/release
contracts with the ranking schema, then evaluate a narrow strict type-check target.

## Statistical and data protections

| Risk | Evidence in the suite |
| --- | --- |
| Shared EPA, negative values, missing actors | Existing baseline and defense tests conserve components plus residuals, preserve negative outcomes, and withhold ambiguous identities without duplicating full play EPA |
| Sparse/collinear players and numerical drift | Existing known-effect/collinearity cases and independent dense ridge solutions test the regularized solvers, including weighted defensive aggregation |
| Future-data leakage | Existing chronological split and held-out-outcome perturbation tests protect fitting and penalty selection; postplay hardship variables remain excluded |
| Corrupted bytes versus incorrect analysis | Existing hash tests detect corrupt bytes; new real-fit CLI tests also reject correctly hashed changed coefficients, individual prediction components and mismatched defense provenance envelopes |
| Invalid numerical/version values | Replay now rejects matching infinities, NaNs and boolean experiment/schema versions, while retaining the declared small roundoff tolerance |
| Unresolved identity and coverage | Existing join/completion tests plus new model-entry conflict regression fail before fitting; missing observations remain distinct from measured zero |
| Source receipts, duplicate records and cutoff drift | Existing ingestion, schedule, first-unit and input tests cover schema/duplicate failures, unavailable sources, mismatched cohorts and retrospective evidence |
| Failed export or archive write | New CLI/reconstruction and fsync fault injection verify old bytes/pointers survive, staging files disappear and invalid manifests do not advance publication; existing replacement-failure tests remain |

New model integration tests start at synthetic **validated input reports**: raw
receipt replay is stubbed, while parsing, hashed storage, fitting, selection,
serialization and numerical replay are real. They complement raw-source tests;
they are not an end-to-end real-NFL or causal validation claim. A valid hash proves
byte identity, not the correctness or scientific validity of those bytes.

Direct Explorer export now requires manifest/payload agreement on producer revision
and source report identities, strict versions and explicit `ranking_ready=false`.
The CLI still reconstructs and checks the payload before export. Direct export
assumes that prior replay, and neither entry point admits CAVAA scores. No fitting
penalties, benchmark definitions, eligibility rules or position admissions changed.

## Manual dependency audit

[pip-audit](https://github.com/pypa/pip-audit) 2.10.1 (Apache-2.0) checks installed
Python packages against public known-vulnerability advisories. The workflow installs
the editable project with model/quality extras, installs the build requirements
from `pyproject.toml`, checks dependency consistency, saves resolved versions, and
audits everything except the local editable project. Its own transitive tools are
included. Audit-tool dependencies resolve at run time and are recorded; model and
frontend dependency pins are unchanged. npm audit includes the lockfile's runtime
and development dependencies. Both jobs fail on reported vulnerabilities or audit
errors; there is no blanket ignore, automatic fix or `continue-on-error`.

Local audit found advisories for pip 25.0 and setuptools 80.9.0. CI now explicitly
bootstraps pip 26.2.2; the build backend is pinned to setuptools 84.1.0. The latter
includes the [documented archive/namespace path fixes](https://setuptools.pypa.io/en/latest/history.html#v84-1-0).
Some advisories are platform/path-specific; their presence is not evidence of an
exploited application. Re-auditing with these pins reports no known vulnerabilities
in Python or npm as of this run. Advisory records may duplicate aliases; report
unique issues rather than treating every JSON entry as a distinct flaw.

Optional audit execution adds no application runtime dependency or purchased
service. Reports retain 14 days. Registry/advisory outages must be distinguished
from successful audits; a green result is not a guarantee of security. Native
Dependabot alerts/rulesets were not enabled or assumed present by this change.

## Acceptance contract for future weekly ranking publication

The following gates must be implemented/tested against the actual ranking schema,
not simulated as if rankings already exist. The publisher must validate the whole
candidate bundle before advancing a pointer and preserve the last valid release
on *every* rejected refresh.

| Gate | Existing foundation | Remaining acceptance test |
| --- | --- | --- |
| Completed games and source readiness | Terminal-event/score reconciliation and receipt cutoffs | Required-feed quorum, expected completed-game set and source-specific freshness policy; reject stale/missing feeds without replacing last good release |
| Historically available evidence | Retrieval timestamps and retrospective labels | Correct `SeasonExposure` observed-by handling; reject future roster/chart evidence in historical evaluations |
| Exact model/benchmark versions | Hashed plans, model artifacts and numerical replay | Release manifest binds admitted model, first-unit benchmark, both sensitivity definitions, qualification and schema versions |
| Accounting and uncertainty | Additive outcome conservation and independent solver references | First-unit contrasts conserve the allocated shared components; joint player/benchmark uncertainty and negative season totals survive serialization |
| Ranking correctness | Existing qualification/benchmark unit contracts; no scores admitted | Three-game/role opportunity grid, eligibility independent of benchmark membership, deterministic ties, cumulative games without recency decay, missing score versus zero |
| Position admission | Explicit unadmitted Explorer values and rejection in Python/browser | A scored row must reference a passing admission decision for its module/position; partial scope cannot silently appear as universal value |
| Reproducibility and retention | Append-only local objects, exact source and numerical model replay | Restore on a clean machine from durable retained bytes; previous weekly and corrected releases remain retrievable |
| Publication failure recovery | Local atomic object-before-pointer ordering and failure tests | Deployment-store concurrency, immutable release index, monotonic/corrected cutoff policy, rollback and failed-refresh end-to-end tests |

These gates do not yet constitute a production ranking validator. Durable remote
retention, weekly refresh, deployment and admitted 2026 rankings remain launch
blockers. The next statistical roadmap unit remains identity/stint evidence and
benchmark/qualification validation, not more CI framework work.
