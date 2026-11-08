"""Fresh fixed-design recovery trials; no observed EPA determines simulated truth."""

from hashlib import sha256

import numpy as np

from nfl_value.qb_math import fit

Z95 = 1.959963984540054


def fixed_truth(prepared, plan):
    truth = np.zeros(len(prepared.names))
    for j, name in enumerate(prepared.names):
        group = name.split("/")[0]
        magnitude = (
            0.1
            if group == "context"
            else 0
            if group == "game"
            else plan["simulation_effect_sd"][group]
        )
        sign = 1 if int(sha256(name.encode()).hexdigest(), 16) % 2 else -1
        truth[j] = magnitude * sign
    return truth


def simulate(prepared, plan, *, scenario, replicate):
    if scenario not in plan["scenarios"] or not 0 <= replicate < plan["simulation_replicates"]:
        raise ValueError("undeclared simulation cell")
    rng = np.random.default_rng(
        [plan["simulation_seed"], plan["scenarios"].index(scenario), replicate]
    )
    truth = fixed_truth(prepared, plan)
    if scenario == "matched_hierarchy":
        for group, indices in zip(prepared.groups, prepared.group_indices):
            truth[indices] = rng.normal(0, plan["simulation_effect_sd"][group], len(indices))
    noise = rng.normal(0, plan["simulation_noise_sd"], len(prepared.x))
    if scenario == "fixed_game_dependence":
        game_indices = prepared.group_indices[prepared.groups.index("game")]
        shared = prepared.x[:, game_indices] @ rng.normal(
            0, plan["simulation_noise_sd"], len(game_indices)
        )
        noise = (noise + shared) / np.sqrt(2)
    y = prepared.x @ truth + noise
    return truth, y


def summarize(errors, widths, *, replicates, failures):
    if not errors:
        return {
            "successful_replicates": 0,
            "requested_replicates": replicates,
            "failures": failures,
            "valid_for_decision": False,
        }
    errors, widths = np.asarray(errors), np.asarray(widths)
    coverage = np.abs(errors) <= widths / 2
    fractions = coverage.mean(axis=1)
    mcse = (
        float(np.std(fractions, ddof=1) / np.sqrt(len(fractions))) if len(fractions) > 1 else None
    )
    mean_coverage = float(coverage.mean())
    return {
        "successful_replicates": len(errors),
        "requested_replicates": replicates,
        "failures": failures,
        "valid_for_decision": not failures,
        "coverage": mean_coverage,
        "monte_carlo_se": mcse,
        "mean_interval_width_ep": float(widths.mean()),
        "rmse_ep": float(np.sqrt(np.mean(errors**2))),
        "mean_signed_error_ep": float(errors.mean()),
        "mean_absolute_player_bias_ep": float(np.abs(errors.mean(axis=0)).mean()),
        "coverage_by_player": coverage.mean(axis=0).tolist(),
        "severe_undercoverage": mcse is not None and mean_coverage + 1.96 * mcse < 0.9,
        "passes_admission": False,
    }


def calibration(prepared, contrasts, plan, *, progress=lambda message: None):
    results = {}
    for scenario in plan["scenarios"]:
        cells = {
            name: {
                "errors": [],
                "widths": [],
                "failures": [],
                "boundary_counts": {g: 0 for g in prepared.groups},
            }
            for name in ("joint", "fixed_precision")
        }
        digest = sha256()
        for replicate in range(plan["simulation_replicates"]):
            truth, y = simulate(prepared, plan, scenario=scenario, replicate=replicate)
            digest.update(truth.astype("<f8").tobytes())
            digest.update(y.astype("<f8").tobytes())
            target = contrasts @ truth
            for name, cell in cells.items():
                try:
                    model, covariance = fit(prepared, y, plan, fixed=name == "fixed_precision")
                    variance = np.einsum("ij,jk,ik->i", contrasts, covariance, contrasts)
                    if not np.isfinite(variance).all() or np.min(variance) < -1e-9:
                        raise ValueError("invalid simulated contrast variance")
                    error = contrasts @ np.array(model["coefficients"]) - target
                    cell["errors"].append(error)
                    cell["widths"].append(2 * Z95 * np.sqrt(np.maximum(variance, 0)))
                    for group in model["boundary_groups"]:
                        cell["boundary_counts"][group] += 1
                except (ValueError, np.linalg.LinAlgError) as exc:
                    cell["failures"].append({"replicate": replicate, "reason": str(exc)})
            if (replicate + 1) % 8 == 0:
                progress(
                    f"{scenario}: {replicate + 1}/{plan['simulation_replicates']} recovery trials"
                )
        results[scenario] = {
            name: {
                **summarize(
                    cell["errors"],
                    cell["widths"],
                    replicates=plan["simulation_replicates"],
                    failures=cell["failures"],
                ),
                "boundary_replicates": cell["boundary_counts"],
            }
            for name, cell in cells.items()
        }
        results[scenario]["synthetic_truth_response_sha256"] = digest.hexdigest()
    return {
        "unit": "cumulative first-unit QB dropback expected-point contrast",
        "player_order": [
            n.split("/")[1]
            for n in prepared.names
            if n.startswith("qb/") and np.any(prepared.x[:, prepared.names.index(n)])
        ],
        "uncertainty": "empirical-Bayes conditional; hyperparameters reestimated in each simulated replicate",
        "monte_carlo_unit": "independent replicate, not correlated player cells",
        "scenarios": results,
        "ranking_ready": False,
    }
