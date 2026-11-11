# Continuous variance recovery — preregistered November 9, 2026

This work is stacked on open PR #21 at `412c99b`. It does not amend that study's
grid, draws or decisions. No review feedback or CI failure was outstanding at
the start. All new alternatives, checks and experiments below are frozen before
evaluating their outcomes. Existing NFL tests and November 8 simulations are
consumed; the archived data are development data only.

## One changed assumption

Replace the five-point variance prior with independent continuous priors
eta_g=log(lambda_g) ~ Normal(log(400), 3²), for QB, offensive-team-season,
defensive-team-season and game. The center is the original grid's geometric
center, not a newly selected NFL optimum. The broad unbounded support removes
both its coarse spacing and hard variance limits. It remains a hypothesis, not
known NFL variance knowledge. Keep the existing inverse-gamma noise prior,
flat rank-reduced context, persistent QB + QB-year contribution, tied innovation
variance, preplay features and team-season/game nuisance structure unchanged.

Fit only the evolving candidate and team control. Preserve all three positional
benchmarks, current-season opportunities, negative values, separate qualification,
full player-minus-benchmark covariance and nonduplicated accounting. Historical
plays inform the model but add zero 2026 points. Use exactly the parent report's
archived 2024–26 sources; no Sunday refresh or Week 10 data is inspected here.
Save a new frozen model; do not overwrite the November 8 models. The same sealed
Week 10 evaluation remains pending. No positive admission follows automatically.

## Integration, not a new latent-effect approximation

Retain the independently checked conditional Gaussian/Student-t algebra and exact
game marginalization. Integrate over the four continuous log precisions with
self-normalized importance quadrature using two independent scrambled Sobol
sequences. Proposals are a 10% original-prior Gaussian plus equally weighted
Gaussian approximations around distinct posterior modes (remaining 90%). Find
mode proposals with three fixed starts; numerical search bounds are not posterior
support bounds. Exact target/prior and complete mixture-proposal densities correct
every node's weight. Hessian eigenvalue bounds and the 1.5 covariance multiplier
affect proposal efficiency only, never the target posterior or reported interval
width directly. The prior component retains support over all finite log precisions.

Use fixed nested powers 7–11 (128–2,048 points per scramble). After each doubling,
compare independent-scramble means and 95% endpoints, and pooled results with the
previous power. Require differences below .01/.02 posterior SD respectively and
effective sample size at least 128 for each scramble. These are numerical
diagnostics, not proofs of an error bound. Report actual effective samples,
convergence levels, failed optimizations/solves and the evidence of instability.
Do not skip failed nodes or silently treat underconverged results as valid.

For prior sensitivity shift the QB log-precision mean by ±log(4), holding every
other setting fixed. Reweight the same nodes with exact density ratios and apply
the same numerical checks; a failed sensitivity remains unavailable, not stable.
No favorable prior is selected after observing estimates. A conditional
posterior-mode control on the same synthetic responses diagnoses the cost of
treating learned variances as known; it is never selected for publication.

If numerical integration fails, retain the failure, use the predeclared doubling
sequence and finish the bounded diagnosis. Independent small-model quadrature,
observation-space likelihood and known-normal integration references must pass.
Routine implementation defects may be fixed and replayed; the prior, scientific
gate or consumed draws must not be changed to make coverage pass.

## Fresh calibration and decision

64 new fixed-design replicates per scenario, seed 20261109. This bounded size is
chosen before results because continuous integration is more expensive; report
Monte Carlo SE by replicate and do not treat players as independent repetitions.
Use the full archived multi-season design and current first-unit contrasts:

1. **continuous_prior:** draw log precisions and noise from the declared proper
   priors, and random effects conditionally Gaussian; fixed context remains the
   same hash-signed ±.1, so this is conditional calibration, not full-prior SBC;
2. **continuous_hierarchy:** retain the prior study's off-grid generator (QB .25,
   innovation .15, offense .15, defense .10, game .20; independent noise SD 1.5);
3. **fixed_year_changes:** retain its fixed signed signals and half shared-game,
   half independent residual variance. The old prior excluded the equivalent game
   precision ratio 1; the new continuous prior does not.

Report coverage, replicate MCSE, width, bias/RMSE and conditional-mode controls.
All failed or underconverged trials remain in the requested denominator and
prevent a calibration-pass claim; report success-only summaries with that caveat
and conservative all-trial coverage bounds. Preserve the severe-undercoverage
flag coverage+1.96 MCSE<.90. Absence of that flag is not a nominal-95% certificate.
Also disclose any nominal shortfall exceeding twice MCSE. No arbitrary interval
inflation, oracle variance assignment or outcome-selected model/threshold change.

A model numerically integrated under its own prior can still allocate value
poorly. Reuse the prior design's explicit QB/team null witnesses; they identify
assumption dependence rather than demand causal identification. Assess real
prior sensitivity and benchmark changes. Positive admission still requires fresh
NFL predictive evidence and the observational-estimand/uncertainty review. If
calibration passes here, freeze the candidate and finish that review, not announce
a ranking. If it fails, record the cause and next bounded action.

## Defense and operational boundary

Keep the required defensive experiment and Explorer intact. Audit public release
metadata for 2026 participation/lineup availability without downloading or looking
at reserved outcomes. Record actual coverage limits and source terms; do not
manufacture defensive scores or substitute aggregate precision for player evidence.
No optional deployment architecture, purchases, automation changes or merge.

Reference: [SciPy Sobol documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html)
explains power-of-two draws and scrambling; installed NumPy/SciPy pins stay
unchanged. [Stan calibration guidance](https://mc-stan.org/docs/stan-users-guide/simulation-based-calibration.html)
distinguishes inference checks under a generator from empirical model adequacy.

## Reproduction and review

The implementation uses the existing pinned NumPy/SciPy optional dependencies;
ordinary CI uses small synthetic cases, not NFL downloads or the full experiment.
`continuous_math.py` contains the density/conditional integration and numerical
checks; `continuous_recovery.py` contains the frozen study and signed season
accounting. `continuous_cli.py` replays the parent's archived sources, verifies
the exact design/population and recomputes the benchmark weights before fitting.

The completed scope and exact commands are in [the result report](CONTINUOUS_RESULTS.md).
Use `config/continuous-variance-diagnostic-v1.json` to reproduce its eight attempts
per generator. The original default config preserves the planned Gaussian/full
study; invoking it is not a replay of the final diagnostic artifact.

Use the recorded producing revision and environment for numerical reproduction.
Builds require committed source. Both commands use local immutable stores;
replay verifies every output hash and recalculates all configured attempts rather
than trusting checkpoints. A diagnostic cap retains unattempted requested trials
in the report's denominator. Checkpoints are diagnostic objects only. Research
artifacts are ignored by Git; the committed audit records their IDs and evidence.
A failed numerical check cannot become a valid frozen prediction candidate.
Neither command publishes rankings, changes a website pointer or refreshes data.

Regression tests compare known-normal integration and a one-dimensional random
effect with independent SciPy quadrature, in addition to the inherited dense
observation-space likelihood checks. They force convergence failure, preserve
its requested denominator, verify signed cumulative accounting and reject altered
source/model populations or corrupted/mismatched replay outputs. These software
checks do not establish NFL uncertainty calibration or correct player attribution.
