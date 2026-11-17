# Frozen integration-aware control study — November 17, 2026

This design precedes implementation and fresh results. Branch
`codex/integration-aware-controls` starts at c49fafc and is stacked on open PR #30,
which itself depends on #29. Both remain reviewable; neither is merged here.

## Question and one candidate

The completed November 16 study passes known-answer coverage but fails numerical
certification in four of five archived cases. Pointwise residual reduction did
not translate into integration variance reduction. All point discrepancies alone
meet tolerance; this is uncertainty about numerical agreement, not established
football-model bias. The fine correction contributes negligible error.

Test one two-stage, integration-aware fit. Keep the Gaussian density/Hermite
zero-mean basis, full proposal density, saved geometry, football model, priors,
primary estimates, three positional benchmarks and signed season ledger fixed.
First fit the existing weighted, centered SVD ridge on **2,048** points (penalty
1e-6 times the largest squared singular value). This supplies one composite
zero-mean control h_j for each unnormalized functional f_j. It does not choose
among basis subsets. A second independent stage uses **16 randomized integration
replicates of 1,024 points each**, matching the evaluation net size and exact
component weights. For each functional, let F_r and H_r be their replicate means.
Set alpha_j = sum((F_r-Fbar)(H_r-Hbar)) /
((1+1e-6) sum((H_r-Hbar)^2)). Exactly zero denominator gives alpha_j=0.
Nonfinite results fail. Do not clip alpha, select it by significance, substitute a
sample mean for the known integral, or choose a fallback after evaluation.

This scalar adjustment avoids trying to fit 24–60 coefficients against only
16 integration replicates. It can undo a harmful pointwise fit, but may also
estimate covariance poorly. No improvement is presumed. The small fixed ridge
regularizes the numerical coefficient, not football effects. The covariance
formula minimizes replicate variance conditional on the first fit, whereas
pointwise regression minimizes a different objective. This rationale is also
discussed in [Owen's practical QMC notes](https://artowen.su.domains/mc/practicalqmc.pdf),
control-variates section (previously consulted; a November 17 retrieval returned
403). No external code or text is copied.

Conditional on both independent fits, h_j still has exact expectation zero, so
subtracting alpha_j h_j preserves the unnormalized integral's expectation. This
does not claim unbiased normalized ratios or exact finite-sample interval
coverage. Keep all mass/numerator covariance; sum coarse and fine-minus-coarse
integrals before normalization. Negative controlled masses are retained and fail
the existing positivity rule; signed player numerators are never clipped.

## Frozen budget, randomness and gates

`config/coarse-control-v2.json` has fresh root **2026111701**. Entropy domains 2
and 3 are the pointwise and integration fits; 0 and 1 remain independent coarse
evaluation and paired fine correction. Fit both stages afresh for every known
trial; points inside a Sobol net are dependent. Use 64 evaluation replicates of
1,024 coarse and 32 paired correction points. Total archived work is
2,048 + 16*1,024 + 64*1,024 + 2*64*32 + 1 = **88,065** evaluations, including
the fine offset. The existing 90,000 evaluations, 1,800 seconds/case and 7,200
seconds total caps remain. The largest case may hit the time cap: retain that
failure, do not extend the cap or omit the case.

Before NFL access, run all five analytic targets, 1,024 trials each, with exact
target-specific proposal restoration, original .001 surrogate perturbation and
deliberately wrong endpoints. All existing marginal/joint coverage, precision,
positive-mass and 0.01 posterior-SD / 0.001 CDF gates remain unchanged. Recompute
144 conditional-solver controls before archived use. A failed known gate blocks
NFL access; complete and diagnose the full denominator anyway.

If authorized by those controls, compare all five archived cases and every
original benchmark/prior contrast. Football outcomes are the consumed archive
through November 7 evening; **Week 10 remains sealed**. Fresh numerical draws
are not fresh football validation. The saved primary model/prediction objects
must remain identical. The previous certificate never authorizes this changed
algorithm. Historical replays require their recorded source revision.

## Diagnostics, verification and decision

Save both-stage coefficients, entropy, training responses/control replicate
means, hashes, fixed net size, alpha and covariance diagnostics. Reconstruct the
scale and coefficient product from raw training arrays. Meaningful tests cover
known analytical covariance answers, exact zero variance, signed coefficients,
separate randomness, unchanged expectations, matching nets, mixture weights,
full work and corrupted artifacts. No new dependency or CI experiment download.

Retain paired unadjusted evaluation integrals at no extra target evaluations.
Compare adjusted/plain empirical known-answer variance, coverage and precision;
report every failure. NFL diagnostics separate point gaps, numerical confidence,
coarse/correction influence and paired conditional variance. These diagnostics
are not selectable alternatives or new gates. Preserve all failed/unattempted
cases, original limits and immutable per-case objects under the existing size
cap. Reconstruct both studies independently offline and compare bytes.

End with a documented retain/reject decision and next concrete modeling action.
If certification passes, it only enables the separate 192-fit player calibration
and observational checks; it does not admit scores or validate causal attribution.
If it fails, analyze covariance-estimation and approximation limitations before
proposing a future design. Do not retry favorable seeds, widen intervals, change
football priors or add basis complexity to obtain a pass. Participation,
defensive comparability and the unified product remain required milestones.
No deployment, automation, paid service or other-project change belongs here.

## Packaging correction before full re-execution

The first two targets passed in both executions of source cc83843. Target 2
reached 1,024 trials, then its checkpoint exceeded the unchanged 128 MiB object
limit; it was not saved and its gate is not certified. There is no complete
control manifest and no archived NFL access from those attempts. Original logs
and the two saved cases in each store are preserved in the failure audit.

The correction stores an oversized case as contiguous blocks of at most 64
complete trial records, with adaptive subdivision if a block exceeds the cap.
Every object remains bounded; an oversized individual trial still fails. Indices
bind order, counts, byte hashes and the original complete logical case hash.
Checkpoints reference cases instead of embedding a second oversized copy.
Corrupt, omitted, reordered or changed blocks fail validation.

No integrand, fitting method, seed, trial count, threshold, target or benchmark
changes. The complete package source fingerprint does change, so **all five
targets are recomputed under the corrected committed source**, twice offline.
Do not reuse the partial old output as a current certificate or relax the source
guard. Compare the first two rebuilt cases with their retained original records.
This is repair of a storage failure, not new independent statistical evidence
from another seed. Archived builds will run sequentially to limit local resource
contention; their original evaluation and time caps remain unchanged.
