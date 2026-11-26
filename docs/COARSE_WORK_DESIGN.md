# Frozen coarse-integration work comparison — November 26

Parent 9b96296 is PR #38, open at inspection with passing final CI and no review
comments. This unit is stacked on that branch until the owner merges it. Freeze
this document and `config/coarse-work-preflight-v1.json` before implementation
experiments. Record a clean numerical producer and verify tests before draws.

## Question and unchanged estimator

The November 25 arithmetic repair resolves the near-constant-control defect, but
stronger curvature meets precision in only 23/32 trials. All mean checks pass;
nine endpoint discrepancy-plus-allowance sums exceed .001. The paired correction
is at most about .022% of measured endpoint residual variance. This motivates a
bounded computation/accuracy comparison, not a new prior, model or interval.

Compare the same repaired endpoint integrator at 1,024, 2,048 and 4,096 coarse
points per replicate. Keep 64 independent scrambled replicates and 32 paired
fine-minus-coarse points per replicate. Keep mode search, protected proposals,
control directions, training observations, coefficient regularization, pilot
size, allocation objective and minimum allocation unchanged. Recompute the finite
allocation at each declared total budget from the same independent pilot. Thus
component counts can differ; component masses still weight their means.

The three arms share proposal/control fitting and allocation-pilot coordinates.
Their final evaluation random domains are separate. This compares the complete
fixed-budget procedures; it is not a claim of nested point sets or independent
fitting across arms. Each arm records actual work, including repeated fitting.
Do not reuse an inspected point estimate as truth or select a result per case,
player, endpoint, mode or trial. Signed integrals and negative values remain.

## Frozen scope and costs

Cases 0–13 are consumed regression geometries. Two new geometries are fixed in
the JSON: stronger negative sine curvature -1.35 with different contrasts/noise
(14), and a displaced correlated mixture with changed weights/contrasts/noise
(15). Truth is the established analytic latent marginal calculation, independent
of the numerical integrator. Fitting receives the density/function callable,
not true modes or answers. No NFL outcomes are read; Week 10 remains sealed.

Each arm requests 32 trials on all 16 cases: 1,536 arm-trials, or 512 matched
triplets. Base seed 2026112601; existing fitting domain [base,0,case,trial].
Evaluation domains are candidate=0, double=7 and quadruple=8; keep all existing
training/pilot/coarse/correction subdomains. These draws have not been inspected.

| Arm | Coarse points per replicate | Maximum counted target evaluations per trial |
| --- | ---: | ---: |
| candidate (current method) | 1,024 | 90,000 |
| double | 2,048 | 160,000 |
| quadruple | 4,096 | 300,000 |

Every trial retains the existing 180-second cap. The larger declared scope has a
7,200-second complete trial-loop cap, excluding preparation/semantic validation.
The work increases are the experiment's independent variable, declared before
outcomes; they are not automatic top-ups for failed trials. No retries or further
budget settings in this unit. Retain failed/unattempted trials in denominators.
Two complete offline builds must reproduce every object and manifest; repeating
the same seeds doubles neither scientific evidence nor coverage sample size.

## Decision and interpretation before results

Mean precision remains .01 posterior SD and endpoint CDF precision .001, including
numerical uncertainty. Every case requires at least 90% precision successes and
all 32 confidence constructions complete. Retain the same severe-undercoverage
screen with family alpha .01 across the three budgets and sixteen cases:
joint .01/48 and marginal .01/336. Smaller per-test alpha reduces false family
flags and individual test power; passing does not certify nominal 95% coverage.
Record every marginal count, joint coverage and wrong-endpoint diagnostic.

Declare an arm feasible only if every case passes. Choose the lowest-work globally
passing arm for a **future, separately frozen fresh confirmation**, or none if no
arm passes. Never combine each case's preferred arm. This is computational-budget
selection evidence, not that fresh confirmation, an NFL reference certificate or
a contribution-admission decision. Choosing among these tested settings requires
new numerical-coverage evidence before using the selected setting in the archived
comparison; the unfinished 192-fit player study and observational review remain.

Report every arm, including adverse errors, mode misses and nonmonotone precision.
Measure matched point RMSE, discrepancy/allowance decomposition, coarse/correction
variance and actual calls/timings. Do not assume the pilot's inverse-count law is
valid for scrambled QMC or that a fourfold budget halves error. Separate failures
to discover density modes from integration error conditional on the fitted geometry.
If no setting passes, stop this bounded comparison with the measured bottleneck
and next justified hypothesis; no third alternative or relaxed gate after results.

## Verification and scope limits

Before draws, test exact per-arm budget dispatch, unchanged fitting/pilot bytes,
separate evaluation domains, signed known answers, component accounting and call
counts. Corrupted budgets, fit records, allocation and claimed selection must fail
closed. Test that complementary per-case passes cannot create a global winner and
that failures/unattempted trials cannot disappear. Preserve legacy plan behavior.

No source ingestion refresh, first-unit/equal-player/opportunity-weighted benchmark
change, eligibility change or score publication is part of this numerical study.
All season games/negative contributions remain in the existing ledger. Defense,
participation, cross-position comparability and Explorer remain mandatory. Verify
their actual status without allowing an operational deployment blocker to displace
model work. No new service, paid feed, dependency or development-schedule change.
