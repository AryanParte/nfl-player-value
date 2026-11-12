# Higher-order reference — frozen November 12 plan

Freeze before implementation or new numerical outcomes. PRs #21–#24 are now
owner-merged; `main` at `ba353dc` passes hosted CI. November 11 binary refinement
passes only the real team control; whitening passes none of the five cases.
These failures remain evidence. The next M1/M2 experiment changes integration
order, not the football model or the standard required for a usable score.

## Fixed target and bounded alternative

Retain the continuous posterior, all first-unit/equal-player/opportunity contrasts,
the two QB prior sensitivities, original QMC seeds and stopping rules, and the
independent Student-t(5) coordinates based on axis-proposal moments. Do not use
the failed whitening alternative. Exact target/proposal correction preserves
full support. Preserve 90,000 conditional solves, 900 seconds per case and 3,600
seconds total, including proposal and QMC work. Same five consumed numerical
stress cases, no new football outcomes or synthetic calibration draws. Week 10
remains sealed; eligibility and all admission flags remain unchanged.

Implement an isotropic Smolyak sum of nested **open Fejer second rules**. Level
`l >= 1` has `2**l - 1` interior cosine nodes. Integrate the tensor difference
rules over indices `sum(l_j - 1) <= L`. Canonical integer dyadic angles make node
reuse exact, without approximate floating-point deduplication. Use the explicit
sine-series weights, independently test their polynomial moments, and use no new
library or copied external implementation. Open nodes avoid infinite transformed
endpoints. Negative sparse-grid weights are integration weights, never posterior
probabilities or negative opportunities.

Compute complete levels only. The largest allowed level is 9, reduced in advance
to fit the remaining conditional-solve budget. Four dimensions at level 8 require
65,537 distinct nodes; level 9 is unaffordable. All lower-level estimates can be
accumulated from these same points. Stream integrand batches and retain weight
tables plus accumulated integrals, not every large vector of player functionals.
Stop at a complete level only after level 4 and two consecutive small increments.

For each component, use the maximum of the last two absolute level differences
plus a roundoff floor based on absolute weighted sums. Require it to meet the
unchanged `atol=1e-6 + rtol=1e-4 * abs(integral)` rule. Then apply the existing
normalizing-mass error propagation and **0.01 posterior SD / 0.001 endpoint-CDF**
limits. This is an error estimate, not a rigorous bound: agreement between grids
can miss unresolved features. Known-answer controls and the separate QMC method
are therefore essential. Never declare convergence merely from budget exhaustion,
discard a negative contribution, or normalize a nonpositive/unverified mass.

## Verification, decisions and failure analysis

1. Independently verify one-dimensional moments, exact nesting, multidimensional
   polynomial integrals and point counts. Compare with direct tensor products on
   small cases; test negative integrals, finite-vector contracts and work limits.
2. Before NFL evaluation, exercise correlated and skewed/tail known targets in
   2–4 dimensions. Verify actual error against analytic answers, and correct
   interval endpoints against independent scalar convolution/root finding.
   Deliberately wrong endpoints and inadequate resolution must fail. Preserve
   failures and fix mathematical defects before running archived football cases.
3. Run all five cases, retain level/error/budget histories and every outcome.
   Independently rebuild with network access forbidden. Compare QMC histories,
   estimates, intervals and signed ledgers with November 11. Reference-only
   changes may alter numerical flags, never the underlying posterior estimates.
4. If the reference converges but rejects QMC functionals, a documented follow-up
   may use both original scrambles at fixed powers 12 and 13, within the same
   budgets and thresholds. No changed seed, model, favorable case selection or
   unlimited retry. Otherwise diagnose the exact remaining numerical failure.
5. A complete numerical pass permits a separately frozen fresh calibration stage;
   it does not admit CAVAA, validate attribution, release Week 10, or manufacture
   a full cross-position leaderboard. Defense and general exposure remain open.

## Primary references and reuse

[Waldvogel's quadrature paper](https://people.math.ethz.ch/~waldvoge/Papers/fejer.pdf)
describes the nested open rule and explicit weights. The
[Smolyak construction explanation](https://people.math.sc.edu/Burkardt/m_src/smolyak_display/smolyak_display.html)
documents combination and polynomial exactness. This implementation derives the
weights/construction directly; it does not import their software. Existing pinned
NumPy/SciPy remain sufficient. The new estimated-error policy is fixed here before
results and is assessed empirically, not presented as a mathematical guarantee.
