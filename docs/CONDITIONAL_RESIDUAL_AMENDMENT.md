# Frozen residual-arithmetic repair — November 14

Freeze this amendment before implementing or testing its candidate. The original
v1 design and artifacts remain unchanged. Hosted run 43653737102 failed the strict
known-answer gate on Python 3.11; diagnostic run 43654467323 also fails across its
Python matrix. Its 3.13 log identifies the near-alias case at player and game
precision 1e-24: quadratic error 1.0360187075533606e-9 exceeds the unchanged 1e-9
limit. Mean error 9.28e-9 SD, variance error 3.26e-9 and likelihood error 1.26e-8
pass their respective limits. Local macOS 3.11 and 3.13 passed the original suite.
The v1 kernel is therefore not established as portable. Retain every failure.

## One bounded computational correction

The QR solve is backward stable, but nearly cancelling columns amplify its small
input perturbations. Computing the minimized quadratic from the transformed QR
residual can consequently differ from the objective on the original observations.
This is an arithmetic diagnosis, not evidence for a different football model.

Keep exact alias integration, QR coefficient/covariance solves and determinant.
For the candidate `exact_alias_residual`, evaluate the penalized residual sum on
the **original sparse design and reconstructed coefficients**. Use error-free
binary64 split products and `math.fsum` for observation residuals; compute game
conditional means from those residuals and include the original player/team and
game penalties. This is the same quadratic in exact arithmetic. At its optimum,
small coefficient errors affect the objective only to second order. Do this for
every candidate evaluation, with no size/fixture/result-dependent fallback and no
substitution of the Decimal reference into the solver. Reject nonfinite arithmetic.

The larger cost must fit the existing work budgets. No likelihood truncation,
precision clipping, changed prior, favorable basis/seed selection, wider interval,
or relaxed gate is authorized. The old candidate/default remains available for
exact versioned replay. A failure ends this amendment with an explicit blocker;
further numerical alternatives need a separate frozen rationale.

## Verification and decision

`config/conditional-solver-v2.json` freezes the new candidate and two seeds:
2026111401 repeats the 72 consumed regression cases; **2026111403** supplies 72
fresh synthetic response cases with the same predeclared six design families and
precision grid. Both must pass, for **144 requested cases**. Neither is new NFL
validation. The independent Decimal references and all four v1 tolerances remain
unchanged. Add analytical product/cancellation tests and explicit finite-input
checks. Run the unchanged Python CI matrix, retaining any platform failures.

Only after the full known-answer gate passes, repeat the existing 85 consumed
archived comparisons, raw/reordered failing-point checks, and originally failed
density fit under the new candidate, with the original seeds and budgets. Save in
new immutable stores with the new plan and producing commit. Reconstruct offline
and compare exact bytes within the recorded environment. Do not overwrite or
relabel v1 reports as new evidence. This tests the same target, not football
calibration or full numerical-error coverage. No module is admitted; Week 10 stays
sealed. Report runtime and the unchanged full-integration/calibration blockers.
