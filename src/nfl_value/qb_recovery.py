"""Bounded QB dropback recovery: held-out prediction and cumulative research contrasts."""

from collections import Counter, defaultdict
from math import isfinite
import json

import numpy as np

from nfl_value.baseline import metrics, paired_rmse_interval, prepare_plays
from nfl_value.contrast_cohorts import exposure_diagnostic, make_cohorts
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.qb_math import (
    GROUPS,
    RestrictedLikelihood,
    contrast,
    design,
    fit,
    identification,
    predict,
    row_digest,
)
from nfl_value.source_audit import aware_time

PLAN_KEYS = set(
    "plan_version historical_season train_through_week validation_through_week test_through_week current_season transfer_train_through_week variants primary variance_ratio_bounds optimizer_starts optimizer_max_iterations optimizer_ftol fixed_penalties bootstrap_replicates simulation_replicates simulation_seed simulation_noise_sd simulation_effect_sd scenarios sensitivity_qb_variance_multipliers allow_retrospective".split()
)
SCENARIOS = ["matched_hierarchy", "fixed_iid", "fixed_game_dependence"]


def validate_plan(plan):
    if set(plan) != PLAN_KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported QB recovery plan")
    ints = [
        "historical_season",
        "current_season",
        "train_through_week",
        "validation_through_week",
        "test_through_week",
        "transfer_train_through_week",
        "optimizer_max_iterations",
        "bootstrap_replicates",
        "simulation_replicates",
        "simulation_seed",
    ]
    if any(type(plan[k]) is not int or plan[k] < 1 for k in ints):
        raise ValueError("positive integer plan fields required")
    if not (
        1999 <= plan["historical_season"] < plan["current_season"] <= 2100
        and 1
        <= plan["train_through_week"]
        < plan["validation_through_week"]
        < plan["test_through_week"]
        <= 18
        and 1 <= plan["transfer_train_through_week"] < 18
    ):
        raise ValueError("invalid chronological recovery plan")
    if (
        plan["variants"] != list(GROUPS)
        or plan["primary"] != "joint"
        or plan["scenarios"] != SCENARIOS
        or plan["allow_retrospective"] is not True
    ):
        raise ValueError("unreviewed recovery policies")
    if set(plan["fixed_penalties"]) != set(GROUPS["joint"]) or set(
        plan["simulation_effect_sd"]
    ) != set(GROUPS["joint"]):
        raise ValueError("variance component policy mismatch")
    bounds, starts = plan["variance_ratio_bounds"], plan["optimizer_starts"]
    values = [
        *bounds,
        *starts,
        plan["optimizer_ftol"],
        plan["simulation_noise_sd"],
        *plan["fixed_penalties"].values(),
        *plan["simulation_effect_sd"].values(),
        *plan["sensitivity_qb_variance_multipliers"],
    ]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v <= 0
        for v in values
    ):
        raise ValueError("finite positive numerical settings required")
    if (
        len(bounds) != 2
        or not bounds[0] < bounds[1]
        or not starts
        or len(set(starts)) != len(starts)
        or any(not bounds[0] <= v <= bounds[1] for v in starts)
    ):
        raise ValueError("invalid variance search bounds/starts")
    if (
        plan["optimizer_ftol"] >= 1
        or not 2 <= plan["simulation_replicates"] <= 1024
        or not 2 <= plan["bootstrap_replicates"] <= 10000
        or plan["sensitivity_qb_variance_multipliers"] != [0.5, 2.0]
    ):
        raise ValueError("invalid recovery experiment sizes or sensitivity policy")


def prepare(ledger, evidence, *, season, low_week, high_week):
    """Slice before constructing model features. Never use later-week roster roles."""
    selected = [p for p in ledger["plays"] if low_week <= p["week"] <= high_week]
    rows, audit = prepare_plays({**ledger, "plays": selected}, season=season)
    roster = {}
    selected_games = {p["game_id"] for p in selected}
    for record in evidence["player_games"]:
        if record["game_id"] not in selected_games:
            continue
        key = (record["player_id"], record["game_id"], record["team"])
        if key in roster:
            raise ValueError("duplicate roster player/game/team evidence")
        roster[key] = record
    output, exclusions = [], Counter()
    for row in rows:
        if row["event_kind"] not in {"pass", "sack", "scramble"}:
            exclusions["outside_dropback_scope"] += 1
            continue
        qb = row["actors"]["dropback"]
        if row["issues"] or qb is None:
            exclusions["ambiguous_or_missing_dropback_identity"] += 1
            continue
        record = roster.get((qb, row["game_id"], row["offense_team"]))
        if not record or record["issues"] or record["source_position_role"] is None:
            exclusions["unresolved_weekly_roster_identity"] += 1
            continue
        if record["source_position_role"] != "QB":
            exclusions["non_qb_dropback"] += 1
            continue
        output.append({**row, "qb": qb, "actors": {"dropback": qb, "rusher": None, "target": None}})
    expected = {
        (p["game_id"], team) for p in selected for team in (p["offense_team"], p["defense_team"])
    }
    observed = {(p["game_id"], p["offense_team"]) for p in output}
    missing = sorted(expected - observed)
    if not output or missing:
        raise ValueError(f"QB observations missing from completed team games: {missing}")
    return output, {
        **audit,
        "dropback_exclusions": dict(sorted(exclusions.items())),
        "modeled_dropbacks": len(output),
        "modeled_games": len({p["game_id"] for p in output}),
        "modeled_team_games": len(observed),
        "rows_sha256": row_digest(output),
    }


def held_out(train, test, plan, *, seed, progress):
    if max(aware_time(p["scheduled_kickoff"]) for p in train) >= min(
        aware_time(p["scheduled_kickoff"]) for p in test
    ):
        raise ValueError("training and held-out chronology overlaps")
    models, predictions, evaluation = {}, {}, {}
    for variant in plan["variants"]:
        progress(f"Fitting {variant}: {len(train)} train / {len(test)} held-out plays")
        prepared = design(train, variant)
        model, _ = fit(
            prepared, [p["offense_epa"] for p in train], plan, fixed=variant == "fixed_precision"
        )
        model["training_rows_sha256"] = row_digest(train)
        model["training_games"] = sorted({p["game_id"] for p in train})
        predictions[variant], unseen = predict(model, test)
        models[variant] = model
        evaluation[variant] = {**metrics(predictions[variant]), "unseen_appearances": unseen}
    for variant in plan["variants"]:
        if variant != "team":
            evaluation[variant]["against_team"] = paired_rmse_interval(
                predictions[variant],
                predictions["team"],
                seed=seed,
                replicates=plan["bootstrap_replicates"],
            )
    return evaluation, models, predictions


def allocation_witness(prepared, rows, contrasts):
    """Connected QB/offense groups permit a common shift with no fitted-play change."""
    adjacency = defaultdict(set)
    for p in rows:
        a, b = "qb/" + p["qb"], "offense/" + p["offense_team"]
        adjacency[a].add(b)
        adjacency[b].add(a)
    visited, cases = set(), []
    for start in sorted(adjacency):
        if start in visited:
            continue
        pending, component = [start], set()
        while pending:
            node = pending.pop()
            if node in component:
                continue
            component.add(node)
            pending.extend(adjacency[node] - component)
        visited.update(component)
        shift = np.array(
            [
                0.25 if n in component and n.startswith("qb/") else -0.25 if n in component else 0
                for n in prepared.names
            ]
        )
        effect = contrasts @ shift
        cases.append(
            {
                "features": sorted(component),
                "shift_per_dropback_ep": 0.25,
                "max_prediction_change_ep": float(np.max(np.abs(prepared.x @ shift))),
                "max_absolute_contrast_change_ep": float(np.max(np.abs(effect))),
            }
        )
    return {
        "connected_components": len(cases),
        "example": max(cases, key=lambda c: c["max_absolute_contrast_change_ep"]),
        "meaning": "QB-versus-team allocations differ under identical play predictions; independent random-effects assumptions select one allocation.",
    }


def season_estimates(rows, all_rows, evidence, first_unit, games, *, season, cutoff, plan):
    cohorts = make_cohorts(rows, evidence, first_unit, games, cutoff=cutoff)
    if "QB" not in cohorts["weights"]:
        raise ValueError(f"Incomplete first-unit QB benchmark: {cohorts['audit']['QB']}")
    qualification = make_cohorts(all_rows, evidence, first_unit, games, cutoff=cutoff)
    prepared = design(rows, "joint", extra_qbs=cohorts["candidates"]["QB"])
    model, covariance = fit(prepared, [p["offense_epa"] for p in rows], plan)
    model["training_rows_sha256"] = row_digest(rows)
    model["training_games"] = sorted({p["game_id"] for p in rows})
    predictions, _ = predict(model, rows)
    counts = Counter(p["qb"] for p in rows)
    players = sorted(counts)
    weights = cohorts["weights"]["QB"]
    matrices = {
        name: np.array([contrast(prepared.names, p, counts[p], w) for p in players])
        for name, w in weights.items()
    }
    l = matrices["first_unit"]
    beta = np.array(model["coefficients"])
    diagnostics = identification(prepared, l)
    results = []
    for i, player in enumerate(players):
        values = {}
        for name, matrix in matrices.items():
            estimate = float(matrix[i] @ beta)
            variance = float(matrix[i] @ covariance @ matrix[i])
            if variance < -1e-10:
                raise ValueError("negative contrast variance")
            half = 1.959963984540054 * np.sqrt(max(variance, 0))
            values[name] = {
                "expected_points": estimate,
                "conditional_95_interval": [float(estimate - half), float(estimate + half)],
            }
        game_counts = Counter(p["game_id"] for p in rows if p["qb"] == player)
        weekly = [
            {
                "game_id": g,
                "week": int(g.split("_")[1]),
                "opportunities": n,
                "expected_points": float(
                    contrast(prepared.names, player, n, weights["first_unit"]) @ beta
                ),
            }
            for g, n in sorted(game_counts.items())
        ]
        if not np.isclose(
            sum(w["expected_points"] for w in weekly),
            values["first_unit"]["expected_points"],
            atol=1e-9,
            rtol=0,
        ):
            raise ValueError("cumulative QB ledger mismatch")
        results.append(
            {
                "player_id": player,
                "position": "QB",
                "scope": "observed_dropbacks_only",
                "opportunities": counts[player],
                "games": len(game_counts),
                "benchmarks": values,
                "game_ledger": weekly,
                "relative_null_projection": diagnostics["relative_null_projection"][i],
                "qualification": exposure_diagnostic(
                    player,
                    "QB",
                    qualification,
                    evidence,
                    games,
                    season=season,
                    week=max(p["week"] for p in rows),
                    cutoff=cutoff,
                    multipliers=[0.75, 1.0, 1.25],
                ),
                "ranking_ready": False,
                "uncertainty_calibrated": False,
            }
        )
    # Subtracting the benchmark transfers its contribution to a separate baseline,
    # not to another player. The ledger conserves every observed outcome.
    benchmark_rate = sum(
        w * beta[prepared.names.index("qb/" + p)] for p, w in weights["first_unit"].items()
    )
    max_error = 0.0
    for p in predictions:
        p["qb_above_first_unit"] = p["components"]["qb"] - benchmark_rate
        p["benchmark_component"] = float(benchmark_rate)
        total = (
            p["qb_above_first_unit"]
            + p["benchmark_component"]
            + sum(v for k, v in p["components"].items() if k != "qb")
            + p["residual"]
        )
        max_error = max(max_error, abs(total - p["observed_epa"]))
    if max_error > 1e-9:
        raise ValueError("benchmark-rebased play accounting failed")
    likelihood = RestrictedLikelihood(prepared, [p["offense_epa"] for p in rows])
    sensitivity = []
    for factor in plan["sensitivity_qb_variance_multipliers"]:
        ratios = np.array([model["variance_ratios"][g] for g in prepared.groups])
        ratios[prepared.groups.index("qb")] /= factor
        _, _, changed, _, _ = likelihood.solve(np.log(ratios))
        delta = l @ (changed - beta)
        sensitivity.append(
            {
                "qb_variance_multiplier": factor,
                "max_absolute_contrast_change_ep": float(np.max(np.abs(delta))),
                "median_absolute_contrast_change_ep": float(np.median(np.abs(delta))),
                "player_changes_ep": dict(zip(players, delta.tolist())),
            }
        )
    report = {
        "games": len({p["game_id"] for p in rows}),
        "plays": len(rows),
        "players": len(players),
        "benchmark_audit": cohorts["audit"]["QB"],
        "benchmark_weights": weights,
        "identification": diagnostics,
        "allocation_witness": allocation_witness(prepared, rows, l),
        "variance_sensitivity": sensitivity,
        "max_accounting_error": max_error,
        "cumulative_component_ep": float(
            sum(r["benchmarks"]["first_unit"]["expected_points"] for r in results)
        ),
        "negative_player_estimates": sum(
            r["benchmarks"]["first_unit"]["expected_points"] < 0 for r in results
        ),
        "qualification_denominators_complete": sum(
            r["qualification"]["denominator_complete"] for r in results
        ),
        "ranking_ready": False,
        "qualification_scope": "Existing full-QB exposure diagnostic is reported separately; partial dropback module does not redefine its opportunity threshold.",
    }
    return report, model, results, predictions, prepared, l


def experiment(
    historical,
    current,
    historical_evidence,
    current_evidence,
    first_unit,
    games,
    *,
    cutoff,
    plan,
    progress=lambda message: None,
):
    validate_plan(plan)
    subsets, audits = {}, {}
    for name, low, high in [
        ("train", 1, plan["train_through_week"]),
        ("validation", plan["train_through_week"] + 1, plan["validation_through_week"]),
        ("refit", 1, plan["validation_through_week"]),
        ("test", plan["validation_through_week"] + 1, plan["test_through_week"]),
    ]:
        subsets[name], audits[name] = prepare(
            historical,
            historical_evidence,
            season=plan["historical_season"],
            low_week=low,
            high_week=high,
        )
    for name, low, high in [
        ("transfer_train", 1, plan["transfer_train_through_week"]),
        ("transfer_test", plan["transfer_train_through_week"] + 1, 18),
        ("current", 1, 18),
    ]:
        subsets[name], audits[name] = prepare(
            current, current_evidence, season=plan["current_season"], low_week=low, high_week=high
        )
    evaluation, models, predictions = {}, {}, {}
    for i, (name, a, b) in enumerate(
        [
            ("validation", "train", "validation"),
            ("test", "refit", "test"),
            ("transfer", "transfer_train", "transfer_test"),
        ]
    ):
        progress("Window: " + name)
        evaluation[name], models[name], predictions[name] = held_out(
            subsets[a], subsets[b], plan, seed=plan["simulation_seed"] + i, progress=progress
        )
    all_rows, _ = prepare_plays(current, season=plan["current_season"])
    progress("Full-season QB contrasts and identifiability")
    season, models["season"], values, predictions["season"], prepared, l = season_estimates(
        subsets["current"],
        all_rows,
        current_evidence,
        first_unit,
        games,
        season=plan["current_season"],
        cutoff=cutoff,
        plan=plan,
    )
    from nfl_value.qb_simulation import calibration

    simulation = calibration(prepared, l, plan, progress=progress)
    report = {
        "experiment": "qb-dropback-recovery-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "cohort_audits": audits,
        "evaluation": evaluation,
        "season": season,
        "calibration": simulation,
        "ranking_ready": False,
        "limitations": [
            "Observational dropback component, not full QB value or causal effect.",
            "Retrospective source revisions; no historical-vintage availability claim.",
            "Empirical-Bayes intervals condition on estimated variance components.",
            "Prediction success alone does not identify QB-versus-team allocation.",
            "No positive position admission; defense and other modules remain required.",
        ],
    }
    return tuple(
        json.loads(json_bytes(value))
        for value in (report, models, {"evaluation": predictions, "player_contrasts": values})
    )
