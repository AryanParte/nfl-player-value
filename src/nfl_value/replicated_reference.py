"""Replicate-level integration uncertainty, separate from player uncertainty."""

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaincinv, logsumexp, ndtri, stdtr
from scipy.stats import multivariate_t, qmc, t

from nfl_value.continuous_math import hessian, normal_logpdf, proposal
from nfl_value.variance_reference import BoundedTarget, BudgetExceeded


@dataclass
class SamplingProposal:
    mean: np.ndarray
    covariance: np.ndarray
    prior_mean: np.ndarray
    prior_covariance: np.ndarray
    diagnostics: dict

    def components(self, method):
        if method == "local-t":
            return [(1.0, self.mean, self.covariance, 5)]
        if method == "defensive-mixture":
            return [
                (0.9, self.mean, self.covariance, 5),
                (0.1, self.prior_mean, self.prior_covariance, None),
            ]
        raise ValueError("unreviewed randomized proposal")

    def logpdf(self, points, method):
        points = np.atleast_2d(points)
        return logsumexp(
            np.stack(
                [
                    np.log(mass)
                    + np.atleast_1d(
                        multivariate_t.logpdf(points, loc=mean, shape=cov, df=df)
                        if df is not None
                        else normal_logpdf(points, mean, cov)
                    )
                    for mass, mean, cov, df in self.components(method)
                ]
            ),
            axis=0,
        )


def fit_proposal(target):
    fitted = proposal(target.log_target, len(target.groups), target.plan)
    center = np.full(len(target.groups), target.plan["log_precision_mean"])
    ref = target.log_target(center)
    eigen = np.linalg.eigvalsh(
        hessian(lambda x: ref - target.log_target(x), fitted.mode, target.plan["hessian_step"])
    )
    lo, hi = target.plan["proposal_covariance_eigen_bounds"]
    return SamplingProposal(
        np.array(fitted.means[1]),
        np.array(fitted.covariances[1]),
        center,
        np.eye(len(center)) * target.plan["log_precision_sd"] ** 2,
        dict(
            optimizer_attempts=fitted.attempts,
            raw_hessian_eigenvalues=eigen.tolist(),
            clipped_eigenvalues=int(np.count_nonzero((eigen < 1 / hi) | (eigen > 1 / lo))),
            mode=fitted.mode.tolist(),
            covariance=np.asarray(fitted.covariances[1]).tolist(),
            geometry_uses_primary_qmc=False,
        ),
    )


def replicate_integrals(f, sampling, method, *, entropy, replicates=32, nodes=2048, progress=None):
    """Equal component allocation uses exact mixture mass, not a changed density."""
    if (
        type(replicates) is not int
        or replicates < 2
        or type(nodes) is not int
        or nodes < 2
        or nodes & (nodes - 1)
        or not entropy
        or any(type(x) is not int or x < 0 for x in entropy)
    ):
        raise ValueError("independent entropy, integer replicates and power-of-two nets required")
    parts = sampling.components(method)
    count = nodes // len(parts)
    if count < 2:
        raise ValueError("complete component net required")
    d = len(sampling.mean)
    result = []
    size = None
    for rep in range(replicates):
        total = None
        for j, (mass, mean, covariance, df) in enumerate(parts):
            rng = np.random.default_rng(np.random.SeedSequence([*entropy, rep, j]))
            unit = qmc.Sobol(d=d + 1, scramble=True, bits=52, seed=rng).random_base2(
                count.bit_length() - 1
            )
            if np.any((unit <= 0) | (unit >= 1)):
                raise ValueError("non-interior randomized coordinate")
            z = ndtri(unit[:, :d])
            if df is not None:
                z *= np.sqrt(df / (2 * gammaincinv(df / 2, unit[:, d])))[:, None]
            points = mean + np.einsum(
                "ij,kj->ik", z, np.linalg.cholesky(covariance), optimize=False
            )
            values = np.asarray(f(points, sampling.logpdf(points, method)), dtype=float)
            if (
                values.ndim != 2
                or values.shape[0] != count
                or values.shape[1] < 1
                or not np.isfinite(values).all()
                or (size is not None and values.shape[1] != size)
            ):
                raise ValueError("finite consistent vector integrals required")
            size = values.shape[1]
            term = mass * values.mean(axis=0)
            total = term if total is None else total + term
        if not np.isfinite(total).all():
            raise ValueError("unrepresentable replicate integral")
        result.append(total)
        if progress is not None:
            progress(f"randomized reference replicate {rep + 1}/{replicates}")
    return np.array(result)


def confidence_sets(samples, denominators, *, simultaneous=True):
    """Student-t mass and Fieller ratios from independent replicate means.

    Each denominator is -1 for a mass integral, otherwise its mass column index.
    Unbounded/unstable mass cannot be repaired by clipping a ratio interval.
    """
    x = np.asarray(samples, dtype=float)
    den = np.asarray(denominators)
    if (
        x.ndim != 2
        or x.shape[0] < 2
        or x.shape[1] < 1
        or den.shape != (x.shape[1],)
        or not np.issubdtype(den.dtype, np.integer)
        or np.any((den < -1) | (den >= x.shape[1]))
        or not np.isfinite(x).all()
        or not np.any(den == -1)
        or np.any(den[den[den >= 0]] != -1)
    ):
        raise ValueError("finite independent replicates and declared mass columns required")
    mean = x.mean(axis=0)
    centered = x - mean
    variance = np.sum(centered**2, axis=0) / (len(x) * (len(x) - 1))
    critical = float(t.isf(0.05 / (2 * (x.shape[1] if simultaneous else 1)), len(x) - 1))
    radius = critical * np.sqrt(variance)
    low, high = mean - radius, mean + radius
    masses = den == -1
    if np.any(x[:, masses] < 0) or np.any(low[masses] <= 0):
        raise ValueError("positive bounded normalizing mass required")
    estimate = mean.copy()
    q = critical**2
    for j in np.flatnonzero(~masses):
        k = den[j]
        cov = float(centered[:, j] @ centered[:, k] / (len(x) * (len(x) - 1)))
        ratio = mean[j] / mean[k]
        a = mean[k] ** 2 - q * variance[k]
        # Centering numerator by the point ratio avoids cancellation for signed
        # or nearly constant functionals. This is the same Fieller quadratic.
        v_res = np.sum((centered[:, j] - ratio * centered[:, k]) ** 2) / (len(x) * (len(x) - 1))
        cov_res = cov - ratio * variance[k]
        radicand = q * (a * v_res + q * cov_res**2)
        if a <= 0 or radicand < 0 or not np.isfinite(radicand):
            raise ValueError("unbounded or invalid Fieller set")
        center = ratio - q * cov_res / a
        half_width = np.sqrt(radicand) / a
        estimate[j], low[j], high[j] = ratio, center - half_width, center + half_width
    if not np.isfinite([estimate, low, high]).all() or np.any(low > high):
        raise ValueError("nonfinite numerical confidence set")
    return dict(estimate=estimate, low=low, high=high, critical=critical)


def functional_check(bounds, expected, tolerances):
    """Every endpoint of the numerical set must satisfy the functional tolerance."""
    error = np.maximum(
        np.abs(bounds["low"] - bounds["estimate"]), np.abs(bounds["high"] - bounds["estimate"])
    )
    discrepancy = np.abs(bounds["estimate"] - expected) + error
    return bool(np.all(discrepancy <= tolerances)), discrepancy


def reference_integral(
    target, contrasts, summaries, plan, method, case_index, progress=lambda _: None
):
    if method == "adaptive-mixture":
        from nfl_value.adaptive_proposal import fit_adaptive

        sampling = fit_adaptive(target, plan, case_index)
    else:
        sampling = fit_proposal(target)
    offset = target.log_target(sampling.mean) - sampling.logpdf(sampling.mean, method)[0]
    n = len(contrasts)
    width = 1 + 3 * n
    shifts = list(summaries)
    den = [k * width if j else -1 for k in range(len(shifts)) for j in range(width)]
    if isinstance(target, BoundedTarget) and (
        target.evaluation_limit - target.evaluations
        < plan["replicates"] * plan["nodes_per_replicate"]
    ):
        raise BudgetExceeded("budget cannot retain all predeclared randomized replicates")

    def f(points, log_q):
        values = []
        for point, log_density in zip(points, log_q):
            c = target.conditional(point, contrasts)
            scale = np.sqrt(c["diagonal"] * c["posterior_scale"][0] / c["posterior_shape"])
            safe = np.where(scale > 0, scale, 1)
            location = c["location"][:, 0]
            row = []
            for shift, s in summaries.items():
                if np.any(s["sd"] <= 0):
                    raise ValueError("positive contrast SD required")
                weight = np.exp(
                    c["log_likelihood"][0] + target.prior(point, shift)[0] - log_density - offset
                )
                cdfs = [
                    np.where(
                        scale > 0,
                        stdtr(2 * c["posterior_shape"], (s[k] - location) / safe),
                        (s[k] >= location).astype(float),
                    )
                    for k in ["low", "high"]
                ]
                row.extend(weight * np.r_[1, (location - s["mean"]) / s["sd"], *cdfs])
            values.append(row)
        return values

    replicas = replicate_integrals(
        f,
        sampling,
        method,
        entropy=[plan["base_seed"], 2, case_index, 0],
        replicates=plan["replicates"],
        nodes=plan["nodes_per_replicate"],
        progress=progress,
    )
    bounds = confidence_sets(replicas, den)
    checks = {}
    for k, shift in enumerate(shifts):
        start = k * width + 1
        b = {name: bounds[name][start : start + 3 * n] for name in ["estimate", "low", "high"]}
        expected = np.r_[np.zeros(n), np.full(n, 0.025), np.full(n, 0.975)]
        tolerances = np.r_[
            np.full(n, plan["reference_mean_tolerance_sd"]),
            np.full(2 * n, plan["reference_endpoint_cdf_tolerance"]),
        ]
        valid, difference = functional_check(b, expected, tolerances)
        checks[str(shift)] = dict(
            valid=valid,
            maximum_mean_difference_plus_error_sd=float(difference[:n].max()),
            maximum_endpoint_cdf_difference_plus_error=float(difference[n:].max()),
        )
    return dict(
        valid=all(c["valid"] for c in checks.values()),
        checks=checks,
        proposal=method,
        geometry=sampling.diagnostics,
        independent_replicates=plan["replicates"],
        nodes_per_replicate=plan["nodes_per_replicate"],
        simultaneous_critical=bounds["critical"],
        confidence_is_approximate=True,
        replicate_integrals=replicas.tolist(),
        bounds={k: v.tolist() for k, v in bounds.items() if k != "critical"},
    )
