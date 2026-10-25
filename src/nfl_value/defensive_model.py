"""Historical aggregation diagnostic. No fitted coefficient is positional CAVAA."""

from collections import Counter, defaultdict
from math import fsum, isclose, isfinite, sqrt
import re

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.preplay import CONTEXT, parse_context
from nfl_value.source_audit import aware_time


VIEWS = {"rich_play_lineups": "plays", "degraded_team_games": "team_games"}
GROUPS = ("context", "offense_team", "defense_team", "defender")
SCALES = dict(zip(CONTEXT, (4, 10, 100, 3600, 5, 14)))
META = {"game_id", "week", "scheduled_kickoff", "offense_team", "defense_team"}
RICH_KEYS = META | {"play_id", "defense_epa", "context", "offense_players", "defense_players"}
DEGRADED_KEYS = META | {"opportunities", "defense_epa_total", "defense_epa_mean", "context_mean", "defender_workloads"}
PLAN_KEYS = {"plan_version", "season", "train_through_week", "validation_through_week", "test_through_week",
             "context_penalty", "team_penalty", "defender_penalties", "solver_tolerance", "solver_iteration_limit",
             "bootstrap_replicates", "seed", "rank_relative_tolerance", "selection_smd_threshold"}


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def close(a, b):
    return isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def validate_plan(plan):
    if set(plan) != PLAN_KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported defensive experiment plan")
    for k in ("season", "train_through_week", "validation_through_week", "test_through_week",
              "solver_iteration_limit", "bootstrap_replicates", "seed"):
        if type(plan[k]) is not int or plan[k] <= 0:
            raise ValueError("positive integer plan fields required")
    if not 1 <= plan["train_through_week"] < plan["validation_through_week"] < plan["test_through_week"] <= 18:
        raise ValueError("invalid chronological plan")
    grid = plan["defender_penalties"]
    if not isinstance(grid, list) or not grid or any(not finite(x) or x <= 0 for x in grid) or len(grid) != len(set(grid)):
        raise ValueError("distinct positive defender penalties required")
    for k in ("context_penalty", "team_penalty", "solver_tolerance", "rank_relative_tolerance", "selection_smd_threshold"):
        if not finite(plan[k]) or plan[k] <= 0:
            raise ValueError("finite positive numerical settings required")
    if max(plan["solver_tolerance"], plan["rank_relative_tolerance"]) >= 1 or plan["bootstrap_replicates"] > 10000:
        raise ValueError("invalid tolerance or bootstrap size")


def _player_id(value):
    return isinstance(value, str) and re.fullmatch(r"00-\d{7}", value)


def validate_rows(rows, view):
    """Strict reduced schema rejects accidental access to per-play information."""
    if view not in VIEWS or not rows:
        raise ValueError("known view and nonempty observations required")
    seen, metadata, sides, player_teams = set(), {}, defaultdict(set), defaultdict(set)
    for p in rows:
        if set(p) != (RICH_KEYS if view == "rich_play_lineups" else DEGRADED_KEYS):
            raise ValueError("invalid view fields; rich information is forbidden in degraded rows")
        if not isinstance(p["game_id"], str) or not re.fullmatch(r"\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}", p["game_id"]):
            raise ValueError("invalid game ID")
        week = p["week"]
        if type(week) is not int or not 1 <= week <= 18 or int(p["game_id"].split("_")[1]) != week:
            raise ValueError("invalid regular-season week")
        if {p["offense_team"], p["defense_team"]} != set(p["game_id"].split("_")[2:]) or p["offense_team"] == p["defense_team"]:
            raise ValueError("teams disagree with game ID")
        stamp = (week, aware_time(p["scheduled_kickoff"]))
        if p["game_id"] in metadata and metadata[p["game_id"]] != stamp:
            raise ValueError("inconsistent game metadata")
        metadata[p["game_id"]] = stamp
        sides[p["game_id"]].add(p["defense_team"])
        if view == "rich_play_lineups":
            if type(p["play_id"]) is not int or p["play_id"] < 0 or not finite(p["defense_epa"]):
                raise ValueError("invalid play identity or outcome")
            key = (p["game_id"], p["play_id"])
            if set(p["context"]) != set(CONTEXT) or any(not finite(x) for x in p["context"].values()):
                raise ValueError("invalid play context")
            parse_context(p["context"])
            for k in ("offense_players", "defense_players"):
                values = p[k]
                if not isinstance(values, list) or len(values) != 11 or any(not _player_id(x) for x in values) or len(set(values)) != 11:
                    raise ValueError("eleven distinct canonical players per side required")
                for player in values:
                    player_teams[(p["game_id"], player)].add(p["offense_team" if k == "offense_players" else "defense_team"])
            if set(p["offense_players"]) & set(p["defense_players"]):
                raise ValueError("player on both sides")
        else:
            key = (p["game_id"], p["defense_team"])
            n = p["opportunities"]
            if type(n) is not int or n <= 0 or any(not finite(p[k]) for k in ("defense_epa_total", "defense_epa_mean")):
                raise ValueError("invalid game weight or outcome")
            if not close(p["defense_epa_total"], n * p["defense_epa_mean"]):
                raise ValueError("game mean and total disagree")
            c = p["context_mean"]
            if set(c) != set(CONTEXT) or any(not finite(x) for x in c.values()):
                raise ValueError("invalid mean context")
            if not (1 <= c["down"] <= 4 and 1 <= c["qtr"] <= 5 and 0 <= c["ydstogo"] <= 100 and
                    0 <= c["yardline_100"] <= 100 and 0 <= c["game_seconds_remaining"] <= 3600):
                raise ValueError("mean context outside bounds")
            workloads, ids, total = p["defender_workloads"], set(), 0
            if not isinstance(workloads, list) or not workloads:
                raise ValueError("missing workloads")
            for item in workloads:
                if set(item) != {"player_id", "appearances", "fraction"} or not _player_id(item["player_id"]):
                    raise ValueError("invalid workload schema")
                count = item["appearances"]
                if item["player_id"] in ids or type(count) is not int or not 1 <= count <= n:
                    raise ValueError("duplicate player or invalid appearances")
                if not finite(item["fraction"]) or not close(item["fraction"], count / n):
                    raise ValueError("fraction does not match observed appearances")
                ids.add(item["player_id"])
                total += count
                player_teams[(p["game_id"], item["player_id"])].add(p["defense_team"])
            if total != 11 * n:
                raise ValueError("workloads do not conserve eleven defenders per play")
        if key in seen:
            raise ValueError("duplicate observation key")
        seen.add(key)
    if any(len(x) != 2 for x in sides.values()) or any(len(x) != 1 for x in player_teams.values()):
        raise ValueError("incomplete game or player assigned to opposing teams")


def aggregate_plays(rows):
    grouped = defaultdict(list)
    for p in rows:
        grouped[(p["game_id"], p["defense_team"])].append(p)
    result = []
    for _, group in sorted(grouped.items()):
        n = len(group)
        counts = Counter(player for p in group for player in p["defense_players"])
        total = fsum(p["defense_epa"] for p in group)
        result.append({**{k: group[0][k] for k in META}, "opportunities": n,
                       "defense_epa_total": total, "defense_epa_mean": total / n,
                       "context_mean": {k: fsum(p["context"][k] for p in group) / n for k in CONTEXT},
                       "defender_workloads": [{"player_id": player, "appearances": count, "fraction": count/n}
                                              for player, count in sorted(counts.items())]})
    return result


def prepare_pair(rich, degraded, season):
    common = {"schema_version", "season", "cohort_sha256", "cohort_plays", "game_ids", "ranking_ready", "provenance"}
    for view, label in ((rich, "rich_play_lineups"), (degraded, "degraded_team_games")):
        if set(view) != common | {"view", VIEWS[label]} or view["view"] != label or type(view["schema_version"]) is not int or view["schema_version"] != 1:
            raise ValueError("unsupported view schema")
        if view["season"] != season or view["ranking_ready"] is not False:
            raise ValueError("season or research-status mismatch")
        validate_rows(view[VIEWS[label]], label)
        if any(not p["game_id"].startswith(f"{season}_") for p in view[VIEWS[label]]):
            raise ValueError("cross-season observation")
    if any(rich[k] != degraded[k] for k in common):
        raise ValueError("cohort metadata/provenance mismatch")
    rows = sorted(rich["plays"], key=lambda p: (p["game_id"], p["play_id"]))
    digest = sha256(json_bytes([[p["game_id"], p["play_id"]] for p in rows]))
    if digest != rich["cohort_sha256"] or len(rows) != rich["cohort_plays"] or sorted({p["game_id"] for p in rows}) != rich["game_ids"]:
        raise ValueError("cohort identity mismatch")
    # Exact equality: both views must be reproducible derivatives of these same plays.
    if aggregate_plays(rows) != degraded["team_games"]:
        raise ValueError("degraded aggregate differs from rich cohort")
    return rows, degraded["team_games"]


def features(p, view, variant):
    if view not in VIEWS or variant not in {"team", "defender"}:
        raise ValueError("unknown view or model variant")
    c = p["context" if view == "rich_play_lineups" else "context_mean"]
    d = {"context/intercept": 1.0, **{"context/" + k: c[k] / scale for k, scale in SCALES.items()},
         "offense_team/" + p["offense_team"]: 1.0, "defense_team/" + p["defense_team"]: 1.0}
    if variant == "defender":
        values = ((x, 1.0) for x in p["defense_players"]) if view == "rich_play_lineups" else (
            (item["player_id"], item["fraction"]) for item in p["defender_workloads"])
        d.update({"defender/" + player: value for player, value in values})
    return d


def design(rows, view, variant, names=None):
    dictionaries = [features(p, view, variant) for p in rows]
    if names is None:
        names = sorted({name for d in dictionaries for name in d})
    index = {name: i for i, name in enumerate(names)}
    rr, cc, vv, unseen = [], [], [], Counter()
    for i, d in enumerate(dictionaries):
        for name, value in d.items():
            if name not in index:
                unseen[name.split("/")[0]] += 1
            elif value:
                rr.append(i)
                cc.append(index[name])
                vv.append(value)
    return sparse.csr_matrix((vv, (rr, cc)), shape=(len(rows), len(names))), names, dict(sorted(unseen.items()))


def weights_target(rows, view):
    if view == "rich_play_lineups":
        return np.ones(len(rows)), np.array([p["defense_epa"] for p in rows])
    return np.array([p["opportunities"] for p in rows]), np.array([p["defense_epa_mean"] for p in rows])


def fit(rows, *, view, variant, plan, defender_penalty):
    validate_plan(plan)
    validate_rows(rows, view)
    if defender_penalty not in plan["defender_penalties"]:
        raise ValueError("undeclared penalty")
    x, names, _ = design(rows, view, variant)
    weights, target = weights_target(rows, view)
    penalties = [0 if name == "context/intercept" else plan["context_penalty"] if name.startswith("context/") else
                 defender_penalty if name.startswith("defender/") else plan["team_penalty"] for name in names]
    xw = x.multiply(np.sqrt(weights)[:, None])
    augmented = sparse.vstack([xw, sparse.diags(np.sqrt(penalties))], format="csr")
    result = lsqr(augmented, np.r_[target * np.sqrt(weights), np.zeros(len(names))], atol=plan["solver_tolerance"],
                  btol=plan["solver_tolerance"], iter_lim=plan["solver_iteration_limit"], conlim=1e8)
    if result[1] not in {0, 1, 2} or not np.all(np.isfinite(result[0])):
        raise ValueError(f"least-squares solver did not converge: stop={result[1]}")
    return {"model_version": 1, "view": view, "variant": variant, "defender_penalty": defender_penalty,
            "features": names, "coefficients": result[0].tolist(), "training_rows": len(rows),
            "training_opportunities": int(sum(weights)), "training_games": sorted({p["game_id"] for p in rows}),
            "training_rows_sha256": sha256(json_bytes({VIEWS[view]: rows})),
            "solver": {"stop": int(result[1]), "iterations": int(result[2]), "augmented_condition_estimate": float(result[6])},
            "ranking_ready": False}


def predict(model, rows):
    """Account per input row, then return common defensive team-game mean units."""
    view = model["view"]
    validate_rows(rows, view)
    x, names, unseen = design(rows, view, model["variant"], model["features"])
    coef = np.array(model["coefficients"])
    if len(names) != len(coef) or len(set(names)) != len(names) or not np.all(np.isfinite(coef)):
        raise ValueError("invalid coefficients")
    weights, target = weights_target(rows, view)
    components = {}
    for group in GROUPS:
        mask = np.array([name.startswith(group + "/") for name in names])
        components[group] = np.asarray(x[:, mask] @ coef[mask]).ravel()
    fitted = np.asarray(x @ coef).ravel()
    residual = target - fitted
    error = np.abs(target - sum(components.values()) - residual)
    if not np.all(np.isfinite(fitted)) or np.max(error) > 1e-9:
        raise ValueError("outcome accounting failed")
    grouped = defaultdict(list)
    for i, p in enumerate(rows):
        grouped[(p["game_id"], p["defense_team"])].append(i)
    predictions = []
    for (game, team), indices in sorted(grouped.items()):
        n = int(sum(weights[indices]))
        def mean(values):
            return float(np.average(values[indices], weights=weights[indices]))
        predictions.append({"game_id": game, "defense_team": team, "opportunities": n,
                            "observed_epa_mean": mean(target), "predicted_epa_mean": mean(fitted),
                            "components": {k: mean(v) for k, v in components.items()}, "residual_mean": mean(residual)})
    return predictions, {"unseen_feature_rows": unseen, "unseen_effect_policy": "zero-centered prior prediction, not measured player value",
                         "max_row_accounting_error": float(np.max(error))}


def metrics(predictions):
    if not predictions:
        raise ValueError("empty evaluation cohort")
    w = np.array([p["opportunities"] for p in predictions])
    e = np.array([p["predicted_epa_mean"] - p["observed_epa_mean"] for p in predictions])
    return {"games": len({p["game_id"] for p in predictions}), "team_games": len(e), "opportunities": int(sum(w)),
            "weighted_rmse": float(np.sqrt(np.average(e**2, weights=w))), "equal_team_game_rmse": float(np.sqrt(np.mean(e**2))),
            "weighted_mae": float(np.average(abs(e), weights=w)), "weighted_bias": float(np.average(e, weights=w)),
            "units": "EP per eligible play, evaluated at team-game means"}


def paired_rmse_interval(candidate, reference, *, seed, replicates):
    keys = lambda p: (p["game_id"], p["defense_team"], p["opportunities"])
    if len(candidate) != len(reference) or not candidate:
        raise ValueError("unpaired predictions")
    cells = defaultdict(lambda: np.zeros(3))
    for a, b in zip(candidate, reference):
        if keys(a) != keys(b) or not close(a["observed_epa_mean"], b["observed_epa_mean"]):
            raise ValueError("unpaired predictions")
        n = a["opportunities"]
        cells[a["game_id"]] += (n, n*(a["predicted_epa_mean"] - a["observed_epa_mean"])**2,
                              n*(b["predicted_epa_mean"] - b["observed_epa_mean"])**2)
    values = np.array([cells[k] for k in sorted(cells)])
    if len(values) < 2:
        raise ValueError("at least two games required for bootstrap")
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(len(values), np.full(len(values), 1 / len(values)), size=replicates)
    totals = counts @ values
    delta = np.sqrt(totals[:, 1]/totals[:, 0]) - np.sqrt(totals[:, 2]/totals[:, 0])
    interval = np.quantile(delta, [0.025, 0.975]).tolist()
    return {"candidate_minus_reference_weighted_rmse": metrics(candidate)["weighted_rmse"] - metrics(reference)["weighted_rmse"],
            "percentile_95_interval": interval, "resampling_unit": "game", "replicates": replicates, "seed": seed,
            "incremental_prediction_evidence": interval[1] < 0, "player_uncertainty": False, "equivalence_test": False}


def identification(rows, view, *, relative_tolerance):
    x, names, _ = design(rows, view, "defender")
    w, _ = weights_target(rows, view)
    x = x.multiply(np.sqrt(w)[:, None]).tocsr()
    mask = np.array([n.startswith("defender/") for n in names])
    a, z = x[:, mask], x[:, ~mask]
    gram = (a.T @ a).toarray()
    zz, za = (z.T @ z).toarray(), (z.T @ a).toarray()
    residual = gram - za.T @ np.linalg.pinv(zz, rcond=relative_tolerance) @ za
    eigen = np.linalg.eigvalsh((residual + residual.T) / 2)
    # Use the original block's scale: a nearly zero residual must not look full rank.
    scale = max(float(np.linalg.eigvalsh(gram)[-1]), 1.0)
    rank = int(np.sum(eigen > relative_tolerance * scale))
    defender_names = [n for n, active in zip(names, mask) if active]
    original = design(rows, view, "defender", names)[0].tocsc()
    duplicate = defaultdict(list)
    for j, name in enumerate(names):
        if name.startswith("defender/"):
            col = original[:, j]
            duplicate[(tuple(col.indices), tuple(col.data))].append(name)
    team_mask = np.array([n.startswith("defense_team/") for n in names])
    t = x[:, team_mask]
    cross = (a.T @ t).toarray()
    norm = np.sqrt(gram.diagonal()[:, None] * np.asarray(t.multiply(t).sum(axis=0)))
    cosine = np.max(cross / norm, axis=1)
    return {"defender_columns": len(defender_names), "observations": len(rows), "residualized_defender_rank": rank,
            "unidentified_linear_dimensions": len(defender_names) - rank,
            "gram_relative_eigenvalue_tolerance": relative_tolerance, "gram_reference_scale": scale,
            "identical_defender_column_groups": [sorted(v) for _, v in sorted(duplicate.items()) if len(v) > 1],
            "defender_team_cosine_median": float(np.median(cosine)), "defender_team_cosine_max": float(max(cosine)),
            "identification_validated": False}


def coefficient_agreement(a, b):
    left = {k: v for k, v in zip(a["features"], a["coefficients"]) if k.startswith("defender/")}
    right = {k: v for k, v in zip(b["features"], b["coefficients"]) if k.startswith("defender/")}
    if left.keys() != right.keys() or not left:
        raise ValueError("defender vocabularies differ")
    x, y = np.array([left[k] for k in sorted(left)]), np.array([right[k] for k in sorted(left)])
    correlation = float(np.corrcoef(x, y)[0, 1]) if min(float(x.std()), float(y.std())) > 1e-12 else None
    return {"defenders": len(x), "pearson_correlation": correlation, "mean_absolute_difference": float(np.mean(abs(x-y))),
            "max_absolute_difference": float(np.max(abs(x-y))), "reference_is_ground_truth": False,
            "units": "penalized coefficient EP per eligible appearance, not CAVAA"}


def selection_diagnostics(rich, ledger, *, threshold):
    if ledger.get("schema_version") != 1 or ledger.get("opportunity_policy") != "observed-offensive-pass-run-v1":
        raise ValueError("unsupported candidate ledger")
    if ledger["provenance"]["season"] != rich["season"] or any(
            ledger["provenance"]["source_receipts"][k] != rich["provenance"]["source_receipts"][k] for k in ("pbp", "schedules")):
        raise ValueError("selection comparison requires identical source receipts and season")
    chosen = {(p["game_id"], p["play_id"]): p for p in rich["plays"]}
    retained, excluded, missing, seen = [], [], 0, set()
    for p in ledger["plays"]:
        key = (p["game_id"], p["play_id"])
        if key in seen:
            raise ValueError("duplicate candidate play")
        seen.add(key)
        if type(p["context_outcome_complete"]) is not bool:
            raise ValueError("invalid candidate completeness flag")
        if not p["context_outcome_complete"]:
            if p["game_id"] in rich["game_ids"]:
                raise ValueError("selected game contains missing candidate outcome")
            missing += 1
            continue
        parse_context(p["context"])
        if not finite(p["offense_epa"]):
            raise ValueError("invalid candidate EPA")
        row = {**p, "defense_epa": -p["offense_epa"]}
        if key in chosen:
            expected = chosen[key]
            if row["defense_epa"] != expected["defense_epa"] or any(row[k] != expected[k] for k in META | {"context"}):
                raise ValueError("candidate and selected outcomes/context disagree")
            retained.append(row)
        else:
            if p["game_id"] in rich["game_ids"]:
                raise ValueError("selected game is not complete in candidate comparison")
            excluded.append(row)
    if not chosen.keys() <= seen or len(retained) != len(chosen):
        raise ValueError("candidate population does not contain selected cohort")
    def describe(rows):
        return {"plays": len(rows), "games": len({p["game_id"] for p in rows}),
                "by_week": dict(sorted(Counter(str(p["week"]) for p in rows).items())),
                "by_defense_team": {t: {"plays": sum(p["defense_team"] == t for p in rows),
                    "games": len({p["game_id"] for p in rows if p["defense_team"] == t})} for t in sorted({p["defense_team"] for p in rows})}}
    contrasts = {}
    for k in (*CONTEXT, "defense_epa"):
        get = lambda p: p[k] if k == "defense_epa" else p["context"][k]
        a, b = np.array([get(p) for p in retained]), np.array([get(p) for p in excluded])
        if not len(a) or not len(b):
            contrasts[k] = {"retained_mean": float(a.mean()) if len(a) else None, "excluded_mean": float(b.mean()) if len(b) else None,
                            "standardized_difference": None, "flagged": None}
            continue
        scale = sqrt((float(a.var()) + float(b.var())) / 2)
        diff = float(a.mean() - b.mean())
        smd = diff / scale if scale else 0.0 if diff == 0 else None
        contrasts[k] = {"retained_mean": float(a.mean()), "excluded_mean": float(b.mean()), "standardized_difference": smd,
                        "flagged": abs(smd) >= threshold if smd is not None else True}
    return {"candidate_plays": len(seen), "candidate_context_outcome_missing": missing, "retained": describe(retained),
            "excluded": describe(excluded), "contrasts": contrasts, "descriptive_smd_threshold": threshold,
            "selection_is_ignorable": False, "outcome_difference_is_causal": False}


def experiment(rich, degraded, ledger, plan):
    validate_plan(plan)
    plays, games = prepare_pair(rich, degraded, plan["season"])
    selection = selection_diagnostics(rich, ledger, threshold=plan["selection_smd_threshold"])
    views = {"rich": ("rich_play_lineups", plays), "degraded": ("degraded_team_games", games)}
    models, predictions, evaluation, validation, selected, diagnostics = {}, {}, {}, {}, {}, {}
    sensitivity, splits = {}, None
    for label, (view, rows) in views.items():
        train = [p for p in rows if p["week"] <= plan["train_through_week"]]
        valid = [p for p in rows if plan["train_through_week"] < p["week"] <= plan["validation_through_week"]]
        test = [p for p in rows if plan["validation_through_week"] < p["week"] <= plan["test_through_week"]]
        if any(p["week"] > plan["test_through_week"] for p in rows) or any(not part for part in (train, valid, test)):
            raise ValueError("empty or out-of-plan chronological split")
        for a, b in ((train, valid), (valid, test)):
            if max(aware_time(p["scheduled_kickoff"]) for p in a) >= min(aware_time(p["scheduled_kickoff"]) for p in b):
                raise ValueError("chronological split overlaps")
        split = {k: sorted({p["game_id"] for p in r}) for k, r in zip(("train", "validation", "test"), (train, valid, test))}
        if splits is not None and split != splits:
            raise ValueError("unpaired splits")
        splits = split
        validation[label] = []
        for penalty in plan["defender_penalties"]:
            model = fit(train, view=view, variant="defender", plan=plan, defender_penalty=penalty)
            validation[label].append({"defender_penalty": penalty, "metrics": metrics(predict(model, valid)[0]), "solver": model["solver"]})
        selected[label] = min(validation[label], key=lambda x: (x["metrics"]["weighted_rmse"], -x["defender_penalty"]))["defender_penalty"]
        final_rows = train + valid
        models[label], predictions[label], evaluation[label], sensitivity[label] = {}, {}, {}, []
        for variant in ("team", "defender"):
            model = fit(final_rows, view=view, variant=variant, plan=plan, defender_penalty=selected[label])
            models[label][variant] = model
            pred, audit = predict(model, test)
            predictions[label][variant] = pred
            evaluation[label][variant] = {**metrics(pred), **audit}
        for penalty in plan["defender_penalties"]:
            model = models[label]["defender"] if penalty == selected[label] else fit(final_rows, view=view, variant="defender", plan=plan, defender_penalty=penalty)
            # Preserve all sensitivity state/predictions for replay and common-penalty comparisons.
            key = "penalty_" + str(penalty)
            models[label][key] = model
            predictions[label][key], _ = predict(model, test)
            sensitivity[label].append({"defender_penalty": penalty, "test": metrics(predictions[label][key]),
                                       "coefficient_change_from_selected": coefficient_agreement(model, models[label]["defender"])})
        evaluation[label]["defender_vs_team"] = paired_rmse_interval(predictions[label]["defender"], predictions[label]["team"],
                                                                   seed=plan["seed"], replicates=plan["bootstrap_replicates"])
        diagnostics[label] = identification(final_rows, view, relative_tolerance=plan["rank_relative_tolerance"])
    comparisons = {key: paired_rmse_interval(predictions["degraded"][key], predictions["rich"][key], seed=plan["seed"],
                                             replicates=plan["bootstrap_replicates"]) for key in predictions["rich"]}
    agreement = {key: coefficient_agreement(models["rich"][key], models["degraded"][key]) for key in predictions["rich"] if key != "team"}
    report = {"experiment_version": 1, "plan": plan, "split_games": splits, "cohort_sha256": rich["cohort_sha256"],
              "selected_defender_penalties": selected, "validation": validation, "evaluation": evaluation,
              "degraded_minus_rich": comparisons, "coefficient_agreement": agreement, "penalty_sensitivity": sensitivity,
              "identification": diagnostics, "selection": selection, "ranking_ready": False, "individual_attribution_validated": False,
              "benchmark_contrasts_computed": False, "qualification_computed": False, "live_source_equivalence_validated": False,
              "scope": "Historical play-to-game aggregation diagnostic; no positional CAVAA or causal attribution"}
    return report, models, predictions
