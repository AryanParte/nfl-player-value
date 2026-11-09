# Numerical repair frozen November 9, before its results

The initial Gaussian-importance attempt in `5a0a808` reached its numerical cap
without validating either real candidate. Its completed simulation checkpoints
are preserved in the [attempt audit](audits/2026-11-09-numerical-attempt.json);
the remaining requested trials were stopped, not declared successful or omitted
from a calibration denominator. No scientific calibration pass was obtained.
One checkpoint had ESS 23.57 out of 2,048 and independent endpoint disagreement
0.262 posterior SD. All three starts found effectively the same mode; this is
evidence of a poor local Gaussian importance proposal, not proof of a model flaw.

One bounded repair changes **numerical sampling only**. Keep the exact log-normal
variance prior, noise model, effects, benchmarks, response draws, 95% intervals,
ESS and independent/nested accuracy thresholds unchanged. The original config
remains immutable. `continuous-variance-numerics-v1.json` adds one proposal policy:

- Keep the 10% Gaussian prior component. Replace each mode's proposal Gaussian
  with a multivariate Student-t with 5 degrees of freedom and the same Hessian
  scale. Its heavier tails reduce rare dominant importance weights. This does
  not use Student-t outcome noise or widen the target posterior.
- Sample each proposal component separately with balanced, independently
  scrambled Sobol nets. Use 128–2,048 points **per component** per scramble, an
  explicitly larger maximum numerical budget. Apply the full mixture density
  in the denominator and the component's quadrature mass in the numerator.
  Deterministic stratification removes the component-selection discontinuity.
- Retain both independent scrambles, all nested convergence checks and the same
  sensitivities. A failed node or capped accuracy failure remains a failure.
  Compare density/moments against independent library and scalar quadrature
  references before running this repair on the archive.

Recompute all 64 requested trials in each of the same three frozen generators.
Previously started draws are explicitly consumed diagnostic evidence, not a new
scientific validation sample. Reusing them checks an inference algorithm for the
**same target**, not a model or gate tuned to coverage. Do not select between
results based on coverage or report this numerical repair as independent model
replication. Record it even if it fails. No further proposal/precision/interval
retuning is part of this bounded repair; subsequent work needs its own decision.

Save real candidate checkpoints before the expensive simulations so their
numerical failures survive interruption. Checkpoints remain diagnostic only;
build/replay recompute all fits. Do not release any score from an underconverged
fit. Sealed Week 10 outcomes, admission policy and production remain unchanged.
