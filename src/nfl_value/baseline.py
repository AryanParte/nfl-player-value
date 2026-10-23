"""Sparse additive outcome baselines; coefficients are NOT positional CAVAA."""

from collections import Counter, defaultdict
from math import isfinite, log1p, sqrt
import re

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.preplay import parse_context
from nfl_value.source_audit import aware_time


GROUPS = ("context", "offense_team", "defense_team", "observed_role", "dropback", "carry", "target")
ACTORS = {"dropback", "carry", "target"}
VARIANTS = {"context", "team", "role", "joint"}
PLAN_KEYS = {"plan_version", "historical_season", "train_through_week", "validation_through_week",
             "test_through_week", "transfer_season", "context_penalty", "team_penalty",
             "actor_penalties", "solver_tolerance", "solver_iteration_limit", "bootstrap_replicates", "seed"}


def validate_plan(plan: dict) -> None:
    if set(plan) != PLAN_KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported or incomplete baseline plan")
    ints = ("historical_season", "transfer_season", "train_through_week", "validation_through_week",
            "test_through_week", "solver_iteration_limit", "bootstrap_replicates", "seed")
    if any(type(plan[k]) is not int or plan[k] < 1 for k in ints):
        raise ValueError("positive integer plan fields required")
    if not (plan["historical_season"] < plan["transfer_season"] and
            1 <= plan["train_through_week"] < plan["validation_through_week"] < plan["test_through_week"] <= 18):
        raise ValueError("invalid chronological plan")
    penalties = plan["actor_penalties"]
    if not isinstance(penalties, list) or not penalties or len(penalties) != len(set(penalties)):
        raise ValueError("distinct actor penalty grid required")
    for value in [plan["context_penalty"], plan["team_penalty"], plan["solver_tolerance"], *penalties]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError("finite positive numerical settings required")
    if plan["solver_tolerance"] >= 1 or plan["bootstrap_replicates"] > 10000:
        raise ValueError("invalid tolerance or excessive bootstrap size")


def prepare_plays(ledger: dict, *, season: int) -> tuple[list[dict], dict]:
    """Validate observed records; missing outcomes/context are counted, never zeroed."""
    if ledger.get("schema_version") != 1 or ledger.get("opportunity_policy") != "observed-offensive-pass-run-v1":
        raise ValueError("unsupported offensive ledger")
    if ledger["provenance"]["season"] != season:
        raise ValueError("ledger season mismatch")
    rows, seen, game_metadata = [], set(), {}
    excluded = Counter()
    actor_teams = defaultdict(set)
    for p in ledger["plays"]:
        if not re.fullmatch(rf"{season}_\d{{2}}_[A-Z]{{2,3}}_[A-Z]{{2,3}}", p["game_id"]):
            raise ValueError("invalid or cross-season game ID")
        if type(p["play_id"]) is not int or p["play_id"] < 0:
            raise ValueError("invalid play ID")
        key = (p["game_id"], p["play_id"])
        if key in seen:
            raise ValueError("duplicate model game/play key")
        seen.add(key)
        week = p["week"]
        if type(week) is not int or not 1 <= week <= 18 or int(p["game_id"].split("_")[1]) != week:
            raise ValueError("invalid regular-season week")
        kickoff = aware_time(p["scheduled_kickoff"])
        teams = set(p["game_id"].split("_")[2:])
        if {p["offense_team"], p["defense_team"]} != teams or len(teams) != 2:
            raise ValueError("model teams disagree with game ID")
        metadata = (week, kickoff)
        if p["game_id"] in game_metadata and game_metadata[p["game_id"]] != metadata:
            raise ValueError("inconsistent game metadata")
        game_metadata[p["game_id"]] = metadata
        if set(p["actors"]) != {"dropback", "rusher", "target"}:
            raise ValueError("invalid actor fields")
        for actor in p["actors"].values():
            if actor is not None:
                if not isinstance(actor, str) or not re.fullmatch(r"00-\d{7}", actor):
                    raise ValueError("invalid actor identity")
                actor_teams[(p["game_id"], actor)].add(p["offense_team"])
        if type(p["context_outcome_complete"]) is not bool or not isinstance(p["issues"], list):
            raise ValueError("invalid observation flags")
        if not p["context_outcome_complete"]:
            excluded["context_outcome_incomplete"] += 1
            continue
        # A true completeness claim with invalid numbers is corruption, not an exclusion.
        parse_context(p["context"])
        if isinstance(p["offense_epa"], bool) or not isinstance(p["offense_epa"], (int, float)) or not isfinite(p["offense_epa"]):
            raise ValueError("invalid EPA despite complete flag")
        rows.append(p)
    if any(len(teams) > 1 for teams in actor_teams.values()):
        raise ValueError("actor assigned to both teams in a game")
    if not rows:
        raise ValueError("no complete model observations")
    rows.sort(key=lambda p: (aware_time(p["scheduled_kickoff"]), p["game_id"], p["play_id"]))
    return rows, {"input_plays": len(seen), "retained_plays": len(rows), "excluded": dict(excluded),
                  "actor_issue_plays_retained": sum(bool(p["issues"]) for p in rows)}


def actor_features(p: dict) -> dict:
    # Avoid trusting a partially valid link from an ambiguous/aborted record.
    if p["issues"]:
        return {}
    a = p["actors"]
    out = {}
    if a["dropback"] is not None:
        out["dropback/" + a["dropback"]] = 1.0
    elif a["rusher"] is not None:
        out["carry/" + a["rusher"]] = 1.0
    if a["target"] is not None:
        out["target/" + a["target"]] = 1.0
    return out


def features(p: dict, variant: str) -> dict:
    if variant not in VARIANTS:
        raise ValueError("unknown model variant")
    c = p["context"]
    distance, field = c["ydstogo"] / 10, c["yardline_100"] / 100
    time, score = c["game_seconds_remaining"] / 3600, c["score_differential"] / 14
    out = {"context/intercept": 1.0, "context/distance": distance,
           "context/log_distance": log1p(c["ydstogo"]) / log1p(10),
           "context/field": field, "context/field_squared": field * field,
           "context/red_zone": float(c["yardline_100"] <= 20),
           "context/time": time, "context/score": score, "context/score_time": score * time,
           "context/final_two_minutes": float(c["game_seconds_remaining"] <= 120),
           "context/overtime": float(c["qtr"] == 5)}
    for down in (2, 3, 4):
        active = float(c["down"] == down)
        out[f"context/down_{down}"] = active
        out[f"context/down_{down}_distance"] = active * distance
    if variant != "context":
        out["offense_team/" + p["offense_team"]] = 1.0
        out["defense_team/" + p["defense_team"]] = 1.0
    if variant in {"role", "joint"}:
        actors = actor_features(p)
        # Conditional role-observation ablation, not preplay hardship adjustment.
        out.update({"observed_role/" + name.split("/")[0]: 1.0 for name in actors})
        if variant == "joint":
            out.update(actors)
    return out


def design(rows: list[dict], variant: str, names: list[str] | None = None):
    dictionaries = [features(p, variant) for p in rows]
    if names is None:
        names = sorted({name for d in dictionaries for name in d})
    index = {name: i for i, name in enumerate(names)}
    rr, cc, vv = [], [], []
    unseen = Counter()
    for i, d in enumerate(dictionaries):
        for name, value in d.items():
            if name not in index:
                unseen[name.split("/")[0]] += 1
            elif value:
                rr.append(i)
                cc.append(index[name])
                vv.append(value)
    return sparse.csr_matrix((vv, (rr, cc)), shape=(len(rows), len(names))), names, dict(sorted(unseen.items()))


def fit(rows: list[dict], *, variant: str, plan: dict, actor_penalty: float) -> dict:
    validate_plan(plan)
    if not rows or actor_penalty not in plan["actor_penalties"]:
        raise ValueError("nonempty training rows and declared actor penalty required")
    matrix, names, _ = design(rows, variant)
    penalties = []
    for name in names:
        group = name.split("/")[0]
        penalties.append(0 if name == "context/intercept" else actor_penalty if group in ACTORS else
                         plan["context_penalty"] if group in {"context", "observed_role"} else plan["team_penalty"])
    target = np.array([p["offense_epa"] for p in rows])
    augmented = sparse.vstack([matrix, sparse.diags(np.sqrt(penalties))], format="csr")
    result = lsqr(augmented, np.concatenate([target, np.zeros(len(names))]),
                  atol=plan["solver_tolerance"], btol=plan["solver_tolerance"],
                  iter_lim=plan["solver_iteration_limit"], conlim=1e8)
    if result[1] not in {0, 1, 2} or not np.all(np.isfinite(result[0])):
        raise ValueError(f"least-squares solver did not converge: stop={result[1]}")
    return {"model_version": 1, "variant": variant, "actor_penalty": actor_penalty,
            "features": names, "coefficients": result[0].tolist(),
            "training_plays": len(rows), "training_games": sorted({p["game_id"] for p in rows}),
            "training_rows_sha256": sha256(json_bytes({"plays": rows})),
            "solver": {"stop": int(result[1]), "iterations": int(result[2]),
                       "augmented_condition_estimate": float(result[6])}}


def predict(model: dict, rows: list[dict]) -> tuple[list[dict], dict]:
    matrix, names, unseen = design(rows, model["variant"], model["features"])
    coef = np.array(model["coefficients"])
    if len(coef) != len(names) or not np.all(np.isfinite(coef)) or len(set(names)) != len(names):
        raise ValueError("invalid fitted coefficients")
    components = {}
    for group in GROUPS:
        mask = np.array([name.startswith(group + "/") for name in names])
        components[group] = np.asarray(matrix[:, mask] @ coef[mask]).ravel()
    predicted = np.asarray(matrix @ coef).ravel()
    output = []
    for i, p in enumerate(rows):
        parts = {k: float(v[i]) for k, v in components.items()}
        residual = float(p["offense_epa"] - predicted[i])
        error = abs(p["offense_epa"] - sum(parts.values()) - residual)
        if not isfinite(predicted[i]) or error > 1e-9:
            raise ValueError("model outcome accounting failed")
        output.append({"game_id": p["game_id"], "play_id": p["play_id"], "offense_team": p["offense_team"],
                       "observed_epa": p["offense_epa"], "predicted_epa": float(predicted[i]),
                       "components": parts, "residual": residual,
                       "actor_links_withheld": bool(p["issues"]), "accounting_error": error})
    return output, {"unseen_feature_appearances": unseen,
                    "max_accounting_error": max((p["accounting_error"] for p in output), default=0.0)}


def metrics(predictions: list[dict]) -> dict:
    if not predictions:
        raise ValueError("empty evaluation cohort")
    errors = np.array([p["predicted_epa"] - p["observed_epa"] for p in predictions])
    team_games = defaultdict(list)
    for p, error in zip(predictions, errors):
        team_games[(p["game_id"], p["offense_team"])].append(float(error))
    means = np.array([np.mean(v) for v in team_games.values()])
    return {"plays": len(errors), "games": len({p["game_id"] for p in predictions}),
            "rmse": float(np.sqrt(np.mean(errors**2))), "mae": float(np.mean(np.abs(errors))),
            "prediction_minus_observation_bias": float(np.mean(errors)),
            "team_game_mean_epa_rmse": float(np.sqrt(np.mean(means**2)))}


def paired_rmse_interval(candidate: list[dict], reference: list[dict], *, seed: int, replicates: int) -> dict:
    keys = lambda rows: [(p["game_id"], p["play_id"], p["observed_epa"]) for p in rows]
    if not candidate or keys(candidate) != keys(reference):
        raise ValueError("paired comparison requires identical ordered observations")
    cells = defaultdict(lambda: [0, 0.0, 0.0])
    for a, b in zip(candidate, reference):
        cell = cells[a["game_id"]]
        cell[0] += 1
        cell[1] += (a["predicted_epa"] - a["observed_epa"])**2
        cell[2] += (b["predicted_epa"] - b["observed_epa"])**2
    values = np.array([cells[k] for k in sorted(cells)])
    if len(values) < 2:
        raise ValueError("at least two games required for cluster bootstrap")
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(values), np.full(len(values), 1 / len(values)), size=replicates)
    totals = weights @ values
    delta = np.sqrt(totals[:, 1] / totals[:, 0]) - np.sqrt(totals[:, 2] / totals[:, 0])
    low, high = np.quantile(delta, [0.025, 0.975])
    return {"candidate_minus_reference_rmse": metrics(candidate)["rmse"] - metrics(reference)["rmse"],
            "percentile_95_interval": [float(low), float(high)], "resampling_unit": "game",
            "replicates": replicates, "seed": seed, "player_uncertainty": False}


def coappearance(rows: list[dict]) -> dict:
    appearances, teams = defaultdict(set), defaultdict(set)
    for i, p in enumerate(rows):
        teams[p["offense_team"]].add(i)
        for actor in actor_features(p):
            appearances[actor].add(i)
    cosine = []
    duplicate = defaultdict(list)
    for actor, indices in appearances.items():
        duplicate[tuple(sorted(indices))].append(actor)
        cosine.append(max(len(indices & t) / sqrt(len(indices) * len(t)) for t in teams.values()))
    return {"actor_columns": len(appearances),
            "identical_actor_column_groups": [sorted(v) for _, v in sorted(duplicate.items()) if len(v) > 1],
            "actor_offense_team_cosine_median": float(np.median(cosine)) if cosine else None,
            "actor_offense_team_cosine_max": max(cosine, default=None),
            "identification_validated": False}


def experiment(historical: dict, transfer: dict, plan: dict) -> tuple[dict, dict, dict]:
    validate_plan(plan)
    hist, hist_audit = prepare_plays(historical, season=plan["historical_season"])
    later, later_audit = prepare_plays(transfer, season=plan["transfer_season"])
    train = [p for p in hist if p["week"] <= plan["train_through_week"]]
    valid = [p for p in hist if plan["train_through_week"] < p["week"] <= plan["validation_through_week"]]
    test = [p for p in hist if plan["validation_through_week"] < p["week"] <= plan["test_through_week"]]
    if any(p["week"] > plan["test_through_week"] for p in hist):
        raise ValueError("historical observations outside declared plan")
    partitions = [train, valid, test, later]
    if any(not rows for rows in partitions):
        raise ValueError("empty chronological split")
    for a, b in zip(partitions, partitions[1:]):
        if max(aware_time(p["scheduled_kickoff"]) for p in a) >= min(aware_time(p["scheduled_kickoff"]) for p in b):
            raise ValueError("chronological split overlaps")
    validation = []
    for penalty in plan["actor_penalties"]:
        model = fit(train, variant="joint", plan=plan, actor_penalty=penalty)
        pred, _ = predict(model, valid)
        validation.append({"actor_penalty": penalty, "metrics": metrics(pred), "solver": model["solver"]})
    selected = min(validation, key=lambda v: (v["metrics"]["rmse"], -v["actor_penalty"]))["actor_penalty"]
    models = {variant: fit(train + valid, variant=variant, plan=plan, actor_penalty=selected) for variant in sorted(VARIANTS)}
    predictions, evaluation = {}, {}
    for label, rows in (("historical_test", test), ("transfer_test", later)):
        predictions[label], evaluation[label] = {}, {}
        for variant, model in models.items():
            pred, audit = predict(model, rows)
            predictions[label][variant] = pred
            evaluation[label][variant] = {**metrics(pred), **audit}
        evaluation[label]["joint_vs_team"] = paired_rmse_interval(predictions[label]["joint"], predictions[label]["team"],
                                                                  seed=plan["seed"], replicates=plan["bootstrap_replicates"])
        evaluation[label]["joint_vs_role"] = paired_rmse_interval(predictions[label]["joint"], predictions[label]["role"],
                                                                  seed=plan["seed"], replicates=plan["bootstrap_replicates"])
    sensitivity = []
    for penalty in plan["actor_penalties"]:
        model = models["joint"] if penalty == selected else fit(train + valid, variant="joint", plan=plan, actor_penalty=penalty)
        coef = dict(zip(model["features"], model["coefficients"]))
        base = dict(zip(models["joint"]["features"], models["joint"]["coefficients"]))
        differences = [abs(value - base[name]) for name, value in coef.items() if name.split("/")[0] in ACTORS]
        sensitivity.append({"actor_penalty": penalty, "historical_test": metrics(predict(model, test)[0]),
                            "max_actor_coefficient_change_from_selected": max(differences, default=0.0),
                            "solver": model["solver"]})
    report = {"experiment_version": 1, "plan": plan, "selected_actor_penalty": selected,
              "selection_uses": "Declared historical validation games only; no test outcomes", "validation": validation,
              "input_audits": {"historical": hist_audit, "transfer": later_audit},
              "split_games": {k: sorted({p["game_id"] for p in rows}) for k, rows in zip(("train", "validation", "historical_test", "transfer_test"), partitions)},
              "evaluation": evaluation, "penalty_sensitivity": sensitivity, "coappearance": coappearance(train + valid),
              "ranking_ready": False, "individual_attribution_validated": False,
              "benchmark_contrasts_computed": False, "qualification_computed": False,
              "scope": "Observed offensive pass/run actor-role outcome model, not positional player value"}
    return report, models, predictions
