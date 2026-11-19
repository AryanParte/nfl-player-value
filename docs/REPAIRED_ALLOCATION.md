# Frozen error diagnosis and one equal-work allocation alternative

November 15, before the diagnostic calculations and alternative results.
The corrected proposal's first control still fails: upper-endpoint marginal
coverage 92.1875%, p=7.6164e-5 against the original 0.0002857143 threshold.
All precision checks pass, but precision cannot override undercoverage. The
proposal restoration is necessary and independently verified; it is not a full
explanation of the coverage failure. Finish all five original controls and their
independent reconstruction; retain every result. No NFL pilot is authorized yet.

## Consumed-control failure diagnosis

Analyze the failed control's upper endpoint (first contrast, raw numerator index
5), without refitting or selecting a different target. For each level use the
influence quantity `H = numerator - 0.975 * mass`. The fine expectation of H is
zero. The coarse expectation is `0.001 * E[H(x) sin(sum(x))]`; the correction's
expectation is its negative. Compute this quantity independently from the known
Gaussian mixture: conditional Gaussian sine moments reduce the integral to one
dimension, followed by adaptive quadrature over [-12, 12]. Cross-check against
128- and 256-node-per-axis Gaussian quadrature in the original two dimensions,
requiring absolute agreement within 1e-9. Never use these known answers in NFL
fitting or alter the frozen control truth.

Report level-specific empirical trial variance, average within-trial estimated
variance, their ratio, centered Student coverage, skewness, kurtosis, and the
combined quantity. This is exploratory diagnosis on consumed numerical draws,
not a new validation pass or a replacement for Fieller ratio decisions. Do not
interpret a descriptive diagnostic as proof of a unique failure cause.

## One prospective alternative, unchanged total points

Approximate Student/Fieller sets rely on independent replicate behavior. More
independent replicates can improve the variance estimate and normal approximation;
fewer points per net can worsen integration precision. Test that tradeoff under
the same total conditional work, not by multiplying uncertainty intervals.

Freeze **64 independent replicates × 1,024 coarse / 32 correction points**, replacing
32 × 2,048 / 64. Both designs use 65,536 coarse and 2,048 fine correction points;
the paired correction also evaluates 2,048 coarse points. The NFL cap remains
90,000 combined evaluations, 1,800 seconds/case and 7,200 seconds total. Geometry,
target, normalization, error construction and all accuracy/coverage rules remain
unchanged. The confidence critical value uses the actual new replicate count,
not a tuned multiplier. This is an allocation change, not a larger primary net.

Use fresh entropy **2026111502**, 1,024 trials for each of the same five analytic
targets, the original .001 sinusoidal surrogate perturbation, and all original
marginal/joint coverage and precision gates. Configuration is
`config/repaired-functional-v2.json`. Only this one candidate is tested; it must
pass every gate before all five archived cases can run. No favorable candidate,
seed, subgroup or prior is selected after results. Failed/unattempted cases remain.

If this fails, retain and diagnose it; do not increase replicates again within
this unit, widen intervals, reduce the known perturbation, relax limits or waive
coverage. If it passes, perform the repaired NFL comparison and complete offline
reconstruction. Numerical agreement still cannot admit a player module without
calibration, observational attribution and the remaining scientific contract.
