"""Required rich/degraded defensive design diagnosis, never positional scores."""

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from nfl_value.defensive_model import design, prepare_pair, weights_target
from nfl_value.variance_mixture import integrate, moments, system


def diagnose(rich, degraded, plan, progress=lambda _: None):
    plays, aggregates = prepare_pair(rich, degraded, season=plan["scoring_season"] - 1)
    reports = {}
    for view, all_rows in [("rich_play_lineups", plays), ("degraded_team_games", aggregates)]:
        rows = [p for p in all_rows if p["week"] <= plan["defense_through_week"]]
        progress("Diagnosing defense: " + view)
        x, original, _ = design(rows, view, "defender")
        order = [original.index("context/intercept")] + [
            j for j, n in enumerate(original) if n != "context/intercept"
        ]
        names = [original[j] for j in order]
        x = x[:, order]
        weights, target = weights_target(rows, view)
        prepared = system(x.multiply(np.sqrt(weights)[:, None]).tocsr(), names, 1)
        y = target * np.sqrt(weights)
        players = [j for j, n in enumerate(names) if n.startswith("defender/")]
        contrasts = np.zeros((len(players), len(names)))
        contrasts[:, players] = np.eye(len(players)) - 1 / len(players)
        eig, vectors = np.linalg.eigh(prepared.gram)
        null = vectors[:, eig <= max(eig.max(), 1.0) * plan["null_relative_cutoff"]]
        projection = np.linalg.norm(contrasts @ null, axis=1) / np.linalg.norm(contrasts, axis=1)
        # Residualized rank isolates what lineups add beyond unregularized
        # context/team columns. It is not recovered by shrinking those columns.
        nuisance = [j for j in range(len(names)) if j not in players]
        g = prepared.gram
        residual_gram = (
            g[np.ix_(players, players)]
            - g[np.ix_(players, nuisance)]
            @ np.linalg.pinv(g[np.ix_(nuisance, nuisance)], rcond=plan["null_relative_cutoff"])
            @ g[np.ix_(nuisance, players)]
        )
        residual_eigen = np.linalg.eigvalsh(residual_gram)
        rank = int(
            np.sum(residual_eigen > max(residual_eigen.max(), 1.0) * plan["null_relative_cutoff"])
        )
        cells, effective_dimensions = [], []
        for precision in plan["precision_grid"]:
            penalty = np.array(
                [
                    0.0
                    if j == 0
                    else precision
                    if n.startswith("defender/")
                    else plan["defense_context_precision"]
                    if n.startswith("context/")
                    else plan["defense_team_precision"]
                    for j, n in enumerate(names)
                ]
            )
            cells.append(
                {
                    "penalty": penalty,
                    "game_precision": None,
                    "log_prior": -np.log(len(plan["precision_grid"])),
                }
            )
            inverse = cho_solve(cho_factor(g + np.diag(penalty), lower=True), np.eye(len(names)))
            effective_dimensions.append(float(np.sum(1 - precision * np.diag(inverse)[players])))
        fit = integrate(
            prepared,
            y,
            contrasts,
            cells,
            shape=plan["noise_prior_shape"],
            scale=plan["noise_prior_scale"],
        )
        point, _ = moments(fit)
        selected = int(np.argmax(projection))
        witness = null @ (null.T @ contrasts[selected])
        if np.max(np.abs(witness)) > 0:
            witness *= 0.25 / np.max(np.abs(witness))
        reports[view] = {
            "rows": len(rows),
            "games": len({p["game_id"] for p in rows}),
            "weighted_plays": int(weights.sum()),
            "players": len(players),
            "columns": len(names),
            "full_design_rank": len(names) - null.shape[1],
            "residualized_defender_rank": rank,
            "nonestimable_mean_contrasts": int(np.sum(projection > 1e-7)),
            "max_null_projection": float(projection.max()),
            "null_witness": {
                "max_row_prediction_change_ep": float(np.max(np.abs(x @ witness))),
                "max_contrast_change_ep_per_appearance": float(np.max(np.abs(contrasts @ witness))),
            },
            "precision_grid": plan["precision_grid"],
            "posterior_precision_mass": fit["weights"][:, 0].tolist(),
            "regularized_defender_effective_dimensions": effective_dimensions,
            "max_contrast_range_across_precisions_ep_per_appearance": float(
                np.ptp(fit["location"][:, :, 0], axis=0).max()
            ),
            "integrated_mean_contrast_range_ep_per_appearance": [
                float(point.min()),
                float(point.max()),
            ],
            "ranking_ready": False,
            "scope": "Defender minus unweighted cohort mean is an identifiability diagnostic, not first-unit positional CAVAA. Rich/degraded likelihoods have different observational units; evidence weights are not compared across views. No defensive uncertainty calibration claimed.",
        }
    if (
        reports["rich_play_lineups"]["weighted_plays"]
        != reports["degraded_team_games"]["weighted_plays"]
    ):
        raise ValueError("defensive diagnostic population changed across views")
    return reports
