"""Frozen multi-season recovery; research estimates cannot enter a leaderboard."""

from collections import Counter
import json

import numpy as np
from scipy.special import logsumexp

from nfl_value.baseline import prepare_plays
from nfl_value.contrast_cohorts import exposure_diagnostic, make_cohorts
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.multiseason_math import allocation_witness, contrast, design, identification
from nfl_value.multiseason_math import matrix, posterior_diagnostics, validate_plan, variance_cells
from nfl_value.multiseason_simulation import calibration
from nfl_value.qb_math import row_digest
from nfl_value.qb_recovery import prepare
from nfl_value.source_audit import aware_time
from nfl_value.variance_mixture import integrate, interval, moments


def predict(model, rows):
    """Frozen coefficients; new players/teams get their zero population mean.

    Unseen exposure is recorded and retained. New-game random intercepts are zero;
    evaluating a future week never refits variance weights or expands vocabulary.
    """
    x, unseen = matrix(rows, model["names"], model["variant"])
    predictions = x @ np.asarray(model["coefficients"])
    training_games = set(model["training_games"])
    if any(p["game_id"] in training_games for p in rows):
        raise ValueError("future evaluation overlaps fitting games")
    if any(
        aware_time(p["scheduled_kickoff"]) <= aware_time(model["last_training_kickoff"])
        for p in rows
    ):
        raise ValueError("future evaluation violates chronological separation")
    window = model["future_test"]
    if any(
        int(p["game_id"][:4]) != window["season"] or p["week"] not in window["weeks"] for p in rows
    ):
        raise ValueError("rows outside the reserved future evaluation window")
    return [
        dict(
            game_id=p["game_id"],
            play_id=p["play_id"],
            observed_epa=p["offense_epa"],
            predicted_epa=float(predictions[i]),
        )
        for i, p in enumerate(rows)
    ], unseen


def accounting(prepared, fit, rows, current, benchmark_weights, season):
    beta = fit["coefficient_mean"]
    game_effects = dict(zip(prepared.game_names, fit["game_mean"]))
    index = {n: i for i, n in enumerate(prepared.names)}

    def qb_effect(player):
        return sum(
            beta[index[key]]
            for key in ["qb/" + player, f"innovation/{season}/{player}"]
            if key in index
        )

    benchmark = sum(weight * qb_effect(p) for p, weight in benchmark_weights.items())
    components = {
        group: prepared.x[:, [j for j, n in enumerate(prepared.names) if n.startswith(group + "/")]]
        @ beta[[j for j, n in enumerate(prepared.names) if n.startswith(group + "/")]]
        for group in ["context", "qb", "innovation", "offense", "defense"]
    }
    selected = {(p["game_id"], p["play_id"]) for p in current}
    output, error = [], 0.0
    for i, p in enumerate(rows):
        if (p["game_id"], p["play_id"]) not in selected:
            continue
        values = {g: float(values[i]) for g, values in components.items()}
        values["game"] = float(game_effects[p["game_id"]])
        residual = p["offense_epa"] - sum(values.values())
        above = values["qb"] + values["innovation"] - benchmark
        total = (
            above
            + benchmark
            + sum(v for g, v in values.items() if g not in {"qb", "innovation"})
            + residual
        )
        error = max(error, abs(total - p["offense_epa"]))
        output.append(
            {
                "game_id": p["game_id"],
                "play_id": p["play_id"],
                "qb": p["qb"],
                "observed_epa": p["offense_epa"],
                "components": values,
                "residual": float(residual),
                "qb_above_first_unit": float(above),
                "benchmark_component": float(benchmark),
            }
        )
    if error > 1e-9 or len(output) != len(current):
        raise ValueError("current-season nonduplicated play accounting failed")
    return output, error


def experiment(datasets, first_unit, *, cutoff, plan, progress=lambda _: None):
    validate_plan(plan)
    if set(datasets) != set(plan["seasons"]):
        raise ValueError("all and only frozen seasons required")
    season = plan["scoring_season"]
    rows, audits = [], {}
    for year in plan["seasons"]:
        ledger, evidence, _, _ = datasets[year]
        selected, audits[str(year)] = prepare(
            ledger, evidence, season=year, low_week=1, high_week=18
        )
        if year == season and any(p["week"] >= min(plan["future_test"]["weeks"]) for p in selected):
            raise ValueError("training archive reaches the reserved future window")
        rows.extend(selected)
    rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
    current = [p for p in rows if p["game_id"].startswith(f"{season}_")]
    ledger, evidence, games, _ = datasets[season]
    all_current, _ = prepare_plays(ledger, season=season)
    cohorts = make_cohorts(current, evidence, first_unit, games, cutoff=cutoff)
    qualification = make_cohorts(all_current, evidence, first_unit, games, cutoff=cutoff)
    if "QB" not in cohorts["weights"]:
        raise ValueError("complete first-unit QB benchmark required")
    weights = cohorts["weights"]["QB"]
    counts = Counter(p["qb"] for p in current)
    players = sorted(counts)
    models, evaluations, estimates, play_ledgers = {}, {}, {}, {}
    primary_design = primary_contrasts = primary_cells = None
    for variant in plan["variants"]:
        progress("Fitting frozen multi-season variant: " + variant)
        prepared, dropped = design(
            rows, variant, scoring_season=season, extra_qbs=cohorts["candidates"]["QB"]
        )
        matrices = (
            {
                name: np.array(
                    [contrast(prepared.names, p, counts[p], w, season=season) for p in players]
                )
                for name, w in weights.items()
            }
            if variant != "team"
            else {}
        )
        names = list(matrices)
        combined = (
            np.vstack(list(matrices.values())) if matrices else np.zeros((1, len(prepared.names)))
        )
        cells = variance_cells(prepared, variant, plan)
        fit = integrate(
            prepared,
            [p["offense_epa"] for p in rows],
            combined,
            cells,
            shape=plan["noise_prior_shape"],
            scale=plan["noise_prior_scale"],
            progress=progress,
        )
        point, _ = moments(fit)
        bounds = interval(fit, iterations=plan["quantile_iterations"])
        model = {
            "variant": variant,
            "names": prepared.names,
            "coefficients": fit["coefficient_mean"].tolist(),
            "game_coefficients": dict(zip(prepared.game_names, fit["game_mean"].tolist())),
            "dropped_context": dropped,
            "precision_cells": [c["precision"] for c in cells],
            "posterior_cell_weights": fit["weights"][:, 0].tolist(),
            "training_rows_sha256": row_digest(rows),
            "training_games": prepared.game_names,
            "last_training_kickoff": max(p["scheduled_kickoff"] for p in rows),
            "future_test": plan["future_test"],
            "ranking_ready": False,
        }
        models[variant] = model
        evaluations[variant] = {
            "training_rows": len(rows),
            "training_games": len(prepared.game_names),
            "posterior_precision_mass": posterior_diagnostics(cells, fit["weights"], plan),
            "future_evaluation": "Pending uninspected Week 10 outcomes; no predictive pass claimed.",
        }
        if not matrices:
            continue
        values = []
        for i, p in enumerate(players):
            benchmarks = {
                name: {
                    "expected_points": float(point[j * len(players) + i, 0]),
                    "integrated_95_interval": [float(b[j * len(players) + i, 0]) for b in bounds],
                }
                for j, name in enumerate(names)
            }
            game_counts = Counter(row["game_id"] for row in current if row["qb"] == p)
            ledger = [
                {
                    "game_id": g,
                    "week": int(g.split("_")[1]),
                    "opportunities": n,
                    "expected_points": benchmarks["first_unit"]["expected_points"] * n / counts[p],
                }
                for g, n in sorted(game_counts.items())
            ]
            if not np.isclose(
                sum(g["expected_points"] for g in ledger),
                benchmarks["first_unit"]["expected_points"],
                atol=1e-9,
                rtol=0,
            ):
                raise ValueError("cumulative current-season ledger mismatch")
            values.append(
                {
                    "player_id": p,
                    "scope": "observed_dropbacks_only",
                    "season": season,
                    "opportunities": counts[p],
                    "games": len(game_counts),
                    "benchmarks": benchmarks,
                    "game_ledger": ledger,
                    "ranking_ready": False,
                    "qualification": exposure_diagnostic(
                        p,
                        "QB",
                        qualification,
                        evidence,
                        games,
                        season=season,
                        week=max(row["week"] for row in current),
                        cutoff=cutoff,
                        multipliers=[0.75, 1.0, 1.25],
                    ),
                }
            )
        estimates[variant] = values
        play_ledgers[variant], error = accounting(
            prepared, fit, rows, current, weights["first_unit"], season
        )
        evaluations[variant]["max_accounting_error_ep"] = error
        # The public contrast sum must equal the single QB contribution ledger.
        if not np.isclose(
            sum(v["benchmarks"]["first_unit"]["expected_points"] for v in values),
            sum(p["qb_above_first_unit"] for p in play_ledgers[variant]),
            atol=1e-8,
            rtol=0,
        ):
            raise ValueError("player totals duplicate or omit current-season contribution")
        if variant in {"evolving", "persistent"}:
            evaluations[variant]["identification"] = identification(
                prepared, matrices["first_unit"], plan["null_relative_cutoff"]
            )
            evaluations[variant]["allocation_witness"] = allocation_witness(
                prepared, rows, matrices["first_unit"], evolving=variant == "evolving"
            )
        if variant == "evolving":
            primary_design, primary_contrasts, primary_cells = (
                prepared,
                matrices["first_unit"],
                cells,
            )
            sensitivity = []
            for tilt in plan["prior_qb_precision_tilts"]:
                # Reweight the declared prior, not intervals or inspected scores.
                log_weights = (
                    np.where(
                        fit["weights"] > 0,
                        np.log(np.maximum(fit["weights"], np.finfo(float).tiny)),
                        -np.inf,
                    )
                    + tilt * np.log([c["precision"]["qb"] for c in cells])[:, None]
                )
                changed_weights = np.exp(log_weights - logsumexp(log_weights, axis=0))
                changed, _ = moments(fit, changed_weights)
                difference = changed[: len(players), 0] - point[: len(players), 0]
                sensitivity.append(
                    {
                        "qb_precision_prior_power": tilt,
                        "max_absolute_contrast_change_ep": float(np.max(np.abs(difference))),
                        "median_absolute_contrast_change_ep": float(np.median(np.abs(difference))),
                        "player_changes_ep": dict(zip(players, difference.tolist())),
                    }
                )
            evaluations[variant]["prior_sensitivity"] = sensitivity
    progress("Running fresh fixed-design uncertainty trials")
    trials = calibration(primary_design, primary_contrasts, primary_cells, plan, progress)
    report = {
        "experiment": "multiseason-variance-recovery-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "cohort_audits": audits,
        "evaluation": evaluations,
        "calibration": trials,
        "season": {
            "season": season,
            "games": len({p["game_id"] for p in current}),
            "plays": len(current),
            "players": len(players),
            "benchmark_weights": weights,
            "benchmark_audit": cohorts["audit"]["QB"],
            "qualification_denominators_complete": sum(
                v["qualification"]["denominator_complete"] for v in estimates["evolving"]
            ),
            "negative_player_estimates": sum(
                v["benchmarks"]["first_unit"]["expected_points"] < 0 for v in estimates["evolving"]
            ),
            "historical_opportunities_in_scoring_total": 0,
            "ranking_ready": False,
        },
        "decision": "Research only. Fresh predictive evidence, substantive attribution and cross-position comparability remain unproven. Simulation coverage is conditional on the declared generators.",
        "ranking_ready": False,
    }
    return (
        report,
        models,
        json.loads(json_bytes({"estimates": estimates, "play_ledgers": play_ledgers})),
    )
