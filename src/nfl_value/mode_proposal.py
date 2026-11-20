"""Bounded log-density mode discovery; proposal geometry is never a prior."""

from time import perf_counter

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, ndtri
from scipy.stats import qmc

from nfl_value.continuous_math import hessian, normal_logpdf
from nfl_value.control_variates import METHOD, training_points
from nfl_value.density_holdout import StabilizedProposal
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.two_level_reference import sampling_hash

KIND = "bounded-mode-proposal-v1"


class WorkLimit(ValueError):
    """An explicit operational stop, retained in the trial denominator."""


class StartLimit(ValueError):
    """One start exhausted its declared allocation; other starts still run."""


class Work:
    def __init__(self, plan, clock=perf_counter):
        self.plan, self.clock, self.started = plan, clock, clock()
        self.counts = {}
        self.trace = {}

    def charge(self, group, n):
        if type(n) is not int or n < 1:
            raise ValueError("positive counted target evaluations required")
        if self.clock() - self.started > self.plan["maximum_seconds_per_trial"]:
            raise WorkLimit("per-trial time budget exhausted")
        if self.total + n > self.plan["maximum_target_evaluations"]:
            raise WorkLimit("target evaluation budget exhausted")
        self.counts[group] = self.counts.get(group, 0) + n

    @property
    def total(self):
        return sum(self.counts.values())

    def record(self):
        return dict(counts=dict(self.counts), total=self.total)


def normalized_masses(log_masses, floor):
    log_masses = np.asarray(log_masses, float)
    if log_masses.ndim != 1 or not np.isfinite(log_masses).all() or len(log_masses) == 0:
        raise ValueError("finite mode mass estimates required")
    w = np.maximum(np.exp(log_masses - logsumexp(log_masses)), floor)
    return w / w.sum()


def pad_modes(means, covariances, masses):
    """Duplicating a stratum splits its mass; it cannot add target probability."""
    means, covariances, masses = map(np.asarray, (means, covariances, masses))
    if not 1 <= len(means) <= 3 or masses.shape != (len(means),):
        raise ValueError("one to three local modes required")
    heavy = int(np.argmax(masses))
    indices = list(range(len(means))) + [heavy] * (3 - len(means))
    counts = np.bincount(indices, minlength=len(means))
    return means[indices], covariances[indices], np.array([masses[j] / counts[j] for j in indices])


def make_proposal(initial, means, covariances, masses, diagnostics):
    return StabilizedProposal(
        initial.mean.copy(),
        initial.covariance.copy(),
        initial.prior_mean.copy(),
        initial.prior_covariance.copy(),
        diagnostics,
        np.array(means),
        np.array(covariances),
        np.array(masses),
    )


def select_starts(points, logp, initial, plan):
    inverse = np.linalg.inv(np.linalg.cholesky(initial.prior_covariance))
    whitened = (points - initial.prior_mean) @ inverse.T
    selected, anchors = [], [(initial.mean - initial.prior_mean) @ inverse.T]
    scores = [logp - initial.logpdf(points, METHOD), logp]
    counts = [plan["ratio_starts"], plan["starts"] - 1 - plan["ratio_starts"]]
    for score, count in zip(scores, counts):
        order = np.argsort(-score, kind="stable")
        chosen = []
        for spacing in (plan["start_spacing"], 0):
            for j in order:
                j = int(j)
                if j in selected or j in chosen:
                    continue
                if min(np.linalg.norm(whitened[j] - a) for a in anchors) < spacing:
                    continue
                chosen.append(j)
                anchors.append(whitened[j])
                if len(chosen) == count:
                    break
            if len(chosen) == count:
                break
        if len(chosen) != count:
            raise ValueError("insufficient distinct search starts")
        selected.extend(chosen)
    return np.vstack([initial.mean, points[selected]]), selected


def fit_modes(log_density, initial, *, entropy, plan, work):
    """Only a density callable and initial geometry enter the fitting interface."""
    d = len(initial.mean)
    if not 1 <= d <= 4:
        raise ValueError("preflight work bound supports dimensions one through four")
    rng = np.random.default_rng(np.random.SeedSequence([*entropy, 10]))
    unit = qmc.Sobol(d=d, scramble=True, bits=52, seed=rng).random_base2(
        plan["search_nodes"].bit_length() - 1
    )
    if len(unit) != plan["search_nodes"] or np.any((unit <= 0) | (unit >= 1)):
        raise ValueError("complete interior search net required")
    points = initial.prior_mean + ndtri(unit) @ np.linalg.cholesky(4 * initial.prior_covariance).T

    def evaluate(x, group):
        x = np.atleast_2d(x)
        work.charge(group, len(x))
        value = np.asarray(log_density(x), float)
        if value.shape != (len(x),) or not np.isfinite(value).all():
            raise ValueError("finite log-density search evaluations required")
        return value

    logp = evaluate(points, "search_cloud")
    search_response_hash = sha256(logp.astype("<f8").tobytes())
    reference = float(evaluate(initial.mean, "search_center")[0])
    starts, selected = select_starts(points, logp, initial, plan)
    attempts, modes = [], []
    work.trace.update(
        attempts=attempts,
        search_entropy=[*entropy, 10],
        search_points_sha256=sha256(points.astype("<f8").tobytes()),
        search_responses_sha256=search_response_hash,
        selected_indices=selected,
    )
    inverse = np.linalg.inv(np.linalg.cholesky(initial.prior_covariance))
    for i, start in enumerate(starts):
        group = f"optimizer_{i}"

        def objective(x):
            if work.counts.get(group, 0) >= plan["optimizer_calls_per_start"]:
                raise StartLimit("start target-call budget exhausted")
            return reference - float(evaluate(x, group)[0])

        try:
            answer = minimize(
                objective,
                start,
                method="L-BFGS-B",
                options=dict(
                    maxiter=plan["optimizer_maxiter"],
                    ftol=plan["optimizer_ftol"],
                    gtol=plan["optimizer_gtol"],
                ),
            )
            if not np.isfinite(answer.x).all() or not np.isfinite(answer.jac).all():
                raise ValueError("nonfinite optimizer point or gradient")
            gradient = float(np.max(np.abs(answer.jac)))
            usable = bool(
                answer.success
                and np.isfinite(answer.x).all()
                and np.isfinite(gradient)
                and gradient <= plan["accept_gradient"]
            )
            record = dict(
                success=bool(answer.success),
                usable=usable,
                point=answer.x.tolist(),
                gradient_max=gradient if np.isfinite(gradient) else None,
                iterations=int(answer.nit),
                message=str(answer.message),
            )
            if usable and not any(
                np.linalg.norm((answer.x - m) @ inverse.T) < plan["mode_distance"] for m in modes
            ):
                modes.append(answer.x.copy())
        except StartLimit as exc:
            record = dict(success=False, usable=False, error=str(exc))
        except (ValueError, np.linalg.LinAlgError) as exc:
            attempts.append(
                dict(
                    success=False,
                    usable=False,
                    error=str(exc),
                    start=start.tolist(),
                    calls=work.counts.get(group, 0),
                )
            )
            raise
        record.update(start=start.tolist(), calls=work.counts.get(group, 0))
        attempts.append(record)
    work.trace["discovered_modes"] = np.array(modes).tolist()
    if not 1 <= len(modes) <= plan["maximum_modes"]:
        raise ValueError(f"discovered mode count outside declared family: {len(modes)}")
    covariances, heights, curvature = [], [], []
    work.trace["curvature"] = curvature
    for i, mode in enumerate(modes):
        h = hessian(lambda x: -float(evaluate(x, f"hessian_{i}")[0]), mode, plan["hessian_step"])
        values, vectors = np.linalg.eigh(h)
        if not np.isfinite(values).all() or np.any(values <= 0):
            raise ValueError("discovered mode has nonpositive curvature")
        raw = 1 / values
        clipped = np.clip(raw, *plan["covariance_bounds"])
        cov = (vectors * clipped) @ vectors.T
        height = float(evaluate(mode, "mode_heights")[0]) + 0.5 * np.linalg.slogdet(cov)[1]
        covariances.append(plan["covariance_inflation"] * cov)
        heights.append(height)
        curvature.append(
            dict(eigenvalues=values.tolist(), clipped=int(np.count_nonzero(raw != clipped)))
        )
    means, covs, masses = pad_modes(
        modes, covariances, normalized_masses(heights, plan["minimum_component_mass"])
    )
    sampling = make_proposal(initial, means, covs, masses, {})
    pilot, q = training_points(sampling, [*entropy, 11], plan["mass_pilot_nodes"])
    logp = evaluate(pilot, "mass_pilot")
    logq = sampling.logpdf(pilot, METHOD)
    weights = q * np.exp(logp - logq)
    if not np.isfinite(weights).all() or weights.sum() <= 0:
        raise ValueError("positive finite mass-pilot integral required")
    logs = np.column_stack(
        [np.log(m) + normal_logpdf(pilot, c, v) for m, c, v in zip(masses, means, covs)]
    )
    responsibilities = np.exp(logs - logsumexp(logs, axis=1)[:, None])
    updated = weights @ responsibilities
    if not np.isfinite(updated).all() or np.any(updated <= 0):
        raise ValueError("positive finite component mass-pilot estimates required")
    masses = normalized_masses(np.log(updated), plan["minimum_component_mass"])
    diagnostics = dict(
        kind=KIND,
        initial_sampling_sha256=sampling_hash(initial),
        entropy=list(entropy),
        search_entropy=[*entropy, 10],
        pilot_entropy=[*entropy, 11],
        search_points_sha256=sha256(points.astype("<f8").tobytes()),
        selected_indices=selected,
        search_responses_sha256=search_response_hash,
        attempts=attempts,
        discovered_modes=np.array(modes).tolist(),
        curvature=curvature,
        pilot_mass=float(weights.sum()),
        pilot_maximum_weight=float(weights.max() / weights.sum()),
        pilot_points_sha256=sha256(pilot.astype("<f8").tobytes()),
        pilot_responses_sha256=sha256(logp.astype("<f8").tobytes()),
        component_means=means.tolist(),
        component_covariances=covs.tolist(),
        component_masses=masses.tolist(),
        geometry_uses_evaluation=False,
        fit_work=work.record(),
    )
    return make_proposal(initial, means, covs, masses, diagnostics)


def restore_modes(geometry, initial):
    g = geometry
    means, covs, masses = [
        np.asarray(g[k], float)
        for k in ("component_means", "component_covariances", "component_masses")
    ]
    d = len(initial.mean)
    if (
        g["kind"] not in (KIND, "known-component-oracle-diagnostic-v1")
        or g["initial_sampling_sha256"] != sampling_hash(initial)
        or means.shape != (3, d)
        or covs.shape != (3, d, d)
        or masses.shape != (3,)
        or not all(np.isfinite(x).all() for x in (means, covs, masses))
        or np.any(masses <= 0)
        or not np.isclose(masses.sum(), 1, rtol=0, atol=1e-14)
        or g["geometry_uses_evaluation"] is not False
    ):
        raise ValueError("invalid mode proposal geometry/support")
    for cov in covs:
        if not np.allclose(cov, cov.T, rtol=0, atol=1e-12):
            raise ValueError("asymmetric proposal covariance")
        np.linalg.cholesky(cov)
    return make_proposal(initial, means, covs, masses, geometry)


def geometry_hash(sampling):
    return sha256(json_bytes(sampling.diagnostics))
