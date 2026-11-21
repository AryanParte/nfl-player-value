# Mode-discovery preflight — frozen November 20, 2026

This unit is stacked on PR #33 (`c149649`), which remains open. No merge is
required. The November 19 candidate failed displaced precision and remote
coverage. This is one new numerical proposal hypothesis, not a changed football
model, benchmark, likelihood, prior, uncertainty interval or admission criterion.

## Question and information boundary

Can bounded, independent multi-start density search find separated probability
regions, and can local Gaussian components then meet the existing functional
precision limits? A small preflight screens feasibility before another expensive
full certification. Its results cannot authorize NFL access or admit scores.

The candidate receives only a callable log density and the original proposal.
It must not inspect analytic component means, covariances, mixing probabilities,
truth, case labels or evaluation points while fitting. It fits the same positive
coarse target used in previous controls, pi(x) * (1 + .001 sin(sum(x))). Full
importance densities and the paired fine correction preserve the original target.

## One frozen candidate

1. Generate 256 scrambled Sobol normal search points around the original defensive
   mean, with covariance four times its covariance. This is a search distribution,
   not a changed prior. Record the entropy, points and all density calls.
2. Use the original central mean plus 23 cloud points: first 12 ordered by
   log-target minus original full-mixture log-density, then 11 by log-target.
   Greedily prefer points at least .5 apart in the defensive covariance metric,
   then fill any shortfall in the same ordering without spacing. Exclude already
   selected indices. No truth-based starts or favorable restart selection.
3. At all 24 starts, minimize negative log density with L-BFGS-B, unbounded
   coordinates, `ftol=1e-12`, `gtol=1e-6`, `maxiter=100`, finite-difference gradient.
   A hard wrapper allows at most 384 density calls per start, including numerical
   derivatives. Retain every optimizer status. A start is usable only if the
   optimizer reports success and its returned gradient infinity norm is <=1e-4.
4. Deduplicate converged modes within .1 in the defensive covariance metric,
   retaining the first discovered representative. Reject the trial if there are
   no usable modes or more than three. This is a scoped family, not permission to
   discard a fourth mode. Compute central-difference Hessians at each mode with
   step .001 in each coordinate. Require positive curvature; bound covariance
   eigenvalues to [1e-6,36] and multiply by the already used proposal factor 1.5.
   These operations affect sampling only. Record raw curvature and clipping.
5. Initial masses use log-density plus half log determinant of the *uninflated*
   local covariance (the common Gaussian constant cancels). Floor normalized
   mode masses at .01 and renormalize. Pad to three central strata by duplicating
   the highest-mass mode and splitting its mass equally among its copies.
   Retain the original .1 defensive component; central total remains .9.
6. One separate 4,096-point pilot updates component masses only, using exact
   mixture quadrature weights and central-mixture responsibilities times target/
   full-proposal density. Floor central masses at .01 and normalize. Do not move
   mode means or covariances. Keep the pilot mass and concentration diagnostics.
7. Use the existing independent 2,048-point zero-mean Hermite fit (ridge 1e-6),
   64 coarse replicates of 1,024 nodes, and 64 paired fine/coarse corrections of
   32 nodes. The paired plain estimator remains diagnostic, never a fallback.

The upper bound in four dimensions is 256 + 24*384 + 3*33 (Hessians) + 3 (mode
height) + 4096 + 2048 + 65536 + 4096 = 85,350 target evaluations. Initial-center
search scoring is one extra call, so the enforced maximum is **85,351**, below the
unchanged 90,000 cap. Count every log-density, gradient/Hessian, pilot, control-fit,
coarse and paired correction call, including failed searches; no free cached
optimization. Initial archived proposal preparation is not performed in this
preflight and remains a separate cost before any future archived execution.

## Frozen experiment, checks and stopping rule

Base seed 2026112001. Each trial gets `[base, stage, case, trial]`. Search uses
suffix 10; the mass pilot 11; independent control fit 2; coarse evaluation 0;
paired correction 1. The existing Sobol generator appends stratum/replicate keys.
No domain is reused across fitting and evaluation. Stage 0 is the candidate;
stage 1 is the diagnostic below. Replicate-level uncertainty uses existing
Student-t / Fieller code and unchanged .01-SD / .001-CDF precision tolerances.

Run 32 independently fitted trials for all original cases 0–7, retaining their
original definitions and initial geometries. Add two prespecified geometry
extensions, with the same original tail proposal and contrast/noise definitions:

- Case 8: .93 N(0,I) + .07 N((-7,0,7,0), diag(.36,1,.36,1)).
- Case 9: .92 N((.5,-.4,.2,0), .8 I) + .08 N((5,-6,4,-3), C), where
  C_ij = s_i s_j * .3^abs(i-j), s=(.4,.7,1,1.2).

These are retained/adversarial known-answer controls with fresh random draws;
not fresh football validation or proof of general posterior calibration. Truth
means/variances are analytic; endpoint truth uses the existing independent scalar
convolution/root solution. Test that solution with the reverse convolution order.

A case clears this **feasibility screen** only if all 32 trials finish within work
limits and >=90% meet unchanged discrepancy-plus-error precision. Also retain
wrong-endpoint checks and marginal/joint binomial undercoverage diagnostics;
a severe undercoverage flag at .01/70 marginal or .01/10 joint blocks progression.
The screen does not estimate a population pass probability with adequate power
and does not replace the full certificate's one-sided coverage lower bound. This
smaller screen is justified solely to stop an infeasible candidate early, never
to authorize NFL work. A passing screen requires a separately frozen full study
before certification. A failed screen stops certification and triggers the
prespecified diagnostic, not seed/parameter tuning or interval widening.

Always complete all cases and both arms unless the 3,600-second overall runtime
or 180-second per-trial cap is reached. Timings are operational metadata, excluded
from deterministic artifact identities. Retain failed/unattempted trials in the
requested denominator. No retry with favorable entropy. Run a second complete
offline reconstruction and compare every artifact byte, not only aggregates.

## Prespecified diagnostic — never deployable

For cases 6–9, run 32 independent trials using the known two Gaussian components
and their true masses, padded to three central strata with the same .1 original
defensive component. No inflation or mode search. The same independent control
fit and evaluation budgets/precision rules apply. This oracle proposal is only a
mechanism diagnostic: it uses information unavailable to real football inference.
It cannot be selected as the candidate or authorize any NFL input. Record its
separate work, plain results, complete trials and numerical-error coverage.

Compare candidate discovery counts, mode locations, target mass, actual point
errors, confidence construction failures, endpoint-only precision and held-out
controlled/plain variances. Distinguish fitting/discovery problems from residual
functional integration error. Oracle success cannot establish a practical way to
find its parameters. Oracle failure cannot show every possible reference fails.

## Implementation and decision contract

Reuse the model dependencies, unittest suite, existing mixture/QMC/confidence
code and immutable SnapshotStore; introduce no services or dependencies. Bind the
plan, numerical source, environment, parent initial geometries, truth and all
attempts. Reject tampered/incomplete artifacts and never set ranking_ready true.
A preflight report must be structurally unable to satisfy the production/archived
numerical certificate loader. Software verification, numerical checks and player
validation remain distinct. No NFL outcomes or sealed Week 10 data are read.

The next product milestone remains a defensibly validated cumulative 2026 CAVAA
module with first-unit/equal-player/opportunity-weighted contrasts. The unfinished
192-fit calibration, participation, defensive work and cross-position comparability
are not removed by this experiment. Deployment access does not block it.

## Post-result analytical diagnosis — declared November 20

After the complete candidate summaries, case 3 has 0% precision while the search
can only recover density modes. Before calculating a further diagnostic, ask
whether its .95 N(0,1)+.05 N(4,4) first-coordinate marginal even has a second mode.
The remaining coordinates factor as standard normals. This is explicitly a
post-result mechanism analysis, not fresh validation or a candidate amendment.

For 0<x<4, the density derivative is positive iff
`g(x)=log(.05/.95/8)+log((4-x)/x)+x²/2-(x-4)²/8 > 0`.
Its derivative vanishes at roots of `3x³-8x²-16x+16=0`. Compute the real roots in
(0,4), evaluate g there and bracket all crossings between these stationary points;
outside [0,4] the marginal derivative has a fixed sign. Validate the algebra against
an independently evaluated Gaussian-mixture derivative, including a stronger
second component as a distinct control. Report finite-precision arithmetic limits.
No new integration trial, oracle fallback, proposal parameter or gate is selected.
