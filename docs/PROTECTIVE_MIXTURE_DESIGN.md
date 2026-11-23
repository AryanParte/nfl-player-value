# Protective-mixture feasibility study — frozen November 23, 2026

This unit is stacked on open PR #35, head d46a2d9. No contribution module is
admitted. Yesterday's target-weighted adaptation improved broad nonmodal mass
but damaged endpoint precision even when the original search found both modes.
Preserve that evidence; do not refit its settings to the consumed trials.

## Candidate and rationale

Use exactly q = .5 q_mode + .5 q_tail, with both proposals fitted by the unchanged
November 22 algorithm. The tail fit already retains the initial mode geometry;
reuse it without another target call. Keep all eight ordered Gaussian strata,
including both half-weighted defensive components. They total .1 original
defensive mass; mode and adapted central mass each total .45. No mode is dropped,
no component is reweighted by an observed functional error, and no outcome or
fixture truth enters the fitter.

Pointwise q >= .5 q_mode and q >= .5 q_tail. For a fixed unnormalized integrand g,
this implies integral(g²/q) <= 2 integral(g²/q_mode), and likewise for q_tail,
when the right side is finite. This elementary second-moment bound is **not** a
twofold variance bound after subtracting the squared integral. It does not certify
the finite fitted-control, self-normalized ratio, stratified-QMC or confidence
procedure, and it cannot find a mode missed by both fitted proposals. Mixture
protection and component-density controls have established motivation in
[Owen and Zhou, Safe and Effective Importance Sampling](https://doi.org/10.1080/01621459.2000.10473909).
We do not import that paper's asymptotic guarantees into this implementation.

Keep the existing Gaussian zero-mean controls, independent 2,048-point training,
relative ridge 1e-6, 64 x 1,024 coarse replicates and 64 x 32 paired corrections.
Eight strata get 256 training, 128 coarse and four correction points each.
In four dimensions this creates 120 control columns, with duplicate columns for
the two defensive components. Existing SVD ridge handles these; verify it against
independent signed known-answer fixtures before scientific draws. Splitting the
fixed nets can reduce QMC precision and increases arithmetic cost. Neither more
points nor a revised control fit is an allowed fallback in this study.

Fitting is unchanged: 256 search points, 24 bounded starts, 4,096 mass pilot,
two 2,048-point/12-step EM pilots. Maximum target calls remain 89,447, below the
90,000 cap. Original 180-second trial and 3,600-second aggregate trial-loop caps
remain. Report fitting, control and evaluation work, failures and timing honestly.
Preparation/truth/storage/validation overhead is outside that loop cap.

## Draws, diagnostics and decision fixed before evaluation

Base seed 2026112301. All ten retained known-answer cases 0–9 have 32 candidate
trials. A mode-only diagnostic and a tail-only diagnostic each have 32 trials
for cases 3,5,6,7: **576 requested trials** in total. These are new numerical draws
on consumed synthetic geometries, not new NFL validation. No oracle arm runs.

All three arms use fitting entropy [base,0,case,trial], including the unchanged
search suffix 10, mass suffix 11 and EM suffix [20,round]. Mode-only recomputes
its own initial fit; tail-only recomputes its own full adaptation, counting work.
Initial mode geometry must match across all three; full adaptation must match
candidate versus tail-only. Evaluation entropy uses arm index 0 for candidate,
2 for mode-only and 3 for tail-only, retaining suffixes 2 (control training),
0 (coarse), 1 (paired correction). Training and evaluation remain independent.

The existing candidate screen is unchanged: every trial completes, >=90% pass
discrepancy plus numerical allowance at .01 SD for means and .001 CDF for endpoints,
and no severe undercoverage at .01/70 marginal or .01/10 joint. Keep wrong-endpoint
diagnostics. Both raw controlled and plain integrals survive failed confidence
construction. Neither diagnostic nor plain estimator can be selected for release.
No gate, target, prior, interval, seed or sample count changes after results.

Complete every case unless the declared operational cap is reached. Report all
failure denominators; compare candidate with both diagnostics using matched fits,
separate evaluation randomness, point errors, numerical allowances, endpoint
failures and plain/controlled variation. Tabulate discovered-mode groups only as
failure analysis, never as selectable validation subsets. Report density probes
as probes, not global coverage proofs. Test the protective bound algebraically
and numerically independently of these outcome comparisons.

If any candidate screen fails, reject progression and diagnose whether discovery,
finite allocation or control residual/endpoint variance is the remaining problem.
No automatic retry, favorable subset, added samples, widened interval or retuned
mixture follows. If all screens pass, freeze a separate full numerical coverage
study before the unchanged archived NFL pilot and unfinished 192-fit player study.
This preflight cannot authorize NFL input access or admission. Week 10 stays sealed.

## Verification and scientific limits

Test full-density weighting against independent Gaussian sums, stratum mass and
support, signed polynomial answers, zero-mean controls with duplicates, source and
geometry corruption, matched fit domains and complete work counts. Reconstruct
proposals from saved responses and bind their ordered mixture, source and plan.
Run two complete offline builds and compare every object/manifest byte-for-byte;
the second execution is replay, not more independent trials. Check the actual
saved report is rejected before archived NFL inputs are read.

No football model, CAVAA benchmark or eligibility policy changes. Negative values,
all completed season games and nonduplicated accounting remain intact. This
numerical unit cannot resolve attribution, participation, defensive measurement,
cross-position comparability, scored history or deployment. Document all six
milestones. Reuse the existing pipeline and dependencies; no service, purchase,
schedule or other-repository change.
