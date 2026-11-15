# Bounded implementation throughput continuation — November 14

The compensated-residual study passes all 144 arithmetic controls and 85 archived
coordinate checks, but its fit replay stops after 3,514 evaluations at the original
900-second cap. Preserve report
`f0d376a9219fa31731aaf2a3a933a1ed1f2ec6ce602cfc008fe939f4d71c3205`;
do not substitute the earlier QR-only fit's completion for this failed attempt.

Before a further attempt, freeze one implementation-only alternative: cache the
unchanging sparse-design product split and row bounds, and pass ordinary float
lists directly to `math.fsum` in the identical term order. Avoid repeated scalar
conversion and iterator dispatch. Do not change addition/product formulas, QR,
mean/covariance/determinant calculations, priors, tolerance, seed, data or fitting
policy. Overflow/underflow must still fail explicitly. Bulk conversion at `0fdf2b7`
already preserves the 144 control bytes; extend the same optimization principle.

Acceptance requires exact original-row residual equality with the unoptimized
implementation on deterministic cancellation fixtures, exact saved 144-control
reconstruction, unchanged 85 archived coordinate and failing-point outputs, and
the ordinary software checks. These are consumed regression checks, not fresh
scientific validation. No football outcome is a tuning signal.

Allow one new fit attempt with the same original 90,000-evaluation / 900-second
limits, inside the 5,400-second study budget. Save a separate report at its producing
revision, with networking disabled and all original failure evidence retained.
If it finishes, independently reconstruct its complete report within the same
limits. If it fails, record the blocker and stop this throughput continuation;
do not keep trying variants or enlarge limits. Exact failed-timeout evaluation
counts are machine/runtime dependent and cannot be promised as replayable values.
No full posterior, calibration or CAVAA admission is authorized by this work.
