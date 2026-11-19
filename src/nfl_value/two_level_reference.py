"""Independent replicated integrals of coarse + (fine - coarse).

The correction is paired at identical points before normalization. No surrogate
is substituted for the target; the returned raw replicates retain both levels.
"""

import numpy as np

from nfl_value.density_holdout import StabilizedProposal
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.replicated_reference import replicate_integrals


def sampling_hash(sampling):
    """Bind the ordered full distribution, including its defensive component."""
    return sha256(
        json_bytes(
            [
                [mass, mean.tolist(), covariance.tolist(), df]
                for mass, mean, covariance, df in sampling.components("stabilized-mixture")
            ]
        )
    )


def integrate(
    fine, coarse, sampling, *, entropy, replicates, nodes, correction_nodes, progress=lambda _: None
):
    method = "stabilized-mixture"
    components = sampling.components(method)
    for count in (nodes, correction_nodes):
        if (
            type(count) is not int
            or count < 2 * len(components)
            or count & (count - 1)
            or count % len(components)
        ):
            raise ValueError("complete power-of-two component nets required at both levels")
    base = replicate_integrals(
        coarse,
        sampling,
        method,
        entropy=[*entropy, 0],
        replicates=replicates,
        nodes=nodes,
        progress=lambda s: progress("coarse " + s),
    )

    def difference(points, logq):
        f, c = np.asarray(fine(points, logq)), np.asarray(coarse(points, logq))
        if f.shape != c.shape or f.ndim != 2 or not np.isfinite([f, c]).all():
            raise ValueError("paired finite integrands with identical dimensions required")
        return f - c

    correction = replicate_integrals(
        difference,
        sampling,
        method,
        entropy=[*entropy, 1],
        replicates=replicates,
        nodes=correction_nodes,
        progress=lambda s: progress("correction " + s),
    )
    return combine(base, correction), base, correction


def combine(base, correction):
    base, correction = np.asarray(base, float), np.asarray(correction, float)
    if (
        base.ndim != 2
        or base.shape != correction.shape
        or base.shape[0] < 2
        or base.shape[1] < 1
        or not np.isfinite([base, correction]).all()
    ):
        raise ValueError("complete finite paired replicate arrays required")
    total = base + correction
    if not np.isfinite(total).all():
        raise ValueError("nonfinite combined integral")
    return total


def restore_proposal(geometry, model_plan):
    """Restore the declared saved geometry without fitting or selecting a trial."""
    if geometry.get("kind") == "functional-moment-proposal-v1":
        from nfl_value.functional_proposal import restore_functional

        return restore_functional(geometry)
    initial = geometry["pilot_initial_geometry"]
    mean = np.asarray(initial["mode"], float)
    covariance = np.asarray(initial["covariance"], float)
    means = np.asarray(geometry["component_means"], float)
    covariances = np.asarray(geometry["component_covariances"], float)
    masses = np.asarray(geometry["component_masses"], float)
    d = len(mean)
    if (
        mean.shape != (d,)
        or d < 1
        or covariance.shape != (d, d)
        or means.shape != (3, d)
        or covariances.shape != (3, d, d)
        or masses.shape != (3,)
        or np.any(masses <= 0)
        or not np.isclose(masses.sum(), 1, rtol=0, atol=1e-14)
        or not all(np.isfinite(a).all() for a in [mean, covariance, means, covariances, masses])
        or geometry["geometry_uses_primary_qmc"] is not False
        or geometry["learning_is_target_density_only"] is not True
    ):
        raise ValueError("invalid independently fitted saved proposal")
    np.linalg.cholesky(covariance)
    np.linalg.cholesky(covariances)
    return StabilizedProposal(
        mean,
        covariance,
        np.full(d, model_plan["log_precision_mean"]),
        np.eye(d) * model_plan["log_precision_sd"] ** 2,
        geometry,
        means,
        covariances,
        masses,
    )
