# Multi-season variance recovery — frozen November 8, 2026

This bounded unit follows the QB recovery non-admission, not a new penalty search
on its inspected tests. Implement a multi-season contribution candidate, integrate
variance uncertainty, run new known-effect experiments, diagnose historical
connections and defensive information loss, replay and record a decision. No
automatic admission or real ranking follows from implementation or simulation.

## Data, estimand and prospective boundary

Reuse the exact archived 2024/2025 full-season offensive/weekly-roster evidence and
2026 snapshot used by the November 7 QB study (122 games, cutoff November 7
20:41 Eastern; Week 9 partial). All are already inspected development/training data.
Do not rerun their predictive tests as fresh evidence or select an alternative by
those outcomes. No source download, purchase or new dependency is needed.
Historical observations inform the prior-linked fit; **only 2026 opportunities add
2026 expected points**. Preserve every completed game at the declared snapshot
cutoff, negative contributions, first-unit/equal-player/opportunity-weighted
comparisons and the existing independent full-QB eligibility diagnostic. The
archived research cutoff is explicit; this is not a current November 8 publication.

Keep the previous roster-verified pass/sack/scramble scope and preplay context.
Primary QB contribution in season t is persistent player effect q_i plus a
season-specific innovation d_it. Team/support effects vary by team and season,
with separate offensive and defensive groups; game effects remain shared nuisance
terms. Context includes season intercepts. A season coefficient is not current
form multiplied backward. First-unit peers face the same additive context/team
conditions; overlapping play value remains in separate components and residuals.

Reserve **2026 Week 10** as an uninspected predictive window. Freeze model inputs,
posterior fits and alternatives before viewing it; no fitting update for that test.
Once completed sources exist, use identical verified QB observations for the
candidate and team control, reporting paired game-bootstrap RMSE, MAE and
team-game errors under the existing predictive evidence rule. Missing/unseen QBs
must not silently disappear. No predictive gate can pass today before these data
exist. Preplay features make this conditional play prediction, not pregame wins.

## Four alternatives, no outcome-selected winner

The [plan](../config/multiseason-v1.json) declares:

- **evolving (primary):** persistent QB plus QB-season innovation, offensive-team-
  season, defensive-team-season and game effects.
- **persistent:** no QB-season innovation. Historical switching may connect teams,
  but the restrictive constant-skill assumption can misattribute year changes.
- **team:** context and team-season/game effects, without QB effects.
- **qb_proxy:** evolving QB plus defense/game, without offensive-team effects;
  an explicitly confounded control, never an individual-value admission candidate.

No pressure/targets/receiver identity/postplay features become hardship controls.
Check QB-to-team-season connected components and explicit prediction-preserving
allocation shifts in both QB designs. This is a structural information diagnostic,
not a claim of unrestricted causal identification. Innovations may reopen aliases
that a constant-QB assumption hides; report that rather than constraining them away.

## Variance integration and numerical contract

Use a **finite, explicitly discrete prior**, not a fitted interval multiplier or
an undocumented approximation to a continuous prior. Independently assign each
of QB, offense, defense and game precision ratios lambda=sigma²/tau² equal mass
on [4,40,400,4000,40000]. QB-season innovations share QB variance in the primary
(innovation SD ratio 1, fixed before outcomes); the persistent control omits them.
This broad grid permits a range of signal strengths including near-zero effects;
it is a modeling hypothesis, not established NFL variance knowledge. Record edge
mass and sensitivity to QB-cell prior weights proportional to lambda^(-.5) and
lambda^(.5); never choose the favorable prior after results.

Use sigma² ~ Inverse-Gamma(shape=3, scale=4.5), mean 2.25, a broad proper noise
prior anchored to the previously declared 1.5 EPA simulation scale. Context
coefficients have a common flat prior after an X-only rank reduction. Integrate
random game effects analytically using per-game sufficient statistics, then use
Cholesky systems for the remaining coefficients. For R=I+Zg Zg'/lambda_game,
H=X'R^-1 X+D, Q=y'R^-1 y-c'H^-1c and r=context rank:

- conditional mean H^-1c, c=X'R^-1y;
- posterior shape a=3+(n-r)/2, scale b=4.5+Q/2;
- cell log weight = -.5(log|R|+log|H|-log|D|positive)-a log(b),
  plus the declared cell prior (constants common to the cells omitted);
- a contrast is Student-t with df=2a, location L H^-1c and scale²=(b/a)L H^-1L'.

Normalize cell probabilities with log-sum-exp. Compute mixture quantiles from the
weighted Student-t CDF, retaining player/benchmark covariance and between-cell
uncertainty; do not average interval endpoints or sort marginal intervals into
rank confidence. Test against independent dense observation-space calculations,
small exact mixtures and augmented game-effect systems. Cache sufficient statistics
and solve batches of synthetic responses; this avoids refitting an optimizer in
each trial. No random sampler or new probabilistic framework is necessary.

A flat context prior means the simulation check conditions on a fixed context
coefficient, rather than claiming full-prior simulation-based calibration of all
parameters. Priors, structural data limits and model uncertainty remain distinct.
Integration does not make the assumptions true or automatically remove bias.

## Fresh known-effect tests and decision

128 deterministic replicates per declared scenario on the actual fixed design:

1. finite hierarchy: draw precision cells and sigma² from the stated proper
   priors, all random effects from their conditional Gaussian distributions;
2. continuous hierarchy: fixed noise SD 1.5; Gaussian persistent QB .25, QB-season
   .15, offense .15, defense .10, game .20 SD. These are off-grid/mismatched truths,
   not chosen to match the prior's finite support or innovation ratio;
3. fixed year changes: hash-signed fixed effects at those magnitudes, game effect
   zero, half residual variance shared by game and half independent. Context
   coefficients are fixed hash-signed ±.1 in every scenario.

For the primary, compare integrated-mixture intervals and a **maximum-posterior-
cell conditional control** on exactly the same synthetic responses. The latter
isolates consequences of treating a variance choice as known; never select it for
publication on these outcomes. Report coverage, Monte Carlo SE by independent
replicate, width, error and edge mass. Keep the prior severe-undercoverage flag
coverage+1.96 MCSE<.90, and do not mistake absence of the flag for a 95% certificate.
Compare real first-unit contrasts across the declared model/prior alternatives;
all remain research outputs pending fresh NFL prediction and attribution evidence.

## Mandatory defensive diagnosis

Replay the existing paired 2025 rich/degraded defensive inputs; slice both through
Week 10 before fitting. Use the same player population/cohort and strict old-view
contracts. Compute full weighted design null directions and diagnostic defender-
minus-unweighted-defender-mean projections (these are **not positional CAVAA**).
Profile the five declared defender precisions with the old context precision 1
and team precision 50 fixed, reporting integrated cell weights, effective player
dimension, coefficient sensitivity and prediction-preserving lineup/team shifts.
Rich rows have weight 1; degraded means have weight equal to their play count.
Their likelihood row counts and noise assumptions differ; do not compare raw
marginal likelihoods across views or assert that aggregate rows are independent
player observations. No new defensive confidence/admission claim is made.
Preserve FTN/nflverse derivative attribution and share-alike terms in the report.

## Review and references

[Stan's simulation-based calibration guidance](https://mc-stan.org/docs/2_39/stan-users-guide/simulation-based-calibration.html)
distinguishes computational calibration under a generating model from empirical
model adequacy. [SciPy's Student-t CDF](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.stdtr.html)
supports deterministic mixture inversion; the installed SciPy version remains
pinned. These references motivate checks, not guarantees for this NFL model.

A positive model decision still requires accurate benchmark/exposure/accounting,
calibration, defensible allocation and fresh predictive evidence. Document failed
assumptions and bounded next actions. Do not modify the v1 non-admission registry,
production labels, development schedule or other NFL project in this unit.
