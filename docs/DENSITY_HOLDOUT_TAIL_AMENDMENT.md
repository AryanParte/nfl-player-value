# Pre-result tail-compatibility correction — November 13

The original design is retained at `aefe914`. During mathematical self-review,
before any paired-density/coverage/archived study results, its quadratic curved
control is found inappropriate for this finite-variance reference comparison.
Unit tests of that control's inverse and exact answers ran; no sampling-proposal
performance or coverage result was inspected. This correction is based on the
tail algebra, not a failed empirical result or relaxed numerical gate.

With x1=z1+0.5*(z0²-1), a normal latent z produces an exponential marginal tail
in x1. The proposal remains a finite Gaussian mixture. Along the curved ridge,
target²/q contains a positive fourth-power term in z0 in its log density and
its integral diverges. Full support is insufficient for finite importance-weight
variance. Student-t/Fieller replicate error cannot be justified by a finite-
variance argument on that example. This is not evidence of NFL failure: the NFL
target retains its normal log-precision prior, and the defensive proposal includes
that prior. The pathological control tests a different tail regime.

Replace only the new control's shear with **x1=z1+0.5*sin(z0)** and
**x3=z3+0.5*sin(z2)**, preserving x0=z0 and x2=z2. The inverse subtracts those
bounded sine terms and the Jacobian determinant is one. Functionals remain the
same two linear contrasts on z(x), plus independent Student-t(20) noise. Their
analytic means/variances and scalar-convolution endpoints are unchanged.

For the control, q >= 0.1 Normal(0,9I). Since x-z is bounded, the exponent of
target²/q is at most `-(17/18)*||z||² + O(||z||)`, up to a constant. Its integral
and the required polynomial-weighted moments are finite. This does not guarantee
useful variance or nominal coverage; the fixed experiment must still measure them.
It is a curved target with a known answer and suitable tails, not a football model.

Active configuration is `density-holdout-v2.json`, with explicit transform name
`bounded_sine`. All other settings, two proposal definitions, 32/four paired
density trials, fixed 1,024 coverage trials per target, error/coverage gates,
failure retention, no retries, NFL budgets and non-admission policy are unchanged.
Commit this amendment before changing the control implementation or running the
new study. Preserve the original configuration and documented correction.
