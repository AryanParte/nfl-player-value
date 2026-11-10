# Numerical-reference pilot — frozen November 10, 2026

Stacked on open PR #22 at `3823416`; PR #21 is its prerequisite. Both have passing
CI and no review comments at inspection. No new NFL outcomes or calibration fits
have been evaluated for this pilot. The November 9 model target, input archive,
benchmarks, noise/variance priors and scientific decisions remain fixed.

## Numerical hypothesis and independent reference

November 9's local elliptical proposals miss long nuisance-precision tails while
QB/defense directions remain narrow. Construct a product proposal from **axis
conditional density curves**, holding the other coordinates at a converged mode.
These curves are a numerical proposal, not posterior marginals or an independence
assumption about player effects. Exact joint target/proposal corrections retain
all posterior dependencies.

For each coordinate combine 97 knots across prior mean ±8 prior SD with 97 knots
across mode ±6 local Hessian SD and the mode itself. Normalize the nonnegative
piecewise-linear conditional density by its exact trapezoidal integral. Mix it
with 10% of the original Gaussian prior on that axis. This supplies nonzero
support beyond every table boundary: no posterior is truncated. Invert the exact
mixture CDF deterministically. Prior sensitivity changes the target only, not the
chosen proposal. Check inverse-CDF/density integration against analytic references.

Use two independently scrambled power-of-two Sobol sequences with the same
128 ESS, 0.01 mean-SD and 0.02 endpoint-SD independent/nested numerical criteria
as November 9. Powers 9–13 bound the work. Both QB prior-mean shifts retain their
own validity flags. This is a new numerical method for the same target, not an
alternative selected for favorable player estimates or interval coverage.

Independently integrate over the transformed unit cube with SciPy's deterministic
adaptive Genz–Malik cubature. Integrate target mass, centered/scaled conditional
means and the conditional CDF at the QMC interval endpoints. These are joint
posterior integrals, not fitted surrogate predictions. Require `converged`,
finite positive mass, estimated mass error smaller than mass, normalized mean
disagreement plus propagated integration error ≤0.01 posterior SD, and endpoint
CDF error plus propagated integration error ≤0.001 from 0.025/0.975. Check all
contrasts and declared prior sensitivities together. For the team control check
coefficient contrasts. Do not treat cubature's error estimator as a rigorous bound
or its agreement as evidence of empirical interval calibration.

The CDF requirement is a declared pilot diagnostic, **not** a replacement for
the existing independent/nested endpoint-SD gate. Both must pass. Small-model
normal/Student-t, correlated, skew-tail, scalar-quadrature and deliberate failure
fixtures must pass before interpreting the full-design pilot. No new package is
needed: the pinned SciPy 1.15.3 includes `integrate.cubature`.

## Fixed cases and compute budget

Evaluate these five cases in order: real evolving QB; real team control; first
draw (index 0) of each November 9 continuous-prior, continuous-hierarchy and
fixed-year generator. All three synthetic draws are **consumed numerical stress
cases**, not fresh validation or a new coverage experiment. No case is selected
because of its resulting coverage. Use the full original design and all current
contrasts; preserve first-unit/equal-player/opportunity-weighted real contrasts.

Measure target/contrast evaluation time before expensive runs. Cap each case at
90,000 target evaluations and 900 seconds, the complete pilot at 3,600 seconds.
Cubature additionally caps at 192 subdivisions, relative tolerance 1e-4 and
absolute tolerance 1e-6. Budget exhaustion is a recorded failure/unattempted case,
not a smaller passing study. Preserve partial diagnostics and do not silently
raise limits. Reuse repeated sufficient statistics or conditional node values
only with exact numerical-equivalence checks; checkpoints never select successful
cases. An independent offline replay/rebuild uses the same five cases and reports
any uncompleted verification honestly.

No full 192-fit calibration campaign is part of this pilot. If all five cases and
references pass within budget, save the numerically supported research estimates
and freeze the next fresh calibration plan before its results. If a case fails,
continue the remaining bounded cases, diagnose actual numerical error/cost and
document the next justified action without changing priors or gates. A passing
pilot still cannot admit CAVAA: fresh calibration, prospective prediction and
observational attribution review remain separate milestones. Week 10 stays sealed.

## Scientific and product safeguards

Retain signed cumulative 2026 accounting, every archived completed game and all
three benchmarks. Historical plays add no current points. Qualification never
filters modeling/benchmark populations. No ranking publication or position
admission; unsupported contributions stay unavailable. Keep the defensive
information-loss experiment and Explorer, and audit its source dependency without
opening reserved outcomes. No deployment infrastructure, automation changes,
purchases, new dependencies, direct main push or merges.

References: [SciPy 1.15.3 cubature](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.integrate.cubature.html)
documents the deterministic rule, vector integrals, explicit nonconvergence and
subdivision limits. [The November 9 result](CONTINUOUS_RESULTS.md) supplies the
consumed failure evidence and immutable parent artifact; it is not a passing
reference. The config in `config/variance-reference-v1.json` fixes these choices.
