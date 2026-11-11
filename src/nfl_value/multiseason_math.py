"""Preplay multi-season QB designs and a declared finite prior over variances."""

from collections import Counter, defaultdict
from itertools import product
from math import isfinite

import numpy as np
from scipy import sparse
from scipy.linalg import qr

from nfl_value.baseline import features
from nfl_value.variance_mixture import system


GROUPS = {
    "evolving": ("qb", "innovation", "offense", "defense"),
    "persistent": ("qb", "offense", "defense"),
    "team": ("offense", "defense"),
    "qb_proxy": ("qb", "innovation", "defense"),
}
KEYS = set(
    "plan_version seasons scoring_season primary variants precision_grid innovation_sd_ratio noise_prior_shape noise_prior_scale prior_qb_precision_tilts simulation_replicates simulation_seed simulation_scenarios stress_effect_sd stress_noise_sd quantile_iterations null_relative_cutoff future_test defense_through_week defense_team_precision defense_context_precision".split()
)


def validate_plan(plan):
    if set(plan) != KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported multi-season plan")
    if plan["variants"] != list(GROUPS) or plan["primary"] != "evolving":
        raise ValueError("unreviewed model alternatives")
    seasons = plan["seasons"]
    if (
        not isinstance(seasons, list)
        or len(seasons) < 2
        or any(type(s) is not int or not 1999 <= s <= 2100 for s in seasons)
        or sorted(set(seasons)) != seasons
        or type(plan["scoring_season"]) is not int
        or plan["scoring_season"] != seasons[-1]
    ):
        raise ValueError("ordered distinct seasons ending with scoring season required")
    grid = plan["precision_grid"]
    numeric = [
        *grid,
        plan["innovation_sd_ratio"],
        plan["noise_prior_shape"],
        plan["noise_prior_scale"],
        plan["stress_noise_sd"],
        *plan["stress_effect_sd"].values(),
        plan["null_relative_cutoff"],
        plan["defense_team_precision"],
        plan["defense_context_precision"],
    ]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v <= 0
        for v in numeric
    ):
        raise ValueError("positive finite prior and experiment settings required")
    if (
        sorted(set(grid)) != grid
        or not 2 <= len(grid) <= 5
        or plan["noise_prior_shape"] <= 1
        or plan["null_relative_cutoff"] >= 1
    ):
        raise ValueError("invalid finite variance grid or noise prior")
    if (
        plan["prior_qb_precision_tilts"] != [-0.5, 0.5]
        or plan["innovation_sd_ratio"] != 1.0
        or set(plan["stress_effect_sd"]) != {"qb", "innovation", "offense", "defense", "game"}
        or plan["simulation_scenarios"]
        != ["finite_hierarchy", "continuous_hierarchy", "fixed_year_changes"]
    ):
        raise ValueError("unreviewed sensitivity or calibration policy")
    for k, low, high in [
        ("simulation_replicates", 2, 1024),
        ("simulation_seed", 1, 2**32 - 1),
        ("quantile_iterations", 16, 64),
        ("defense_through_week", 1, 18),
    ]:
        if type(plan[k]) is not int or not low <= plan[k] <= high:
            raise ValueError("invalid bounded experiment setting")
    future = plan["future_test"]
    if (
        set(future) != {"season", "weeks", "fitting_update_allowed"}
        or future["season"] != seasons[-1]
        or future["fitting_update_allowed"] is not False
        or not future["weeks"]
        or any(type(w) is not int or not 1 <= w <= 18 for w in future["weeks"])
        or sorted(set(future["weeks"])) != future["weeks"]
    ):
        raise ValueError("explicit future evaluation window without fitting updates required")


def row_features(row, variant):
    season = row["game_id"].split("_")[0]
    result = features(row, "context")
    result["context/season_" + season] = 1.0
    values = {
        "qb": row["qb"],
        "innovation": f"{season}/{row['qb']}",
        "offense": f"{season}/{row['offense_team']}",
        "defense": f"{season}/{row['defense_team']}",
    }
    result.update({f"{g}/{values[g]}": 1.0 for g in GROUPS[variant]})
    return result


def matrix(rows, names, variant):
    index = {n: i for i, n in enumerate(names)}
    ii, jj, vv, unseen = [], [], [], Counter()
    for i, row in enumerate(rows):
        for key, value in row_features(row, variant).items():
            if key in index and value != 0:
                ii.append(i)
                jj.append(index[key])
                vv.append(value)
            elif key not in index and not key.startswith("context/"):
                unseen[key.split("/")[0]] += 1
    x = sparse.csr_matrix((vv, (ii, jj)), shape=(len(rows), len(names)))
    return x, dict(sorted(unseen.items()))


def design(rows, variant, *, scoring_season, extra_qbs=()):
    if variant not in GROUPS or not rows:
        raise ValueError("known multi-season variant and observations required")
    dictionaries = [row_features(p, variant) for p in rows]
    vocabulary = {k for d in dictionaries for k in d}
    context = sorted(k for k in vocabulary if k.startswith("context/"))
    fixed = np.array([[d.get(k, 0.0) for k in context] for d in dictionaries])
    _, upper, pivots = qr(fixed, mode="economic", pivoting=True)
    diagonal = np.abs(np.diag(upper))
    rank = int(np.sum(diagonal > max(fixed.shape) * np.finfo(float).eps * diagonal.max()))
    keep = set(pivots[:rank])
    retained = [k for i, k in enumerate(context) if i in keep]
    random = {k for k in vocabulary if not k.startswith("context/")}
    for player in extra_qbs:
        if "qb" in GROUPS[variant]:
            random.add("qb/" + player)
        if "innovation" in GROUPS[variant]:
            random.add(f"innovation/{scoring_season}/{player}")
    names = retained + sorted(random)
    x, _ = matrix(rows, names, variant)
    prepared = system(x, names, rank, [p["game_id"] for p in rows])
    return prepared, [k for i, k in enumerate(context) if i not in keep]


def variance_cells(prepared, variant, plan):
    groups = [g for g in GROUPS[variant] if g != "innovation"] + ["game"]
    settings = [
        dict(zip(groups, values)) for values in product(plan["precision_grid"], repeat=len(groups))
    ]
    cells = []
    for values in settings:
        penalty = np.zeros(len(prepared.names))
        for j, name in enumerate(prepared.names[prepared.fixed_count :], prepared.fixed_count):
            group = name.split("/")[0]
            penalty[j] = (
                values["qb"] / plan["innovation_sd_ratio"] ** 2
                if group == "innovation"
                else values[group]
            )
        cells.append(
            {
                "precision": values,
                "penalty": penalty,
                "game_precision": values["game"],
                "log_prior": -np.log(len(settings)),
            }
        )
    return cells


def contrast(names, player, opportunities, weights, *, season):
    if not weights or not np.isclose(sum(weights.values()), 1.0, atol=1e-12, rtol=0):
        raise ValueError("normalized positional benchmark required")
    if any(not isfinite(w) or w < 0 for w in weights.values()) or opportunities < 0:
        raise ValueError("invalid benchmark weights or opportunity count")
    index = {n: j for j, n in enumerate(names)}
    result = np.zeros(len(names))
    prefixes = ["qb/"] + (
        [f"innovation/{season}/"] if any(n.startswith("innovation/") for n in names) else []
    )
    for prefix in prefixes:
        required = {prefix + player, *(prefix + p for p in weights)}
        if not required <= set(index):
            raise ValueError("observed and cold benchmark parameters must remain in design")
        result[index[prefix + player]] += opportunities
        for other, weight in weights.items():
            result[index[prefix + other]] -= opportunities * weight
    return result


def identification(prepared, contrasts, tolerance):
    gram = np.block(
        [[prepared.gram, prepared.game_x.T], [prepared.game_x, np.diag(prepared.game_counts)]]
    )
    eigenvalues, vectors = np.linalg.eigh(gram)
    null = vectors[:, eigenvalues <= max(eigenvalues.max(), 1.0) * tolerance]
    l = np.column_stack([contrasts, np.zeros((len(contrasts), len(prepared.game_names)))])
    projection = np.linalg.norm(l @ null, axis=1) / np.maximum(np.linalg.norm(l, axis=1), 1e-30)
    return {
        "columns": len(gram),
        "rank": len(gram) - null.shape[1],
        "null_dimension": null.shape[1],
        "relative_null_projection": projection.tolist(),
        "nonestimable_contrasts": int(np.sum(projection > 1e-7)),
        "meaning": "Unrestricted fixed-effect attribution is unidentified; the hierarchy selects allocations through explicit assumptions.",
    }


def allocation_witness(prepared, rows, contrasts, *, evolving):
    adjacency = defaultdict(set)
    for p in rows:
        season = p["game_id"].split("_")[0]
        a = f"innovation/{season}/{p['qb']}" if evolving else "qb/" + p["qb"]
        b = f"offense/{season}/{p['offense_team']}"
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
                -0.25
                if n in component and n.startswith("offense/")
                else 0.25
                if n in component
                else 0.0
                for n in prepared.names
            ]
        )
        cases.append(
            {
                "features": sorted(component),
                "max_prediction_change_ep": float(np.max(np.abs(prepared.x @ shift))),
                "max_absolute_contrast_change_ep": float(np.max(np.abs(contrasts @ shift))),
            }
        )
    return {
        "connected_components": len(cases),
        "example": max(cases, key=lambda c: c["max_absolute_contrast_change_ep"]),
        "scope": "QB/offense-team-season incidence subsystem; full-design null projection reported separately.",
    }


def posterior_diagnostics(cells, weights, plan):
    return {
        g: {
            str(value): float(
                weights[[c["precision"][g] == value for c in cells]].sum(axis=0).mean()
            )
            for value in plan["precision_grid"]
        }
        for g in cells[0]["precision"]
    }
