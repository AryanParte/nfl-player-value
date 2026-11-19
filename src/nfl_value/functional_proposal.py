"""Independently fitted importance proposals for declared ratio functionals.

Proposal regularization changes sampling only. Full mixture densities and paired
fine corrections continue to integrate the original target, never a surrogate.
"""

import numpy as np

from nfl_value.adaptive_proposal import bounded_covariance
from nfl_value.control_variates import METHOD, training_points
from nfl_value.density_holdout import StabilizedProposal
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.two_level_reference import sampling_hash

KIND = "functional-moment-proposal-v1"


def envelopes(values, quadrature_weights, layout):
    """Each prior owns its normalizer; signed means enter through magnitude."""
    f, q = np.asarray(values, float), np.asarray(quadrature_weights, float)
    if (
        f.ndim != 2
        or f.shape[0] < 2
        or q.shape != (len(f),)
        or not np.isfinite(f).all()
        or not np.isfinite(q).all()
        or np.any(q <= 0)
        or not np.isclose(q.sum(), 1, rtol=0, atol=1e-14)
        or not isinstance(layout, dict)
        or set(layout) != {"anchors", "mass_columns"}
        or len(layout["anchors"]) != f.shape[1]
        or len(layout["mass_columns"]) != f.shape[1]
    ):
        raise ValueError("finite pilot values, normalized weights and explicit layout required")
    anchors, masses = layout["anchors"], layout["mass_columns"]
    if any(type(k) is not int or not 0 <= k < f.shape[1] for k in masses) or any(
        masses[k] != k or anchors[k] != 0 for k in masses
    ):
        raise ValueError("self-indexed prior mass columns required")
    parts, normalizers = [], []
    for k in dict.fromkeys(masses):
        groups = [
            [j for j, a in enumerate(anchors) if masses[j] == k and j != k and a == r]
            for r in (0, 0.025, 0.975)
        ]
        if any(not g for g in groups) or 1 + sum(map(len, groups)) != masses.count(k):
            raise ValueError("complete mean/lower/upper functional groups required")
        mass = f[:, k]
        z = float(q @ mass)
        if np.any(mass < 0) or not np.isfinite(z) or z <= 0:
            raise ValueError("positive finite prior-specific pilot mass required")
        normalizers.append(z)
        parts.append(
            np.column_stack(
                [
                    (mass + np.abs(f[:, groups[0]]).mean(axis=1)) / z,
                    np.abs(f[:, groups[1]] - 0.025 * mass[:, None]).mean(axis=1) / z,
                    np.abs(f[:, groups[2]] - 0.975 * mass[:, None]).mean(axis=1) / z,
                ]
            )
        )
    result = np.mean(parts, axis=0)
    if not np.isfinite(result).all():
        raise ValueError("nonfinite functional proposal envelope")
    return result, normalizers


def regularized_covariance(empirical, effective, reference):
    """The fixed d+2 shrinkage applies only to a proposal, not to football."""
    c, ref = np.asarray(empirical, float), np.asarray(reference, float)
    if (
        c.shape != ref.shape
        or c.ndim != 2
        or c.shape[0] != c.shape[1]
        or not np.isfinite([c, ref]).all()
        or not np.isfinite(effective)
        or effective < 1
        or not np.allclose(c, c.T, rtol=0, atol=1e-12)
        or np.linalg.eigvalsh(c).min() < -1e-12
    ):
        raise ValueError("finite centered covariance and effective weight count required")
    np.linalg.cholesky(ref)
    strength = len(c) + 2
    shrunk = (effective * c + strength * ref) / (effective + strength)
    bounded, clipped = bounded_covariance(shrunk)
    return 1.5 * bounded, clipped


def moment_component(points, weights, reference, fallback):
    x, w = np.asarray(points, float), np.asarray(weights, float)
    if (
        x.ndim != 2
        or w.shape != (len(x),)
        or not np.isfinite(x).all()
        or not np.isfinite(w).all()
        or np.any(w < 0)
        or not np.isfinite(w.sum())
    ):
        raise ValueError("finite nonnegative envelope weights required")
    if w.sum() == 0:
        return fallback[0].copy(), fallback[1].copy(), {"active": False, "reason": "zero_envelope"}
    total = float(w.sum())
    w = w / total
    mean = w @ x
    centered = x - mean
    covariance = (centered * w[:, None]).T @ centered
    # Floating sums may produce 1-epsilon for a single nonzero normalized weight.
    effective = max(1.0, float(1 / (w @ w)))
    final, clipped = regularized_covariance(covariance, effective, reference)
    return (
        mean,
        final,
        dict(
            active=True,
            envelope_mass=total,
            effective_weights=effective,
            maximum_weight=float(w.max()),
            mean=mean.tolist(),
            centered_covariance=covariance.tolist(),
            clipped_eigenvalues=clipped,
            normalized_weights_sha256=sha256(w.astype("<f8").tobytes()),
        ),
    )


def new_proposal(initial, means, covariances, geometry):
    return StabilizedProposal(
        initial.mean.copy(),
        initial.covariance.copy(),
        initial.prior_mean.copy(),
        initial.prior_covariance.copy(),
        geometry,
        np.asarray(means, float),
        np.asarray(covariances, float),
        np.ones(3) / 3,
    )


def initial_metadata(initial):
    parts = initial.components(METHOD)
    if len(parts) != 4 or any(p[3] is not None for p in parts) or parts[-1][0] != 0.1:
        raise ValueError("three Gaussian strata and original 10% Gaussian defense required")
    return dict(
        initial_sampling_sha256=sampling_hash(initial),
        initial_geometry=initial.diagnostics,
        initial_center=initial.mean.tolist(),
        initial_covariance=initial.covariance.tolist(),
        defensive_mean=initial.prior_mean.tolist(),
        defensive_covariance=initial.prior_covariance.tolist(),
    )


def fit_functional_proposal(f, initial, *, entropy, plan, layout):
    sampling = initial
    stages = []
    for iteration in range(plan["proposal_rounds"]):
        domain = [*entropy, iteration]
        points, q = training_points(sampling, domain, plan["proposal_nodes"])
        values = np.asarray(f(points, sampling.logpdf(points, METHOD)), float)
        env, normalizers = envelopes(values, q, layout)
        means, covs, moments = [], [], []
        for j in range(3):
            _, old_mean, old_covariance, _ = sampling.components(METHOD)[j]
            mean, cov, moment = moment_component(
                points, q * env[:, j], initial.covariance, (old_mean, old_covariance)
            )
            means.append(mean)
            covs.append(cov)
            moments.append(moment)
        stage = dict(
            entropy=domain,
            nodes=plan["proposal_nodes"],
            input_sampling_sha256=sampling_hash(sampling),
            points_sha256=sha256(points.astype("<f8").tobytes()),
            quadrature_weights_sha256=sha256(q.astype("<f8").tobytes()),
            responses_sha256=sha256(values.astype("<f8").tobytes()),
            prior_mass_estimates=normalizers,
            moments=moments,
            component_means=np.asarray(means).tolist(),
            component_covariances=np.asarray(covs).tolist(),
        )
        stages.append(dict(**stage, stage_sha256=sha256(json_bytes(stage))))
        sampling = new_proposal(initial, means, covs, {})
    geometry = dict(
        kind=KIND,
        **initial_metadata(initial),
        entropy=list(entropy),
        layout=layout,
        proposal_rounds=plan["proposal_rounds"],
        proposal_nodes=plan["proposal_nodes"],
        stages=stages,
        component_means=sampling.mixture_means.tolist(),
        component_covariances=sampling.mixture_covariances.tolist(),
        component_masses=sampling.mixture_masses.tolist(),
        geometry_uses_evaluation=False,
    )
    sampling.diagnostics = geometry
    return sampling


def restore_functional(geometry):
    """Parse a saved proposal; independent provenance validation is also required."""
    g = geometry
    mean, cov, prior, pcov, means, covs = [
        np.asarray(g[k], float)
        for k in (
            "initial_center",
            "initial_covariance",
            "defensive_mean",
            "defensive_covariance",
            "component_means",
            "component_covariances",
        )
    ]
    d = len(mean)
    if (
        g["kind"] != KIND
        or mean.shape != (d,)
        or d < 1
        or cov.shape != (d, d)
        or prior.shape != (d,)
        or pcov.shape != (d, d)
        or means.shape != (3, d)
        or covs.shape != (3, d, d)
        or not all(np.isfinite(a).all() for a in (mean, cov, prior, pcov, means, covs))
        or g["component_masses"] != [1 / 3] * 3
        or g["geometry_uses_evaluation"] is not False
    ):
        raise ValueError("invalid fitted functional geometry or support")
    for c in (cov, pcov, *covs):
        np.linalg.cholesky(c)
    return StabilizedProposal(mean, cov, prior, pcov, g, means, covs, np.ones(3) / 3)


def validate_functional_fit(geometry, initial, *, entropy, plan, layout):
    g = geometry
    fitted = restore_functional(g)
    metadata = initial_metadata(initial)
    if (
        json_bytes({k: g[k] for k in metadata}) != json_bytes(metadata)
        or g["entropy"] != entropy
        or json_bytes(g["layout"]) != json_bytes(layout)
        or g["proposal_rounds"] != plan["proposal_rounds"]
        or g["proposal_nodes"] != plan["proposal_nodes"]
        or len(g["stages"]) != plan["proposal_rounds"]
    ):
        raise ValueError("functional fitting provenance or independent layout differs")
    sampling = initial
    blocks = len(set(layout["mass_columns"]))
    for iteration, stage in enumerate(g["stages"]):
        masses = np.asarray(stage["prior_mass_estimates"], float)
        if (
            stage["stage_sha256"]
            != sha256(json_bytes({k: v for k, v in stage.items() if k != "stage_sha256"}))
            or stage["entropy"] != [*entropy, iteration]
            or stage["nodes"] != plan["proposal_nodes"]
            or stage["input_sampling_sha256"] != sampling_hash(sampling)
            or masses.shape != (blocks,)
            or not np.isfinite(masses).all()
            or np.any(masses <= 0)
            or len(stage["moments"]) != 3
        ):
            raise ValueError("proposal stage hash, mass, support or entropy differs")
        means, covs = [], []
        for j, moment in enumerate(stage["moments"]):
            if moment["active"] is False:
                if moment != {"active": False, "reason": "zero_envelope"}:
                    raise ValueError("unexplained inactive proposal component")
                _, mean, cov, _ = sampling.components(METHOD)[j]
            elif moment["active"] is True:
                mean = np.asarray(moment["mean"], float)
                cov, clipped = regularized_covariance(
                    moment["centered_covariance"], moment["effective_weights"], initial.covariance
                )
                if (
                    moment["clipped_eigenvalues"] != clipped
                    or moment["envelope_mass"] <= 0
                    or not np.isfinite(moment["envelope_mass"])
                    or not 0 < moment["maximum_weight"] <= 1
                    or moment["effective_weights"] > plan["proposal_nodes"] * (1 + 1e-14)
                ):
                    raise ValueError("proposal moments or effective weights differ")
            else:
                raise ValueError("explicit component activity required")
            means.append(np.asarray(mean).tolist())
            covs.append(np.asarray(cov).tolist())
        if json_bytes(means) != json_bytes(stage["component_means"]) or json_bytes(
            covs
        ) != json_bytes(stage["component_covariances"]):
            raise ValueError("proposal moment calculation does not reproduce")
        sampling = new_proposal(initial, means, covs, {})
    if sampling_hash(sampling) != sampling_hash(fitted):
        raise ValueError("final proposal differs from fitted rounds")
    return fitted
