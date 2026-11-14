# Conditional solver repair — November 14

The exact-alias square-root candidate passes its frozen arithmetic and archived
equivalence checks and completes the previously failed density fit. This clears
the **observed conditional-factorization blocker**, not the broader numerical,
calibration or CAVAA-admission gates. No contribution module is admitted and no
new season leaderboard is published. The [audit](audits/2026-11-14-conditional-solver.json)
binds the complete failures, numerical artifacts, code and decision.

## Frozen sequence

The [design](CONDITIONAL_SOLVER.md) and `config/conditional-solver-v1.json` were
committed at `5be5f60` before new study results. `7408846` implements the two
alternatives, independent Decimal reference and immutable controls; `57fa720`
adds the gated archived comparison and failed-fit replay. The branch
`codex/conditional-square-root` is stacked on still-open PR #27 at `abab5fd`.
Its parent CI passes and had no review feedback at inspection. No merge occurred.

The alternatives change only computation. Plain augmented QR retains all penalty
rows. The preferred alternative first certifies exact binary aliases by rational
row reduction within each equal-precision group and the retained intercept/season
context. It integrates the unobserved proper-prior directions and restores their
covariance to contrasts. This is not setting players or team effects to zero.
Nonbinary near aliases remain modeled; unequal precision blocks are not pooled.
No likelihood truncation, prior change, jitter, seed retry or tolerance relaxation
was needed. Software-test setup errors (source import path and a test's store-path
attribute) were fixed before the relevant checks completed; neither changed a
scientific result or the numerical algorithm.

## Independent known answers

Six families each have twelve precision combinations: partition, duplicates,
near alias, cold player, player/year links and game-constant context. Each has two
signed responses, individual and player-minus-peer contrasts, zero and doubled
contrasts. The reference assembles the original augmented coefficient model,
including random game effects, directly from exact float inputs at 80 and 110
Decimal digits. All 72 pairs of references agree within the frozen 1e-20 mixed
absolute/relative requirement. They do not use the production Gram matrix, QR,
alias reduction or game marginalization.

| Kernel | Passed / requested | Decision |
| --- | ---: | --- |
| Archived normal-equation kernel | 28 / 72 | Retain failures as diagnosis |
| Augmented QR alone | 61 / 72 | Block archived use under this study |
| Exact-alias QR | 72 / 72 | Permit the bounded archived equivalence check |

Worst exact-alias errors are 7.01e-9 posterior SD for means, 1.06e-9 relative
variance, 8.64e-10 relative residual quadratic, and 9.54e-9 absolute log likelihood.
The corresponding frozen limits are 1e-6, 1e-6, 1e-9 and 1e-6. The near-alias
quadratic is close to its strict limit; this finite suite does not certify every
ill-conditioned matrix or precision configuration. CI explicitly requires the
preferred candidate's complete control gate, rather than merely checking that
a failed result can be serialized.

Post-study self-review tightened certificate loading: it now recomputes the
independent high-precision answer from the frozen fixture and binds its response
hash, rather than accepting two mutually consistent saved answers alone. A
regression for altered answers and outputs that agree with each other must fail.
Existing reports pass the stronger check unchanged; no numerical algorithm,
control outcome or gate changed.

Plain QR's eleven failures involve partitions, duplicates, year links and game
means. Its maximum standardized mean error is 0.000933 and maximum relative
variance error is 9.91e-5. Working with square roots helps but does not by itself
remove leakage of roundoff into extremely weakly penalized aliases. The exact
reduction addresses that mechanism while preserving the prior distribution.

These are arithmetic accuracy tests. No numerical-error coverage rate or fresh
football calibration rate is estimated by this study. The November 13 replicated
coverage results remain separate, unchanged evidence.

## Archived equivalence and repaired failure

All **85 requested coordinate comparisons** finish and pass: the prior center
and sixteen declared fresh coordinate draws for each of five consumed cases.
The old kernel is a comparison where it remains finite, not a truth oracle.
The same response hashes, model plans, cutoffs and first-unit/sensitivity contrast
matrices are used. No new NFL outcomes or calibration responses are inspected.

| Case | Passing coordinates | Largest mean error (posterior SD) | Largest absolute log-likelihood error |
| --- | ---: | ---: | ---: |
| Real QB | 17 / 17 | 3.37e-12 | 4.66e-10 |
| Real team | 17 / 17 | 2.73e-10 | 3.49e-10 |
| Consumed prior stress | 17 / 17 | 8.57e-13 | 2.91e-11 |
| Consumed hierarchy stress | 17 / 17 | 2.08e-12 | 5.82e-11 |
| Consumed fixed-year stress | 17 / 17 | 1.29e-12 | 8.73e-11 |

The evolving design goes from 525 computational columns to 414: 105 QB/year/cold
alias directions and three each for offense and defense are integrated out.
All original coefficient identities and their appropriate prior covariance remain
in the returned estimates. The team design goes from 211 to 205 columns. These
counts describe linear combinations, not excluded players or identified effects.

At the exact previously failed point, the old kernel again raises the same
359th-leading-minor error. The new calculation is finite at the unchanged offense
precision 9.66e-24. Bypassing compression gives a 2.52e-13-SD mean difference;
reversing the exact alias basis gives 3.73e-13 SD. Their absolute likelihood
differences are 2.91e-11 and 1.16e-10. A separate original-row penalized-residual
calculation agrees to 9.94e-16 relative error, with reconstruction error 8.88e-16 EP.
These are equivalent computations sharing the new algebra, not an arbitrary-
precision solve of the full NFL system; the independent Decimal evidence is on
the small controls.

The gated replay of **the originally failed fit only** then completes in 4,938
conditional evaluations and 41.2 seconds, below the original 90,000/900-second
limits. The adaptive and stabilized geometries are archived separately from the
November 13 failure. Stabilization's training log-score gain is -0.0223; completion
does not establish superior overlap or functional integration accuracy. No new
holdout or full five-case posterior pilot was run, and no successful fit replaces
an old failed trial. The original report and failure trace are unchanged.

## Reproducibility and costs

| Artifact | SHA-256 |
| --- | --- |
| Known-answer report | `e3c8608a76bd0f4b766220eaa31b3593de7806a1b6fcd6e7dda08aa12808b7ce` |
| Archived equivalence/repaired fit | `fd42ac3140a010c5b89ec98c79403ff3524c2954a3927c688e0baa369247b00e` |

Independent reconstruction disables socket creation, connection and DNS after
imports. Both manifests and every study object match byte for byte in separate
stores. Timings are separate execution diagnostics, not deterministic artifact
fields. The archived computation takes about 52 seconds after input restoration;
controls take about 0.3 seconds. No budget is exhausted and no case is unattempted.
No dependency or recurring cost is added. The large data/artifacts stay outside
normal Git history; local replay does not establish durable remote retention.

Reproduce from the producing revision and existing verified source stores:

```sh
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.conditional_cli known
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.conditional_cli --output-store data/derived/conditional-archive archive e3c8608a76bd0f4b766220eaa31b3593de7806a1b6fcd6e7dda08aa12808b7ce
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m nfl_value.conditional_cli --output-store data/derived/conditional-archive replay-archive fd42ac3140a010c5b89ec98c79403ff3524c2954a3927c688e0baa369247b00e
```

Local `make check` passes 449 Python tests and 27 frontend contracts, lint,
formatting, TypeScript/build, compilation and whitespace. A strengthened gate
assertion was rerun successfully after the full suite. Hosted CI is reported
against the actual PR head; local tests are not evidence that hosted CI passed.

## Decision and next milestone

Use the candidate for the next separately frozen functional numerical comparison;
do not silently replace the default kernel or any existing model artifact. The
same observed posterior remains the target, with independent new randomizations,
declared work budgets and unchanged 0.01-SD / 0.001-CDF requirements. Diagnose
remaining primary/reference disagreement and reference imprecision before the
unfinished 192-fit calibration and observational admission. Do not automatically
enlarge sample counts or select a favorable proposal.

The last integrated real-QB pilot still fails at 0.014228 SD / 0.001308 CDF; this
study does not recompute or supersede that result. All 17 modules remain
unadmitted. Archived 2026 coverage remains 122 games / 8,996 QB dropbacks, with
57 QBs, all three benchmark comparisons and negative values retained. The source
cohort ends November 7 evening, not November 14. Qualification gaps, defense and
cross-position comparability remain separate requirements. Deployment is still
an Explorer setup issue, not an admitted leaderboard: the newly inspected
scheduled run 43515405405 fails at initial retention/bootstrap before publication.
