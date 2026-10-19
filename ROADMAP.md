# Delivery roadmap

Target release: **November 7, 2026**. Research and design were approved on October 18. This roadmap deliberately reserves time for validation and release repair rather than adding increasingly elaborate models.

## October 18: bootstrap

- Establish an independent canonical repository and stable local clone.
- Implement the first benchmark and qualification contracts with meaningful tests.
- Add CI, engineering instructions, status notes, and a learning log.
- Open the first reviewable PR; configure the separate authorized development automation.

These are bootstrap tasks, not evidence that the player-value model works. The current project-status record tracks what is actually complete.

## October 19–23: data contracts and transparent baseline

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
