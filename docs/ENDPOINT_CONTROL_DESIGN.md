# Frozen endpoint-control preflight — November 25

Design parent b977164 (PR #37, still open at inspection). This branch is stacked on
`codex/allocation-discovery-preflight`; no merge is required for independent work.
Freeze this document and `config/endpoint-control-preflight-v1.json` before study
outcomes. Implement and verify the identities below before any study draw. Record
one clean numerical producer commit and kernel hash before execution.

## Hypothesis and bounded comparison

The consumed November 24 cases diagnose coarse upper-CDF residual variance, not
correction variance, as the curved-case precision blocker. Adding a small number
of analytically centered smooth CDF controls may approximate these functionals
better than degree-two polynomials. This is a numerical-integration hypothesis,
not a new football estimand, prior or uncertainty-inflation rule.

One candidate only: retain the protected proposal, bounded mode search, allocation
pilot, sample budgets, polynomial basis and coefficient ridge from November 24;
append four affine-probit controls per proposal component. Compare with the
unchanged November 24 adaptive-allocation polynomial method on every case.
Both arms share proposal fitting entropy and training points/responses. Each
fits its own controls and allocation with the same pilot coordinates; evaluation
random domains differ. Allocation may therefore differ; this is a comparison of
complete methods, not an isolated coefficient ablation. No winner selection per
trial, control, mode, geometry or diagnostic statistic is allowed.

## Analytic identity and fitting

For each proposal component use its Gaussian kernel g_j, including the Gaussian
with the same location/scale when the sampling component itself is Student-t.
Let z = L_j^{-1}(x-mu_j). With full proposal density q and fitted intercept b and
slope a, append

    h_j(x) = g_j(x)/q(x) * [Phi(b + a'z) - Phi(b/sqrt(1 + a'a))].

Its q-integral is zero: under g_j, z is standard normal, so adding an independent
standard normal gives E Phi(b+a'z) = Phi(b/sqrt(1+a'a)). The Student-t component
is not incorrectly assigned a Gaussian expectation; g_j is only the analytic
control kernel. Preserve all proposal masses and signed integrands. Do not clip
final estimates, integrals, negative player values or confidence intervals.

Use only the existing independent 2,048 fitting points and their coarse responses.
For each of columns 3–6, divide the endpoint response by positive mass response.
Zero mass rows have no information and receive zero fitting weight. Require finite
ratios in [0,1] up to floating-point tolerance; malformed responses fail explicitly.
Clip only this auxiliary probability to [1e-8,1-1e-8] before the inverse normal
transform. Fit an affine function of z with weights equal to the fitting mixture
weights times g_j/q, normalized over valid rows. Use an unpenalized intercept and
fixed slope ridge 1e-6 in the weighted-centered local coordinates. No known
quantile probability, true mixture parameter, mode label or validation answer is
an input to this fitter. Retain clipping counts and all direction coefficients.

Fit all polynomial and new zero-integral features to all response columns using
the existing weighted-centered, scaled SVD regression with relative ridge 1e-6.
Direction and coefficient fitting may share training observations: the complete
fitted control is independent of evaluation. No extra target evaluations are
required. Preserve and validate training/response/parameter hashes, dimensions,
random domains, component totals and signed fine-minus-coarse correction.

## Cases, randomness and costs

Keep consumed cases 0–9 as regressions, not fresh validation. Two new geometries
are fixed in the JSON before any results: case 10 is a unit-Jacobian sine transform
of a four-dimensional normal with curvature -0.8, changed contrasts and conditional
noise; case 11 is a displaced, correlated Gaussian mixture with new means,
Cholesky factor, mixture weights, contrasts and noise. Their linear latent
functionals have independent one-dimensional normal/Student-t quadrature answers.
The fitter sees only the callable density/function values and initial proposal.

Each arm has 32 trials on all 12 cases: 768 requested trials. Base seed 2026112501;
candidate stage 0, polynomial comparator stage 6; common fitting domain
[base,0,case,trial]. Existing fit/search/pilot subdomains remain unchanged;
coarse and correction evaluations use distinct arm/subdomains. Run two complete
offline builds and compare every object and manifest. Replay is reproducibility,
not independent coverage evidence (it uses the same randomizations).

Keep 64 replicates, total 1,024 coarse points per replicate, 32 paired correction
points, eight allocation pilots of 32 points per component, minimum 32 allocated
points, 90,000 target evaluations per trial, 180 seconds per trial and 3,600
seconds for the complete trial loop. No automatic retry, top-up or budget increase.
Retain all failures/unattempted cases in requested denominators. Report wall time
and memory/output limitations separately from counted target work.

## Decision before results

Keep mean precision 0.01 posterior SD and endpoint CDF precision 0.001, each
including numerical error; at least 90% precision successes in every candidate
case. All 32 confidence constructions per case must finish. Retain the same
one-sided 95%-coverage severe-undercoverage test with family alpha .01; denominator
increases from ten to twelve cases (joint .01/12, marginal .01/84), making the
screen stricter for the larger family. This is not certification of 95% coverage.
Wrong endpoint rejection, every marginal count and simultaneous coverage remain
visible. No test data or gate changes after outcomes.

Only an all-case pass allows a separately frozen full numerical-coverage study;
otherwise reject progression and analyze failures from saved raw replicates.
Report all paired point-error/RMSE changes, including adverse ones, and discovered
mode groups descriptively. Check endpoint residual variance, correction share,
auxiliary clipping and fitted-control stability without selecting favorable trials.
If failure is a reproducible implementation defect, repair it with a documented
invalidation decision; if statistical, preserve the result and freeze a genuinely
new study before further tuning. Do not silently rerun for better results.

Numerical coverage alone cannot admit a player module. The unchanged archived NFL
comparison, unfinished 192-fit player calibration and observational attribution
review remain required. Week 10 is sealed. No new NFL outcomes, rankings, admission,
qualification rule, first-unit/equal/opportunity benchmark or defensive scope changes.
