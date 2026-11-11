# Reference-coordinate repair — before NFL pilot results, November 10

The first independent known-answer test is a correlated Gaussian mixing law
with Student-t conditional observations. QMC passes its checks, but Genz–Malik
cubature using the table's inverse CDF reaches 192 subdivisions without convergence:
estimated mass error 0.0005913, endpoint CDF discrepancy plus estimated error
0.0016355, exceeding the declared 0.001. The test assertion is retained. No NFL
pilot or new scientific calibration has run. This is a numerical reference-design
failure on a known target, not evidence about player performance.

Piecewise-linear density tables produce derivative changes at their knots. The
independent reference will instead use a **smooth product Student-t(5) transform**.
Its location and variance match the proposal table's exact first two moments,
including the Gaussian prior mixture. These moments are analytic integrals of
each linear segment. The Student-t scale equals SD × sqrt(3/5). The reference
therefore has a different change of variables from QMC, with smooth heavy tails
and support over all finite log precisions. Its exact density/Jacobian correction
integrates the same joint posterior; no prior, outcome model, interval, acceptance
rule, case selection or compute budget changes.

The original config remains preserved. `variance-reference-smooth-v1.json` adds
only `reference_transport: independent_student_t5_moments`. Verify the moments
against independent quadrature and keep the original known-answer assertion.
Do not run more numerical alternatives if this fails the bounded NFL pilot; record
the failure and diagnose it. Consumed numerical tests are not fresh calibration.

The smooth known-answer reference then met the external mean/CDF error checks,
but its internal relative-error controller still exhausted subdivisions on the
near-zero **centered mean integral** (maximum mean error plus estimate 0.000272
SD, endpoint CDF error plus estimate 0.000477). This reflects a poor numerical
scale for relative integration accuracy. Precondition that integral by adding one
copy of the target mass, then subtract one after normalization. Propagate both
numerator and mass errors for the shifted integral before applying the unchanged
external check. This exact linear identity changes neither the posterior mean
nor any tolerance or interval. Keep the assertion that the reference converges;
the reference status cannot be ignored because another check happens to pass.

Apply that same mass-offset identity to the two CDF integrals as well: otherwise
the 0.025-tail integral still makes the internal relative tolerance far tighter
than the unchanged normalized-CDF error requirement. All three ratio-integrand
types are thus computed on the mass scale, with one subtracted afterward and
conservative error propagation using the full shifted numerator. No positivity
assumption is made about the centered-mean integrand. The externally assessed
posterior means, CDF values, acceptance thresholds and budgets are unchanged.
