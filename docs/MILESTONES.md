# Product milestone backlog

Execution reset requested November 7, 2026. The launch target was missed. This
backlog reports implemented behavior, scientific evidence and blockers separately.
There is no measured completion percentage; “60% remaining” is not an estimate
supported by this backlog. The entries differ in scope and uncertainty and are
not equally weighted tasks.

| Milestone | Implemented | Passing evidence | Blocked / unfinished | Next concrete action |
| --- | --- | --- | --- | --- |
| M1: Defensible scoring and benchmark comparisons | Continuous QB model and two dimension-adaptive reference versions; 48,776 training dropbacks, only 8,996 archived 2026 dropbacks add points for 57 QBs/122 games | All three benchmark populations, 38 negative estimates and nonduplicated season accounting retained; both versions independently rebuild exactly and preserve estimates | No admitted module or fresh predictive pass; real QB references still fail; source archive ends November 7 evening | Resolve numerical reliability without changing the posterior, then complete calibration/prospective/observational admission |
| M2: Attribution and uncertainty | Binary Genz–Malik refinement, exact correlation-aware reference transform, bounded complete diagnostics and independent analytical controls | Binary version passes the team control; primary QB errors improve to 0.011921 SD / 0.008648 CDF but fail 0.01 / 0.001 limits; known correct intervals pass and inaccurate ones are rejected | QB and three consumed stress cases fail binary reference; all five correlation-aware references fail; prior 192-fit calibration remains unfinished | Preregister bounded higher-order references on correlated/skewed/tail controls before these consumed cases; preserve gates and negative evidence; no fresh calibration claim yet |
| M3: Participation and qualification | Three-game/role thresholds, sensitivity grid, weekly joins and narrow exposure proof | 23/57 current QBs have proven full-QB denominators and pass all three participation grids | 32 lack positive participation in every team game; 2 lack single-team windows; these are evidence gaps, not verified ineligibility | Reconcile exact stint/missed-game evidence and review the partial module's denominator without changing model/benchmark populations |
| M4: Defense and cross-position comparability | Historical information-loss experiment, Defense Explorer, variance/null-space diagnosis for 895 defenders and November 11 participation metadata audit | Same 131 games/15,803 plays; residualized rank 856 versus 193; audited release has no 2026-named asset among 46 | No positional CAVAA, calibrated defensive uncertainty or proven live lineups; checked-feed absence is not all-provider absence | Resolve permitted live workload/position evidence and define a bounded defensive candidate; never rescale event counts into CAVAA |
| M5: Leaderboard, explanations and history | React/TypeScript Explorer, all-position availability, player details/provenance | Data/admission browser contracts; archived snapshot integrity | No admitted CAVAA leaderboard or ranked history | Consume the first passing module's versioned estimates, uncertainty and benchmark sensitivities; do not display research fits as real scores |
| M6: Deployment and independent refresh | PRs #18/#19 owner-merged; source gates, portable retention, main-only production workflow; scheduled trigger observed | Main CI and scheduled offline gates passed; no publication after failed prerequisite | Run 42908770888 stopped because no retained Explorer exists and first manual bootstrap is required; API still has no Pages site; configuration/dispatch access unavailable | Authenticated Pages setup and one explicit bootstrap, then remote retention/replay and site verification; preserve the safeguard and keep M1/M2 moving |

M1/M2 are the critical path. Optional infrastructure is paused. Deployment repair
is a bounded parallel responsibility within the same repository, not the default
substitute for model work. M4 is mandatory and cannot be removed by narrowing an
intermediate QB module. Report progress against these milestones before test or
commit counts. Each model run includes experiments, alternatives and a decision,
not merely a plan or one negative result. Update this table from observed results.
