"""Bounded binary Genz–Malik refinement for the frozen variance reference.

Only the pinned SciPy rule data are reused. The controller and finite-difference
axis choice are separate from scipy.integrate.cubature's all-axis subdivision.
Errors are estimates, not rigorous bounds for arbitrary integrands.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate._rules import GenzMalikCubature


@dataclass
class Region:
    low: np.ndarray
    high: np.ndarray
    estimate: np.ndarray
    error: np.ndarray
    axis: int


@dataclass
class Result:
    estimate: np.ndarray
    error: np.ndarray
    status: str
    subdivisions: int
    evaluations: int
    axis_splits: list[int]


class Rule:
    """Checked adapter to an intentionally pinned private dependency API."""

    def __init__(self, dimensions):
        if dimensions not in (2, 3, 4):
            raise ValueError("reviewed reference dimensions are 2, 3 and 4")
        rule = GenzMalikCubature(dimensions)
        self.nodes, self.high_weights = map(np.asarray, rule.nodes_and_weights)
        lower, lower_weights = map(np.asarray, rule.lower_nodes_and_weights)
        expected = 1 + 2 * dimensions * (dimensions + 1) + 2**dimensions
        index = {tuple(row): i for i, row in enumerate(self.nodes)}
        if (
            self.nodes.shape != (expected, dimensions)
            or len(index) != expected
            or self.high_weights.shape != (expected,)
            or lower.shape != (expected - 2**dimensions, dimensions)
            or lower_weights.shape != (len(lower),)
            or not all(tuple(row) in index for row in lower)
        ):
            raise ValueError("pinned Genz–Malik node contract changed")
        self.low_weights = np.zeros(expected)
        self.low_weights[[index[tuple(row)] for row in lower]] = lower_weights
        if not all(
            np.isfinite(w).all() and np.isclose(w.sum(), 2**dimensions, rtol=0, atol=1e-12)
            for w in [self.high_weights, self.low_weights]
        ):
            raise ValueError("pinned Genz–Malik weight contract changed")
        self.center = index.get((0.0,) * dimensions)
        self.axes = []
        for j in range(dimensions):
            indices = []
            for radius in [np.sqrt(9 / 70), np.sqrt(9 / 10)]:
                for sign in [-1, 1]:
                    point = np.zeros(dimensions)
                    point[j] = sign * radius
                    indices.append(index.get(tuple(point)))
            self.axes.append(indices)
        if self.center is None or any(i is None for a in self.axes for i in a):
            raise ValueError("pinned Genz–Malik axis nodes changed")

    def region(self, f, low, high):
        half, middle = (high - low) / 2, (high + low) / 2
        values = np.asarray(f(middle + self.nodes * half), dtype=float)
        if (
            values.ndim != 2
            or values.shape[0] != len(self.nodes)
            or values.shape[1] < 1
            or not np.isfinite(values).all()
        ):
            raise ValueError("finite vector reference integrand required")
        volume = float(np.prod(half))
        high_value = volume * (self.high_weights @ values)
        low_value = volume * (self.low_weights @ values)
        rounding = 50 * np.finfo(float).eps * volume * (np.abs(self.high_weights) @ np.abs(values))
        error = np.maximum(np.abs(high_value - low_value), rounding)
        indicators = []
        for ia, ib, ic, id_ in self.axes:
            small = values[ia] + values[ib] - 2 * values[self.center]
            large = values[ic] + values[id_] - 2 * values[self.center]
            indicators.append(float(np.max(np.abs(large - 7 * small))))
        choices = np.flatnonzero(indicators == np.max(indicators))
        axis = int(choices[np.argmax(half[choices])])
        if not np.isfinite(high_value).all() or not np.isfinite(error).all():
            raise ValueError("unrepresentable reference rule estimate")
        return Region(low.copy(), high.copy(), high_value, error, axis)


def integrate(f, low, high, *, rtol, atol, max_subdivisions):
    """Retain complete leaves and sum their nonnegative error estimates."""
    low, high = np.asarray(low, dtype=float), np.asarray(high, dtype=float)
    if (
        low.ndim != 1
        or high.shape != low.shape
        or not np.isfinite([low, high]).all()
        or np.any(high <= low)
        or not np.isfinite([rtol, atol]).all()
        or rtol < 0
        or atol < 0
        or rtol + atol <= 0
        or type(max_subdivisions) is not int
        or max_subdivisions < 0
    ):
        raise ValueError("finite ordered bounds and bounded positive accuracy policy required")
    rule = Rule(len(low))
    regions = [rule.region(f, low, high)]
    splits = [0] * len(low)
    for count in range(max_subdivisions + 1):
        estimate = np.sum([r.estimate for r in regions], axis=0)
        error = np.sum([r.error for r in regions], axis=0)
        converged = bool(np.all(error <= atol + rtol * np.abs(estimate)))
        if converged or count == max_subdivisions:
            return Result(
                estimate,
                error,
                "converged" if converged else "not_converged",
                count,
                (1 + 2 * count) * len(rule.nodes),
                splits,
            )
        index = int(np.argmax([np.max(r.error) for r in regions]))
        parent = regions[index]
        j = parent.axis
        middle = (parent.low[j] + parent.high[j]) / 2
        if not parent.low[j] < middle < parent.high[j]:
            raise ValueError("reference subdivision exhausted floating point resolution")
        first_high, second_low = parent.high.copy(), parent.low.copy()
        first_high[j] = second_low[j] = middle
        first = rule.region(f, parent.low, first_high)
        second = rule.region(f, second_low, parent.high)
        regions[index] = first
        regions.append(second)
        splits[j] += 1
