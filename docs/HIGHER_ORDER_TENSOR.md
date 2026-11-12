# Tensor reference controls — frozen November 12 follow-up

This is frozen while the sparse pilot is still in its first QMC stage, before
any archived-case sparse result. The sparse implementation passes its software
checks and scalar-convolution endpoint control. Its fixed correlated/skewed
moment controls retain honest nonconvergence in 2–4 dimensions; at four dimensions
the mass error estimate is 0.000887 and the maximum component error ratio 383.7.
Actual errors remain below the reported estimates. Sparse growth may underresolve
mixed-coordinate structure under the fixed budget. This motivates a bounded
dense-rule comparison on known answers, rather than a change to the NFL model.

Compare two tensor rules using the same predeclared orders **7, 11, 15**:

- Gauss–Legendre on the existing open unit cube and Student-t(5) transform.
- Gauss–Hermite on independent standard normals, transformed with the same
  axis-proposal means and variances. Divide by the exact normal proposal density
  at each node. This is full-support integration, not a finite log-precision box
  or a replacement prior. Its tail reliability must be tested, not assumed.

Pinned SciPy supplies the public `roots_legendre` / `roots_hermitenorm` rules.
Stream complete tensor products and reserve each full order before evaluating it.
Maximum work across all three four-dimensional orders is 67,667 nodes; proposal
and QMC costs still count toward the existing 90,000 solves / 900 seconds per case
/ 3,600 seconds per pilot. No extra budget or deleted case. No requirement to use
remaining capacity once the reference converges.

Estimate each component error as twice the absolute successive-order difference
plus an absolute-weighted roundoff floor. Require at least order 11, the same
raw-integral absolute/relative limits, and the existing normalized mean/CDF gates.
The factor two is a conservative estimator, not a rigorous guarantee. Report all
orders, positive-mass checks and failure reasons. It is distinct from the sparse
two-increment estimator, which is preserved unchanged.

Before using either rule on archived cases, verify polynomial moments, independent
tensor answers, signed components, budgeting and deterministic replay. Compare
both on the already specified correlated/skewed/tail targets, independently
known scalar-convolution endpoints and deliberately wrong endpoints. Add a fixed
tail stress mixture: 95% standard normal and 5% Normal(4, 2²) in the first
coordinate, other coordinates standard normal, in four dimensions. A reported
convergence with an actual moment error exceeding its numerical tolerance rejects
that rule for this pilot; do not suppress the test or change the target to pass.

Candidate selection uses these numerical controls only. Among rules with correct
control decisions and a converged correct-endpoint reference, choose the one with
more converged moment controls; ties use fewer endpoint-control evaluations, then
Legendre. If both fail the controls, run neither on NFL cases. Record that outcome
and the next numerical decision. If one is selected, run all five consumed cases
and independently rebuild offline. Preserve the sparse results and every
failure. The original optional higher-QMC follow-up applies only to a converged
reference that rejects QMC functionals.

No new NFL validation, prior, benchmark, interval inflation, qualification change
or score publication. All methods target the same continuous posterior; no result
is causal evidence or a calibration pass. Week 10 remains sealed.

Sources: SciPy's primary documentation for
[Gauss–Hermite](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.special.roots_hermitenorm.html)
and [Gauss–Legendre](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.special.roots_legendre.html).
No new dependency, license obligation, service or automation change.
