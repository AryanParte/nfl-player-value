"""Independent two-direction controls for fixed-anchor ratio influences."""

import numpy as np

from nfl_value.ingestion import json_bytes, sha256
from nfl_value.integration_controls import integration_scales
from nfl_value.replicated_reference import replicate_integrals


def ratio_layout(contrasts, blocks=1, *, wrong_endpoints=False):
    if (
        type(contrasts) is not int
        or contrasts < 1
        or type(blocks) is not int
        or blocks < 1
        or type(wrong_endpoints) is not bool
    ):
        raise ValueError("positive contrast/block counts and explicit endpoint layout required")
    anchors = [0.0] + [0.0] * contrasts + [0.025] * contrasts + [0.975] * contrasts
    if wrong_endpoints:
        anchors += [0.975] * contrasts
    width = len(anchors)
    return dict(
        anchors=anchors * blocks,
        mass_columns=[block * width for block in range(blocks) for _ in range(width)],
    )


def joint_slopes(function_means, control_means, layout, ridge):
    """Fit N-rZ on [h_N,h_Z], then restore the common mass-control term."""
    f, h = np.asarray(function_means, float), np.asarray(control_means, float)
    scalar = integration_scales(f, h, ridge)
    if not isinstance(layout, dict) or set(layout) != {"anchors", "mass_columns"}:
        raise ValueError("explicit joint ratio layout required")
    anchors = np.asarray(layout["anchors"], float)
    masses = layout["mass_columns"]
    width = f.shape[1]
    if (
        set(layout) != {"anchors", "mass_columns"}
        or anchors.shape != (width,)
        or len(masses) != width
        or not np.isfinite(anchors).all()
        or any(type(k) is not int or k < 0 or k >= width for k in masses)
        or any(masses[k] != k or anchors[k] != 0 for k in masses)
    ):
        raise ValueError("explicit finite anchors and self-indexed mass columns required")
    fc, hc = f - f.mean(axis=0), h - h.mean(axis=0)
    numerator, mass, singular_values = [], [], []
    for j, (k, anchor) in enumerate(zip(masses, anchors)):
        if j == k:
            numerator.append(scalar["alpha"][j])
            mass.append(0.0)
            singular_values.append([])
            continue
        design = hc[:, [j, k]]
        scales = np.linalg.norm(design, axis=0)
        scales = np.where(scales > 0, scales, 1)
        u, singular, vt = np.linalg.svd(design / scales, full_matrices=False)
        denominator = singular**2 + ridge * singular[0] ** 2
        factor = np.divide(
            singular, denominator, out=np.zeros_like(singular), where=denominator > 0
        )
        slope = (vt.T @ (factor * (u.T @ (fc[:, j] - anchor * fc[:, k])))) / scales
        numerator.append(float(slope[0]))
        mass.append(float(slope[1] + anchor * scalar["alpha"][k]))
        singular_values.append(singular.tolist())
    if not np.isfinite([numerator, mass]).all():
        raise ValueError("nonfinite joint coefficients")
    return dict(
        numerator_slopes=numerator,
        mass_slopes=mass,
        mass_scalar_fit=scalar,
        singular_values=singular_values,
    )


def coefficient_product(base, slopes, layout):
    coefficients = np.asarray(base, float)
    result = coefficients * np.asarray(slopes["numerator_slopes"])[None, :]
    result += coefficients[:, layout["mass_columns"]] * np.asarray(slopes["mass_slopes"])[None, :]
    if not np.isfinite(result).all():
        raise ValueError("nonfinite joint coefficient product")
    return result


def fit_joint_control(f, fitted, sampling, *, entropy, replicates, nodes, ridge, layout):
    from nfl_value.control_variates import FittedControl, METHOD

    def paired(points, logq):
        values = np.asarray(f(points, logq), float)
        controls = fitted.adjustment(points, logq)
        if values.shape != controls.shape or not np.isfinite(values).all():
            raise ValueError("joint training response dimensions differ")
        return np.column_stack([values, controls])

    raw = replicate_integrals(
        paired, sampling, METHOD, entropy=entropy, replicates=replicates, nodes=nodes
    )
    values, controls = np.split(raw, 2, axis=1)
    slopes = joint_slopes(values, controls, layout, ridge)
    coefficients = coefficient_product(fitted.coefficients, slopes, layout)
    diagnostics = dict(
        **fitted.diagnostics,
        joint_fit=dict(
            base_fit=fitted.record(),
            entropy=list(entropy),
            replicates=replicates,
            nodes_per_replicate=nodes,
            ridge=ridge,
            layout=layout,
            function_means=values.tolist(),
            control_means=controls.tolist(),
            **slopes,
        ),
    )
    diagnostics.update(
        coefficients_sha256=sha256(json_bytes(coefficients.tolist())),
        coefficient_norm=float(np.linalg.norm(coefficients)),
    )
    return FittedControl(fitted.basis, coefficients, diagnostics)


def validate_joint_fit(fit, sampling, entropy, plan, columns, validate_point_fit, layout):
    record = fit["joint_fit"]
    base = record["base_fit"]
    validate_point_fit(base, sampling, entropy, plan, columns)
    if "integration_fit" in base or "joint_fit" in base or "integration_fit" in fit:
        raise ValueError("joint fit must use the independent pointwise fit")
    f, h = np.asarray(record["function_means"]), np.asarray(record["control_means"])
    if (
        record["entropy"] != [*entropy[:-1], 3]
        or record["replicates"] != plan["integration_fit_replicates"]
        or record["nodes_per_replicate"] != plan["nodes_per_replicate"]
        or record["ridge"] != plan["integration_scale_ridge"]
        or json_bytes(record["layout"]) != json_bytes(layout)
        or f.shape != (plan["integration_fit_replicates"], columns)
        or h.shape != f.shape
    ):
        raise ValueError("independent joint training provenance or layout differs")
    actual = joint_slopes(f, h, layout, plan["integration_scale_ridge"])
    coefficients = coefficient_product(base["coefficients"], actual, layout)
    if (
        json_bytes(actual) != json_bytes({k: record[k] for k in actual})
        or json_bytes(coefficients.tolist()) != json_bytes(fit["coefficients"])
        or fit["coefficient_norm"] != float(np.linalg.norm(coefficients))
    ):
        raise ValueError("joint slopes or coefficient product do not reproduce")
