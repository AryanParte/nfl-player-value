"""Deterministic finite variance-prior integration; no interval inflation or MCMC.

Random game intercepts are marginalized exactly. All other random coefficients
have variance sigma² / precision; fixed context has a common flat prior.
"""

from dataclasses import dataclass

import numpy as np
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from scipy.special import logsumexp, stdtr, stdtrit


@dataclass
class System:
    x: sparse.csr_matrix
    names: list[str]
    fixed_count: int
    gram: np.ndarray
    game_names: list[str]
    game_codes: np.ndarray
    game_counts: np.ndarray
    game_x: np.ndarray


def system(x, names, fixed_count, game_ids=None):
    x = sparse.csr_matrix(x, dtype=float)
    if x.shape[1] != len(names) or len(set(names)) != len(names) or not np.isfinite(x.data).all():
        raise ValueError("invalid mixture design")
    if type(fixed_count) is not int or not 0 < fixed_count < x.shape[0] or fixed_count > x.shape[1]:
        raise ValueError("invalid unpenalized context dimension")
    if game_ids is None:
        game_names, codes = [], np.zeros(x.shape[0], dtype=int)
        counts, gx = np.empty(0), np.empty((0, x.shape[1]))
    else:
        if len(game_ids) != x.shape[0] or any(not isinstance(g, str) or not g for g in game_ids):
            raise ValueError("one game ID per modeled row required")
        game_names = sorted(set(game_ids))
        index = {g: i for i, g in enumerate(game_names)}
        codes = np.array([index[g] for g in game_ids])
        z = sparse.csr_matrix(
            (np.ones(len(codes)), (codes, np.arange(len(codes)))),
            shape=(len(game_names), len(codes)),
        )
        counts = np.asarray(z.sum(axis=1)).ravel()
        gx = (z @ x).toarray()
    return System(x, names, fixed_count, (x.T @ x).toarray(), game_names, codes, counts, gx)


def response_stats(prepared, y):
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    if y.ndim != 2 or y.shape[0] != prepared.x.shape[0] or not np.isfinite(y).all():
        raise ValueError("finite response matrix matching design required")
    gy = np.zeros((len(prepared.game_names), y.shape[1]))
    if len(gy):
        np.add.at(gy, prepared.game_codes, y)
    return {"cross": np.asarray(prepared.x.T @ y), "yty": np.sum(y * y, axis=0), "game_y": gy}


def marginal_stats(prepared, stats, game_precision):
    """Only game precision changes the marginalized sufficient statistics."""
    gram, cross, yty = prepared.gram.copy(), stats["cross"].copy(), stats["yty"].copy()
    logdet_r = 0.0
    if prepared.game_names:
        if game_precision is None or not np.isfinite(game_precision) or game_precision <= 0:
            raise ValueError("positive game precision required")
        denominator = game_precision + prepared.game_counts
        gram -= prepared.game_x.T @ (prepared.game_x / denominator[:, None])
        cross -= prepared.game_x.T @ (stats["game_y"] / denominator[:, None])
        yty -= np.sum(stats["game_y"] ** 2 / denominator[:, None], axis=0)
        logdet_r = float(np.log1p(prepared.game_counts / game_precision).sum())
    elif game_precision is not None:
        raise ValueError("game precision requires a game design")
    return gram, cross, yty, logdet_r


def cell(
    prepared,
    stats,
    penalty,
    game_precision,
    contrasts,
    shape,
    scale,
    *,
    marginal=None,
    need_games=True,
):
    penalty = np.asarray(penalty, dtype=float)
    p, r = len(prepared.names), prepared.fixed_count
    if (
        penalty.shape != (p,)
        or not np.isfinite(penalty).all()
        or np.any(penalty[:r] != 0)
        or np.any(penalty[r:] <= 0)
    ):
        raise ValueError("positive random-effect and zero context precisions required")
    if not np.isfinite([shape, scale]).all() or shape <= 1 or scale <= 0:
        raise ValueError("proper finite-mean noise prior required")
    contrasts = np.asarray(contrasts, dtype=float)
    if contrasts.ndim != 2 or contrasts.shape[1] != p or not np.isfinite(contrasts).all():
        raise ValueError("invalid linear contrasts")
    gram, cross, yty, logdet_r = (
        marginal_stats(prepared, stats, game_precision) if marginal is None else marginal
    )
    h = gram + np.diag(penalty)
    factor = cho_factor(h, lower=True)
    mean = cho_solve(factor, cross)
    projected_inverse = cho_solve(factor, contrasts.T)
    diagonal = np.einsum("ij,ji->i", contrasts, projected_inverse)
    q = yty - np.sum(cross * mean, axis=0)
    if np.any(q < -1e-9 * (stats["yty"] + 1)) or np.any(diagonal < -1e-9):
        raise ValueError("negative mixture residual quadratic or contrast variance")
    q, diagonal = np.maximum(q, 0), np.maximum(diagonal, 0)
    a = shape + (prepared.x.shape[0] - r) / 2
    b = scale + q / 2
    determinant = logdet_r + 2 * np.log(np.diag(factor[0])).sum() - np.log(penalty[r:]).sum()
    log_likelihood = -0.5 * determinant - a * np.log(b)
    if not np.isfinite(mean).all() or not np.isfinite(log_likelihood).all():
        raise ValueError("nonfinite variance-mixture fit")
    game_mean = (
        (stats["game_y"] - prepared.game_x @ mean)
        / (game_precision + prepared.game_counts)[:, None]
        if prepared.game_names and need_games
        else np.empty((0, mean.shape[1]))
    )
    return {
        "mean": mean,
        "game_mean": game_mean,
        "location": contrasts @ mean,
        "diagonal": diagonal,
        "posterior_shape": a,
        "posterior_scale": b,
        "log_likelihood": log_likelihood,
    }


def integrate(prepared, y, contrasts, cells, *, shape, scale, progress=lambda _: None):
    """Cache the response-independent design; evaluate all synthetic responses together."""
    if not cells:
        raise ValueError("nonempty finite variance prior required")
    priors = np.array([item["log_prior"] for item in cells], dtype=float)
    if not np.isfinite(priors).all() or abs(float(logsumexp(priors))) > 1e-10:
        raise ValueError("normalized finite log prior required")
    stats = response_stats(prepared, y)
    locations, diagonals, scales, log_weights = [], [], [], []
    real_means, real_games = [], []
    marginalized = {}
    for i, item in enumerate(cells):
        game_precision = item["game_precision"]
        if game_precision not in marginalized:
            marginalized[game_precision] = marginal_stats(prepared, stats, game_precision)
        result = cell(
            prepared,
            stats,
            item["penalty"],
            game_precision,
            contrasts,
            shape,
            scale,
            marginal=marginalized[game_precision],
            need_games=stats["cross"].shape[1] == 1,
        )
        locations.append(result["location"])
        diagonals.append(result["diagonal"])
        scales.append(result["posterior_scale"])
        log_weights.append(result["log_likelihood"] + item["log_prior"])
        if stats["cross"].shape[1] == 1:
            real_means.append(result["mean"][:, 0])
            real_games.append(result["game_mean"][:, 0])
        if (i + 1) % 125 == 0:
            progress(f"Integrated {i + 1}/{len(cells)} variance cells")
    log_weights = np.asarray(log_weights)
    weights = np.exp(log_weights - logsumexp(log_weights, axis=0))
    result = {
        "location": np.asarray(locations),
        "diagonal": np.asarray(diagonals),
        "scale": np.asarray(scales),
        "shape": result["posterior_shape"],
        "weights": weights,
    }
    if real_means:
        result["coefficient_mean"] = weights[:, 0] @ np.asarray(real_means)
        result["game_mean"] = weights[:, 0] @ np.asarray(real_games)
    return result


def moments(result, weights=None):
    weights = result["weights"] if weights is None else weights
    location = result["location"]
    mean = np.sum(weights[:, None, :] * location, axis=0)
    within = result["diagonal"][:, :, None] * result["scale"][:, None, :] / (result["shape"] - 1)
    variance = np.sum(weights[:, None, :] * (within + (location - mean[None, :, :]) ** 2), axis=0)
    return mean, variance


def interval(result, *, iterations=48, weights=None, probability=0.95):
    weights = result["weights"] if weights is None else np.asarray(weights)
    if (
        weights.shape != result["weights"].shape
        or np.any(weights < 0)
        or not np.isfinite(weights).all()
        or not np.allclose(weights.sum(axis=0), 1.0, atol=1e-12, rtol=0)
    ):
        raise ValueError("normalized posterior cell weights required")
    if type(iterations) is not int or not 16 <= iterations <= 64 or not 0 < probability < 1:
        raise ValueError("invalid deterministic mixture quantile policy")
    location = result["location"]
    scales = np.sqrt(result["diagonal"][:, :, None] * result["scale"][:, None, :] / result["shape"])
    safe_scales = np.where(scales > 0, scales, 1.0)
    answers = []
    for probability in ((1 - probability) / 2, (1 + probability) / 2):
        endpoint = location + float(stdtrit(2 * result["shape"], probability)) * scales
        low, high = endpoint.min(axis=0), endpoint.max(axis=0)
        for _ in range(iterations):
            mid = (low + high) / 2
            cdf = stdtr(2 * result["shape"], (mid[None, :, :] - location) / safe_scales)
            cdf = np.where(scales > 0, cdf, (mid[None, :, :] >= location).astype(float))
            below = np.sum(weights[:, None, :] * cdf, axis=0) < probability
            low, high = np.where(below, mid, low), np.where(below, high, mid)
        answers.append((low + high) / 2)
    return tuple(answers)


def modal_interval(result):
    indices = np.argmax(result["weights"], axis=0)
    n = np.arange(len(indices))
    location = result["location"][indices, :, n].T
    scale = np.sqrt(
        result["diagonal"][indices].T * result["scale"][indices, n][None, :] / result["shape"]
    )
    half = float(stdtrit(2 * result["shape"], 0.975)) * scale
    return location - half, location + half
