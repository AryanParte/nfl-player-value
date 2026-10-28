"""Bounded simulation on a verified archived joint design and first-unit contrasts."""

import numpy as np

from nfl_value.baseline import design
from nfl_value.calibration_math import (
    alias_diagnostics,
    evaluate,
    groups,
    operator,
    penalty_vector,
    simulate,
    summarize,
    validate_plan,
)
from nfl_value.contrast_math import SCOPES, contrast_vector
from nfl_value.ingestion import json_bytes, sha256


def experiment(rows, upstream, model, window, *, plan):
    validate_plan(plan)
    season = upstream["season"]
    week = plan["windows"][str(season)]
    if (
        upstream["plan"]["actor_penalties"] != plan["actor_penalties"]
        or upstream["plan"]["primary_actor_penalty"] != plan["primary_actor_penalty"]
        or model["actor_penalty"] != plan["primary_actor_penalty"]
    ):
        raise ValueError("calibration must preserve the upstream penalty grid")
    if (
        not rows
        or any(p["week"] > week or not p["game_id"].startswith(f"{season}_") for p in rows)
        or model["training_rows_sha256"] != sha256(json_bytes({"plays": rows}))
        or model["training_games"] != sorted({p["game_id"] for p in rows})
        or model["training_plays"] != len(rows)
    ):
        raise ValueError("calibration design differs from archived prefix")
    names = model["features"]
    x, _, unseen = design(rows, "joint", names)
    if unseen or len(names) != len(set(names)):
        raise ValueError("incomplete or duplicate calibration features")
    weights = window["benchmark_weights"]
    if set(weights) != set(SCOPES):
        raise ValueError("all four complete first-unit populations required")
    players = window["fits"][f"week-{week}/penalty-{plan['primary_actor_penalty']:g}"]["players"]
    identities = [(p["role"], p["player_id"]) for p in players]
    if not players or len(identities) != len(set(identities)):
        raise ValueError("nonempty unique role-player contrasts required")
    if any(p["role"] not in SCOPES or not p["comparisons"] for p in players):
        raise ValueError("calibration cannot omit unsupported comparisons")
    contrasts = np.stack(
        [
            contrast_vector(
                names,
                player=p["player_id"],
                counts=p["component_opportunities"],
                weights=weights[p["role"]]["first_unit"],
            )
            for p in players
        ]
    )
    metadata = [
        {k: p[k] for k in ("player_id", "role", "component_opportunities", "unique_opportunities")}
        for p in players
    ]
    game_indices = groups([p["game_id"] for p in rows])
    team_indices = groups([p["offense_team"] for p in rows])
    penalties = {
        penalty: penalty_vector(
            names,
            actor=penalty,
            context=upstream["plan"]["context_penalty"],
            team=upstream["plan"]["team_penalty"],
        )
        for penalty in plan["actor_penalties"]
    }
    operators = {p: operator(x, contrasts, d) for p, d in penalties.items()}
    aliases = alias_diagnostics(x, names, contrasts, shift=plan["alias_shift_ep_per_component"])
    diagnostics = {
        "design_rows_sha256": model["training_rows_sha256"],
        "features": names,
        "contrast_order": metadata,
        "alias_diagnostics": aliases,
        "benchmark_weights": {role: weights[role]["first_unit"] for role in SCOPES},
        "observed_outcomes_used_to_generate_truth": False,
    }
    selections = {"overall": np.arange(len(players))}
    selections.update(
        {role: np.array([i for i, p in enumerate(players) if p["role"] == role]) for role in SCOPES}
    )
    if any(not len(indices) for indices in selections.values()):
        raise ValueError("each declared role needs observed contrasts")
    results, summaries = {}, {}
    for scenario_index, scenario in enumerate(plan["scenarios"]):
        noise_indices = game_indices if scenario["noise_group"] == "game" else team_indices
        beta, y = simulate(
            x,
            names,
            penalties[plan["primary_actor_penalty"]],
            plan=plan,
            season=season,
            week=week,
            scenario_index=scenario_index,
            noise_groups=noise_indices,
        )
        for penalty, op in operators.items():
            error, bias, widths, covered = evaluate(
                x,
                contrasts,
                op,
                beta,
                y,
                game_indices=game_indices,
                noise_indices=noise_indices,
                noise_sd=plan["noise_sd"],
                fraction=scenario["correlated_fraction"],
            )

            def summary(indices):
                return summarize(
                    error[indices],
                    bias[indices],
                    {k: v[indices] for k, v in widths.items()},
                    {k: v[indices] for k, v in covered.items()},
                    failure_bound=plan["severe_undercoverage_bound"],
                )

            key = f"{scenario['name']}/penalty-{penalty:g}"
            summaries[key] = {role: summary(indices) for role, indices in selections.items()}
            results[key] = {
                "groups": summaries[key],
                "players": [{**p, **summary([i])} for i, p in enumerate(metadata)],
            }
    report = {
        "experiment_kind": "known-effect-calibration",
        "experiment_version": 1,
        "season": season,
        "week": week,
        "plan": plan,
        "evidence_cutoff": upstream["evidence_cutoff"],
        "game_cohort_cutoff": upstream["game_cohort_cutoff"],
        "source_attribution": upstream["source_attribution"],
        "historical_availability": upstream["historical_availability"],
        "summary": {
            "modeled_plays": len(rows),
            "completed_games": len(game_indices),
            "compared_role_players": len(players),
            "features": len(names),
            "observed_alias_pairs": aliases["observed_alias_pairs"],
            "prior_only_actor_columns": aliases["prior_only_columns"],
            "synthetic_response_fits": plan["replicates"] * len(plan["scenarios"]) * len(penalties),
            "scenarios": summaries,
        },
        "ranking_ready": False,
        "individual_attribution_validated": False,
        "outcomes": "synthetic-known-truth-on-archived-design",
    }
    return report, diagnostics, results
