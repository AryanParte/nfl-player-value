"""Small crossed-effects REML model for the preregistered QB recovery study.

No scores are admitted here. Empirical-Bayes covariance conditions on estimated
variance ratios; convergence is neither calibration nor individual identification.
"""

from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve, qr
from scipy.optimize import minimize

from nfl_value.baseline import features
from nfl_value.ingestion import json_bytes, sha256


GROUPS = {
    "team": ("offense", "defense", "game"),
    "qb_proxy": ("qb", "defense", "game"),
    "joint": ("qb", "offense", "defense", "game"),
    "fixed_precision": ("qb", "offense", "defense", "game"),
}


def row_features(row, groups):
    result = features(row, "context")
    values = {
        "qb": row["qb"],
        "offense": row["offense_team"],
        "defense": row["defense_team"],
        "game": row["game_id"],
    }
    result.update({f"{g}/{values[g]}": 1.0 for g in groups})
    return result


def matrix(rows, names, groups):
    if len(set(names)) != len(names):
        raise ValueError("duplicate model features")
    index = {n: j for j, n in enumerate(names)}
    x = np.zeros((len(rows), len(names)))
    unseen = Counter()
    for i, row in enumerate(rows):
        for key, value in row_features(row, groups).items():
            if key in index:
                x[i, index[key]] = value
            elif not key.startswith("context/"):
                unseen[key.split("/")[0]] += 1
    if not np.isfinite(x).all():
        raise ValueError("nonfinite design")
    return x, dict(unseen)


@dataclass
class Design:
    x: np.ndarray
    gram: np.ndarray
    names: list[str]
    groups: tuple[str, ...]
    fixed_count: int
    group_indices: list[np.ndarray]
    dropped_context: list[str]


def design(rows, variant, *, extra_qbs=()):
    if variant not in GROUPS or not rows:
        raise ValueError("declared variant and nonempty observations required")
    groups = GROUPS[variant]
    dictionaries = [row_features(p, groups) for p in rows]
    context = sorted(k for k in dictionaries[0] if k.startswith("context/"))
    f = np.array([[d[k] for k in context] for d in dictionaries])
    _, upper, pivots = qr(f, mode="economic", pivoting=True)
    diagonal = np.abs(np.diag(upper))
    rank = int(np.sum(diagonal > max(f.shape) * np.finfo(float).eps * diagonal.max()))
    keep = set(pivots[:rank])
    fixed = [k for i, k in enumerate(context) if i in keep]
    random = {k for d in dictionaries for k in d if not k.startswith("context/")}
    if "qb" in groups:
        random.update(f"qb/{p}" for p in extra_qbs)
    names = fixed + sorted(random)
    x, _ = matrix(rows, names, groups)
    if len(rows) <= rank + 2:
        raise ValueError("insufficient residual degrees of freedom")
    return Design(
        x,
        x.T @ x,
        names,
        groups,
        rank,
        [np.array([j for j, k in enumerate(names) if k.startswith(g + "/")]) for g in groups],
        [k for i, k in enumerate(context) if i not in keep],
    )


class RestrictedLikelihood:
    """Profiled observation-space REML via a small coefficient-space system."""

    def __init__(self, prepared, y):
        self.design = prepared
        self.y = np.asarray(y, dtype=float)
        if self.y.shape != (len(prepared.x),) or not np.isfinite(self.y).all():
            raise ValueError("finite response matching design required")
        self.cross = prepared.x.T @ self.y
        self.yty = float(self.y @ self.y)
        self.df = len(self.y) - prepared.fixed_count

    def solve(self, log_ratios):
        if np.shape(log_ratios) != (len(self.design.groups),) or not np.isfinite(log_ratios).all():
            raise ValueError("finite variance ratios required")
        ratios = np.exp(log_ratios)
        penalty = np.zeros(len(self.design.names))
        for value, indices in zip(ratios, self.design.group_indices):
            penalty[indices] = value
        h = self.design.gram + np.diag(penalty)
        factor = cho_factor(h, lower=True)
        mean = cho_solve(factor, self.cross)
        inverse = cho_solve(factor, np.eye(len(h)))
        q = self.yty - float(self.cross @ mean)
        if not np.isfinite(q) or q <= 0:
            raise ValueError("nonpositive restricted residual quadratic")
        logdet = 2 * np.log(np.diag(factor[0])).sum()
        objective = self.df * np.log(q / self.df) + logdet - np.log(penalty[penalty > 0]).sum()
        gradient = np.array(
            [
                self.df / q * value * (mean[indices] @ mean[indices])
                + value * np.diag(inverse)[indices].sum()
                - len(indices)
                for value, indices in zip(ratios, self.design.group_indices)
            ]
        )
        sigma2 = q / self.df
        if not np.isfinite(mean).all() or not np.isfinite(inverse).all():
            raise ValueError("nonfinite restricted fit")
        return float(objective), gradient, mean, sigma2 * inverse, float(sigma2)

    def objective(self, theta):
        result = self.solve(theta)
        return result[0], result[1]


def fit(prepared, y, plan, *, fixed=False):
    likelihood = RestrictedLikelihood(prepared, y)
    attempts = []
    low, high = np.log(plan["variance_ratio_bounds"])
    if fixed:
        theta = np.log([plan["fixed_penalties"][g] for g in prepared.groups])
    else:
        converged = []
        for start in plan["optimizer_starts"]:
            result = minimize(
                likelihood.objective,
                np.full(len(prepared.groups), np.log(start)),
                jac=True,
                method="L-BFGS-B",
                bounds=[(low, high)] * len(prepared.groups),
                options={
                    "maxiter": plan["optimizer_max_iterations"],
                    "ftol": plan["optimizer_ftol"],
                    "gtol": 1e-6,
                },
            )
            attempts.append(
                {
                    "start": start,
                    "converged": bool(result.success),
                    "objective": float(result.fun),
                    "iterations": int(result.nit),
                }
            )
            if result.success and np.isfinite(result.fun):
                converged.append(result)
        if not converged:
            raise ValueError("REML did not converge from any declared start")
        best = min(converged, key=lambda result: result.fun)
        if any(a["objective"] < best.fun - 1e-6 for a in attempts if not a["converged"]):
            raise ValueError("nonconverged start has a better objective; review optimizer")
        theta = best.x
    objective, _, mean, covariance, sigma2 = likelihood.solve(theta)
    ratios = np.exp(theta)
    model = {
        "features": prepared.names,
        "groups": list(prepared.groups),
        "fixed_context_rank": prepared.fixed_count,
        "dropped_context": prepared.dropped_context,
        "coefficients": mean.tolist(),
        "variance_ratios": dict(zip(prepared.groups, ratios.tolist())),
        "effect_variances": dict(zip(prepared.groups, (sigma2 / ratios).tolist())),
        "noise_variance": sigma2,
        "objective": objective,
        "optimizer_attempts": attempts,
        "boundary_groups": [
            g for g, t in zip(prepared.groups, theta) if min(t - low, high - t) < 1e-4
        ],
        "training_plays": len(prepared.x),
        "fixed_precision": fixed,
        "uncertainty": "empirical-bayes-conditional-reml-v1",
        "uncertainty_calibrated": False,
    }
    return model, covariance


def predict(model, rows):
    x, unseen = matrix(rows, model["features"], model["groups"])
    coef = np.asarray(model["coefficients"])
    if coef.shape != (x.shape[1],) or not np.isfinite(coef).all():
        raise ValueError("invalid fitted coefficients")
    prediction = x @ coef
    groups = ("context", *model["groups"])
    parts = {
        g: x[:, [j for j, n in enumerate(model["features"]) if n.startswith(g + "/")]]
        @ coef[[j for j, n in enumerate(model["features"]) if n.startswith(g + "/")]]
        for g in groups
    }
    output = []
    for i, row in enumerate(rows):
        components = {g: float(v[i]) for g, v in parts.items()}
        residual = row["offense_epa"] - float(prediction[i])
        if (
            not np.isfinite(prediction[i])
            or abs(sum(components.values()) + residual - row["offense_epa"]) > 1e-9
        ):
            raise ValueError("QB outcome accounting failed")
        output.append(
            {
                "game_id": row["game_id"],
                "play_id": row["play_id"],
                "offense_team": row["offense_team"],
                "qb": row["qb"],
                "observed_epa": row["offense_epa"],
                "predicted_epa": float(prediction[i]),
                "components": components,
                "residual": float(residual),
            }
        )
    return output, unseen


def contrast(names, player, count, weights):
    if not weights or not np.isclose(sum(weights.values()), 1, atol=1e-12, rtol=0):
        raise ValueError("normalized benchmark required")
    if (
        any(not np.isfinite(v) or v < 0 for v in weights.values())
        or type(count) is not int
        or count < 0
    ):
        raise ValueError("invalid benchmark or opportunity count")
    index = {n: j for j, n in enumerate(names)}
    if len(index) != len(names) or not {f"qb/{p}" for p in [player, *weights]} <= index.keys():
        raise ValueError("missing or duplicate QB parameters")
    result = np.zeros(len(names))
    result[index[f"qb/{player}"]] = count
    for peer, weight in weights.items():
        result[index[f"qb/{peer}"]] -= count * weight
    return result


def identification(prepared, contrasts):
    values, vectors = np.linalg.eigh(prepared.gram)
    null = vectors[:, values <= values[-1] * 1e-10]
    ratios = np.linalg.norm(contrasts @ null, axis=1) / np.maximum(
        np.linalg.norm(contrasts, axis=1), 1e-30
    )
    return {
        "columns": len(values),
        "numerical_rank": int(len(values) - null.shape[1]),
        "gram_relative_cutoff": 1e-10,
        "contrast_relative_cutoff": 1e-8,
        "relative_null_projection": ratios.tolist(),
        "nonestimable_contrasts": int(np.sum(ratios > 1e-8)),
        "interpretation": "Unrestricted fixed-effect identifiability; hierarchical allocation additionally assumes exchangeability and variance components.",
    }


def row_digest(rows):
    return sha256(json_bytes({"plays": rows}))
