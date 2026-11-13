# Proposal adaptation — frozen before follow-up results

The original November 12 randomized study is complete: neither local-t nor the
defensive mixture passes all four known-answer fixtures. Report
`0477148ccfea35276838997962c6a9b78ac4bef8204cbf1cc8b40f932681a6b7`
retains all 1,024 trials; no confirmation or NFL evaluation was authorized.
Source `1171b1d` records the implementation. These failures are not discarded.

Failure analysis identifies a proposal problem as well as an error-coverage
problem: a single local mode misses substantial secondary/tail mass. The existing
optimizer actually found secondary modes in the three/four-dimensional mixtures,
but the explicitly single-mode proposal did not use them. The broad prior
component reduces some variability without achieving the precision gate. Merely
declaring broader numerical intervals cannot solve this failure.

## One bounded repair, same posterior and error gates

Fit a small **three-component Gaussian sampling mixture** using a separate
4,096-node density-only pilot (four scrambled replicates of 1,024 nodes from the
original defensive proposal). No known answers, CAVAA contrast values, interval
coverage outcomes or primary-QMC samples enter the fit. Correct pilot weights by
their full proposal density and component masses. Fit once per target, before
selection/confirmation replicates. This approximates a sampling density, not the
football model or its posterior; final weights always correct to the exact target.

Use weighted EM with three deterministic-seeded weighted k-means++ starts,
100 iterations maximum and absolute weighted-log-likelihood tolerance 1e-6.
Initialize component covariances to the pilot's weighted covariance. Initialize
centres by weighted squared distance in globally variance-scaled coordinates.
Clip sampling covariance eigenvalues to the existing [1e-6,36] limits, floor
sampling component masses at 0.01 and renormalize, and select the start with
highest final weighted log likelihood. Record iterations, convergence, clipping,
pilot effective samples and all component parameters. These safeguards affect
the proposal only and cannot alter the exact target or player intervals.

Inflate the fitted covariance matrices by the existing 1.5 proposal multiplier.
Mix them at total mass 0.9 with the original prior normal at mass 0.1. There are
four strata, each receiving 512 nodes in each of 32 independent final replicates
(65,536 final nodes). Exact mixture density and component mass correct the equal
allocation. Three components accommodate more than one mode and asymmetry while
keeping the proposal small; four total strata preserve power-of-two nets. Do not
select component count/covariance scale from the control outcomes.

## Fresh randomizations and decision

Base seed **2026111214** is new. Pilot entropy stage 3; EM initialization stage 4;
selection/confirmation/NFL remain stages 0/1/2, with separate case/trial/replicate
indices. Proposal learning uses no final-reference draws. Evaluate only this
candidate on the same declared analytical targets: 128 trials per fixture for
selection, then 256 new trials per fixture only if selection passes. This is
new randomization evidence on explicitly reused diagnostic functions, not new
football truth or fresh model calibration. Do not inspect confirmation early.

Keep every original coverage, precision, wrong-endpoint and Fieller condition,
the 0.01 SD / 0.001 CDF limits, 32 replicates, and sealed Week 10 unchanged. The
pilot and proposal fits count toward the existing 90,000 solves/900 seconds per
NFL case and 3,600 seconds per five-case pilot. If insufficient budget remains
for the whole final design, fail; do not shorten it opportunistically.

If either control stage fails, retain it and keep NFL evaluation blocked. If both
pass, run all five archived cases and offline replay under the original plan.
Agreement still cannot certify attribution, real-football uncertainty or position
admission. Mandatory defense and general qualification work remain unfinished.
No new library, service, data download, prior, statistical interval inflation or
automatic publication is introduced.
