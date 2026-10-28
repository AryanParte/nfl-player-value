"""Bounded, retrospective positional contrasts; no admitted player-value scores."""

from collections import Counter
from math import fsum

import numpy as np

from nfl_value.baseline import actor_features, coappearance, predict, prepare_plays
from nfl_value.contrast_cohorts import exposure_diagnostic, make_cohorts
from nfl_value.contrast_math import (
    SCOPES,
    contrast_vector,
    fit_joint,
    summarize_contrast,
    validate_plan,
)


def evaluate_fit(rows, cohorts, model, covariance):
    """Recenter actor components without redistributing team/context/residual EPA."""
    coefficients = dict(zip(model["features"], model["coefficients"]))
    mean = np.array(model["coefficients"])
    references = {
        role: {
            name: {
                component: fsum(w * coefficients[f"{component}/{p}"] for p, w in weights.items())
                for component in SCOPES[role]
            }
            for name, weights in comparisons.items()
        }
        for role, comparisons in cohorts["weights"].items()
    }
    players = []
    for (role, player), counts in sorted(cohorts["counts"].items()):
        comparisons = {}
        for name, weights in cohorts["weights"].get(role, {}).items():
            vector = contrast_vector(
                model["features"], player=player, counts=counts, weights=weights
            )
            comparisons[name] = summarize_contrast(vector, mean, covariance)
        players.append(
            {
                "player_id": player,
                "role": role,
                "component_opportunities": dict(counts),
                "unique_opportunities": len(cohorts["opportunities"][(role, player)]),
                "comparisons": comparisons or None,
                "main_qualified": False,
            }
        )
    predictions, prediction_audit = predict(model, rows)
    accounting = {}
    for name in ("first_unit", "equal_player", "opportunity_weighted"):
        totals = Counter()
        max_error = 0.0
        for play, prediction in zip(rows, predictions):
            parts = {
                k: v
                for k, v in prediction["components"].items()
                if k not in {"dropback", "carry", "target"}
            }
            parts.update(
                contrast=0.0,
                benchmark_reference=0.0,
                outside_module_actor=0.0,
                residual=prediction["residual"],
            )
            for feature in actor_features(play):
                component, _ = feature.split("/")
                role = cohorts["links"].get((play["game_id"], play["play_id"], feature))
                if role in references:
                    reference = references[role][name][component]
                    parts["contrast"] += coefficients[feature] - reference
                    parts["benchmark_reference"] += reference
                else:
                    parts["outside_module_actor"] += coefficients[feature]
            error = abs(fsum(parts.values()) - play["offense_epa"])
            max_error = max(max_error, error)
            # Counter.update preserves negative values; Counter '+' does not.
            totals.update(parts)
        summed_players = fsum(
            p["comparisons"][name]["contrast_ep"] for p in players if p["comparisons"]
        )
        if max_error > 1e-9 or abs(summed_players - totals["contrast"]) > 1e-8:
            raise ValueError("contrast accounting does not conserve actor components")
        accounting[name] = {
            "totals_ep": dict(totals),
            "max_play_accounting_error": max_error,
            "player_sum_error": abs(summed_players - totals["contrast"]),
            "observed_epa": fsum(p["offense_epa"] for p in rows),
        }
    return {
        "players": players,
        "benchmark_component_means": references,
        "accounting": accounting,
        "prediction_audit": prediction_audit,
    }


def experiment(ledger, evidence, first_units, team_games, *, season, cutoff, plan):
    validate_plan(plan)
    if str(season) not in plan["windows"]:
        raise ValueError("season absent from frozen contrast plan")
    if not team_games or len({(g.game_id, g.team_id) for g in team_games}) != len(team_games):
        raise ValueError("nonempty unique team-game inventory required")
    if any(int(g.game_id[:4]) != season or g.completed_at > cutoff for g in team_games):
        raise ValueError("game outside season or evidence cutoff")
    max_week = max(int(g.game_id.split("_")[1]) for g in team_games)
    if max(plan["windows"][str(season)]) > max_week:
        raise ValueError("declared window exceeds archived game coverage")
    if not plan["allow_retrospective"]:
        raise ValueError("this retrospective experiment requires explicit acknowledgement")
    models, results, summary = {}, {}, {}
    for week in plan["windows"][str(season)]:
        first_unit = first_units[str(week)]
        games = [g for g in team_games if int(g.game_id.split("_")[1]) <= week]
        if {g.team_id for g in games} != {g.team_id for g in team_games}:
            raise ValueError("prefix does not cover the declared season teams")
        # Slice before preparing features, roles or vocabulary. Future rows must
        # not change even the earlier prefix's exclusions or player identities.
        prefix = {**ledger, "plays": [p for p in ledger["plays"] if p["week"] <= week]}
        rows, preparation = prepare_plays(prefix, season=season)
        inventory = {(g.game_id, g.team_id) for g in games}
        if any((p["game_id"], p["offense_team"]) not in inventory for p in rows):
            raise ValueError("modeled play outside completed game inventory")
        if {p["game_id"] for p in rows} != {g.game_id for g in games}:
            raise ValueError("a completed game has no usable model rows")
        cohorts = make_cohorts(rows, evidence, first_unit, games, cutoff=cutoff)
        qualification = [
            {
                "player_id": player,
                "role": role,
                **exposure_diagnostic(
                    player,
                    role,
                    cohorts,
                    evidence,
                    games,
                    season=season,
                    week=week,
                    cutoff=cutoff,
                    multipliers=plan["qualification_multipliers"],
                ),
            }
            for role, player in sorted(cohorts["counts"])
        ]
        fits = {}
        for penalty in plan["actor_penalties"]:
            model, covariance = fit_joint(
                rows, cohorts["candidates"], plan=plan, actor_penalty=penalty
            )
            key = f"week-{week}/penalty-{penalty:g}"
            models[key] = model
            fits[key] = evaluate_fit(rows, cohorts, model, covariance)
        primary = fits[f"week-{week}/penalty-{plan['primary_actor_penalty']:g}"]
        compared = [p for p in primary["players"] if p["comparisons"]]
        summary[str(week)] = {
            "modeled_plays": len(rows),
            "completed_games": len({g.game_id for g in games}),
            "observed_role_players": len(primary["players"]),
            "compared_players": len(compared),
            "benchmark_ready_roles": sorted(cohorts["weights"]),
            "exposure_proven_players": sum(q["denominator_complete"] for q in qualification),
            "participation_qualified_by_multiplier": {
                str(m): sum(
                    q["qualification_grid"] is not None
                    and q["qualification_grid"][str(m)]["participation_qualified"]
                    for q in qualification
                )
                for m in plan["qualification_multipliers"]
            },
            "negative_primary_contrasts": sum(
                p["comparisons"]["first_unit"]["contrast_ep"] < 0 for p in compared
            ),
            "max_benchmark_difference_ep": max(
                (
                    max(c["contrast_ep"] for c in p["comparisons"].values())
                    - min(c["contrast_ep"] for c in p["comparisons"].values())
                    for p in compared
                ),
                default=None,
            ),
            "max_penalty_difference_ep": max(
                (
                    max(
                        f["players"][i]["comparisons"]["first_unit"]["contrast_ep"]
                        for f in fits.values()
                    )
                    - min(
                        f["players"][i]["comparisons"]["first_unit"]["contrast_ep"]
                        for f in fits.values()
                    )
                    for i, p in enumerate(primary["players"])
                    if p["comparisons"]
                ),
                default=None,
            ),
            "main_admitted_players": 0,
        }
        results[str(week)] = {
            "preparation": preparation,
            "coappearance": coappearance(rows),
            "cohorts": cohorts["audit"],
            "benchmark_weights": cohorts["weights"],
            "unsupported_actor_appearances": cohorts["unsupported_actor_appearances"],
            "qualification": qualification,
            "fits": fits,
            "first_unit_assignments": [
                a for a in first_unit["assignments"] if a["game_id"] in {g.game_id for g in games}
            ],
        }
    report = {
        "experiment_kind": "positional-contrast-diagnostics",
        "experiment_version": 1,
        "season": season,
        "evidence_cutoff": cutoff.isoformat(),
        "plan": plan,
        "summary": summary,
        "ranking_ready": False,
        "individual_attribution_validated": False,
        "limitations": [
            "Retrospective within-prefix fits, not historically available weekly publications.",
            "Shared team/context and residual outcomes are not reassigned to individuals.",
            "Conditional Gaussian intervals are not calibrated NFL confidence intervals.",
            "Observed role indicators may adjust away player-created opportunity value.",
            "Full single-team observed participation is a selected, incomplete eligibility sample.",
            "No defense, offensive line or other unsupported position receives an invented contrast.",
            "No cross-position or causal interpretation is validated; all main admissions remain false.",
        ],
    }
    return report, models, results
