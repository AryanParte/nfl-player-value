# Tail-mixture feasibility study — frozen November 22, 2026

PRs #33 and #34 were owner-merged; base main is 579e150. No scoring module is
admitted. The previous mode-only candidate failed both broad nonmodal probability
and remote-mode discovery. This is one bounded numerical sampling hypothesis,
not a change to football priors, likelihood, benchmark, ledger or intervals.

## Rationale and information boundary

A Gaussian mixture can represent important mass without assigning each component
to a density mode. Importance-weighted mixture EM adapts component means,
covariances and probabilities to approximate a target. This is informed by
[Cappé et al., Adaptive Importance Sampling in General Mixture Classes, section 3](https://arxiv.org/html/0710.4242).
The paper supplies an algorithmic rationale, not a guarantee for this finite,
regularized, stratified-QMC implementation or CAVAA attribution.

Retain the exact prior mode search and mass pilot. Add a broad central component
where a duplicated stratum leaves room, then adapt the whole central mixture
using target-weighted responsibilities. The fitter receives only the same coarse
log-density callable and initial proposal. No fixture index, true components,
exact functional answer or evaluation point may enter adaptation. Synthetic truth
is used only for evaluation and labeled diagnostics.

## One frozen candidate

1. Run the unchanged 256-point/24-start bounded mode search, Hessians and
   independent 4,096-point mass pilot from MODE_PREFLIGHT_DESIGN.md.
2. Aggregate duplicated central strata by their discovered mode. If fewer than
   three unique modes exist, reserve central mass .2 for a Gaussian at the
   original defensive mean/covariance; allocate .8 proportionally to the fitted
   unique modes. Pad to three by splitting the largest mass as before. If three
   unique modes exist, retain all three without dropping a mode or adding a slot.
   Record whether a broad slot was available. The separate original .1 defensive
   component is always unchanged; central components total .9.
3. Use exactly two fresh stratified-QMC pilots of 2,048 points each. Each pilot
   uses its current full mixture and exact quadrature weights. Normalize
   quadrature_weight * exp(log_target - log_full_proposal) in log space.
   Retain all log responses and hashes of deterministic points/weights.
4. On each fixed pilot perform exactly 12 weighted EM steps on the three central
   Gaussians. Responsibilities are proportional to central mass times central
   density. Their importance-weighted sums update masses (floor .01 then
   renormalize), means, and centered covariances. Use effective weight count
   1/sum(normalized_component_weights^2) only as a numerical shrinkage diagnostic,
   not as an independent sample count. Shrink each covariance toward the original
   central covariance with pseudo-count d+2, clip eigenvalues to [1e-6,36], and
   apply no further inflation. These affect proposals only. Reuse stored pilot
   responses within EM; no extra target calls are hidden. Report objective changes;
   regularization means monotone likelihood improvement is not guaranteed.
5. Keep the original 2,048-point independent zero-mean control fit, 64x1,024
   coarse replicates and 64x32 paired corrections, with unchanged Student-t/Fieller
   numerical uncertainty. All full mixture weights and signed integrals remain.

Worst-case target calls are the previous 85,351 plus 4,096 = **89,447**, below
90,000. Count all search/derivative/pilot/control/coarse/fine calls, including
failures. Count EM iterations and record wall time separately from target calls;
no claim of equal total computational cost follows. Existing 180-second trial
and 3,600-second trial-loop limits remain; input/truth/storage/validation overhead
is reported separately. Time exhaustion retains failed/unattempted denominators.

## Experiment and diagnostic comparison

Base seed 2026112201; all ten previous cases 0–9 remain unchanged, 32 trials each.
No geometry is removed or newly called fresh football evidence. New random draws
on these consumed known-answer cases are numerical diagnostics.

The candidate's fitting entropy is [base,0,case,trial], mode search suffix 10,
mass pilot 11, new EM pilots [20,round]. Candidate evaluation uses the same base
tuple with the existing suffixes 2 (control fit), 0 (coarse), 1 (paired correction).
Those domains are distinct. A mode-only diagnostic runs all 32 trials for cases
3,5,6,7, independently recomputing the exact same initial mode fit using that
fitting entropy, but evaluating under [base,2,case,trial] with existing suffixes.
It repeats and counts its own search calls. Its common initial fitting geometry
must agree byte-for-byte with the candidate's saved initial fit. Different
evaluation randomizations prevent selecting a fortunate shared realization.
Paired differences describe this algorithm comparison, never causal NFL value.
No oracle arm or diagnostic fallback is eligible for adoption.

All 448 trials are requested and must be retained. The candidate uses the exact
previous feasibility screen: every trial completes, >=90% discrepancy-plus-error
precision at .01 SD for means and .001 CDF for endpoints, no severe undercoverage
at .01/70 marginal or .01/10 joint. Include individual wrong-endpoint checks.
No gate, prior, interval, sample budget or seed is changed after results.
This screen cannot replace full coverage certification or authorize NFL access.

## Failure analysis, stopping and verification

Complete all cases unless the declared operational cap is reached. Report every
failure, raw controlled/plain integral, actual point error versus numerical
allowance, pilot mass/concentration, discovered modes, fitted component moments,
and controlled/plain variance. Compare casewise candidate and mode-only diagnostics
with matched initial fits; do not select successful searches, diagnostic or plain
results. Assess whether adaptation improves broad-tail precision while preserving
remote mass, or instead distorts its initial geometry. Explain contradictions.

A failed screen stops this candidate before full certification. No automatic
sample increase, extra EM step, covariance retuning or favorable retry. If all
screens pass, require a separately frozen full coverage study before the unchanged
archived pilot and unfinished 192-fit player calibration. Week 10 remains sealed.
Original failed artifacts are immutable.

Test weighted responsibilities/moments against independent finite sums and known
Gaussian answers, duplicate-stratum conservation, preserved defensive support,
small/collinear weights, work caps, separate entropy and retained failures.
Recompute adaptation from saved responses; validate source, original geometry,
raw records, gates and actual rejection by the archived NFL loader. Run two
complete offline builds and compare every object and manifest. Replays are not
additional independent trials. Use existing NumPy/SciPy and unittest/CI only.

Update all six product milestones: this work does not resolve participation,
defensive identification, cross-position comparability, scored history or
authenticated deployment. No dependency, service, automation or other-repo change.
