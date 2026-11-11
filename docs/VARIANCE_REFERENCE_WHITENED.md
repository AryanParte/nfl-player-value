# Correlation-aware reference coordinates — frozen November 11 follow-up

Freeze this follow-up before its numerical results. The binary-refinement study
is still finishing all five cases and its offline rebuild. Its observed real team
control passes; the real QB reference remains nonconverged at 89,941 solves.
QB mean disagreement plus estimated error improves to 0.01192 SD and endpoint-CDF
disagreement plus error to 0.00865, still above 0.01/0.001. Keep those failures.

## Specific numerical hypothesis

The current transform treats variance coordinates independently and takes its
moments from conditional-axis curves mixed with 10% of the broad prior. These
curves are neither joint-posterior marginals nor its correlation structure. Even
efficient binary subdivision can waste nodes along narrow, correlated ridges.
This is a numerical hypothesis about the reference, not evidence for a different
football prior or allocation. No known synthetic variance enters the NFL fit.

Construct a smooth full-support reference transform from the **existing pooled
primary QMC weights and log-precision nodes**. Compute their weighted mean and
population covariance (not a sampling-error estimate). Require a finite positive
definite covariance and use its Cholesky factor `L`. Transform independent
Student-t(5) coordinates `z` as `eta = mean + sqrt(3/5)*L*z`. This matches the
proposal covariance to those moments. Evaluate its exact Jacobian and product-t
log density; correct by the unchanged joint target at every reference node.
There is no posterior truncation, covariance regularization, variance override,
new latent effect or selected prior. Invalid geometry fails explicitly.

The reference integrates with a different method from QMC, but its coordinate
geometry now uses QMC. This shared geometry is disclosed; it is not independent
football evidence or a completely independent software implementation. Approximate
proposal moments do not change the exact importance-corrected target. Known-answer
tests must check the Jacobian, covariance and resulting integrals, including
correlated targets and deliberately incorrect endpoints.

Keep binary refinement, all mean/CDF/ESS/nesting rules, all contrasts and both real
prior sensitivities. Retain **90,000 solves / 900 seconds per case / 3,600 seconds
total**. Same five consumed cases, same QMC seeds and stopping policy. Run all five
and independently rebuild; compare point estimates and QMC histories to the first
version. No fresh calibration or admission. This changes only reference geometry.

If the new reference converges but rejects QMC means/endpoints, a separately
recorded numerical follow-up may use both original scrambles at fixed powers
12 and 13 (4,096 then 8,192 nodes each), under the same total solve/time budgets.
That is additional deterministic numerical resolution of the same target, not
retuning on football test outcomes. Do not change seeds, priors, thresholds,
case selection or interval formulas. Otherwise report the unresolved reference
failure and the specific next action; no hidden unlimited retry.

The original study, intermediate failures and source revisions remain reproducible.
Week 10 stays sealed. Defense/qualification/module admission are unchanged.

## Known-answer verification before NFL follow-up

The analytical test exposed two issues. Floating-point Cholesky alone accepted
a singular covariance after scaling; an explicit positive-eigenvalue check now
rejects it without adding a ridge. A more correlated known target produced QMC
endpoints that the converged reference rejected (CDF disagreement about 0.00261).
That rejection is retained as a regression test. Independent one-dimensional
Normal-plus-Student-t convolution and root finding provide the correct endpoints;
the same reference passes them. No numerical tolerance or NFL model changed to
make the inaccurate endpoint pass. Density/Jacobian, exact proposal moments,
unchanged QMC estimates and deliberate wrong-endpoint tests pass before this run.
