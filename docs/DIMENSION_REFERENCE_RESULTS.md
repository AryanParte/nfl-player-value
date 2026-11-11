# Dimension-adaptive numerical recovery — November 11

**No contribution module is admitted.** Binary adaptive refinement improves the
existing independent reference and makes the team control pass. The real QB
reference still fails. A preregistered correlation-aware follow-up is tested rather
than assuming covariance alignment helps; its real-model references are worse.
Both complete five-case versions independently reproduce byte-for-byte offline.
Binary refinement passes **1/5**; the follow-up passes **0/5**. No case is omitted.
These are numerical findings, not fresh calibration or football validation.

## Implementation and decision sequence

1. `12f9591` freezes the [binary-refinement plan](VARIANCE_REFERENCE_ADAPTIVE.md).
   The pinned SciPy Genz–Malik rules are reused through a checked adapter, with
   our own largest-fourth-difference binary controller. Each split evaluates two
   children instead of 16 in four dimensions. Global estimated error includes all
   retained leaves, with a roundoff floor and complete subdivision accounting.
2. Producing source `06a81b9f48943f0925320669e06002eff9b33f81` passes analytical
   polynomial moments, anisotropic Gaussian integrals, known correlated mixtures,
   actual small random-effect references, wrong endpoints and bounded-failure tests.
   The complete five-case build and separate network-disabled build reproduce
   manifest/model/result bytes exactly. No case is omitted.
3. The real QB failure motivates a second, [frozen coordinate experiment](VARIANCE_REFERENCE_WHITENED.md)
   at `66c653a`. It uses primary-QMC mean/covariance only as proposal geometry,
   with full-support product-t coordinates and the exact transformation density.
   The posterior, priors, QMC estimates, benchmarks and gates remain unchanged.
4. Known-answer controls expose a singular-covariance check defect, fixed without
   covariance regularization, and an inaccurate QMC interval on a strongly
   correlated target. The latter remains rejected; independent scalar convolution
   roots verify correct endpoints. Producing source
   `842ad136b3bfb0840bb95c3ee3f5af43132d1d69` passes these checks before NFL evaluation.

Both versions retain 90,000 target solves per case, 900 seconds per case and
3,600 seconds for all five. The binary-subdivision ceiling changes to 2,048, with
a tighter cap calculated from the same available solve budget. More subdivisions
are not extra target solves. Numerical tolerances remain 0.01 posterior SD for
mean discrepancy plus estimated reference error and 0.001 for endpoint-CDF
discrepancy plus estimated error. The reference must also converge under the
original absolute/relative error policy. All real QB prior sensitivities must pass.

## Binary-refinement evidence

All original QMC checks still pass. The table reports the primary prior; all
three real QB priors remain unsuccessful. These are estimated errors, not rigorous
error bounds against the exact posterior.

| Case | Actual target solves | Mean discrepancy + estimated error (SD) | Endpoint-CDF discrepancy + estimated error | Result |
| --- | ---: | ---: | ---: | --- |
| Real QB | 89,941 | 0.011921 | 0.008648 | Failed, nonconverged |
| Real team control | 41,005 | 0.001223 | 0.000406 | Passed |
| Consumed continuous-prior draw 0 | 89,988 | 0.007537 | 0.012674 | Failed, nonconverged |
| Consumed hierarchy draw 0 | 89,972 | 0.005441 | 0.007659 | Failed, nonconverged |
| Consumed fixed-year draw 0 | 89,942 | 0.016644 | 0.018021 | Failed, nonconverged |

The QB's prior sensitivities have mean/error diagnostics 0.010823/0.013182 SD
and CDF/error diagnostics 0.008526/0.008842. The original November 10 cached QB
values were 0.024490 SD and 0.032561 CDF: this is measured improvement, still
insufficient. The team control reaches convergence after 572 binary subdivisions.
The four-dimensional cases retain 738–739 complete subdivisions within budget.
This controller calls each rule node once; its inherited bounded cache has zero
hits in these runs. The benefit is refinement strategy, not new cache savings.

## Follow-up evidence

The correlation-aware reference is not an improvement on the real data. The QB
uses 89,941 solves, remains nonconverged, and has primary diagnostics 0.030987 SD /
0.044315 CDF. The team uses 89,977 solves and remains nonconverged at 0.001635 SD /
0.001248 CDF. Its pass in the first version cannot be carried over to this version.
The reference geometry shares QMC information; numerical-method independence does
not mean independent data, all code or coordinate construction.

The recorded geometry challenges the correlation-only explanation: the largest
absolute correlation is about 0.401 for the real QB, only 0.088 for the team and
0.041 for the consumed prior draw. All are positive definite. The real QB's
estimated normalizing-mass relative error worsens from 0.001986 in the binary
version to 0.010950 in the whitened version. Small raw mean/CDF disagreements
cannot remove that error. This suggests moment matching alone is insufficient;
it does not identify the exact integration error or invalidate the football prior.
The next reference study needs skew/tail controls as well as correlated Gaussians.

| Follow-up case | Actual target solves | Mean discrepancy + estimated error (SD) | Endpoint-CDF discrepancy + estimated error | Result |
| --- | ---: | ---: | ---: | --- |
| Real QB | 89,941 | 0.030987 | 0.044315 | Failed, nonconverged |
| Real team control | 89,977 | 0.001635 | 0.001248 | Failed, nonconverged |
| Consumed continuous-prior draw 0 | 89,988 | 0.018188 | 0.032509 | Failed, nonconverged |
| Consumed hierarchy draw 0 | 89,972 | 0.019481 | 0.032983 | Failed, nonconverged |
| Consumed fixed-year draw 0 | 89,942 | 0.035822 | 0.053446 | Failed, nonconverged |

Both QB prior sensitivities fail too: 0.029459/0.032717 SD and
0.043554/0.045278 CDF. No time cap is hit. Ordinary-build case time totals are
1,332.5 seconds (22.2 minutes) for binary refinement and 1,456.1 seconds (24.3
minutes) for the follow-up, excluding source reconstruction. Independent-build
totals are 1,326.9 and 1,455.0 seconds. Two owned builds ran concurrently with
single-threaded numerical libraries; these are measurements, not controlled
hardware performance comparisons. No new dependency or recurring service cost.

All QMC histories match November 10 exactly. Both versions preserve its estimates,
intervals, coefficients and signed ledgers. The follow-up's model/result bytes
also equal November 10's cached version because all numerical flags remain false.
The binary version changes only numerical flags for the team control. Every
manifest/model/result object is hash-verified and byte-identical to its independent
network-disabled rebuild in separate storage, including all failure decisions.

**Decision:** keep binary refinement as tested research code, retain the failed
coordinate alternative for reproduction, and admit no module. The optional
higher-QMC-resolution follow-up is not triggered: every new reference is itself
nonconverged, so this is not a converged-reference/QMC-disagreement diagnosis.
No new calibration or prospective evaluation is started. Next, preregister a
bounded higher-order quadrature comparison with correlated/skewed/tail controls
before these same consumed cases. Preserve the posterior, all functional accuracy
limits and every failed result. Do not assume another coordinate rotation fixes
the reference. Fresh calibration, prediction and observational admission remain
subsequent requirements; this numerical unit does not complete the scoring milestone.

## Scientific and product limits

The same 48,776 historical/current dropbacks inform estimation; only the archived
57 QBs / 122 completed 2026 games / 8,996 dropbacks contribute season points.
Coverage stops November 7 at 20:41:17 Eastern, not November 11 live coverage.
Every archived completed game and all 38 negative player estimates remain.
First-unit, equal-player and opportunity-weighted populations are unchanged,
including joint player/benchmark uncertainty. Qualification never selects fitting
or benchmark membership. Twenty-three narrow participation denominators remain
proven; 34 remain unresolved, not automatically ineligible.

The binary version preserves every point estimate, interval, coefficient and
ledger from November 10 exactly when numerical-status flags are excluded. Its
passing team control changes a status flag, not player attribution. Maximum
per-play reconstruction error remains 8.88e-16 EP. A season effect allocated over
opportunities is not a separately measured game-specific performance score.

All three synthetic cases are consumed numerical stress tests. No fresh coverage
evidence is produced; the earlier 192-fit calibration is unfinished. Week 10
remains sealed. QB/team attribution is assumption-dependent, and team-season
controls do not directly measure individual protection, receivers or scheme.
No model uncertainty interval establishes causal value or cross-position admission.

Defense remains required. The existing 131-game / 15,803-play / 895-defender
information-loss evidence and Explorer are preserved. The November 11 metadata
audit finds no 2026-named asset among 46 assets in the checked participation
release; it is not an all-provider absence claim or an audit of game-level snap
counts. Live lineup/role coverage and calibrated defensive contributions remain open.

## Reproduction and review

Binary report: `5f159279f0148d75f319c636886d578067bf6eb5c31f2bc14fad477d0af271a6`.
Models: `d5179596e957d1a7b2bc1d7c17cdee953f46b4cf2297bfdabe426c9096e89a21`.
Results: `0c8c27b6d1001db0d881635d05989fe551730daadf76ba416be84492824d4a13`.
Whitened report: `4337d5270ca066e47679b4fef014454c40434f08a4cea8f7be624e749e810433`.
Models: `969823d70ceabc6cb5c7dec3e7065a1e23ff547c6275e9322fad71f04d320c51`.
Results: `b55976166828f825cd9343e30dc3a2a08e306e3b4136f755dc40ff80addd64c9`.
The [audit](audits/2026-11-11-dimension-reference.json) binds inputs, plans, versions,
case evidence, execution timing and independent-rebuild verification.

```sh
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv/bin/python -m nfl_value.reference_cli \
  --output-store data/derived/variance-reference-adaptive \
  build --plan config/variance-reference-adaptive-v1.json
```

Use `variance-reference-whitened` for both store and plan prefix for the second
version. `replay REPORT_ID` verifies stored hashes/environment and independently
recomputes all five cases. The code revision and environment matter. Exact local
rebuild is not cross-platform scientific validation or durable remote retention.

Local `make check` passes 411 Python tests and 27 frontend contracts, with Ruff,
adopted formatting, TypeScript/build, syntax and whitespace checks. Hosted
[CI 43090344898](https://github.com/AryanParte/nfl-player-value/actions/runs/43090344898)
passes on the first producing source, and
[CI 43110458678](https://github.com/AryanParte/nfl-player-value/actions/runs/43110458678)
passes on the second, including Python 3.11/3.12/3.13 and Chromium. Tests passing
is separate from statistical validation. No package, fee, automation or hosting
setting changes. PR #24 is stacked on #23; the owner must review/merge the stack.

The scheduled Explorer refresh did run and failed at the expected first-bootstrap
safeguard; capture and publish were skipped. The [runbook](PRODUCTION_REFRESH.md)
records the exact failure/access blocker. A deployed Explorer still would not
be an admitted MVP leaderboard.
