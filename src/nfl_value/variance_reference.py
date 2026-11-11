"""Axis-CDF transport with independent deterministic cubature for one fixed target."""

from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

import numpy as np
from scipy.integrate import cubature
from scipy.special import ndtr, ndtri, stdtr, stdtrit
from scipy.stats import qmc, t

from nfl_value.continuous_math import Target, compare, describe, packed, proposal
from nfl_value.dimension_cubature import integrate as dimension_integrate


class BudgetExceeded(ValueError):
    """A declared work limit is a recorded numerical failure, never a pass."""


class BoundedTarget(Target):
    def __init__(self, *args, evaluation_limit, deadline, **kwargs):
        super().__init__(*args, **kwargs)
        self.evaluations = 0
        self.evaluation_limit, self.deadline = evaluation_limit, deadline

    def conditional(self, *args, **kwargs):
        if self.evaluations >= self.evaluation_limit or perf_counter() >= self.deadline:
            raise BudgetExceeded("declared target evaluation/time budget exhausted")
        self.evaluations += 1
        return super().conditional(*args, **kwargs)


@dataclass
class Axis:
    grid: np.ndarray
    density: np.ndarray
    mean: float
    sd: float
    prior_mass: float

    def __post_init__(self):
        self.grid = np.asarray(self.grid, dtype=float)
        self.density = np.asarray(self.density, dtype=float)
        if (
            self.grid.ndim != 1
            or len(self.grid) < 2
            or self.density.shape != self.grid.shape
            or not np.isfinite(self.grid).all()
            or not np.isfinite(self.density).all()
            or np.any(np.diff(self.grid) <= 0)
            or np.any(self.density < 0)
            or not np.isfinite([self.mean, self.sd, self.prior_mass]).all()
            or self.sd <= 0
            or not 0 < self.prior_mass < 1
        ):
            raise ValueError("valid positive-support axis proposal required")
        masses = np.diff(self.grid) * (self.density[:-1] + self.density[1:]) / 2
        normalizer = masses.sum()
        if not np.isfinite(normalizer) or normalizer <= 0:
            raise ValueError("nonzero finite axis mass required")
        self.density = self.density / normalizer
        self.cumulative = np.r_[0.0, np.cumsum(masses / normalizer)]
        self.cumulative[-1] = 1.0

    def pdf(self, value):
        z = (np.asarray(value) - self.mean) / self.sd
        gaussian = np.exp(-z * z / 2) / (np.sqrt(2 * np.pi) * self.sd)
        return self.prior_mass * gaussian + (1 - self.prior_mass) * np.interp(
            value, self.grid, self.density, left=0.0, right=0.0
        )

    def cdf(self, value):
        value = np.asarray(value)
        i = np.clip(np.searchsorted(self.grid, value, side="right") - 1, 0, len(self.grid) - 2)
        width = self.grid[i + 1] - self.grid[i]
        delta = np.clip(value - self.grid[i], 0, width)
        partial = self.cumulative[i] + self.density[i] * delta
        partial += (self.density[i + 1] - self.density[i]) * delta**2 / (2 * width)
        partial = np.where(value <= self.grid[0], 0, np.where(value >= self.grid[-1], 1, partial))
        return (
            self.prior_mass * ndtr((value - self.mean) / self.sd) + (1 - self.prior_mass) * partial
        )

    def ppf(self, probability):
        probability = np.asarray(probability)
        if not np.isfinite(probability).all() or np.any((probability <= 0) | (probability >= 1)):
            raise ValueError("interior unit coordinates required")
        normal = self.mean + self.sd * ndtri(probability)
        low = np.minimum(self.grid[0], normal)
        high = np.maximum(self.grid[-1], normal)
        for _ in range(64):
            mid = (low + high) / 2
            below = self.cdf(mid) < probability
            low, high = np.where(below, mid, low), np.where(below, high, mid)
        answer = (low + high) / 2
        if np.max(np.abs(self.cdf(answer) - probability)) > 1e-12:
            raise ValueError("axis inverse CDF accuracy failure")
        return answer

    def moments(self):
        width, left = np.diff(self.grid), self.grid[:-1]
        a, b = self.density[:-1], self.density[1:]
        mass = width * (a + b) / 2
        first_offset = width**2 * (a + 2 * b) / 6
        first = np.sum(left * mass + first_offset)
        second = np.sum(left**2 * mass + 2 * left * first_offset + width**3 * (a + 3 * b) / 12)
        mean = (1 - self.prior_mass) * first + self.prior_mass * self.mean
        second = (1 - self.prior_mass) * second + self.prior_mass * (self.mean**2 + self.sd**2)
        return mean, second - mean**2


@dataclass
class Transport:
    axes: list[Axis]
    mode: np.ndarray
    attempts: list

    def transform(self, unit):
        unit = np.asarray(unit)
        if unit.ndim != 2 or unit.shape[1] != len(self.axes):
            raise ValueError("unit coordinate dimension differs from transport")
        return np.column_stack([a.ppf(unit[:, j]) for j, a in enumerate(self.axes)])

    def logpdf(self, eta):
        eta = np.atleast_2d(eta)
        density = np.column_stack([a.pdf(eta[:, j]) for j, a in enumerate(self.axes)])
        if not np.isfinite(density).all() or np.any(density <= 0):
            raise ValueError("unrepresentable product proposal density")
        return np.log(density).sum(axis=1)


class SmoothReferenceTransport:
    """Independent Student-t coordinates avoid the table's interpolation corners."""

    def __init__(self, transport):
        moments = np.array([a.moments() for a in transport.axes])
        self.mean = moments[:, 0]
        self.scale = np.sqrt(moments[:, 1] * 3 / 5)
        if not np.isfinite(self.scale).all() or np.any(self.scale <= 0):
            raise ValueError("positive smooth reference scales required")

    def transform(self, unit):
        return self.mean + self.scale * stdtrit(5, unit)

    def logpdf(self, eta):
        return np.sum(
            t.logpdf((np.atleast_2d(eta) - self.mean) / self.scale, 5) - np.log(self.scale), axis=1
        )


def build_transport(target, plan):
    model = target.plan
    geometry = proposal(target.log_target, len(target.groups), model)
    axes = []
    mu, sd = model["log_precision_mean"], model["log_precision_sd"]
    for j in range(len(target.groups)):
        local_sd = np.sqrt(geometry.covariances[1][j, j] / model["proposal_covariance_multiplier"])
        grid = np.unique(
            np.r_[
                np.linspace(
                    mu - plan["prior_span_sd"] * sd,
                    mu + plan["prior_span_sd"] * sd,
                    plan["axis_grid_points"],
                ),
                np.linspace(
                    geometry.mode[j] - plan["local_span_sd"] * local_sd,
                    geometry.mode[j] + plan["local_span_sd"] * local_sd,
                    plan["axis_grid_points"],
                ),
                geometry.mode[j],
            ]
        )
        points = np.tile(geometry.mode, (len(grid), 1))
        points[:, j] = grid
        log_values = np.array([target.log_target(x) for x in points])
        axes.append(
            Axis(grid, np.exp(log_values - log_values.max()), mu, sd, plan["prior_mass_per_axis"])
        )
    return Transport(axes, geometry.mode, geometry.attempts)


def qmc_integrate(
    target,
    contrasts,
    transport,
    plan,
    *,
    sensitivities=False,
    need_games=False,
    progress=lambda _: None,
):
    shifts = [0.0, *target.plan["qb_prior_mean_shifts"]] if sensitivities else [0.0]
    nodes = []
    for seed in plan["scramble_seeds"]:
        unit = qmc.Sobol(len(target.groups), scramble=True, seed=seed).random_base2(
            max(plan["sobol_powers"])
        )
        eta = transport.transform(unit)
        nodes.append((eta, transport.logpdf(eta)))
    cases, logs = [[], []], [[], []]
    previous, summaries, history = {}, {}, []
    evaluated = 0
    for power in plan["sobol_powers"]:
        size = 2**power
        for j, (eta, log_q) in enumerate(nodes):
            for i in range(evaluated, size):
                c = target.conditional(eta[i], contrasts, need_games)
                cases[j].append(c)
                logs[j].append(float(c["log_likelihood"][0] + target.prior(eta[i])[0] - log_q[i]))
        evaluated = size
        checks = {}
        for shift in shifts:
            adjusted = [
                np.asarray(logs[j])
                + target.prior(nodes[j][0][:size], shift)
                - target.prior(nodes[j][0][:size])
                for j in range(2)
            ]
            halves = [
                describe(packed(cases[j], adjusted[j]), target.plan["quantile_iterations"])
                for j in range(2)
            ]
            current = describe(
                packed(cases[0] + cases[1], np.concatenate(adjusted)),
                target.plan["quantile_iterations"],
            )
            independent = compare(*halves)
            nested = compare(current, previous[shift]) if shift in previous else None
            ess = min(s["effective_samples"] for s in halves)
            valid = bool(
                nested
                and ess >= plan["minimum_effective_samples"]
                and max(independent["mean"], nested["mean"])
                <= plan["maximum_standardized_mean_difference"]
                and max(independent["endpoint"], nested["endpoint"])
                <= plan["maximum_standardized_endpoint_difference"]
            )
            checks[str(shift)] = dict(
                valid=valid,
                minimum_effective_samples=ess,
                independent_difference=independent,
                nested_difference=nested,
            )
            previous[shift] = summaries[shift] = current
        history.append(dict(power=power, checks=checks))
        progress(f"axis QMC {size} per scramble; valid={all(c['valid'] for c in checks.values())}")
        if all(c["valid"] for c in checks.values()):
            break
    combined = cases[0] + cases[1]
    result = packed(combined, np.r_[logs[0], logs[1]])
    result["coefficient_mean"] = result["weights"][:, 0] @ np.array(
        [c["mean"][:, 0] for c in combined]
    )
    result["game_mean"] = result["weights"][:, 0] @ np.array(
        [c["game_mean"][:, 0] for c in combined]
    )
    return (
        result,
        summaries,
        dict(
            valid=all(c["valid"] for c in checks.values()),
            nodes_per_scramble=evaluated,
            history=history,
        ),
    )


def reference_integral(target, contrasts, transport, summaries, plan, progress=lambda _: None):
    """Integrate conditional means and endpoint CDFs using an independent rule."""
    shifts = list(summaries)
    n = len(contrasts)
    coordinates = (
        SmoothReferenceTransport(transport)
        if plan.get("reference_transport") == "independent_student_t5_moments"
        else transport
    )
    log_reference = target.log_target(transport.mode) - coordinates.logpdf(transport.mode)[0]
    calls = 0

    @lru_cache(maxsize=plan.get("reference_cache_nodes", 0))
    def node(point, log_q):
        point = np.asarray(point)
        c = target.conditional(point, contrasts)
        scale = np.sqrt(c["diagonal"] * c["posterior_scale"][0] / c["posterior_shape"])
        safe = np.where(scale > 0, scale, 1.0)
        location = c["location"][:, 0]
        values = []
        for shift in shifts:
            s = summaries[shift]
            if np.any(s["sd"] <= 0):
                raise ValueError("strictly positive contrast SD required for reference")
            log_weight = (
                c["log_likelihood"][0] + target.prior(point, shift)[0] - log_q - log_reference
            )
            weight = np.exp(log_weight)
            cdfs = [
                np.where(
                    scale > 0,
                    stdtr(2 * c["posterior_shape"], (s[k] - location) / safe),
                    (s[k] >= location).astype(float),
                )
                for k in ["low", "high"]
            ]
            # A mass offset avoids a near-zero relative-error denominator.
            # Subtract it after normalization and propagate the full error.
            values.extend(
                weight
                * np.r_[1.0, 1.0 + (location - s["mean"]) / s["sd"], *(1.0 + f for f in cdfs)]
            )
        return values

    def integrand(unit):
        nonlocal calls
        eta = coordinates.transform(unit)
        log_q = coordinates.logpdf(eta)
        output = [node(tuple(point), float(q)) for point, q in zip(eta, log_q)]
        calls += len(eta)
        if calls // 10000 != (calls - len(eta)) // 10000:
            progress(f"deterministic reference evaluated {calls} nodes")
        result = np.asarray(output)
        if not np.isfinite(result).all():
            raise ValueError("nonfinite reference integrand")
        return result

    subdivision_limit = plan["cubature_max_subdivisions"]
    budget_limited = False
    if isinstance(target, BoundedTarget) and plan.get("reference_cache_nodes"):
        # Pinned Genz-Malik repeats the high rule for its error; the low rule
        # is a subset. Our cache can retain an entire rule pair (at most 155
        # requests in the four-dimensional pilot). Charge the worst-case
        # distinct solves, including every child of a complete subdivision.
        d = len(target.groups)
        if plan["cubature_rule"] != "genz-malik" or d not in (2, 3, 4):
            raise ValueError("unreviewed cached reference work bound")
        region_nodes = 1 + 2 * d * (d + 1) + 2**d
        available = target.evaluation_limit - target.evaluations
        children = 2 if plan.get("reference_subdivision") == "largest_fourth_difference" else 2**d
        affordable = (available - region_nodes) // (children * region_nodes)
        if affordable < 1:
            raise BudgetExceeded("budget cannot retain one complete reference subdivision")
        subdivision_limit = min(subdivision_limit, affordable)
        budget_limited = subdivision_limit < plan["cubature_max_subdivisions"]
    adaptive = plan.get("reference_subdivision") == "largest_fourth_difference"
    integrate = dimension_integrate if adaptive else cubature
    r = integrate(
        integrand,
        np.zeros(len(target.groups)),
        np.ones(len(target.groups)),
        rtol=plan["cubature_rtol"],
        atol=plan["cubature_atol"],
        max_subdivisions=subdivision_limit,
        **({} if adaptive else {"rule": plan["cubature_rule"]}),
    )
    checks = {}
    for j, shift in enumerate(shifts):
        estimate = r.estimate[j * (1 + 3 * n) : (j + 1) * (1 + 3 * n)]
        error = np.abs(r.error[j * (1 + 3 * n) : (j + 1) * (1 + 3 * n)])
        mass, mass_error = estimate[0], error[0]
        if not np.isfinite(estimate).all() or not np.isfinite(error).all() or mass <= mass_error:
            checks[str(shift)] = dict(valid=False, reason="unverified positive reference mass")
            continue
        normalized = estimate[1:] / mass
        propagated = (error[1:] + np.abs(normalized) * mass_error) / (mass - mass_error)
        mean_difference = np.abs(normalized[:n] - 1.0)
        cdf_difference = np.abs(normalized[n:] - 1.0 - np.repeat([0.025, 0.975], n))
        mean_upper = float(np.max(mean_difference + propagated[:n]))
        cdf_upper = float(np.max(cdf_difference + propagated[n:]))
        checks[str(shift)] = dict(
            valid=bool(
                r.status == "converged"
                and mean_upper <= plan["reference_mean_tolerance_sd"]
                and cdf_upper <= plan["reference_endpoint_cdf_tolerance"]
            ),
            mass=float(mass),
            estimated_mass_error=float(mass_error),
            maximum_mean_difference_sd=float(mean_difference.max()),
            maximum_mean_difference_plus_error_sd=mean_upper,
            maximum_endpoint_cdf_difference=float(cdf_difference.max()),
            maximum_endpoint_cdf_difference_plus_error=cdf_upper,
        )
    result = dict(
        valid=all(v["valid"] for v in checks.values()),
        status=r.status,
        subdivisions=int(r.subdivisions),
        evaluations=calls,
        checks=checks,
        error_is_estimated_not_rigorous=True,
    )
    if plan.get("reference_cache_nodes"):
        result["subdivision_limit"] = subdivision_limit
        result["subdivision_limit_from_solve_budget"] = budget_limited
        result["cache"] = dict(
            capacity=plan["reference_cache_nodes"],
            hits=node.cache_info().hits,
            misses=node.cache_info().misses,
            retained=node.cache_info().currsize,
        )
    if adaptive:
        result["subdivision_strategy"] = "largest_fourth_difference"
        result["axis_splits"] = r.axis_splits
    return result
