"""Additive contrasts with joint, explicitly conditional Gaussian uncertainty."""

from math import isfinite, sqrt

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from nfl_value.baseline import ACTORS, design
from nfl_value.benchmarks import validate_player_id
from nfl_value.ingestion import json_bytes, sha256


SCOPES = {
    "QB": ("dropback", "carry"),
    "RB": ("carry", "target"),
    "WR": ("target",),
    "TE": ("target",),
}
UNCERTAINTY = "conditional-gaussian-plugin-iid-v1"
EXPOSURE = "full-observed-single-team-window-v1"
PLAN_KEYS = {
    "plan_version",
    "windows",
    "roles",
    "primary_actor_penalty",
    "actor_penalties",
    "context_penalty",
    "team_penalty",
    "qualification_multipliers",
    "uncertainty",
    "exposure_policy",
    "allow_retrospective",
}


def validate_plan(plan: dict) -> None:
    if set(plan) != PLAN_KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported contrast plan")
    if plan["roles"] != list(SCOPES) or plan["qualification_multipliers"] != [0.75, 1.0, 1.25]:
        raise ValueError("unreviewed role or qualification grid")
    if any(type(v) not in (int, float) for v in plan["qualification_multipliers"]):
        raise ValueError("numeric qualification multipliers required")
    if plan["uncertainty"] != UNCERTAINTY or plan["exposure_policy"] != EXPOSURE:
        raise ValueError("unreviewed uncertainty or exposure policy")
    if type(plan["allow_retrospective"]) is not bool:
        raise ValueError("retrospective use must be explicit")
    windows = plan["windows"]
    if not isinstance(windows, dict) or not windows:
        raise ValueError("season windows required")
    for season, weeks in windows.items():
        if not isinstance(season, str) or not season.isdecimal() or not 2025 <= int(season) <= 2100:
            raise ValueError("unreviewed contrast season")
        if (
            not isinstance(weeks, list)
            or not weeks
            or any(type(w) is not int or not 1 <= w <= 18 for w in weeks)
        ):
            raise ValueError("invalid contrast weeks")
        if weeks != sorted(set(weeks)):
            raise ValueError("contrast weeks must be unique and increasing")
    penalties = plan["actor_penalties"]
    if not isinstance(penalties, list) or not penalties or len(penalties) != len(set(penalties)):
        raise ValueError("distinct penalty grid required")
    for value in [
        *penalties,
        plan["primary_actor_penalty"],
        plan["context_penalty"],
        plan["team_penalty"],
    ]:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError("finite positive penalties required")
    if plan["primary_actor_penalty"] not in penalties:
        raise ValueError("primary penalty outside declared grid")


def fit_joint(rows: list[dict], candidates: dict, *, plan: dict, actor_penalty: float):
    """Equivalent ridge objective with explicit prior-only candidate parameters.

    This is a within-prefix descriptive fit, not a new predictive validation.
    Keep the existing baseline fit/replay unchanged. Covariance is transient;
    saved means/contrasts are rebuilt with numerical tolerance during replay.
    """
    validate_plan(plan)
    if not rows or isinstance(actor_penalty, bool) or actor_penalty not in plan["actor_penalties"]:
        raise ValueError("nonempty rows and declared penalty required")
    for role, players in candidates.items():
        if role not in SCOPES or len(players) != len(set(players)):
            raise ValueError("unsupported role or duplicate candidate")
        for player in players:
            validate_player_id(player)
    _, observed_names, _ = design(rows, "joint")
    extra = {
        f"{component}/{player}"
        for role, players in candidates.items()
        for player in players
        for component in SCOPES[role]
    }
    names = sorted(set(observed_names) | extra)
    x, _, unseen = design(rows, "joint", names)
    if unseen:
        raise ValueError("joint fit omitted an observed feature")
    penalties = np.array(
        [
            0.0
            if n == "context/intercept"
            else actor_penalty
            if n.split("/")[0] in ACTORS
            else plan["context_penalty"]
            if n.startswith(("context/", "observed_role/"))
            else plan["team_penalty"]
            for n in names
        ]
    )
    y = np.array([p["offense_epa"] for p in rows], dtype=float)
    h = (x.T @ x).toarray() + np.diag(penalties)
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(h)):
        raise ValueError("nonfinite joint system")
    try:
        factor = cho_factor(h, lower=True, check_finite=True)
        mean = cho_solve(factor, np.asarray(x.T @ y).ravel())
        inverse = cho_solve(factor, np.eye(len(names)))
    except np.linalg.LinAlgError as exc:
        raise ValueError("joint precision is not positive definite") from exc
    residual = y - np.asarray(x @ mean).ravel()
    noise_variance = float(residual @ residual / len(rows))
    if not isfinite(noise_variance) or noise_variance <= 0:
        raise ValueError("positive residual scale required for conditional uncertainty")
    covariance = noise_variance * inverse
    if not np.all(np.isfinite(mean)) or not np.all(np.isfinite(covariance)):
        raise ValueError("nonfinite joint fit or conditional covariance")
    cold = [
        names[i]
        for i, count in enumerate(x.getnnz(axis=0))
        if count == 0 and names[i].split("/")[0] in ACTORS
    ]
    model = {
        "model_version": 1,
        "variant": "joint",
        "actor_penalty": actor_penalty,
        "features": names,
        "coefficients": mean.tolist(),
        "training_plays": len(rows),
        "training_games": sorted({p["game_id"] for p in rows}),
        "training_rows_sha256": sha256(json_bytes({"plays": rows})),
        "prior_only_actor_parameters": cold,
        "noise_variance_sse_over_n": noise_variance,
        "uncertainty": UNCERTAINTY,
        "uncertainty_calibrated": False,
    }
    return model, covariance


def contrast_vector(
    names: list[str], *, player: str, counts: dict[str, int], weights: dict[str, float]
) -> np.ndarray:
    """L for sum_k n_ik (beta_ik - sum_j w_j beta_jk)."""
    if len(set(names)) != len(names):
        raise ValueError("duplicate feature names")
    if not weights or any(
        isinstance(w, bool) or not isfinite(w) or w < 0 for w in weights.values()
    ):
        raise ValueError("finite nonnegative benchmark weights required")
    if not np.isclose(sum(weights.values()), 1.0, atol=1e-12, rtol=0):
        raise ValueError("benchmark weights must sum to one")
    index = {n: i for i, n in enumerate(names)}
    result = np.zeros(len(names))
    for component, count in counts.items():
        if component not in ACTORS or type(count) is not int or count < 0:
            raise ValueError("invalid component opportunity count")
        if not count:
            continue
        required = {f"{component}/{p}" for p in weights} | {f"{component}/{player}"}
        if not required <= index.keys():
            raise ValueError("missing focal or benchmark model parameter")
        result[index[f"{component}/{player}"]] += count
        for peer, weight in weights.items():
            result[index[f"{component}/{peer}"]] -= count * weight
    return result


def summarize_contrast(vector: np.ndarray, mean: np.ndarray, covariance: np.ndarray) -> dict:
    if vector.shape != mean.shape or covariance.shape != (len(mean), len(mean)):
        raise ValueError("contrast/covariance dimension mismatch")
    if not all(np.all(np.isfinite(x)) for x in (vector, mean, covariance)):
        raise ValueError("nonfinite contrast inputs")
    value = float(vector @ mean)
    nonzero = np.flatnonzero(vector)
    weights = vector[nonzero]
    variance = float(weights @ covariance[np.ix_(nonzero, nonzero)] @ weights)
    if variance < -1e-10:
        raise ValueError("negative contrast variance")
    se = sqrt(max(variance, 0.0))
    return {
        "contrast_ep": value,
        "conditional_standard_error_ep": se,
        "conditional_normal_95_interval_ep": [
            value - 1.959963984540054 * se,
            value + 1.959963984540054 * se,
        ],
        "uncertainty_calibrated": False,
    }
