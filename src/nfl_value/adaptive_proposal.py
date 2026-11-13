"""Density-only importance-proposal adaptation; never a fitted football model."""

from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp

from nfl_value.continuous_math import normal_logpdf
from nfl_value.replicated_reference import SamplingProposal, fit_proposal, replicate_integrals


def bounded_covariance(covariance):
    eigen, vectors = np.linalg.eigh(covariance)
    changed = int(np.count_nonzero((eigen < 1e-6) | (eigen > 36)))
    return (vectors * np.clip(eigen, 1e-6, 36)) @ vectors.T, changed


def weighted_mixture(points, weights, entropy):
    x, w = np.asarray(points, float), np.asarray(weights, float)
    if (
        x.ndim != 2
        or len(x) < 3
        or w.shape != (len(x),)
        or not np.isfinite(x).all()
        or not np.isfinite(w).all()
        or np.any(w < 0)
        or w.sum() <= 0
    ):
        raise ValueError("finite positively weighted pilot points required")
    w = w / w.sum()
    mean = w @ x
    centered = x - mean
    global_cov, initial_clipping = bounded_covariance((centered * w[:, None]).T @ centered)
    distance_scale = np.diag(global_cov)
    attempts = []
    fits = []
    for restart in range(3):
        rng = np.random.default_rng(np.random.SeedSequence([*entropy, restart]))
        centers = [x[rng.choice(len(x), p=w)]]
        for _ in range(2):
            distance = np.min(
                [np.sum((x - c) ** 2 / distance_scale, axis=1) for c in centers], axis=0
            )
            mass = w * distance
            centers.append(x[rng.choice(len(x), p=mass / mass.sum() if mass.sum() > 0 else w)])
        means = np.array(centers)
        covariances = np.array([global_cov.copy() for _ in range(3)])
        masses = np.full(3, 1 / 3)
        previous = None
        clipping = initial_clipping
        converged = False
        for iteration in range(100):
            log_density = np.column_stack(
                [np.log(p) + normal_logpdf(x, m, c) for p, m, c in zip(masses, means, covariances)]
            )
            log_total = logsumexp(log_density, axis=1)
            objective = float(w @ log_total)
            if previous is not None and abs(objective - previous) <= 1e-6:
                converged = True
                break
            previous = objective
            responsibilities = w[:, None] * np.exp(log_density - log_total[:, None])
            counts = responsibilities.sum(axis=0)
            for j in range(3):
                if counts[j] <= 1e-12:
                    continue
                local = responsibilities[:, j] / counts[j]
                means[j] = local @ x
                delta = x - means[j]
                covariances[j], clipped = bounded_covariance((delta * local[:, None]).T @ delta)
                clipping += clipped
            masses = np.maximum(counts, 0.01)
            masses /= masses.sum()
        final = float(
            w
            @ logsumexp(
                np.column_stack(
                    [
                        np.log(p) + normal_logpdf(x, m, c)
                        for p, m, c in zip(masses, means, covariances)
                    ]
                ),
                axis=1,
            )
        )
        attempts.append(
            dict(
                restart=restart,
                iterations=iteration + 1,
                converged=converged,
                weighted_log_likelihood=final,
                clipped_eigenvalues=clipping,
            )
        )
        fits.append((means.copy(), covariances.copy(), masses.copy()))
    best = max(range(3), key=lambda j: attempts[j]["weighted_log_likelihood"])
    means, covariances, masses = fits[best]
    return means, covariances, masses, dict(attempts=attempts, selected_restart=best)


@dataclass
class AdaptiveProposal(SamplingProposal):
    mixture_means: np.ndarray
    mixture_covariances: np.ndarray
    mixture_masses: np.ndarray

    def components(self, method):
        if method != "adaptive-mixture":
            raise ValueError("unreviewed adapted proposal")
        return [
            (0.9 * p, m, c, None)
            for p, m, c in zip(self.mixture_masses, self.mixture_means, self.mixture_covariances)
        ] + [(0.1, self.prior_mean, self.prior_covariance, None)]


def fit_adaptive(target, plan, case_index):
    initial = fit_proposal(target)
    offset = target.log_target(initial.mean) - initial.logpdf(initial.mean, "defensive-mixture")[0]
    batches = []

    def f(points, logq):
        logtarget = (
            target.logpdf(points)
            if hasattr(target, "logpdf")
            else np.array([target.log_target(p) for p in points])
        )
        weights = np.exp(logtarget - logq - offset)
        batches.append((points.copy(), weights.copy()))
        return weights[:, None]

    entropy = [plan["base_seed"], 3, case_index, 0]
    replicate_integrals(f, initial, "defensive-mixture", entropy=entropy, replicates=4, nodes=1024)
    if len(batches) != 8 or any(len(x) != 512 for x, w in batches):
        raise ValueError("density-pilot allocation differs from declared strata")
    points = np.vstack([x for x, w in batches])
    weights = np.concatenate([(0.9 if j % 2 == 0 else 0.1) * w for j, (x, w) in enumerate(batches)])
    weights /= weights.sum()
    means, covs, masses, diagnostics = weighted_mixture(
        points, weights, [plan["base_seed"], 4, case_index, 0]
    )
    covs *= 1.5
    diagnostics.update(
        density_pilot_entropy=entropy,
        pilot_nodes=len(points),
        pilot_effective_samples=float(1 / (weights @ weights)),
        pilot_initial_geometry=initial.diagnostics,
        geometry_uses_primary_qmc=False,
        component_means=means.tolist(),
        component_covariances=covs.tolist(),
        component_masses=masses.tolist(),
        learning_is_target_density_only=True,
    )
    return AdaptiveProposal(
        initial.mean,
        initial.covariance,
        initial.prior_mean,
        initial.prior_covariance,
        diagnostics,
        means,
        covs,
        masses,
    )
