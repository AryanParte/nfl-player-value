# Fresh failure-analysis control — November 8, 2026

Frozen after inspecting multi-season report
`2e6708b65c30b2da606859aa14726228238082d887d05d76ed870606ef7180e6`,
before any new control outcomes. The primary covers 95.13% for its finite prior,
90.78% for the continuous off-grid hierarchy and 92.06% for fixed year changes.
The latter two are below nominal 95% despite not triggering the severe <90% flag.
Modal-cell conditioning is nearly identical to integration off-grid; simply
accounting for cell uncertainty has not resolved model mismatch. Do not widen
intervals, select a favorable prior or reuse these draws for tuning.

One bounded diagnostic uses 128 **new** continuous-hierarchy draws, seed
2026110802, on the identical multi-season design, first-unit contrasts, magnitudes
and noise defined by the original plan. Compare:

1. unchanged finite-grid integrated primary;
2. known true precision ratios for every random group, including the distinct
   persistent QB and QB-season innovation variances;
3. the same known ratios except innovation is forced to share persistent QB
   variance, matching the primary restriction.

Both controls integrate the residual scale under the original inverse-gamma prior
and flat context; neither knows realized player effects. They use unavailable
synthetic variance knowledge. Report coverage/replicate MCSE, width, bias/error,
paired replicate coverage differences and the unchanged severe-undercoverage flag.
No real-model coefficients, production intervals, benchmark, participation or
admission rules change. The two controls diagnose the combination of finite-grid
support and variance restriction; they do not establish that a continuous-prior
fit will succeed on NFL data, and they do not isolate each group's grid error.

If known ratios improve coverage, the next justified work is a new, separately
preregistered variance model tested on fresh draws and reserved NFL evidence.
If not, investigate design/estimand or covariance errors before more complexity.
Either result is diagnostic, not an admission. Keep Week 10 untouched and the
defensive non-admission in force. This is the only additional simulation family
in this run; finish replay, review and the milestone decision afterward.
