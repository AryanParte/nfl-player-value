"""Post-result analytic mechanism check; no fitted alternative or admission gate."""

import json

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def log_derivative_ratio(x, remote_mass):
    x = np.asarray(x, float)
    if not 0 < remote_mass < 1 or np.any((x <= 0) | (x >= 4)):
        raise ValueError("ratio is defined only between the two component means")
    return (
        np.log(remote_mass / (1 - remote_mass) / 8)
        + np.log((4 - x) / x)
        + x * x / 2
        - (x - 4) ** 2 / 8
    )


def marginal_derivative(x, remote_mass):
    return -(1 - remote_mass) * x * norm.pdf(x) - remote_mass * (x - 4) / 4 * norm.pdf(
        x, loc=4, scale=2
    )


def diagnose(remote_mass=0.05):
    roots = np.roots([3, -8, -16, 16])
    critical = sorted(float(x.real) for x in roots if abs(x.imag) < 1e-10 and 0 < x.real < 4)
    edges = [1e-10, *critical, 4 - 1e-10]
    stationary = []
    for a, b in zip(edges[:-1], edges[1:]):
        ga, gb = log_derivative_ratio(np.array([a, b]), remote_mass)
        if ga * gb < 0:
            root = brentq(lambda x: float(log_derivative_ratio(x, remote_mass)), a, b, xtol=1e-13)
            stationary.append(
                dict(
                    x=root,
                    kind="mode" if ga > 0 else "minimum",
                    direct_derivative=float(marginal_derivative(root, remote_mass)),
                )
            )
    return dict(
        remote_mass=remote_mass,
        critical_ratio_points=critical,
        critical_log_derivative_ratios=log_derivative_ratio(critical, remote_mass).tolist(),
        stationary_points=stationary,
        fine_target_modes=sum(p["kind"] == "mode" for p in stationary),
        caveat="Unperturbed fine-target first-coordinate marginal only; other coordinates factor as standard normals. Monotonic intervals use analytic derivative roots evaluated in floating point, without interval-arithmetic certification. Not the exact sine-tilted coarse target, a fresh integration trial or an oracle candidate.",
    )


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2, allow_nan=False))
