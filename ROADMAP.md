# Delivery roadmap

Target release: **November 7, 2026**. Research and design were approved on October 18. This roadmap deliberately reserves time for validation and release repair rather than adding increasingly elaborate models.

## November 7 execution reset: scoring first

The target arrived without a usable CAVAA ranking. The dated sections below are
delivery history/plans, not evidence that their calendar milestones were met.
The active backlog is [M1–M6](docs/MILESTONES.md), separating implementation,
passing evidence, blockers and the next concrete action; no completion percentage
is justified. Pause optional infrastructure unless it removes a concrete blocker.

The first substantial recovery unit is complete: four preregistered QB dropback
alternatives, new historical/transfer windows, cumulative 2026 contrasts, fresh
calibration, allocation/sensitivity diagnostics, an additional known-variance
control and a [documented non-admission decision](docs/QB_RECOVERY_RESULTS.md).
The unit identifies variance estimation/boundaries and QB/team confounding as
remaining problems; it does not claim the scoring milestone is complete.

November 8 completes that [multi-season unit](docs/MULTISEASON_RESULTS.md): four
alternatives, variance integration, three new calibration generators, fresh
known-ratio failure controls, cumulative 2026 contrasts and the required defensive
diagnosis. Matched-prior coverage passes an internal check; off-grid coverage
remains below nominal. Historical links do not remove allocation ambiguity.

November 9 implements and evaluates that [continuous-variance candidate](docs/CONTINUOUS_RESULTS.md),
one target-preserving proposal repair, exact mixture intervals and independent
offline reconstruction. Both real fits fail numerical accuracy. The documented
scope stop completes eight attempts per generator with 4/3/0 numerically valid;
56 per generator remain unattempted in the original denominator. Full calibration
is unfinished and no module is admitted. Weight concentration in weak team/game
variance tails is the next concrete numerical problem, not evidence for changing
priors or inflating intervals. The archive remains November 7 evening coverage.

November 10 completes the [independent numerical-reference unit](docs/VARIANCE_REFERENCE_RESULTS.md):
all five original QMC stress checks pass; every original deterministic reference
exhausts its solve budget. Exact node reuse and a budget-aware complete-subdivision
checkpoint preserve error estimates in the follow-up. All five follow-up references
fail, so no contribution module is admitted. Both versions independently reproduce
all failures offline, with identical model/result bytes between versions. This
consumed-case pilot is not fresh calibration.

November 11 implements and evaluates [binary reference refinement and a
correlation-aware alternative](docs/DIMENSION_REFERENCE_RESULTS.md), with frozen
plans, known-answer controls, complete case retention and independent replay. The
first version passes the team control but not the QB or three consumed stress
cases. The second loses the real team pass; improved-looking raw agreement cannot
override nonconvergence or reference error. No contribution module is admitted.

November 12 implements the [higher-order comparison](docs/HIGHER_ORDER_REFERENCE_RESULTS.md):
nested sparse quadrature, independent analytic controls and a predeclared dense
rule comparison. The real QB/team sparse references fail; neither tensor
alternative passes all controls, so both are blocked from the archived runner.
No posterior, accuracy threshold or admission rule changes, and no new calibration
is claimed. The archive remains November 7 evening coverage.

The additional November 12 manual unit implements the
[replicated randomized reference](docs/RANDOMIZED_REFERENCE_RESULTS.md). Two initial
proposals and the first density-adapted study fail; a separately frozen larger
confirmation of unchanged geometry passes all four known-answer gates. The real
QB reference still fails because numerical uncertainty is too large, while the
team-only control passes. These are numerical findings, not fresh calibration or
admission. Failed studies remain immutable and replayable.

November 13 completes the [paired density/stabilization unit](docs/DENSITY_HOLDOUT_RESULTS.md).
All five coverage gates pass on 5,120 completed known-answer trials; all 160 known
and 19/20 archived density pairs finish. One conditional factorization failure
remains. The five-case numerical pilot has one pass and four failures, all
independently reproduced offline. Real-QB discrepancy plus error improves to
0.014228 SD / 0.001308 CDF, still outside 0.01 / 0.001. A bounded trace reproduces
a 9.66e-24 precision lost at matrix roundoff scale. No jitter, prior change or
scoring admission follows. Primary models, predictions and season ledgers retain
their earlier object hashes.

Next substantial unit: freeze a target-preserving conditional-factorization
repair/equivalence study using exact aliases, weak precisions and independent
known answers. Resolve that concrete failure before another proposal search.
Then diagnose remaining primary/reference disagreement under separately declared
randomizations and budgets; do not automatically enlarge primary nets or select
a favorable density pilot. Numerical reliability precedes the unfinished 192-fit
calibration, prospective evidence and observational admission. Week 10 stays
sealed. Defense remains mandatory; November 13 metadata still finds no
2026-named asset in the checked participation release, not all-provider absence.

PRs #18–#26 are merged; main CI passed. Authenticated Pages/bootstrap access remains
unavailable, so deployment cannot hold up modeling. Produce the first admitted,
reproducible contribution module, then connect its honest estimates/explanations
and history to the existing dashboard. Cross-position coverage remains the goal;
unsupported modules stay explicitly unavailable. Update milestone evidence each
run, using multiple reviewable commits where useful; never merge as an agent.

## October 18: bootstrap

- Establish an independent canonical repository and stable local clone.
- Implement the first benchmark and qualification contracts with meaningful tests.
- Add CI, engineering instructions, status notes, and a learning log.
- Open the first reviewable PR; configure the separate authorized development automation.

Completed in [PR #1](https://github.com/AryanParte/nfl-player-value/pull/1), merged by the owner. These contracts are not evidence that the player-value model works.

## October 19–23: data contracts and transparent baseline

October 19 progress: immutable capture, source audit, and offline replay now work
for real 2026 PBP, rosters, and depth charts. See [ingestion](docs/INGESTION.md).

October 20 progress: schedule capture, terminal-PBP/score reconciliation,
formation-aware pregame first-unit selection, and immutable offline derived
reports now work. Fresh data reconcile 93 games through Week 6. The audit retains
11 blocked cohort issues and flags retrospective availability; no score is
published. See [pregame inputs](docs/PREGAME_INPUTS.md).

October 21 progress: dedicated historical participation capture with its own
CC-BY-SA terms, structural identity/lineup checks, join audit and paired research
inputs are implemented. The 2025 cohort retains 241 games / 29,059 plays; the
whole-game rule excludes 29 games with candidate lineup failures. Two additional
games reveal the strict completion rule's numeric-ID ordering assumption and
remain excluded. See [defensive inputs](docs/DEFENSE_INPUTS.md).

October 22 progress: completion v2 checks quarter/clock evidence and restores the
two reordered-event games; old reports replay unchanged. The defensive paired
cohort is now 243 games / 29,297 plays. The new offensive ledger has one EPA outcome
per play, observed actor links and nonduplicated workload unions. Fresh 2026 data
provide 11,441 candidate plays in 93 games; 2025 provides 32,813 in 272 games.
Actor gaps remain visible without dropping their negative team outcomes.

October 23 progress: the first context, team, observed-role and regularized
joint-actor baselines are fitted under a committed chronological plan. Validation
selected penalty 1000. The final 2025 actor-identity increment over the role model
has an interval spanning zero; the 2026 transfer gain is small. Results, shared
component accounting, collinearity and numerical replay are recorded in the
[baseline audit](docs/audits/2026-10-23-offensive-baseline.json). No CAVAA is admitted.
The immediate owner-requested run counts as today's work; the existing daily
7:30 PM Eastern automation resumes October 24 and skips October 23.

October 24 progress: the first bounded [defensive rich/degraded comparison](docs/DEFENSE_MODEL.md)
is fitted and replayed on the same 243-game cohort. Both select penalty 1000; neither
adds reliable predictive improvement over its team/context baseline. Aggregation
reduces residualized defender rank from 922 to 301 across 951 columns. Selection
diagnostics account for 3,516 excluded plays; no measured standardized difference exceeds
the fixed flag, without establishing harmless selection. No defender is admitted.
PRs #6 and #7 were subsequently merged by the owner before the October 25 run.

October 25 progress: the required [Defense Explorer foundation](docs/DEFENSE_EXPLORER.md)
and first React/TypeScript dashboard are implemented. The archived Week 6 view
contains 518 players, 425 recorded sack credits and 130 interceptions; four sack
events, 92 chart roles, one name and ten defensive role cells retain explicit
limitations. Charts show team EPA without attributing it to individuals. Hash
verification, runtime contracts, offline replay and browser tests guard the view.
No live workload fractions or CAVAA scores are supplied, and the site is not yet
deployed. See [the measured audit](docs/audits/2026-10-25-defense-explorer.json).

October 26 progress: [weekly position/team evidence](docs/ROSTER_INPUTS.md) now
archives the distinct weekly roster source, joins exact GSIS/team/season/week,
preserves missing and ambiguous observations, and replays both seasons offline.
2025 resolves 5,323/5,347 observed offensive player-game positions; archived 2026
resolves 1,814/1,819. Broad labels remain unresolved. The `SeasonExposure`
observed-by timestamp bug is fixed with regression tests. Weekly listing is
insufficient to certify exact roster stints: that policy/denominator gate remains
open, with no backfill or invented participation. See the
[audit](docs/audits/2026-10-26-roster-evidence.json).

October 27 progress: the [frozen positional contrast experiment](docs/CONTRASTS.md)
fits six cumulative windows and three declared penalties, with both benchmark
sensitivities, joint conditional intervals, complete component accounting and
offline numerical replay. Twenty regressions guard independent math, leakage,
negative/shared accounting, cold priors, exposure and artifacts. Archived 2026
Week 6 supports 463 role-players' diagnostic contrasts but only 163 denominators
under the narrow full-observed single-team rule. The 0.75×/1×/1.25× grid admits
158/146/130 on participation alone; zero receive main admission. Later 2025
RB/WR/TE benchmark cells fail closed on one ARI game's missing slots. The largest
2026 penalty range is 87.14 EP versus 0.54 EP across benchmark choices at the
primary setting. See the [audit](docs/audits/2026-10-27-positional-contrasts.json).

October 28 progress: [known-effect calibration](docs/CALIBRATION.md) implements
four frozen scenarios, three unchanged penalties and 256 replicates on each real
Week 6 design (6,144 synthetic-response fits), plus exact-alias diagnostics.
Both complete chains replay offline. Matched-prior conditional coverage is near
95%, while stronger-signal primary coverage falls below 2%; the game-cluster
diagnostic does not fix regularization bias. Oracle expectation controls remain
near 95%. No interval or position is admitted. Thirteen new regression tests
protect independent algebra, cold parameters, simulated truth and archive replay.
See the [audit](docs/audits/2026-10-28-calibration.json).

October 29 progress: the [frozen QB/target-mix audit](docs/TRANSITIONS.md) reuses
the original baseline predictions and evaluation games, with full offline replay.
It retains 61/112 adjacent pairs and all 35/42 exclusions in 2025/2026. Eight/five
QB changes provide weak, selected evidence; only four/two identity swaps have
training support for both players. The joint model does not improve mean change
error in those QB-change groups. Fifteen new regressions protect case selection,
chronology, accounting, missing evidence and artifact integrity. Target mix is
observed usage; injury causes, cast quality and real substitution effects remain
unverified. See the [audit](docs/audits/2026-10-29-transitions.json).

November 2 progress: the overdue October 30 module decision is recorded on its
actual date. The [admission contract](docs/ADMISSION.md) binds 13 evidence/plan/
policy references and records seven gates for every one of the 17 supported role
codes. All current modules remain unadmitted. The read-only CLI verifies hashes
and rejects score requests; a participation adapter preserves the existing
thresholds. Fourteen new regressions guard evidence corruption, missing modules,
scope changes, false admission and eligibility separation. The production ranking
validator and an actually admissible model remain unfinished. See the
[decision](docs/decisions/2026-11-02-module-admission.md).

November 3 progress: the [availability panel and static review bundle](docs/STATIC_REVIEW.md)
expose all 17 unadmitted modules with exact evidence links, independent integrity
checks and retries. The full archived Explorer chain plus a clean committed
frontend builds into an immutable 1.19 MB ZIP; two offline builds are byte-identical.
The restored `/nfl/` view passes desktop/mobile inspection. Thirteen Python,
fourteen frontend and four browser regressions protect these boundaries. See the
[audit](docs/audits/2026-11-03-static-review.json). This is local archived research,
not deployment, durable remote retention, fresh coverage or admitted rankings.

November 4 progress: [Explorer recovery](docs/RECOVERY.md) packages the exact 17
verified store members, source credits/licenses and saved review ZIP. Two offline
packs produce the same 32,538,960-byte archive; all 20 entries restore byte-exact
with complete candidate-store replay. Twenty-two regressions cover corruption,
missing/extra dependencies, unsafe paths, failure cleanup and prior-data
preservation. The [audit](docs/audits/2026-11-04-recovery.json) records unchanged
cutoffs and null scores. Remote upload/download verification remains blocked on
authenticated release-upload access; historical/model research stores remain
outside this narrow recovery artifact. Local recovery is not durable remote
retention, deployment or ranking admission.

November 5 progress: [source readiness and immutable Explorer candidates](docs/SOURCE_READINESS.md)
now check four source receipts, retrieval/upstream ages, all 32 teams' chart ages,
the full schedule inventory and completed-game reconciliation. The real candidate
has 121 games / 14,851 plays / 562 players through Week 8, adding 28 games and
recording two changed earlier team-context rows. Offline replay and the frontend
contract pass; old Week 6 inputs correctly fail at the new cutoff. Eighteen
regressions protect stale/missing/corrupt inputs, frozen replay and preservation
of prior candidates. No public pointer, model or admission decision changed. See
the [audit](docs/audits/2026-11-05-source-readiness.json).

November 6 progress: [portable Explorer launch packages](docs/LAUNCH_PACKAGE.md)
bind the exact candidate/site, a new packaging-time source assessment and all
current/prior-comparison replay dependencies. Optional isolated builds preserve
the canonical staged site. Twelve new Python regressions cover missing, stale,
corrupt or mismatched evidence, complete restoration and failure cleanup. The UI
now says the latest included week may be partial; a completed game from Week 9
does not imply complete Week 9 coverage. The 39-member package restores exactly,
and its saved site passes desktop/mobile checks. See the
[audit](docs/audits/2026-11-06-launch-package.json) and
[learning report](docs/learning/2026-11-06.md).

November 7 implements the [GitHub-native Explorer refresh/publisher](docs/PRODUCTION_REFRESH.md),
stacked on PR #18. It captures/builds/tests with read-only access, verifies the
exact workflow producer and content hash, downloads/replays draft release assets
before retaining them, and rechecks freshness before requesting Pages deployment.
Failed prepublication gates preserve the prior website. A local real-source
bootstrap rehearsal covers 122 games / 14,960 plays / 562 players; it is not a
remote upload or deployment. Existing CI, the model policies and both Codex
development schedules remain unchanged. See the November 7 learning report.

At the end of the earlier production unit, the next operational action was owner
review/merges, Pages configuration and the first hosted bootstrap. The owner has
since merged #18/#19; the model-first reset above supersedes that priority.
Verify actual off-machine recovery and deployment/failure behavior
before claiming production is active. The November 7 unified-MVP objective is
unmet: all 17 modules remain unadmitted. Keep the exploratory release accurately
labeled and preserve the outstanding statistical work; no paid infrastructure.

The now-measured selective exposure rule cannot be promoted to general
eligibility. Resolve historical missing chart evidence and broader stints without
invented fills or outcome-selected cohorts. Preserve the frozen evidence and
November 7 target; the universal-MVP objective remains unfinished. Defense requires
actual live workload/role coverage, more seasons, absence and uncertainty evidence.

October 25 additional manual reliability unit: preserve the existing CI matrix
and frontend stack while adding Ruff, measured branch/statement coverage,
retained browser diagnostics, 13 replay/archive/export regressions, strict
numerical/manifest guards and an optional manual dependency audit. Patch the
flagged installer/build-tool pins without changing model dependencies. The suite
now has 199 Python tests; coverage is 90.15% and informational. See
[CI and the future publication acceptance contract](docs/CI.md). This extra unit
changes no development schedule and does not complete ranking publication gates.

- Build content-addressed ingestion for 2026 play-by-play, player identifiers, rosters, depth-chart snapshots, and game status.
- Audit historical seasons and current-year schemas before fitting; record source coverage at the game and position level.
- Implement pregame first-unit role membership and the two sensitivity benchmarks. Fail closed on missing required role cells.
- Establish historical splits and a simple regularized baseline with additive player effects where the data identify them.
- Start defensive ingestion and the historical rich-versus-degraded information experiment.
- Produce reproducible development artifacts. Publish no score as CAVAA until its contribution module passes its admission checks.

Exit evidence: a clean offline replay from a recorded manifest, checked player identities and denominators, baseline comparison results, and explicit coverage gaps.

## October 24–27: context and defensive feasibility

- Add supported opponent, teammate, and preplay context adjustments with chronological evaluation.
- Evaluate partial pooling and player/team confounding; retain the simpler model when complexity adds no reliable benefit.
- Run the defensive information-loss experiment, simulations, and absence checks.
- Evaluate cumulative contribution separately from current skill; retain every qualifying season game.
- Begin the Defense Explorer using measured events, workloads, context, and visible missingness.

Exit evidence: measured performance against the baseline, attribution stress tests, a draft defense admission decision, and an accounting audit for shared value.

## October 28–30: bounded decisions and model freeze

- Test the approved qualification grid at 0.75×, 1×, and 1.25× the provisional opportunity requirements.
- Compare first-unit, equal-player, and opportunity-weighted benchmarks.
- Check uncertainty calibration where testable, rank sensitivity, collinearity, and prior dependence.
- Make a documented admission decision for each position/contribution module.
- Freeze release methodology, eligibility policy, labels, and output schemas.

The fallback for failed comparability is a clearly scoped supported-position board plus exploratory coverage. This explicitly leaves the universal-ranking goal unfinished; an experimental label alone does not justify mixing incompatible scores.

## October 31–November 4: dashboard and production refresh

- Build the React/TypeScript leaderboard, player details, benchmark comparisons, uncertainty displays, and weekly history.
- Make supported scope, as-of time, missing sources, and provisional results obvious.
- Implement independent scheduled ingestion and publication, retries, manual reruns, and last-good-output behavior.
- Preserve original weekly releases and timestamped corrected versions.
- Verify mobile use, accessibility, chart labels, and page performance.

## November 5–7: release verification

- Replay the full pipeline from immutable inputs and verify numerical outputs.
- Exercise incomplete games, late feeds, source corrections, schema failure, and deployment rollback.
- Review historical examples without selecting cases only because they flatter the model.
- Confirm attribution and data-license limitations are visible in the product.
- Publish the usable initial website and a reproducibility guide.

## After release

Refresh after completed games when required feeds are available. Publish the Week 10 snapshot after Week 10 completion and source checks, then continue weekly. Track unsupported-position research explicitly. Tracking attribution, graph interaction models, elaborate current-form models, and commercial feeds are later work, not dependencies for launch.

Each development run should complete a substantial coherent deliverable: implementation, meaningful experiments where applicable, failure analysis, justified fixes/alternatives, verification and a documented decision. Update milestone evidence, status and learning notes, and open or update a PR. One component, commit or negative result is not an automatic stopping point. Record real blockers; filler commits are not progress.
