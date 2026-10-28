# Delivery roadmap

Target release: **November 7, 2026**. Research and design were approved on October 18. This roadmap deliberately reserves time for validation and release repair rather than adding increasingly elaborate models.

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

October 28 priority: bounded calibration/attribution stress tests and a formal
admission decision, with prespecified clustered/shrinkage and absence/cast cases.
The now-measured selective exposure rule cannot be promoted to general
eligibility. Resolve historical missing chart evidence and broader stints without
invented fills or outcome-selected cohorts. Protect the October 28–30 freeze and
November 7 target; the universal-MVP objective remains at risk. Defense requires
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

Each development run should deliver one coherent verified unit, update status and learning notes, and open or update a PR. A blocked run should record the actual obstacle; filler commits are not progress.
