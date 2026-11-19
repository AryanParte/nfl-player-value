"""Separately fitted zero-mean Gaussian controls for unnormalized integrals."""

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaincinv, ndtri
from scipy.stats import qmc

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.replicated_reference import replicate_integrals
from nfl_value.two_level_reference import combine, sampling_hash

METHOD = "stabilized-mixture"


class GaussianControls:
    """Each column integrates to zero under the complete proposal density q."""

    def __init__(self, sampling):
        self.sampling_sha256 = sampling_hash(sampling)
        self.parts = []
        self.dimension = len(sampling.mean)
        for _, mean, covariance, _ in sampling.components(METHOD):
            chol = np.linalg.cholesky(covariance)
            self.parts.append(
                (
                    np.asarray(mean),
                    np.linalg.inv(chol),
                    self.dimension * np.log(2 * np.pi) / 2 + np.log(np.diag(chol)).sum(),
                )
            )
        self.width = len(self.parts) * (
            1 + self.dimension + self.dimension * (self.dimension + 1) // 2
        )

    def features(self, points, logq):
        points, logq = np.asarray(points, float), np.asarray(logq, float)
        if (
            points.ndim != 2
            or points.shape[1] != self.dimension
            or logq.shape != (len(points),)
            or not np.isfinite(points).all()
            or not np.isfinite(logq).all()
        ):
            raise ValueError("finite points and full proposal log density required")
        columns = []
        for mean, inverse, normalizer in self.parts:
            z = np.einsum("ij,kj->ik", points - mean, inverse, optimize=False)
            ratio = np.exp(-0.5 * np.sum(z * z, axis=1) - normalizer - logq)
            columns.append(ratio - 1)
            columns.extend(ratio * z[:, i] for i in range(self.dimension))
            columns.extend(
                ratio * (z[:, i] * z[:, j] - int(i == j))
                for i in range(self.dimension)
                for j in range(i, self.dimension)
            )
        result = np.column_stack(columns)
        if not np.isfinite(result).all():
            raise ValueError("nonfinite zero-mean controls")
        return result


def training_points(sampling, entropy, nodes):
    parts = sampling.components(METHOD)
    if (
        type(nodes) is not int
        or nodes < 2 * len(parts)
        or nodes & (nodes - 1)
        or nodes % len(parts)
        or not entropy
        or any(type(i) is not int or i < 0 for i in entropy)
    ):
        raise ValueError("independent entropy and complete power-of-two training nets required")
    count, dimension = nodes // len(parts), len(sampling.mean)
    points, weights = [], []
    for j, (mass, mean, covariance, df) in enumerate(parts):
        rng = np.random.default_rng(np.random.SeedSequence([*entropy, j]))
        unit = qmc.Sobol(d=dimension + 1, scramble=True, bits=52, seed=rng).random_base2(
            count.bit_length() - 1
        )
        if np.any((unit <= 0) | (unit >= 1)):
            raise ValueError("non-interior training coordinate")
        z = ndtri(unit[:, :dimension])
        if df is not None:
            z *= np.sqrt(df / (2 * gammaincinv(df / 2, unit[:, dimension])))[:, None]
        points.append(mean + np.einsum("ij,kj->ik", z, np.linalg.cholesky(covariance)))
        weights.extend([mass / count] * count)
    return np.vstack(points), np.array(weights)


@dataclass
class FittedControl:
    basis: GaussianControls
    coefficients: np.ndarray
    diagnostics: dict

    def adjustment(self, points, logq):
        return self.basis.features(points, logq) @ self.coefficients

    def record(self):
        return dict(coefficients=self.coefficients.tolist(), **self.diagnostics)


def fit_control(f, sampling, *, entropy, nodes, relative_ridge):
    if not np.isfinite(relative_ridge) or relative_ridge <= 0:
        raise ValueError("positive fixed numerical ridge required")
    points, weights = training_points(sampling, entropy, nodes)
    logq = sampling.logpdf(points, METHOD)
    y = np.asarray(f(points, logq), float)
    if y.ndim != 2 or y.shape[0] != nodes or y.shape[1] < 1 or not np.isfinite(y).all():
        raise ValueError("complete finite training responses required")
    if np.any(weights <= 0) or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-14):
        raise ValueError("normalized positive mixture fitting weights required")
    basis = GaussianControls(sampling)
    h = basis.features(points, logq)
    hmean, ymean = weights @ h, weights @ y
    centered = h - hmean
    scales = np.sqrt(weights @ (centered * centered))
    scales = np.where(scales > 0, scales, 1)
    design = np.sqrt(weights)[:, None] * centered / scales
    u, singular, vt = np.linalg.svd(design, full_matrices=False)
    penalty = relative_ridge * singular[0] ** 2
    factor = np.divide(
        singular,
        singular * singular + penalty,
        out=np.zeros_like(singular),
        where=singular * singular + penalty > 0,
    )
    coefficients = vt.T @ (factor[:, None] * (u.T @ (np.sqrt(weights)[:, None] * (y - ymean))))
    coefficients /= scales[:, None]
    residual = y - ymean - centered @ coefficients
    if not np.isfinite(coefficients).all() or not np.isfinite(residual).all():
        raise ValueError("nonfinite fitted control")
    diagnostics = dict(
        training_entropy=list(entropy),
        training_nodes=nodes,
        sampling_sha256=basis.sampling_sha256,
        points_sha256=sha256(points.astype("<f8").tobytes()),
        weights_sha256=sha256(weights.astype("<f8").tobytes()),
        responses_sha256=sha256(y.astype("<f8").tobytes()),
        coefficients_sha256=sha256(json_bytes(coefficients.tolist())),
        feature_count=basis.width,
        relative_ridge=relative_ridge,
        singular_values=singular.tolist(),
        numerical_rank=int(
            np.count_nonzero(singular > max(design.shape) * np.finfo(float).eps * singular[0])
        ),
        coefficient_norm=float(np.linalg.norm(coefficients)),
        training_residual_rms=np.sqrt(weights @ (residual * residual)).tolist(),
        training_response_rms=np.sqrt(weights @ ((y - ymean) ** 2)).tolist(),
    )
    return FittedControl(basis, coefficients, diagnostics)


def controlled_integrals(f, fitted, sampling, *, entropy, replicates, nodes, progress=None):
    if fitted.basis.sampling_sha256 != sampling_hash(sampling):
        raise ValueError("fitted control belongs to a different proposal")
    means = []

    def adjusted(points, logq):
        values = np.asarray(f(points, logq), float)
        adjustment = fitted.adjustment(points, logq)
        if values.shape != adjustment.shape or not np.isfinite(values).all():
            raise ValueError("fitted control response dimensions differ")
        means.append(values.mean(axis=0))
        return values - adjustment

    controlled = replicate_integrals(
        adjusted,
        sampling,
        METHOD,
        entropy=entropy,
        replicates=replicates,
        nodes=nodes,
        progress=progress,
    )
    parts = sampling.components(METHOD)
    if len(means) != replicates * len(parts):
        raise ValueError("incomplete paired plain reference")
    plain = []
    for rep in range(replicates):
        total = np.zeros(controlled.shape[1])
        for j, (mass, *_rest) in enumerate(parts):
            total += mass * means[rep * len(parts) + j]
        plain.append(total)
    return controlled, np.asarray(plain)


def integrate_controlled(fine, coarse, sampling, *, entropy, plan, progress=lambda _: None):
    fitted = fit_control(
        coarse,
        sampling,
        entropy=[*entropy, 2],
        nodes=plan["training_nodes"],
        relative_ridge=plan["relative_ridge"],
    )
    if plan.get("plan_version") == 2:
        from nfl_value.integration_controls import fit_integration_control

        fitted = fit_integration_control(
            coarse,
            fitted,
            sampling,
            entropy=[*entropy, 3],
            replicates=plan["integration_fit_replicates"],
            nodes=plan["nodes_per_replicate"],
            ridge=plan["integration_scale_ridge"],
        )
    controlled, plain = controlled_integrals(
        coarse,
        fitted,
        sampling,
        entropy=[*entropy, 0],
        replicates=plan["replicates"],
        nodes=plan["nodes_per_replicate"],
        progress=lambda s: progress("coarse " + s),
    )

    def difference(points, logq):
        f, c = np.asarray(fine(points, logq)), np.asarray(coarse(points, logq))
        if f.shape != c.shape or f.ndim != 2 or not np.isfinite([f, c]).all():
            raise ValueError("finite paired fine/coarse dimensions required")
        return f - c

    correction = replicate_integrals(
        difference,
        sampling,
        METHOD,
        entropy=[*entropy, 1],
        replicates=plan["replicates"],
        nodes=plan["correction_nodes_per_replicate"],
        progress=lambda s: progress("correction " + s),
    )
    return dict(
        total=combine(controlled, correction),
        coarse=controlled,
        plain_coarse=plain,
        correction=correction,
        fit=fitted.record(),
    )
