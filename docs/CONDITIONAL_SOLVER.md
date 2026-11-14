# Frozen conditional-factorization study — November 14

This design precedes all new numerical results. It is stacked on PR #27 at
`abab5fd`, which remains open with passing CI and no reviews at inspection.
The producing commits, failed controls, timings, complete requested denominators
and immutable artifacts will be recorded. No football outcome is downloaded;
Week 10 remains sealed. This is numerical repair, not fresh player calibration.

## Target and alternatives

The existing conditional kernel forms `X' R^-1 X + D`. The November 13 trace
loses a positive precision of 9.66e-24 at the scale of the normal matrix. Freeze
two alternatives, leaving all priors, observations and contrasts unchanged:

1. `augmented_qr`: factor the augmented least-squares problem with square-root
   penalties instead of adding penalties to a cross-product matrix. Construct
   game weighting from within-game residual rows and weighted game means, not
   subtraction of nearly equal Gram matrices. Compress the response and design
   together once by QR; retain the residual row and all prior rows. Compute the
   residual quadratic as a sum of squares. Do not use rank truncation or jitter.
2. `exact_alias_qr` (preferred before testing): before the same factorization,
   remove **certified exact** within-precision-block aliases with the retained
   intercept/season context. Use rational row reduction on binary design patterns,
   not a numerical singular-value cutoff. Nonbinary blocks receive no such
   reduction. The independent proper-prior directions are integrated analytically
   and their full covariance is restored to requested contrasts and fixed effects.
   Near aliases must remain modeled. Different precision blocks are never pooled.

If `X_g N = F A`, `N'N = I`, and `C` is its orthogonal complement, write
`b_g = C theta + N t` and `alpha_new = alpha + A t`. An isotropic group prior
makes `theta` and `t` independent with the same precision. The flat fixed prior
is invariant to the shift. Integrating `t` leaves a normalized prior integral of
one; a contrast gains variance `||l_g N - l_fixed A||^2 / lambda_g`. Its mean is
zero, not an estimated absence of uncertainty. This algebra does not justify
dropping an approximately dependent direction or imposing zero-sum player scores.

The scientific basis is the equivalence of penalized least squares and mixed
models ([Bates](https://lme4.github.io/lme4/articles/PLSvGLS.pdf)); QR solves the
full-rank least-squares system without forming normal equations
([LAPACK](https://netlib.org/lapack/lug/node27.html)). These sources motivate the
computation; independent tests below must establish this implementation's accuracy.

## Known-answer gate

`config/conditional-solver-v1.json` freezes seeds, dimensions of the experiment,
precision grid and tolerances. Six small deterministic families cover partition
indicators, exact duplicates, a nonzero 1e-8 near-alias perturbation, a cold player,
linked player/year indicators, and game-constant fixed effects. Use 24 observations
and two signed responses generated once from the declared seed; include individual,
signed player-minus-peer, zero and doubled contrasts. Retain every combination of
the four random-effect precisions and three game precisions: **72 cases per
candidate**. Other random blocks, if present, have precision 7.0, never a fitted
oracle setting. This bounded suite is not every possible precision configuration.

An independent standard-library Decimal LDL solve of the **original augmented
coefficient model including game intercepts** supplies means, contrast variances,
residual quadratic, noise posterior and integrated log likelihood. Construct its
cross-products directly from exact float inputs at 80 and 110 decimal digits;
do not convert the rounded production Gram matrix. Require the two references
to agree far more tightly than candidate tolerances (1e-20 relative / absolute
on their Decimal outputs). No dependency is added. Known zero variances must be
zero; near-zero means are tested in posterior-SD units, not relative mean error.

Each candidate must pass every case: maximum mean discrepancy <=1e-6 conditional
posterior SD; variance relative error <=1e-6; quadratic relative error <=1e-9;
log likelihood absolute error <=1e-6. These arithmetic limits are much stricter
than the existing integrated 0.01-SD / 0.001-CDF accuracy requirements, which stay
unchanged. Exact accounting and restoration of prior-only directions are required.
A candidate failure blocks its archived equivalence claim. The preferred candidate
is not selected using a favorable NFL outcome. All baseline failures remain visible.

## Bounded archived equivalence and failure analysis

Only a candidate that passes all known cases proceeds. For each of the five
already-consumed cases from PR #27, evaluate the prior center and 16 fresh normal
coordinate draws with SD 3 and the fixed archive seed (case index via SeedSequence).
Compare conditional means, variances and likelihoods with the old kernel where
it returns finite results. A disagreement is a diagnostic failure, never proof
that the old method is ground truth. Use the same normalized mean/variance limits
and a 1e-5 absolute likelihood limit for the larger archived systems. Record errors,
condition diagnostics and elapsed time without discarding any coordinate.

Additionally evaluate the exact recorded failing point for the prior-stress case.
Require finite outputs, unchanged response hash and a complete coefficient/game
accounting identity. Check the repaired point with a second computation on the
original observation rows, bypassing QR compression, and with alternate exact
alias bases/permutations. This tests implementation equivalence, not a fully
independent arbitrary-precision NFL answer. Retain that limitation.

If these checks pass, replay **only the originally failed density fit**, with the
same coordinates/seed/work policy, replacing the conditional kernel. Its new
geometry and result are a separate version; the original failure is never replaced.
The global 5,400-second and 900-second per-case caps include recorded preparation
and solve work; the replay also retains the original 90,000-evaluation limit.
Report exhausted budgets and unattempted work explicitly. No automatic budget
increase, favorable restart, full calibration, posterior promotion or score
publication follows. One bounded implementation defect may be fixed with its
cause and rerun disclosed; a changed numerical alternative needs a new frozen
rationale before its new results. Further primary/reference integration requires
a separately declared study, not an opportunistic rerun of the old pilot.

## Product contract

Preserve cumulative archived 2026 expected points, all completed archived games,
negative contributions, first-unit and both sensitivities, and eligibility apart
from model/benchmark membership. The defense information-loss study and Explorer
remain required. No unsupported module becomes available from a numerical pass.
No existing model artifact or default scoring kernel is overwritten by this study.
