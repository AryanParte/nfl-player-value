"""New, fixed-design calibration trials of the frozen multi-season hierarchy."""

from hashlib import sha256

import numpy as np

from nfl_value.multiseason_math import posterior_diagnostics
from nfl_value.variance_mixture import integrate, interval, modal_interval, moments


def simulate(prepared, plan, scenario):
    if scenario not in plan["simulation_scenarios"]:
        raise ValueError("undeclared calibration scenario")
    truth, responses = [], []
    for replicate in range(plan["simulation_replicates"]):
        rng = np.random.default_rng(
            [plan["simulation_seed"], plan["simulation_scenarios"].index(scenario), replicate]
        )
        beta = np.array(
            [
                0.1 * (1 if int(sha256(n.encode()).hexdigest(), 16) % 2 else -1)
                if n.startswith("context/")
                else 0.0
                for n in prepared.names
            ]
        )
        groups = {
            g: np.array([j for j, n in enumerate(prepared.names) if n.startswith(g + "/")])
            for g in ["qb", "innovation", "offense", "defense"]
        }
        noise_sd = plan["stress_noise_sd"]
        if scenario == "finite_hierarchy":
            noise_sd = np.sqrt(plan["noise_prior_scale"] / rng.gamma(plan["noise_prior_shape"]))
            precision = {
                g: float(rng.choice(plan["precision_grid"]))
                for g in ["qb", "offense", "defense", "game"]
            }
            sds = {
                g: noise_sd / np.sqrt(precision["qb" if g == "innovation" else g]) for g in groups
            }
            game = rng.normal(0, noise_sd / np.sqrt(precision["game"]), len(prepared.game_names))
        elif scenario == "continuous_hierarchy":
            sds = plan["stress_effect_sd"]
            game = rng.normal(0, sds["game"], len(prepared.game_names))
        else:
            sds = plan["stress_effect_sd"]
            game = np.zeros(len(prepared.game_names))
        for group, indices in groups.items():
            if scenario == "fixed_year_changes":
                beta[indices] = [
                    sds[group]
                    * (1 if int(sha256(prepared.names[j].encode()).hexdigest(), 16) % 2 else -1)
                    for j in indices
                ]
            else:
                beta[indices] = rng.normal(0, sds[group], len(indices))
        noise = rng.normal(0, noise_sd, prepared.x.shape[0])
        if scenario == "fixed_year_changes":
            noise = (
                noise + rng.normal(0, noise_sd, len(prepared.game_names))[prepared.game_codes]
            ) / np.sqrt(2)
        responses.append(prepared.x @ beta + game[prepared.game_codes] + noise)
        truth.append(beta)
    return np.asarray(truth).T, np.asarray(responses).T


def summary(truth, point, low, high):
    coverage = (low <= truth) & (truth <= high)
    fractions = coverage.mean(axis=0)
    mcse = float(fractions.std(ddof=1) / np.sqrt(len(fractions)))
    error = point - truth
    return {
        "replicates": len(fractions),
        "coverage": float(coverage.mean()),
        "monte_carlo_se": mcse,
        "coverage_by_player": coverage.mean(axis=1).tolist(),
        "rmse_ep": float(np.sqrt(np.mean(error**2))),
        "mean_interval_width_ep": float((high - low).mean()),
        "mean_signed_error_ep": float(error.mean()),
        "mean_absolute_player_bias_ep": float(np.abs(error.mean(axis=1)).mean()),
        "severe_undercoverage": bool(coverage.mean() + 1.96 * mcse < 0.9),
        "passes_admission": False,
    }


def calibration(prepared, contrasts, cells, plan, progress):
    reports = {}
    for scenario in plan["simulation_scenarios"]:
        progress("Calibrating " + scenario)
        beta, y = simulate(prepared, plan, scenario)
        truth = contrasts @ beta
        result = integrate(
            prepared,
            y,
            contrasts,
            cells,
            shape=plan["noise_prior_shape"],
            scale=plan["noise_prior_scale"],
            progress=progress,
        )
        point, _ = moments(result)
        progress("Computing deterministic mixture quantiles: " + scenario)
        bounds = interval(result, iterations=plan["quantile_iterations"])
        modes = np.argmax(result["weights"], axis=0)
        conditional_point = result["location"][modes, :, np.arange(len(modes))].T
        reports[scenario] = {
            "integrated": summary(truth, point, *bounds),
            "modal_cell_control": summary(truth, conditional_point, *modal_interval(result)),
            "posterior_precision_mass_mean": posterior_diagnostics(cells, result["weights"], plan),
            "synthetic_responses_sha256": sha256(y.astype("<f8").tobytes()).hexdigest(),
            "scope": "Fixed-design coverage under the declared generator, conditional on fixed context; not NFL attribution validation or full proper-prior SBC.",
        }
    return reports
