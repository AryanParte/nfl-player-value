"""Independent replicate-covariance fitting of zero-mean control scales."""

import numpy as np

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.replicated_reference import replicate_integrals


def integration_scales(function_means, control_means, ridge):
    """One centered scalar slope per integral; no selection or coefficient clipping."""
    f, h = np.asarray(function_means, float), np.asarray(control_means, float)
    if (
        f.ndim != 2
        or f.shape != h.shape
        or f.shape[0] < 4
        or f.shape[1] < 1
        or not np.isfinite(f).all()
        or not np.isfinite(h).all()
        or not np.isfinite(ridge)
        or ridge <= 0
    ):
        raise ValueError("finite matching integration replicates and positive ridge required")
    fc, hc = f - f.mean(axis=0), h - h.mean(axis=0)
    cross = np.sum(fc * hc, axis=0)
    squares = np.sum(hc * hc, axis=0)
    alpha = np.divide(
        cross,
        (1 + ridge) * squares,
        out=np.zeros_like(cross),
        where=squares > 0,
    )
    if not np.isfinite([cross, squares, alpha]).all():
        raise ValueError("nonfinite replicate covariance or fitted scale")
    return dict(
        alpha=alpha.tolist(), cross_products=cross.tolist(), control_squares=squares.tolist()
    )


def fit_integration_control(f, fitted, sampling, *, entropy, replicates, nodes, ridge):
    from nfl_value.control_variates import FittedControl, METHOD

    def paired(points, logq):
        values = np.asarray(f(points, logq), float)
        control = fitted.adjustment(points, logq)
        if values.shape != control.shape or not np.isfinite(values).all():
            raise ValueError("integration fit response dimensions differ")
        return np.column_stack([values, control])

    raw = replicate_integrals(
        paired, sampling, METHOD, entropy=entropy, replicates=replicates, nodes=nodes
    )
    values, controls = np.split(raw, 2, axis=1)
    scale = integration_scales(values, controls, ridge)
    coefficients = fitted.coefficients * np.asarray(scale["alpha"])[None, :]
    if not np.isfinite(coefficients).all():
        raise ValueError("nonfinite integration-adjusted coefficients")
    diagnostics = dict(
        **fitted.diagnostics,
        integration_fit=dict(
            base_fit=fitted.record(),
            entropy=list(entropy),
            replicates=replicates,
            nodes_per_replicate=nodes,
            ridge=ridge,
            function_means=values.tolist(),
            control_means=controls.tolist(),
            **scale,
        ),
    )
    diagnostics.update(
        coefficients_sha256=sha256(json_bytes(coefficients.tolist())),
        coefficient_norm=float(np.linalg.norm(coefficients)),
    )
    return FittedControl(fitted.basis, coefficients, diagnostics)


def validate_integration_fit(fit, sampling, entropy, plan, columns, validate_point_fit):
    record = fit["integration_fit"]
    base = record["base_fit"]
    validate_point_fit(base, sampling, entropy, plan, columns)
    if "integration_fit" in base:
        raise ValueError("pointwise fit cannot contain another integration fit")
    f, h = np.asarray(record["function_means"]), np.asarray(record["control_means"])
    if (
        record["entropy"] != [*entropy[:-1], 3]
        or record["replicates"] != plan["integration_fit_replicates"]
        or record["nodes_per_replicate"] != plan["nodes_per_replicate"]
        or record["ridge"] != plan["integration_scale_ridge"]
        or f.shape != (plan["integration_fit_replicates"], columns)
        or h.shape != f.shape
    ):
        raise ValueError("independent integration training provenance or dimensions differ")
    actual = integration_scales(f, h, plan["integration_scale_ridge"])
    coefficients = np.asarray(base["coefficients"]) * np.asarray(actual["alpha"])[None, :]
    if (
        json_bytes(actual) != json_bytes({k: record[k] for k in actual})
        or json_bytes(coefficients.tolist()) != json_bytes(fit["coefficients"])
        or fit["coefficient_norm"] != float(np.linalg.norm(coefficients))
    ):
        raise ValueError("integration scales or coefficient product do not reproduce")
