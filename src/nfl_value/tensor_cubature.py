"""Small bounded high-order tensor comparison, with estimated successive-rule errors."""

from dataclasses import dataclass

import numpy as np
from scipy.special import roots_hermitenorm, roots_legendre


def rule(method, order):
    if type(order) is not int or not 1 <= order <= 31:
        raise ValueError("reviewed tensor order must be an integer from 1 to 31")
    if method == "gauss-legendre":
        nodes, weights = roots_legendre(order)
        nodes, weights = (nodes + 1) / 2, weights / 2
    elif method == "gauss-hermite":
        nodes, weights = roots_hermitenorm(order)
        weights = weights / np.sqrt(2 * np.pi)
    else:
        raise ValueError("unknown tensor reference rule")
    if (
        not np.isfinite([nodes, weights]).all()
        or np.any(weights <= 0)
        or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-13)
    ):
        raise ValueError("invalid tensor rule")
    return nodes, weights


@dataclass
class Result:
    estimate: np.ndarray
    error: np.ndarray
    status: str
    evaluations: int
    order: int
    history: list[dict]


def integrate(f, dimensions, *, method, rtol, atol, max_evaluations):
    if (
        type(dimensions) is not int
        or not 1 <= dimensions <= 4
        or not np.isfinite([rtol, atol]).all()
        or rtol < 0
        or atol < 0
        or rtol + atol <= 0
        or type(max_evaluations) is not int
        or max_evaluations < 7**dimensions
    ):
        raise ValueError("finite accuracy and budget for a complete tensor rule required")
    previous, history, used, components = None, [], 0, None
    for order in [7, 11, 15]:
        size = order**dimensions
        if used + size > max_evaluations:
            break
        x, w = rule(method, order)
        indices = np.indices((order,) * dimensions).reshape(dimensions, -1).T
        estimate = compensation = absolute = None
        for start in range(0, size, 128):
            selected = indices[start : start + 128]
            values = np.asarray(f(x[selected]), dtype=float)
            if (
                values.ndim != 2
                or values.shape[0] != len(selected)
                or values.shape[1] < 1
                or not np.isfinite(values).all()
            ):
                raise ValueError("finite vector reference integrand required")
            if components is None:
                components = values.shape[1]
            if values.shape[1] != components:
                raise ValueError("reference component count changed")
            if estimate is None:
                estimate = np.zeros(components)
                compensation, absolute = np.zeros_like(estimate), np.zeros_like(estimate)
            weights = np.prod(w[selected], axis=1)
            term = weights @ values - compensation
            total = estimate + term
            compensation = (total - estimate) - term
            estimate = total
            absolute += weights @ np.abs(values)
        used += size
        if not np.isfinite([estimate, absolute]).all():
            raise ValueError("unrepresentable tensor integral")
        error = (
            2 * np.abs(estimate - previous) + 50 * np.finfo(float).eps * absolute
            if previous is not None
            else np.full_like(estimate, np.inf)
        )
        ratio = float(np.max(error / (atol + rtol * np.abs(estimate))))
        history.append(
            dict(
                order=order,
                evaluations=used,
                maximum_error_ratio=ratio if np.isfinite(ratio) else None,
            )
        )
        converged = previous is not None and ratio <= 1
        result = Result(
            estimate, error, "converged" if converged else "not_converged", used, order, history
        )
        if converged:
            return result
        previous = estimate
    return result
