"""Analytically centered affine-probit controls fitted without validation truth."""

import numpy as np
from scipy.special import ndtr, ndtri

from nfl_value.control_variates import GaussianControls
from nfl_value.ingestion import json_bytes, sha256

KIND = "gaussian-affine-probit-v1"
STABLE_KIND = "gaussian-affine-probit-v2"


class EndpointControls(GaussianControls):
    """Gaussian kernels define the controls even for Student-t sampling strata."""

    def __init__(self, sampling, directions, *, stable=False):
        super().__init__(sampling)
        self.stable = stable
        self.directions = np.asarray(directions, float)
        if (
            self.directions.ndim != 3
            or self.directions.shape[0] != len(self.parts)
            or self.directions.shape[1] < 1
            or self.directions.shape[2] != self.dimension + 1
            or not np.isfinite(self.directions).all()
        ):
            raise ValueError("finite complete affine endpoint directions required")
        self.centers = ndtr(
            self.directions[:, :, 0] / np.sqrt(1 + np.sum(self.directions[:, :, 1:] ** 2, axis=2))
        )
        self.width += len(self.parts) * self.directions.shape[1]

    def features(self, points, logq):
        polynomial = super().features(points, logq)
        columns = [polynomial]
        for j, (mean, inverse, normalizer) in enumerate(self.parts):
            z = np.einsum("ij,kj->ik", points - mean, inverse, optimize=False)
            ratio = np.exp(-0.5 * np.sum(z * z, axis=1) - normalizer - logq)
            if self.stable:
                from nfl_value.cdf_increment import centered_probit

                centered = centered_probit(self.directions[j, :, 0], self.directions[j, :, 1:], z)
            else:
                affine = self.directions[j, :, 0] + z @ self.directions[j, :, 1:].T
                centered = ndtr(affine) - self.centers[j]
            columns.append(ratio[:, None] * centered)
        result = np.column_stack(columns)
        if not np.isfinite(result).all():
            raise ValueError("nonfinite endpoint controls")
        return result


def fit_endpoint_basis(sampling, points, weights, logq, responses, settings):
    """Only independent coarse training responses enter this auxiliary fit."""
    columns = settings["columns"]
    clip, ridge = settings["probability_clip"], settings["direction_ridge"]
    y, points, weights, logq = (np.asarray(x, float) for x in (responses, points, weights, logq))
    stable = settings["kind"] == STABLE_KIND
    if (
        settings["kind"] not in (KIND, STABLE_KIND)
        or (stable and settings.get("arithmetic") != "stable_normal_increment_v1")
        or settings["direction_fit"] != "component_gaussian_weighted_affine_probit"
        or settings["training"] != "same_independent_point_fit_no_extra_evaluations"
        or not np.isfinite([clip, ridge]).all()
        or not 0 < clip < 0.5
        or ridge <= 0
        or not columns
        or len(set(columns)) != len(columns)
        or y.ndim != 2
        or y.shape[0] != len(points)
        or not np.isfinite(y).all()
        or any(type(k) is not int or not 1 <= k < y.shape[1] for k in columns)
        or weights.shape != (len(points),)
        or not np.isfinite(weights).all()
        or np.any(weights <= 0)
        or np.any(y[:, 0] < 0)
    ):
        raise ValueError("complete finite mass/CDF fitting responses and settings required")
    valid = y[:, 0] > 0
    if not valid.any() or np.any(y[~valid][:, columns] != 0):
        raise ValueError("positive fitting mass and consistent zero-mass CDF rows required")
    probability = y[valid][:, columns] / y[valid, 0, None]
    if not np.isfinite(probability).all() or np.any(
        (probability < -1e-14) | (probability > 1 + 1e-14)
    ):
        raise ValueError("CDF responses must be probabilities conditional on mass")
    # This clipping transforms an auxiliary fit only, never a target integral.
    response = ndtri(np.clip(probability, clip, 1 - clip))
    basis = GaussianControls(sampling)
    directions, weight_hashes = [], []
    for mean, inverse, normalizer in basis.parts:
        z = np.einsum("ij,kj->ik", points - mean, inverse, optimize=False)[valid]
        ratio = np.exp(-0.5 * np.sum(z * z, axis=1) - normalizer - logq[valid])
        w = weights[valid] * ratio
        if not np.isfinite(w).all() or w.sum() <= 0:
            raise ValueError("positive finite Gaussian-kernel fitting weights required")
        w /= w.sum()
        zmean = w @ z
        if stable:
            deviation = response - response[0]
            mean_deviation = w @ deviation
            ymean = response[0] + mean_deviation
            residual_response = deviation - mean_deviation
        else:
            ymean = w @ response
            residual_response = response - ymean
        centered = z - zmean
        design = np.sqrt(w)[:, None] * centered
        rhs = np.sqrt(w)[:, None] * residual_response
        # Independent augmented least-squares reference protects collinear fits.
        augmented = np.vstack([design, np.sqrt(ridge) * np.eye(basis.dimension)])
        slopes = np.linalg.lstsq(
            augmented, np.vstack([rhs, np.zeros((basis.dimension, len(columns)))]), rcond=None
        )[0]
        directions.append(np.column_stack([ymean - zmean @ slopes, slopes.T]))
        weight_hashes.append(sha256(w.astype("<f8").tobytes()))
    fitted = EndpointControls(sampling, directions, stable=stable)
    record = dict(
        settings=settings,
        directions=fitted.directions.tolist(),
        centers=fitted.centers.tolist(),
        gaussian_weight_sha256=weight_hashes,
        transformed_response_sha256=sha256(response.astype("<f8").tobytes()),
        positive_mass_rows=int(valid.sum()),
        zero_mass_rows=int((~valid).sum()),
        clipped_low=np.sum(probability < clip, axis=0).tolist(),
        clipped_high=np.sum(probability > 1 - clip, axis=0).tolist(),
    )
    return fitted, dict(endpoint_basis=record, endpoint_basis_sha256=sha256(json_bytes(record)))
