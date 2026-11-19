# Frozen joint ratio-control study — November 18, 2026

Frozen before implementation or fresh experimental draws on
`codex/joint-ratio-controls`, stacked on open PR #31 at 21731dc. The previous
candidate is rejected. Its consumed results motivate this one alternative; they
are not a new validation set. Week 10 remains sealed. No player model, prior,
benchmark, interval, source cohort or admission rule changes.

## Objective and construction

For a ratio N/Z near a fixed anchor r, its first-order integration error is
proportional to N-rZ. Separate reductions in Var(N) and Var(Z) need not reduce
this quantity: covariance matters. This is the ratio-variance argument in
[Owen, chapter 9, sections 9.2 and 9.10](https://artowen.su.domains/mc/Ch-var-is.pdf).
The proposed two-direction fit below is our bounded hypothesis, not a coverage
theorem or a football model. We retain full joint Fieller calculations.

Keep the existing 2,048-point weighted centered Hermite SVD fit, supplying one
zero-mean composite h_j for each unnormalized numerator and h_0 for its mass.
Use 16 independent integration-training replicates of 1,024 points. Fit mass
exactly as v2: alpha_0 = centered_cross(F_0,H_0) /
((1+1e-6)*centered_squares(H_0)); zero variance yields zero.

For each numerator j, regress centered Y=F_j-r_j F_0 on the two centered columns
[H_j,H_0]. Scale each column by its Euclidean norm (exact zero becomes scale 1).
Use SVD ridge penalty 1e-6 times the largest squared singular value. Zero singular
values yield zero; no jitter, clipping, rank selection or evaluation fallback.
Let the resulting original-scale slopes be b_j and c_j. The final numerator
control is b_j h_j + (c_j+r_j alpha_0) h_0. The final mass control is alpha_0 h_0.
Consequently the adjusted fixed-anchor influence subtracts precisely
b_j h_j+c_j h_0. All controls still have known expectation zero, conditional on
both independent fits. This preserves unnormalized expectations; normalized
ratios can remain biased and intervals can fail. Coefficients may be negative.

Anchors are fixed before fresh draws: centered means 0, lower CDF .025, upper
CDF .975. The deliberately shifted wrong upper endpoints also use .975, without
pretending that is their truth or using their actual CDF to fit. Each prior's
block has its own mass; columns cannot borrow another prior's mass. Never use
evaluation estimates or known-answer integrals to choose coefficients. The
two-direction fit also gives centered means access to the mass control, which
the preceding one-dimensional fit lacked.

## Fresh design, controls and unchanged budgets

`config/coarse-control-v3.json` fixes root 2026111801. Existing entropy domains
2/3 fit the pointwise/integration stages; 0/1 evaluate coarse/correction stages.
The original five analytic targets and geometries remain exactly unchanged.
Add two four-dimensional Gaussian mixtures with exactly known mass, mean and
variance; their endpoint CDFs are independently evaluated by one-dimensional
normal/Student-t convolution and root finding, as in the original fixtures.

Both added targets have .9 mass at N(0,I). Target 5 has .1 at
N(0,diag(4,1,1,1)); target 6 has .1 at
N((4,4,0,0),diag(.5,.5,1,1)). The fixed proposal for both is
.9 N(0,I)+.1 N(0,9I), represented by three identical central strata and one
defensive stratum. No pilot fitting or selection occurs. Existing two contrasts,
Student-t(20) conditional noises (.2,.4), and wrong endpoints shifted by -.5
are retained. These are broad-tail and displaced-mass challenges, chosen from
the observed failure mechanisms, not fitted to an NFL density. They do not
establish universal robustness. For every target component, 2 Sigma^-1-I/9 is
positive definite, so the importance-weight second moment and polynomial
functional moments are finite; poor finite-sample coverage is still possible.

Run all seven targets, each with 1,024 trials and a newly fitted control in
every trial. Preserve all failed trials in denominators. Original five gates
retain their marginal alpha .01/35 and joint alpha .01/5. Added targets form a
separately declared stress family (.01/14 marginal, .01/2 joint); both families
must pass. Other positivity, precision (90% of trials), coverage lower bound .9,
wrong-endpoint rejection, .01 SD and .001 CDF rules are unchanged. No early
stopping on a failure or passing subset. These are numerical-error coverage
tests, not the unfinished 192-fit player-calibration experiment.

Evaluation retains 64 replicates of 1,024 coarse plus 32 paired fine-correction
points: 88,065 target evaluations per archived case, including the offset.
Archived caps remain 90,000 evaluations, 1,800 seconds/case and 7,200 seconds
total. Only a complete passing new control certificate plus reproduction of
all 144 conditional controls authorizes the unchanged five-case NFL pilot.
Run all archived benchmark/prior contrasts if authorized. Otherwise mark that
pilot unattempted and diagnose the full known-answer failure. Never drop a
tail control, relax a limit, repeat a favorable seed or choose the paired plain
result after evaluation.

## Verification, failure analysis and decision

Test the covariance cancellation against independent analytical answers,
signed and zero-variance fits, duplicate/collinear directions, common scaling,
separate prior blocks, independent entropy, full work and corrupted metadata.
Store/recompute raw training integrals, slopes, anchors/mass indices and final
coefficient hashes. Known-case storage must bind all seven cases; archival
storage still binds its original five. All tests remain offline.

Complete an independent full offline reconstruction and compare object bytes.
Record target-wise precision, marginal/joint coverage, bias, empirical error,
paired plain results, mass concentration, and fixed-anchor influence variance
for training versus evaluation. Report whether remaining failures concern
coverage, accuracy, concentration or ineffective controls; do not reinterpret
an inconclusive numerical interval as proven model bias. End with a decision
and the next concrete scoring action. A pass only enables subsequent player
calibration and observational validation; no score is admitted by this study.
