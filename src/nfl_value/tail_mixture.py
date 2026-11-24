"""Independent target-weighted mixture adaptation; never a football prior."""

import numpy as np
from scipy.special import logsumexp

from nfl_value.continuous_math import normal_logpdf
from nfl_value.control_variates import METHOD, training_points
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.mode_proposal import (
    KIND as MODE_KIND,
    fit_modes,
    make_proposal,
    pad_modes,
    restore_modes,
)
from nfl_value.two_level_reference import sampling_hash

KIND = "tail-mixture-em-v1"


def array_hash(value):
    return sha256(np.asarray(value, dtype="<f8").tobytes())


def central_logs(points, sampling):
    return np.column_stack(
        [
            np.log(w) + normal_logpdf(points, m, c)
            for w, m, c in zip(
                sampling.mixture_masses, sampling.mixture_means, sampling.mixture_covariances
            )
        ]
    )


def reserve_tail(mode, initial, mass):
    """Replace only duplicated slots; do not discard a discovered mode."""
    count = len(mode.diagnostics["discovered_modes"])
    if not 1 <= count <= 3 or not 0 < mass < 1:
        raise ValueError("bounded unique mode count and tail mass required")
    means, covs = mode.mixture_means[:count], mode.mixture_covariances[:count]
    weights = np.zeros(count)
    for mean, weight in zip(mode.mixture_means, mode.mixture_masses):
        matches = np.flatnonzero(np.all(means == mean, axis=1))
        if len(matches) != 1:
            raise ValueError("duplicated mode stratum mapping is ambiguous")
        weights[matches[0]] += weight
    if count < 3:
        means = np.vstack([means, initial.prior_mean])
        covs = np.concatenate([covs, initial.prior_covariance[None, :, :]])
        weights = np.r_[(1 - mass) * weights / weights.sum(), mass]
    means, covs, weights = pad_modes(means, covs, weights)
    return make_proposal(initial, means, covs, weights, {}), count < 3


def em_step(points, weights, sampling, reference, *, pseudo_count, bounds, mass_floor):
    """One finite weighted EM update; weights are target, not sampling mass."""
    x, w, ref = np.asarray(points, float), np.asarray(weights, float), np.asarray(reference, float)
    if (
        x.ndim != 2
        or w.shape != (len(x),)
        or len(x) < 2
        or not np.isfinite(x).all()
        or not np.isfinite(w).all()
        or np.any(w < 0)
        or not np.isclose(w.sum(), 1, rtol=0, atol=1e-12)
        or not np.isfinite(pseudo_count)
        or pseudo_count < 0
        or not 0 < bounds[0] <= bounds[1]
        or not 0 < mass_floor < 1 / 3
    ):
        raise ValueError("finite normalized pilot and bounded EM parameters required")
    if (
        ref.shape != (x.shape[1], x.shape[1])
        or not np.isfinite(ref).all()
        or not np.allclose(ref, ref.T, rtol=0, atol=1e-12)
    ):
        raise ValueError("finite reference covariance required")
    np.linalg.cholesky(ref)
    logs = central_logs(x, sampling)
    responsibilities = np.exp(logs - logsumexp(logs, axis=1)[:, None])
    allocation = w[:, None] * responsibilities
    totals = allocation.sum(axis=0)
    if np.any(totals <= 0) or not np.isfinite(totals).all():
        raise ValueError("positive finite component allocations required")
    means, covs, effective, clipped = [], [], [], []
    for j in range(3):
        a = allocation[:, j] / totals[j]
        mean = a @ x
        centered = x - mean
        empirical = (centered * a[:, None]).T @ centered
        neff = max(1.0, float(1 / (a @ a)))
        covariance = (neff * empirical + pseudo_count * ref) / (neff + pseudo_count)
        values, vectors = np.linalg.eigh((covariance + covariance.T) / 2)
        bounded = np.clip(values, *bounds)
        means.append(mean)
        covs.append((vectors * bounded) @ vectors.T)
        effective.append(neff)
        clipped.append(int(np.count_nonzero(values != bounded)))
    masses = np.maximum(totals, mass_floor)
    result = make_proposal(sampling, means, covs, masses / masses.sum(), {})
    return result, dict(
        allocated_mass=totals.tolist(),
        effective_weights=effective,
        clipped_eigenvalues=clipped,
        objective_before=float(w @ logsumexp(logs, axis=1)),
        objective_after=float(w @ logsumexp(central_logs(x, result), axis=1)),
    )


def adapt_stage(sampling, initial, logp, entropy, plan):
    points, quadrature = training_points(sampling, entropy, plan["em_nodes"])
    logp = np.asarray(logp, float)
    if logp.shape != (len(points),) or not np.isfinite(logp).all():
        raise ValueError("complete finite pilot responses required")
    logw = np.log(quadrature) + logp - sampling.logpdf(points, METHOD)
    logz = float(logsumexp(logw))
    weights = np.exp(logw - logz)
    stage = dict(
        entropy=entropy,
        input_sampling_sha256=sampling_hash(sampling),
        points_sha256=array_hash(points),
        quadrature_sha256=array_hash(quadrature),
        log_density=logp.tolist(),
        log_density_sha256=array_hash(logp),
        log_mass=logz,
        maximum_weight=float(weights.max()),
        effective_weights=float(1 / (weights @ weights)),
        steps=[],
    )
    for _ in range(plan["em_steps"]):
        sampling, diagnostic = em_step(
            points,
            weights,
            sampling,
            initial.covariance,
            pseudo_count=len(initial.mean) + 2,
            bounds=plan["covariance_bounds"],
            mass_floor=plan["minimum_component_mass"],
        )
        stage["steps"].append(diagnostic)
    stage.update(
        component_means=sampling.mixture_means.tolist(),
        component_covariances=sampling.mixture_covariances.tolist(),
        component_masses=sampling.mixture_masses.tolist(),
    )
    stage["stage_sha256"] = sha256(json_bytes(stage))
    return sampling, stage


def fit_tail_mixture(log_density, initial, *, entropy, plan, work):
    mode = fit_modes(log_density, initial, entropy=entropy, plan=plan, work=work)
    sampling, available = reserve_tail(mode, initial, plan["tail_initial_mass"])
    stages = []
    work.trace["tail_adaptation"] = dict(broad_slot_available=available, stages=stages)
    for iteration in range(plan["em_rounds"]):
        domain = [*entropy, 20, iteration]
        points, _ = training_points(sampling, domain, plan["em_nodes"])
        work.charge(f"em_pilot_{iteration}", len(points))
        sampling, stage = adapt_stage(sampling, initial, log_density(points), domain, plan)
        stages.append(stage)
    g = dict(
        kind=KIND,
        entropy=list(entropy),
        initial_sampling_sha256=sampling_hash(initial),
        search_entropy=[*entropy, 10],
        pilot_entropy=[*entropy, 11],
        mode_geometry=mode.diagnostics,
        broad_slot_available=available,
        stages=stages,
        component_means=sampling.mixture_means.tolist(),
        component_covariances=sampling.mixture_covariances.tolist(),
        component_masses=sampling.mixture_masses.tolist(),
        geometry_uses_evaluation=False,
        fit_work=work.record(),
    )
    sampling.diagnostics = g
    return sampling


def restore_tail_mixture(g, initial, plan):
    if (
        g["kind"] != KIND
        or g["initial_sampling_sha256"] != sampling_hash(initial)
        or g["geometry_uses_evaluation"] is not False
        or len(g["stages"]) != plan["em_rounds"]
        or g["mode_geometry"]["entropy"] != g["entropy"]
        or g["mode_geometry"]["kind"] != MODE_KIND
    ):
        raise ValueError("tail proposal provenance differs")
    mode = restore_modes(g["mode_geometry"], initial)
    counts = {
        **g["mode_geometry"]["fit_work"]["counts"],
        **{f"em_pilot_{k}": plan["em_nodes"] for k in range(plan["em_rounds"])},
    }
    if g["fit_work"] != dict(counts=counts, total=sum(counts.values())):
        raise ValueError("tail fitting work differs")
    sampling, available = reserve_tail(mode, initial, plan["tail_initial_mass"])
    if g["broad_slot_available"] is not available:
        raise ValueError("tail slot accounting differs")
    for iteration, saved in enumerate(g["stages"]):
        sampling, reconstructed = adapt_stage(
            sampling, initial, saved["log_density"], [*g["entropy"], 20, iteration], plan
        )
        if json_bytes(saved) != json_bytes(reconstructed):
            raise ValueError("tail EM pilot/step evidence does not reproduce")
    if (
        any(
            json_bytes(g[key]) != json_bytes(value.tolist())
            for key, value in (
                ("component_means", sampling.mixture_means),
                ("component_covariances", sampling.mixture_covariances),
                ("component_masses", sampling.mixture_masses),
            )
        )
        or g["search_entropy"] != [*g["entropy"], 10]
        or g["pilot_entropy"] != [*g["entropy"], 11]
    ):
        raise ValueError("tail fitted geometry/random domains differ")
    sampling.diagnostics = g
    return sampling
