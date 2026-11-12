"""Bounded open Fejer/Smolyak integration; errors are estimated, not certified.

The nested difference construction is independent of the Genz-Malik controller.
Signed quadrature weights are never used as posterior probabilities. Node keys
are integer dyadic angles; integrand vectors are streamed, not cached in full.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import comb

import numpy as np


@lru_cache(maxsize=10)
def fejer(level):
    """Open second-rule weights on [0, 1], from the explicit sine series."""
    if type(level) is not int or not 1 <= level <= 10:
        raise ValueError("reviewed Fejer levels are integers from 1 to 10")
    denominator = 2**level
    theta = np.pi * np.arange(1, denominator) / denominator
    odd = np.arange(1, denominator, 2)
    weights = 2 * np.sin(theta) / denominator * (np.sin(np.outer(theta, odd)) @ (1.0 / odd))
    nodes = (1 + np.cos(theta)) / 2
    if np.any(weights <= 0) or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-13):
        raise ValueError("invalid Fejer rule weights")
    nodes.setflags(write=False)
    weights.setflags(write=False)
    return nodes, weights


def compositions(total, dimensions):
    if dimensions == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for rest in compositions(total - first, dimensions - 1):
                yield (first, *rest)


def point_count(dimensions, level):
    if type(dimensions) is not int or not 1 <= dimensions <= 4:
        raise ValueError("reviewed sparse dimensions are integers from 1 to 4")
    if type(level) is not int or not 0 <= level <= 9:
        raise ValueError("reviewed sparse levels are integers from 0 to 9")
    return sum(2**s * comb(s + dimensions - 1, dimensions - 1) for s in range(level + 1))


def grid(dimensions, level):
    """Return nested nodes, all complete-level weights and each node's birth level."""
    expected = point_count(dimensions, level)
    rules = []
    for r in range(level + 1):
        difference = fejer(r + 1)[1].copy()
        if r:
            difference[1::2] -= fejer(r)[1]
        keys = np.arange(1, 2 ** (r + 1)) * 2 ** (level - r)
        rules.append(list(zip(keys.tolist(), difference.tolist())))
    weights = {}
    for total in range(level + 1):
        for powers in compositions(total, dimensions):
            for terms in product(*(rules[r] for r in powers)):
                key = tuple(t[0] for t in terms)
                if key not in weights:
                    weights[key] = np.zeros(level + 1)
                value = 1.0
                for _, weight in terms:
                    value *= weight
                weights[key][total] += value
    if len(weights) != expected:
        raise ValueError("sparse node-count contract failed")

    def birth(key):
        return sum(level - ((k & -k).bit_length() - 1) for k in key)

    keys = sorted(weights, key=lambda key: (birth(key), key))
    born = np.array([birth(key) for key in keys])
    nodes = (1 + np.cos(np.pi * np.asarray(keys) / 2 ** (level + 1))) / 2
    cumulative = np.cumsum(np.array([weights[key] for key in keys]), axis=1)
    if (
        np.any((nodes <= 0) | (nodes >= 1))
        or not np.isfinite(cumulative).all()
        or not np.allclose(cumulative.sum(axis=0), 1, rtol=0, atol=1e-11)
    ):
        raise ValueError("invalid sparse grid nodes or mass")
    return nodes, cumulative, born


@dataclass
class Result:
    estimate: np.ndarray
    error: np.ndarray
    status: str
    evaluations: int
    level: int
    level_limit: int
    history: list[dict]


def integrate(f, dimensions, *, rtol, atol, max_level, max_evaluations):
    """Require two small complete-level increments; never consume a partial level."""
    point_count(dimensions, max_level)
    if (
        not np.isfinite([rtol, atol]).all()
        or rtol < 0
        or atol < 0
        or rtol + atol <= 0
        or type(max_evaluations) is not int
        or max_evaluations < 1
    ):
        raise ValueError("positive finite accuracy and integer evaluation budget required")
    limit = max_level
    while point_count(dimensions, limit) > max_evaluations:
        limit -= 1
    nodes, weights, born = grid(dimensions, limit)
    sums = corrections = absolute = None
    history, previous = [], []
    used = 0
    for level in range(limit + 1):
        end = int(np.searchsorted(born, level, side="right"))
        for start in range(used, end, 128):
            stop = min(start + 128, end)
            values = np.asarray(f(nodes[start:stop]), dtype=float)
            if (
                values.ndim != 2
                or values.shape[0] != stop - start
                or values.shape[1] < 1
                or not np.isfinite(values).all()
            ):
                raise ValueError("finite vector reference integrand required")
            if sums is None:
                sums = np.zeros((limit + 1, values.shape[1]))
                corrections, absolute = np.zeros_like(sums), np.zeros_like(sums)
            if values.shape[1] != sums.shape[1]:
                raise ValueError("reference component count changed")
            contribution = weights[start:stop].T @ values
            adjusted = contribution - corrections
            total = sums + adjusted
            corrections = (total - sums) - adjusted
            sums = total
            absolute += np.abs(weights[start:stop]).T @ np.abs(values)
        used = end
        estimate = sums[level].copy()
        if not np.isfinite(estimate).all() or not np.isfinite(absolute).all():
            raise ValueError("unrepresentable sparse integral")
        floor = 50 * np.finfo(float).eps * absolute[level]
        error = (
            np.maximum(np.abs(estimate - previous[-1]), np.abs(previous[-1] - previous[-2])) + floor
            if len(previous) >= 2
            else np.full_like(estimate, np.inf)
        )
        ratio = float(np.max(error / (atol + rtol * np.abs(estimate))))
        converged = level >= 4 and ratio <= 1
        history.append(
            dict(
                level=level,
                evaluations=used,
                maximum_error_ratio=ratio if np.isfinite(ratio) else None,
            )
        )
        previous.append(estimate)
        if converged or level == limit:
            return Result(
                estimate,
                error,
                "converged" if converged else "not_converged",
                used,
                level,
                limit,
                history,
            )
