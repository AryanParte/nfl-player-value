# Fixed coverage confirmation — frozen before new trials

The density-adapted proposal's initial study remains **failed**, report
`a3ec189abc21fc3d42c1319ab3df74dbcd9ec4f1168a2bb520192c373ecc96cc`.
All four fixtures meet precision in 99.2–100% of 128 trials. The first three pass
their complete gates. The tail fixture's simultaneous coverage is 120/128, with
one-sided 95% lower bound 0.890057, below 0.90. No NFL case ran, and no original
decision is changed. Its nominal marginal coverages include 90.625% and 92.1875%;
these require investigation, not dismissal as a near-pass.

Review identified limited power in the original selection design: at n=128 the
lower-bound criterion requires at least 122 successes. Even if true simultaneous
coverage were exactly 0.95, its pass probability is only 0.54071447. Four such
conditions compound that risk. This does not prove the observed failure is noise.
The correct response is more informative validation, not a looser error limit or
a succession of new seeds until a favorable result appears.

Freeze **one fixed 1,024-trial confirmation per fixture**, all four fixtures,
unconditional on intermediate outcomes. Use the identical adapted sampling
geometry from the failed study; verify its exact recorded hash before any trial.
Base seed remains 2026111214 so density-pilot/EM geometry is unchanged. New
confirmation entropy stage **5** supplies fresh independent randomizations.
There is no new selection stage, no optional stopping, no geometry refit chosen
from these outcomes, and no follow-on confirmation retries in this run.

Retain the original marginal undercoverage tests, simultaneous lower-bound >=0.90,
90% precision requirement, wrong-endpoint checks, 32 replicates, 65,536 final
nodes per trial, exact target and covariance-aware intervals. Add a one-sided
exact test of simultaneous nominal 95% coverage at 0.01/4 across fixtures. This
is an additional check, not a relaxation. Report point coverage and binomial
uncertainty explicitly; a nonsignificant test is not proof of exact coverage.

At n=1,024 the original lower-bound condition requires 938 successes and has
0.9999983 pass probability at true coverage 0.95. The marginal tests also gain
power to detect actual undercoverage. This study is a fresh randomization audit
on reused diagnostic functions, not fresh NFL/calibration evidence. Both earlier
failed studies stay visible. Only a complete pass of this fixed audit may
authorize the same five-case archived numerical pilot. It cannot admit CAVAA.

The frozen geometry hashes are recorded in `randomized-reference-confirmation-v1.json`.
No sample-size or accuracy budget for any NFL case changes. No statistical
interval is enlarged, no test outcome is used to refit the posterior, and no
score, benchmark, qualification or defensive policy changes.
