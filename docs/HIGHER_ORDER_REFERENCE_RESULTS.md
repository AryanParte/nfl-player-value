# November 12 higher-order reference decision

No contribution module is admitted. The higher-order sparse reference fails both
real models. Two additional tensor alternatives fail their known-answer selection
controls and are blocked from the archived-data runner. This is a completed
implementation and a negative numerical finding, not a usable MVP leaderboard or
new calibration evidence. All five sparse cases finish and fail; the full report,
models and results independently rebuild byte-for-byte with networking blocked.

## What was held fixed

The [sparse plan](HIGHER_ORDER_REFERENCE.md) was committed at `f16c5b1` before
implementation or results. Producing source: `418abd062b71e4a47f630e6d870bbcbf082d4c41`.
The [tensor follow-up](HIGHER_ORDER_TENSOR.md) was frozen at `350bd69`, while the
first archived case was still in QMC and before any sparse archived-case result.
It responds to known-answer control failures, not new football outcomes.
Its producing source is `a251069984bd45a30ba57449d386d3cbc780555c`.

All versions retain the continuous posterior, first-unit and both sensitivity
benchmarks, QMC seeds/stopping rules, 90,000 solves/900 seconds per case and 3,600
seconds per five-case pilot. The limits remain 0.01 posterior SD for means and
0.001 probability for interval-endpoint CDFs, including propagated reference error.
No prior, interval, qualification or admission rule is changed. Week 10 is sealed.
These three synthetic responses were already consumed and cannot be fresh
coverage evidence. The original 192-fit calibration remains unfinished.

## Sparse-reference results

Nested Fejer rules reuse exact integer-angle nodes and stream the large vectors
of player functionals. Smolyak levels use signed integration weights; these are
neither negative opportunities nor posterior probabilities. The rule requires two
small complete-level changes and retains the last complete estimate at its cap.

The primary QB result is 0.015804 SD for mean discrepancy plus estimated error
and 0.005090 for endpoint-CDF discrepancy plus error. Both exceed the unchanged
limits. The team control also fails (0.002041 SD / 0.001853 CDF); its November 11
binary-rule pass does not transfer to a new numerical version. These complete
real-case results finish within their budgets, rather than stopping on a timer.

| Case | Target solves | Mean discrepancy + error (SD) | Endpoint-CDF discrepancy + error | Decision |
| --- | ---: | ---: | ---: | --- |
| `real_evolving` | 71,175 | 0.015804 | 0.005090 | Failed, reference nonconverged |
| `real_team` | 50,323 | 0.002041 | 0.001853 | Failed, reference nonconverged |
| `continuous_prior_0` | 71,222 | 0.187115 | 0.219789 | Failed, reference nonconverged |
| `continuous_hierarchy_0` | 71,320 | 0.840644 | 1.410564 | Failed, reference nonconverged |
| `fixed_year_changes_0` | 71,176 | 9.670000 | 16.846122 | Failed, reference nonconverged |

All five original QMC checks still pass; their histories are identical to November
11. Both real-QB prior sensitivities fail the independent reference too: minus
log(4) gives 0.012345 SD / 0.005002 CDF and plus log(4) gives 0.020833 / 0.010317.
No extra-QMC follow-up is triggered because the reference itself has not converged.
No case is omitted or stopped by its time cap.

The fixed-year stress case is especially poorly resolved: its estimated mass
error is 80.3% of the estimated mass. Normalization amplifies that uncertainty.
The 16.846 value above is a discrepancy-plus-error diagnostic, not a probability.
It is not clipped to make an unusable reference look acceptable. Even its raw
CDF disagreement is 0.008022, but a nonconverged reference cannot establish that
the QMC estimate is wrong. Prior/hierarchy stress failures are also materially
worse than the real-model cases. This rule is not promoted.

The complete [machine-readable audit](audits/2026-11-12-higher-order-reference.json)
retains all priors, levels, errors, resource limits, source receipts and decisions.
The ordinary five-case compute totals 2,397.47 seconds; the independent offline
build totals 2,389.65 seconds (input replay is outside these case timings). Both
remain below the declared caps. Timing is execution metadata, not part of the
numerical report hash.

Report ID:
`5e443e3f10ece581299557bf55441f47a43eb6cdfea9d2bb2ace4bc427b346d3`.
Models: `969823d70ceabc6cb5c7dec3e7065a1e23ff547c6275e9322fad71f04d320c51`.
Results: `b55976166828f825cd9343e30dc3a2a08e306e3b4136f755dc40ff80addd64c9`.
The two snapshot stores (`data/derived/variance-reference-sparse` and
`data/derived/variance-reference-sparse-offline`) have byte-identical manifests
and objects, checked through their hashes. Model/result bytes are also identical
to the November 11 whitened version, including numerical flags. All benchmark,
qualification, signed estimate, interval and ledger values remain unchanged;
maximum per-play accounting error remains 8.88e-16 EP. The original binary version's
team-only pass remains a separate version-specific result.

Reproduce using the committed producing source and the retained parent stores:

```sh
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m nfl_value.reference_cli --output-store data/derived/variance-reference-sparse build --plan config/variance-reference-sparse-v1.json
PYTHONPATH=src VECLIB_MAXIMUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m nfl_value.reference_cli --output-store data/derived/variance-reference-sparse replay 5e443e3f10ece581299557bf55441f47a43eb6cdfea9d2bb2ace4bc427b346d3
```

The independent rebuild used a separate empty store with socket creation,
connections and DNS forbidden. Archived raw/derived bytes are required; their
hashes alone do not provide durable remote storage. The reference CLI records
model/config/environment provenance and verifies archived bytes before fitting.

## Known-answer controls and rejected alternatives

One-dimensional polynomial moments and multidimensional tensor identities verify
the sparse construction independently. Its fixed 2D/3D/4D correlated, skewed moment
controls retain nonconvergence; actual errors remain below the error estimates.
The scalar-convolution interval control converges and passes: mean difference
plus error 0.00005822 SD and endpoint-CDF difference plus error 0.00005373. Moving
the upper endpoint by 0.5 makes it fail. Budget truncation also fails explicitly.

The tensor comparison streams public SciPy rules at fixed orders 7, 11 and 15:

| Alternative | Basic correlated/skewed moments | Four-dimensional tail stress | Correct interval reference | Decision |
| --- | --- | --- | --- | --- |
| Gauss–Legendre / Student-t coordinates | None converge; error estimates understate some actual errors | Nonconverged; maximum actual moment error 0.58388 | Nonconverged, fails | Reject; no NFL run |
| Gauss–Hermite / normal coordinates | All three dimensions converge; maximum actual error below 6.46e-11 | Nonconverged; maximum actual error 0.18952 is covered by the estimate | Nonconverged; 0.010832 SD / 0.002575 CDF including error | Reject; no NFL run |

None of those failed controls falsely declares convergence. Gauss–Hermite's
accurate basic moments do not establish reliable interval endpoints. The frozen
selection returns `null`; `reference_cli` rejects both tensor configurations.
They remain available only for reproducing the analytical comparison. Its
canonical JSON hash is
`9cf5d9bbaace9e46438db794f8df64a3e27bcdef4f3d6a178ce0e11ec9969588`;
an independent rerun with sockets and DNS forbidden matches exactly.

## Failure analysis and next scoring action

Increasing quadrature order alone is not a sufficient remedy under this budget.
The bounded controls separate basic-moment accuracy from interval/tail accuracy.
An error indicator is not a theorem: successive-rule agreement can understate
error, as the Legendre controls demonstrate. The sparse indicator is conservative
on the inspected controls, but this is not a guarantee for untested integrands.
Neither result proves the football posterior or its attribution assumptions wrong.

Do not repeat whitening or promote a tensor rule because a subset looks good.
Next, preregister a replicated randomized-integration reference with explicit
numerical-error coverage controls, independent scrambles and a separate full-support
proposal. Preserve the posterior and functional accuracy limits; distinguish
reference-method dependence and multiple-function comparisons. Validate numerical
error estimates on known correlated/skewed/tail answers before these consumed
cases. This is a recommendation, not an implemented or passing reference.
[Primary RQMC research](https://www.gerad.ca/en/papers/G-2023-67) motivates independent
replication but also warns that valid intervals are challenging; treating points
within one scramble as independent would be wrong. No automatic pass or rigorous
finite-sample guarantee is implied.

Only after reliable numerical integration should the project resume fresh
calibration, prospective prediction and the observational admission review. These
gates remain separate. QB/team allocation uncertainty is not solved by an exact
integral. Defense and cross-position coverage remain required.

## Verification and scope

Local `make check` passes 423 Python tests, 27 frontend contracts, Ruff/adopted
formatting, TypeScript/production build, compile and whitespace. Hosted CI passes
on the sparse producing source and tensor-control source; final-head status is
reported in the PR checks. The existing Python matrix and dashboard
browser checks remain intact. No new dependency or service is introduced.

Self-review fixed an exact-zero/relative-only tolerance case that could produce
NaN and false nonconvergence. Its regression passes for both integrators; the
pilot's positive absolute tolerance is unchanged. Initial test-authoring defects
were also corrected: the independent normal-density check now declares its two
dimensions, and high odd Gaussian moments are checked relative to their large
cancelling terms. These fixes do not loosen NFL acceptance gates.

The archive still ends November 7 evening, not November 12 live coverage. The
same 57 QBs/122 games/8,996 dropbacks and 48,776 training dropbacks define the
research scope. Thirty-eight negative estimates and all three benchmarks remain;
historical opportunities add no 2026 points. The existing ledger is a season
effect allocated over observed opportunities, not a new game-specific skill score.
General exposure, defensive uncertainty and public CAVAA publication remain open.
