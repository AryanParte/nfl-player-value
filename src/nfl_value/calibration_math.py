"""Known-truth ridge diagnostics; neither score publication nor causal attribution."""

from hashlib import sha256
from math import isfinite

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from nfl_value.baseline import ACTORS, GROUPS


Z95 = 1.959963984540054
SCENARIOS = [
    {
        "name": "matched_prior_iid",
        "truth": "matched_prior",
        "noise_group": "game",
        "correlated_fraction": 0.0,
    },
    {
        "name": "fixed_signal_iid",
        "truth": "fixed_signal",
        "noise_group": "game",
        "correlated_fraction": 0.0,
    },
    {
        "name": "fixed_signal_game",
        "truth": "fixed_signal",
        "noise_group": "game",
        "correlated_fraction": 0.5,
    },
    {
        "name": "fixed_signal_team",
        "truth": "fixed_signal",
        "noise_group": "offense_team",
        "correlated_fraction": 0.5,
    },
]
PLAN_KEYS = {
    "plan_version",
    "windows",
    "benchmark",
    "actor_penalties",
    "primary_actor_penalty",
    "replicates",
    "seed",
    "noise_sd",
    "fixed_effect_magnitudes",
    "scenarios",
    "cluster_estimator",
    "nominal_coverage",
    "severe_undercoverage_bound",
    "alias_shift_ep_per_component",
}


def positive(value):
    return type(value) in (int, float) and isfinite(value) and value > 0


def validate_plan(plan):
    if set(plan) != PLAN_KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported calibration plan")
    if (
        plan["benchmark"] != "first_unit"
        or plan["cluster_estimator"] != "game_cr0_penalized_scores_v1"
        or plan["nominal_coverage"] != 0.95
        or plan["severe_undercoverage_bound"] != 0.9
        or plan["scenarios"] != SCENARIOS
    ):
        raise ValueError("unreviewed calibration scenarios or interval policy")
    if any(type(s["correlated_fraction"]) not in (int, float) for s in plan["scenarios"]):
        raise ValueError("numeric noise fractions required")
    if type(plan["replicates"]) is not int or plan["replicates"] < 2:
        raise ValueError("at least two independent replicates required")
    if type(plan["seed"]) is not int or plan["seed"] < 0:
        raise ValueError("nonnegative integer seed required")
    windows = plan["windows"]
    if not isinstance(windows, dict) or not windows:
        raise ValueError("season windows required")
    if any(
        s not in {"2025", "2026"} or type(w) is not int or not 1 <= w <= 18
        for s, w in windows.items()
    ):
        raise ValueError("invalid calibration window")
    magnitudes = plan["fixed_effect_magnitudes"]
    if set(magnitudes) != {"actor", "context", "team", "observed_role"}:
        raise ValueError("explicit signal magnitudes required")
    penalties = plan["actor_penalties"]
    if not isinstance(penalties, list) or not penalties or any(not positive(v) for v in penalties):
        raise ValueError("positive penalty grid required")
    if len(set(penalties)) != len(penalties) or penalties != sorted(penalties):
        raise ValueError("distinct increasing penalty grid required")
    if plan["primary_actor_penalty"] not in penalties:
        raise ValueError("primary penalty outside grid")
    if any(
        not positive(v)
        for v in [
            plan["primary_actor_penalty"],
            plan["noise_sd"],
            plan["alias_shift_ep_per_component"],
            *magnitudes.values(),
        ]
    ):
        raise ValueError("positive finite calibration settings required")


def penalty_vector(names, *, actor, context, team):
    if (
        not names
        or len(set(names)) != len(names)
        or any(not positive(v) for v in (actor, context, team))
    ):
        raise ValueError("unique features and positive penalties required")
    if any(n.split("/")[0] not in GROUPS or "/" not in n for n in names):
        raise ValueError("unknown feature family")
    return np.array(
        [
            0.0
            if n == "context/intercept"
            else actor
            if n.split("/")[0] in ACTORS
            else context
            if n.startswith(("context/", "observed_role/"))
            else team
            for n in names
        ]
    )


def operator(x, contrasts, penalties):
    """Cache H^-1 L' and A; do not invert or refit separately for each response."""
    if (
        x.ndim != 2
        or contrasts.ndim != 2
        or penalties.shape != (x.shape[1],)
        or contrasts.shape[1] != x.shape[1]
        or not x.shape[0]
        or not len(contrasts)
        or not np.all(np.isfinite(x.data))
        or not np.all(np.isfinite(contrasts))
        or not np.all(np.isfinite(penalties))
        or np.any(penalties < 0)
    ):
        raise ValueError("invalid calibration design dimensions or values")
    h = (x.T @ x).toarray() + np.diag(penalties)
    try:
        factor = cho_factor(h, lower=True)
        hl = cho_solve(factor, contrasts.T)
    except np.linalg.LinAlgError as exc:
        raise ValueError("calibration precision is not positive definite") from exc
    diagonal = np.einsum("ij,ji->i", contrasts, hl)
    if np.any(diagonal < -1e-10):
        raise ValueError("negative conditional contrast variance")
    return {
        "factor": factor,
        "a": np.asarray(x @ hl),
        "hl": hl,
        "conditional_diagonal": np.maximum(diagonal, 0),
        "penalties": penalties,
    }


def groups(labels):
    if not labels or any(not isinstance(s, str) or not s for s in labels):
        raise ValueError("nonempty group identifiers required")
    return [np.flatnonzero(np.array(labels) == label) for label in sorted(set(labels))]


def oracle_variance(a, cluster_indices, *, noise_sd, fraction):
    independent = np.sum(a * a, axis=0)
    shared = sum(np.sum(a[g], axis=0) ** 2 for g in cluster_indices)
    return noise_sd**2 * ((1 - fraction) * independent + fraction * shared)


def cluster_variance(a, residual, game_indices):
    """Uncorrected penalized-score sampling variance, not posterior uncertainty."""
    return sum((a[g].T @ residual[g]) ** 2 for g in game_indices)


def simulate(x, names, primary_penalties, *, plan, season, week, scenario_index, noise_groups):
    """Real incidence, synthetic outcomes; never read actual EPA to generate truth."""
    rng = np.random.Generator(
        np.random.PCG64(
            np.random.SeedSequence(
                [
                    plan["seed"],
                    season,
                    week,
                    scenario_index,
                ]
            )
        )
    )
    scenario = plan["scenarios"][scenario_index]
    b = plan["replicates"]
    sigma = plan["noise_sd"]
    if scenario["truth"] == "matched_prior":
        scale = np.zeros(len(names))
        penalized = primary_penalties > 0
        scale[penalized] = sigma / np.sqrt(primary_penalties[penalized])
        beta = rng.normal(size=(len(names), b)) * scale[:, None]
    else:
        signal = []
        for name in names:
            family = name.split("/")[0]
            magnitude = (
                0.0
                if name == "context/intercept"
                else plan["fixed_effect_magnitudes"][
                    "actor" if family in ACTORS else "team" if family.endswith("_team") else family
                ]
            )
            signal.append(magnitude * (1 if sha256(name.encode()).digest()[0] % 2 == 0 else -1))
        beta = np.repeat(np.array(signal)[:, None], b, axis=1)
    rho = scenario["correlated_fraction"]
    noise = sigma * np.sqrt(1 - rho) * rng.normal(size=(x.shape[0], b))
    if rho:
        for indices in noise_groups:
            noise[indices] += sigma * np.sqrt(rho) * rng.normal(size=(1, b))
    return beta, np.asarray(x @ beta) + noise


def evaluate(x, contrasts, op, beta, y, *, game_indices, noise_indices, noise_sd, fraction):
    """Known truth and exact bias distinguish calibration from sampling precision."""
    coefficients = cho_solve(op["factor"], np.asarray(x.T @ y))
    residual = y - x @ coefficients
    estimated = contrasts @ coefficients
    truth = contrasts @ beta
    bias = -op["hl"].T @ (op["penalties"][:, None] * beta)
    sigma2 = np.sum(residual * residual, axis=0) / x.shape[0]
    variances = {
        "conditional_gaussian": op["conditional_diagonal"][:, None] * sigma2,
        "game_cluster_cr0": cluster_variance(op["a"], residual, game_indices),
        "oracle_sampling": np.repeat(
            oracle_variance(op["a"], noise_indices, noise_sd=noise_sd, fraction=fraction)[:, None],
            y.shape[1],
            axis=1,
        ),
    }
    if any(not np.all(np.isfinite(v)) or np.any(v < 0) for v in variances.values()):
        raise ValueError("invalid simulated interval variance")
    error = estimated - truth
    widths = {name: 2 * Z95 * np.sqrt(v) for name, v in variances.items()}
    covered = {name: np.abs(error) <= width / 2 for name, width in widths.items()}
    # This is a known-truth control, NEVER a deployable bias correction.
    covered["oracle_expectation_control"] = np.abs(error - bias) <= widths["oracle_sampling"] / 2
    widths["oracle_expectation_control"] = widths["oracle_sampling"]
    if not all(np.all(np.isfinite(v)) for v in (error, bias)):
        raise ValueError("nonfinite simulation estimates")
    return error, bias, widths, covered


def summarize(error, bias, widths, covered, *, failure_bound):
    """Replicates are independent; player/benchmark cells within them are not."""
    result = {
        "contrasts": error.shape[0],
        "replicates": error.shape[1],
        "mean_bias_ep": float(np.mean(error)),
        "rmse_ep": float(np.sqrt(np.mean(error**2))),
        "mean_absolute_conditional_bias_ep": float(np.mean(np.abs(bias))),
        "intervals": {},
    }
    for name, coverage in covered.items():
        per_draw = np.mean(coverage, axis=0)
        rate = float(np.mean(per_draw))
        mcse = float(np.std(per_draw, ddof=1) / np.sqrt(len(per_draw)))
        result["intervals"][name] = {
            "coverage": rate,
            "monte_carlo_se": mcse,
            "mean_width_ep": float(np.mean(widths[name])),
            "severe_undercoverage": rate + Z95 * mcse < failure_bound,
        }
    return result


def alias_diagnostics(x, names, contrasts, *, shift):
    """Construct exactly equivalent expected outcomes with differing attribution."""
    csc = x.tocsc()
    buckets, cold = {}, []
    for j, name in enumerate(names):
        if name.split("/")[0] not in ACTORS:
            continue
        column = csc[:, j]
        if not column.nnz:
            cold.append(j)
        else:
            key = (tuple(column.indices), tuple(column.data))
            buckets.setdefault(key, []).append(j)
    cases = []
    pairs = [[members[0], other] for members in buckets.values() for other in members[1:]]
    for indices in pairs + [[j] for j in cold]:
        delta = np.zeros(len(names))
        delta[indices[0]] = shift
        if len(indices) == 2:
            delta[indices[1]] = -shift
        prediction_change = float(np.max(np.abs(x @ delta)))
        if prediction_change != 0.0:
            raise ValueError("declared alias changes expected outcomes")
        change = contrasts @ delta
        cases.append(
            {
                "kind": "identical_observed_columns" if len(indices) == 2 else "prior_only_column",
                "coefficient_shifts": {names[j]: float(delta[j]) for j in indices},
                "max_play_expectation_change_ep": prediction_change,
                "affected_contrasts": int(np.count_nonzero(change)),
                "max_absolute_contrast_change_ep": float(np.max(np.abs(change))),
                "max_change_contrast_index": int(np.argmax(np.abs(change))),
                "signed_change_at_max_ep": float(change[np.argmax(np.abs(change))]),
            }
        )
    return {"observed_alias_pairs": len(pairs), "prior_only_columns": len(cold), "cases": cases}
