"""Continuous log-variance integration with explicit importance-accuracy failures."""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import minimize
from scipy.special import logsumexp, ndtri
from scipy.stats import qmc

from nfl_value.variance_mixture import cell, interval, moments, normalized_weights, response_stats


def normal_logpdf(points, mean, covariance):
    points = np.atleast_2d(points)
    factor = np.linalg.cholesky(covariance)
    z = solve_triangular(factor, (points - mean).T, lower=True).T
    return (
        -0.5 * (np.sum(z * z, axis=1) + len(mean) * np.log(2 * np.pi))
        - np.log(np.diag(factor)).sum()
    )


def hessian(function, point, step):
    d = len(point)
    result = np.zeros((d, d))
    identity = np.eye(d) * step
    center = function(point)
    for i in range(d):
        result[i, i] = (
            function(point + identity[i]) + function(point - identity[i]) - 2 * center
        ) / step**2
        for j in range(i):
            result[i, j] = result[j, i] = (
                function(point + identity[i] + identity[j])
                - function(point + identity[i] - identity[j])
                - function(point - identity[i] + identity[j])
                + function(point - identity[i] - identity[j])
            ) / (4 * step**2)
    return result


@dataclass
class Proposal:
    means: list
    covariances: list
    masses: np.ndarray
    attempts: list
    mode: np.ndarray

    def draw(self, power, seed):
        uniform = qmc.Sobol(d=len(self.mode) + 1, scramble=True, seed=seed).random_base2(power)
        if np.any((uniform <= 0) | (uniform >= 1)):
            raise ValueError("non-interior Sobol coordinate")
        component = np.searchsorted(np.cumsum(self.masses), uniform[:, 0], side="right")
        z = ndtri(uniform[:, 1:])
        points = np.empty_like(z)
        for j, (mean, covariance) in enumerate(zip(self.means, self.covariances)):
            mask = component == j
            # Fixed-coordinate summation preserves exact prefixes across batch sizes.
            points[mask] = mean + np.einsum(
                "ij,kj->ik", z[mask], np.linalg.cholesky(covariance), optimize=False
            )
        return points, self.logpdf(points)

    def logpdf(self, points):
        return logsumexp(
            np.stack(
                [
                    np.log(w) + normal_logpdf(points, m, c)
                    for w, m, c in zip(self.masses, self.means, self.covariances)
                ]
            ),
            axis=0,
        )


def proposal(log_target, dimensions, plan):
    mu, sd = plan["log_precision_mean"], plan["log_precision_sd"]
    center = np.full(dimensions, mu)
    reference = log_target(center)

    def objective(eta):
        return float(reference - log_target(eta))

    attempts, modes = [], []
    for start in plan["optimizer_start_offsets"]:
        answer = minimize(
            objective,
            center + start * sd,
            method="L-BFGS-B",
            jac="3-point",
            bounds=[
                (
                    mu - plan["optimizer_bound_prior_sds"] * sd,
                    mu + plan["optimizer_bound_prior_sds"] * sd,
                )
            ]
            * dimensions,
            options={
                "maxiter": plan["optimizer_max_iterations"],
                "ftol": 1e-10,
                "gtol": 1e-5,
                "finite_diff_rel_step": 1e-3,
            },
        )
        attempts.append(
            {
                "success": bool(answer.success),
                "point": answer.x.tolist(),
                "relative_objective": float(answer.fun),
                "iterations": int(answer.nit),
            }
        )
        if (
            answer.success
            and np.isfinite(answer.fun)
            and not any(np.max(np.abs(answer.x - m)) < 0.05 for m, _ in modes)
        ):
            modes.append((answer.x, answer.fun))
    if not modes:
        raise ValueError("no converged variance proposal mode")
    modes.sort(key=lambda pair: pair[1])
    modes = [(m, v) for m, v in modes if v <= modes[0][1] + 15.0]
    means, covs = [center], [np.eye(dimensions) * sd**2]
    for mode, _ in modes:
        eigen, vectors = np.linalg.eigh(hessian(objective, mode, plan["hessian_step"]))
        lo, hi = plan["proposal_covariance_eigen_bounds"]
        # These caps only shape an importance proposal; target density is exact.
        covariance = (vectors * (1 / np.clip(eigen, 1 / hi, 1 / lo))) @ vectors.T
        means.append(mode)
        covs.append(plan["proposal_covariance_multiplier"] * covariance)
    mass = plan["proposal_prior_mass"]
    return Proposal(
        means,
        covs,
        np.array([mass] + [(1 - mass) / len(modes)] * len(modes)),
        attempts,
        modes[0][0],
    )


class Target:
    def __init__(self, prepared, y, groups, parent_plan, plan):
        self.prepared, self.stats, self.groups = prepared, response_stats(prepared, y), list(groups)
        if self.stats["cross"].shape[1] != 1:
            raise ValueError("continuous integration uses one response per target")
        self.parent_plan, self.plan = parent_plan, plan
        self.empty = np.zeros((0, len(prepared.names)))
        self.group_indices = {
            g: np.array(
                [
                    j
                    for j, n in enumerate(prepared.names)
                    if n.split("/")[0] == g or (g == "qb" and n.startswith("innovation/"))
                ],
                dtype=int,
            )
            for g in groups
            if g != "game"
        }
        self.cache = {}

    def prior(self, eta, qb_shift=0.0):
        mean = np.full(len(self.groups), self.plan["log_precision_mean"])
        if "qb" in self.groups:
            mean[self.groups.index("qb")] += qb_shift
        return normal_logpdf(eta, mean, np.eye(len(mean)) * self.plan["log_precision_sd"] ** 2)

    def conditional(self, eta, contrasts, need_games=False):
        eta = np.asarray(eta, dtype=float)
        if eta.shape != (len(self.groups),) or not np.isfinite(eta).all():
            raise ValueError("finite log variance coordinates required")
        values = np.exp(eta)
        if not np.isfinite(values).all() or np.any(values <= 0):
            raise ValueError("unrepresentable continuous precision")
        penalty = np.zeros(len(self.prepared.names))
        game = None
        for group, value in zip(self.groups, values):
            if group == "game":
                game = value
            else:
                penalty[self.group_indices[group]] = value
        return cell(
            self.prepared,
            self.stats,
            penalty,
            game,
            contrasts,
            self.parent_plan["noise_prior_shape"],
            self.parent_plan["noise_prior_scale"],
            need_games=need_games,
        )

    def log_target(self, eta):
        key = tuple(eta)
        if key not in self.cache:
            result = self.conditional(eta, self.empty)
            self.cache[key] = float(result["log_likelihood"][0] + self.prior(eta)[0])
        return self.cache[key]


def packed(cases, log_weights):
    return {
        "location": np.stack([c["location"] for c in cases]),
        "diagonal": np.stack([c["diagonal"] for c in cases]),
        "scale": np.stack([c["posterior_scale"] for c in cases]),
        "shape": cases[0]["posterior_shape"],
        "weights": normalized_weights(np.asarray(log_weights)[:, None]),
    }


def describe(result, iterations):
    mean, variance = moments(result)
    low, high = interval(result, iterations=iterations)
    return {
        "mean": mean[:, 0],
        "sd": np.sqrt(np.maximum(variance[:, 0], 0)),
        "low": low[:, 0],
        "high": high[:, 0],
        "effective_samples": float(1 / np.sum(result["weights"] ** 2)),
    }


def compare(a, b):
    scale = np.maximum(np.sqrt((a["sd"] ** 2 + b["sd"] ** 2) / 2), 1e-12)
    return {
        "mean": float(np.max(np.abs(a["mean"] - b["mean"]) / scale)),
        "endpoint": float(
            max(
                np.max(np.abs(a["low"] - b["low"]) / scale),
                np.max(np.abs(a["high"] - b["high"]) / scale),
            )
        ),
    }


def integrate(
    target,
    contrasts,
    plan,
    *,
    seed_offset=0,
    need_games=False,
    sensitivities=False,
    progress=lambda _: None,
):
    geometry = proposal(target.log_target, len(target.groups), plan)
    # Generate the largest balanced net once; every power uses its nested prefix.
    nodes = [
        geometry.draw(max(plan["sobol_powers"]), s + seed_offset) for s in plan["scramble_seeds"]
    ]
    cases, base_logs = [[], []], [[], []]
    shifts = (
        [0.0, *plan["qb_prior_mean_shifts"]] if sensitivities and "qb" in target.groups else [0.0]
    )
    previous, history, descriptions, convergence = {}, [], {}, {}
    evaluated = 0
    for power in plan["sobol_powers"]:
        size = 2**power
        for j in range(2):
            points, log_q = nodes[j]
            for i in range(evaluated, size):
                c = target.conditional(points[i], contrasts, need_games)
                cases[j].append(c)
                base_logs[j].append(
                    float(c["log_likelihood"][0] + target.prior(points[i])[0] - log_q[i])
                )
        evaluated = size
        diagnostics = {}
        for shift in shifts:
            adjusted = [
                np.asarray(base_logs[j])
                + target.prior(nodes[j][0][:size], shift)
                - target.prior(nodes[j][0][:size])
                for j in range(2)
            ]
            halves = [
                describe(packed(cases[j], adjusted[j]), plan["quantile_iterations"])
                for j in range(2)
            ]
            pooled = packed(cases[0] + cases[1], np.concatenate(adjusted))
            current = describe(pooled, plan["quantile_iterations"])
            independent = compare(*halves)
            nested = compare(current, previous[shift]) if shift in previous else None
            ess = min(h["effective_samples"] for h in halves)
            valid = bool(
                nested
                and ess >= plan["minimum_effective_samples"]
                and max(independent["mean"], nested["mean"])
                <= plan["maximum_standardized_mean_difference"]
                and max(independent["endpoint"], nested["endpoint"])
                <= plan["maximum_standardized_endpoint_difference"]
            )
            diagnostics[str(shift)] = {
                "valid": valid,
                "minimum_effective_samples": ess,
                "independent_difference": independent,
                "nested_difference": nested,
            }
            previous[shift], descriptions[shift], convergence[shift] = current, current, valid
        history.append({"power": power, "checks": diagnostics})
        progress(f"Continuous quadrature 2 x {size}; primary valid={convergence[0.0]}")
        if all(convergence.values()):
            break
    combined = cases[0] + cases[1]
    result = packed(combined, np.r_[base_logs[0], base_logs[1]])
    result["coefficient_mean"] = result["weights"][:, 0] @ np.array(
        [c["mean"][:, 0] for c in combined]
    )
    result["game_mean"] = result["weights"][:, 0] @ np.array(
        [c["game_mean"][:, 0] for c in combined]
    )
    mode = target.conditional(geometry.mode, contrasts, need_games)
    mode_summary = describe(packed([mode], [0.0]), plan["quantile_iterations"])
    diagnostic = {
        "valid": convergence[0.0],
        "nodes_per_scramble": evaluated,
        "history": history,
        "mode_attempts": geometry.attempts,
        "mode": geometry.mode.tolist(),
        "proposal_components": len(geometry.means),
        "prior_sensitivity": {
            str(s): {
                "valid": convergence[s],
                **{
                    k: float(np.max(np.abs(descriptions[s]["mean"] - descriptions[0.0]["mean"])))
                    for k in ["max_mean_change"]
                },
            }
            for s in shifts
            if s != 0.0
        },
    }
    return result, descriptions[0.0], mode_summary, diagnostic
