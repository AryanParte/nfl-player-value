"""Independent pilot allocation; mixture masses, not sample counts, weight estimates."""

import numpy as np
from scipy.special import gammaincinv, ndtri
from scipy.stats import qmc

from nfl_value.control_variates import METHOD, fit_control
from nfl_value.ingestion import json_bytes
from nfl_value.two_level_reference import combine, sampling_hash


def power_two(value):
    return type(value) is int and value >= 2 and not value & (value - 1)


def weighted_total(component_means, masses):
    values, masses = np.asarray(component_means, float), np.asarray(masses, float)
    if (
        values.ndim != 3
        or values.shape[1] != len(masses)
        or values.shape[2] < 1
        or masses.ndim != 1
        or not np.isfinite(values).all()
        or not np.isfinite(masses).all()
        or np.any(masses <= 0)
        or not np.isclose(masses.sum(), 1, rtol=0, atol=1e-12)
    ):
        raise ValueError("finite component means and complete positive mixture masses required")
    total = masses[0] * values[:, 0]
    for j in range(1, len(masses)):
        total = total + masses[j] * values[:, j]
    return total


def component_integrals(f, sampling, *, entropy, replicates, counts, fitted=None):
    """Retain independent component nets, using the full proposal density throughout."""
    parts = sampling.components(METHOD)
    if (
        type(replicates) is not int
        or replicates < 2
        or len(counts) != len(parts)
        or not all(power_two(n) for n in counts)
        or not entropy
        or any(type(x) is not int or x < 0 for x in entropy)
        or (fitted is not None and fitted.basis.sampling_sha256 != sampling_hash(sampling))
    ):
        raise ValueError(
            "independent entropy, complete power-of-two nets and matching fit required"
        )
    d, width = len(sampling.mean), None
    plain, controlled = [], []
    for rep in range(replicates):
        p, c = [], []
        for j, (_mass, mean, covariance, df) in enumerate(parts):
            rng = np.random.default_rng(np.random.SeedSequence([*entropy, rep, j]))
            unit = qmc.Sobol(d=d + 1, scramble=True, bits=52, seed=rng).random_base2(
                counts[j].bit_length() - 1
            )
            if np.any((unit <= 0) | (unit >= 1)):
                raise ValueError("non-interior randomized coordinate")
            z = ndtri(unit[:, :d])
            if df is not None:
                z *= np.sqrt(df / (2 * gammaincinv(df / 2, unit[:, d])))[:, None]
            points = mean + np.einsum(
                "ij,kj->ik", z, np.linalg.cholesky(covariance), optimize=False
            )
            logq = sampling.logpdf(points, METHOD)
            y = np.asarray(f(points, logq), float)
            if (
                y.ndim != 2
                or y.shape[0] != counts[j]
                or y.shape[1] < 1
                or (width is not None and y.shape[1] != width)
                or not np.isfinite(y).all()
            ):
                raise ValueError("finite consistent vector integrals required")
            width = y.shape[1]
            adjustment = fitted.adjustment(points, logq) if fitted is not None else np.zeros_like(y)
            if adjustment.shape != y.shape or not np.isfinite(adjustment).all():
                raise ValueError("control dimensions or values differ")
            p.append(y.mean(axis=0))
            c.append((y - adjustment).mean(axis=0))
        plain.append(p)
        controlled.append(c)
    plain, controlled = np.array(plain), np.array(controlled)
    masses = [part[0] for part in parts]
    return dict(
        plain=weighted_total(plain, masses),
        controlled=weighted_total(controlled, masses),
        plain_components=plain,
        controlled_components=controlled,
    )


def allocate(scores, budget, minimum):
    """Exact finite inverse-count optimum; no claim of optimal QMC allocation."""
    scores = np.asarray(scores, float)
    if (
        scores.ndim != 1
        or len(scores) == 0
        or not np.isfinite(scores).all()
        or np.any(scores < 0)
        or not power_two(budget)
        or not power_two(minimum)
        or minimum * len(scores) > budget
    ):
        raise ValueError(
            "finite nonnegative allocation scores and feasible power-of-two budget required"
        )
    if np.all(scores == 0):
        equal = budget // len(scores)
        if equal * len(scores) != budget or not power_two(equal):
            raise ValueError("zero-score equal allocation unavailable")
        return [equal] * len(scores)
    options = [2**k for k in range(minimum.bit_length() - 1, budget.bit_length())]
    states = {0: (0.0, ())}
    for score in scores:
        next_states = {}
        for used, (loss, counts) in states.items():
            for n in options:
                if used + n > budget:
                    continue
                candidate = (loss + float(score) / n, (*counts, n))
                key = used + n
                if key not in next_states or candidate < next_states[key]:
                    next_states[key] = candidate
        states = next_states
    if budget not in states:
        raise ValueError("no complete component allocation")
    return list(states[budget][1])


def pilot_allocation(plain, controlled, masses, plan):
    plain, controlled = np.asarray(plain, float), np.asarray(controlled, float)
    columns = plan["allocation_ratio_columns"]
    tolerances = np.asarray(plan["allocation_tolerances"], float)
    if (
        plain.shape != controlled.shape
        or plain.ndim != 3
        or plain.shape[:2] != (plan["allocation_replicates"], len(masses))
        or plain.shape[0] < 2
        or not np.isfinite(controlled).all()
        or not columns
        or len(set(columns)) != len(columns)
        or any(type(k) is not int or not 1 <= k < plain.shape[2] for k in columns)
        or tolerances.shape != (len(columns),)
        or not np.isfinite(tolerances).all()
        or np.any(tolerances <= 0)
    ):
        raise ValueError("complete finite independent allocation pilot required")
    average = weighted_total(plain, masses).mean(axis=0)
    if average[0] <= 0:
        raise ValueError("positive pilot normalizing mass required")
    anchors = average[columns] / average[0]
    residual = controlled[:, :, columns] - controlled[:, :, 0, None] * anchors
    variance = np.var(residual, axis=0, ddof=1)
    scores = (
        np.asarray(masses) ** 2
        * plan["allocation_component_nodes"]
        * np.sum(variance / tolerances**2, axis=1)
    )
    counts = allocate(scores, plan["nodes_per_replicate"], plan["allocation_minimum_nodes"])
    return dict(
        anchors=anchors.tolist(),
        residual_variances=variance.tolist(),
        scores=scores.tolist(),
        counts=counts,
        predicted_loss=float(sum(float(s) / n for s, n in zip(scores, counts))),
    )


def integrate_allocated(
    fine, coarse, sampling, *, entropy, fitting_entropy, plan, adaptive, endpoint_settings=None
):
    fitted = fit_control(
        coarse,
        sampling,
        entropy=[*fitting_entropy, 2],
        nodes=plan["training_nodes"],
        relative_ridge=plan["relative_ridge"],
        endpoint_settings=endpoint_settings,
    )
    parts = sampling.components(METHOD)
    masses = [part[0] for part in parts]
    pilot = component_integrals(
        coarse,
        sampling,
        entropy=[*fitting_entropy, 30],
        replicates=plan["allocation_replicates"],
        counts=[plan["allocation_component_nodes"]] * len(parts),
        fitted=fitted,
    )
    allocation = pilot_allocation(
        pilot["plain_components"], pilot["controlled_components"], masses, plan
    )
    counts = (
        allocation["counts"]
        if adaptive
        else [plan["nodes_per_replicate"] // len(parts)] * len(parts)
    )
    evaluated = component_integrals(
        coarse,
        sampling,
        entropy=[*entropy, 0],
        replicates=plan["replicates"],
        counts=counts,
        fitted=fitted,
    )

    def difference(points, logq):
        f, c = np.asarray(fine(points, logq)), np.asarray(coarse(points, logq))
        if f.shape != c.shape or f.ndim != 2 or not np.isfinite([f, c]).all():
            raise ValueError("finite paired fine/coarse dimensions required")
        return f - c

    correction = component_integrals(
        difference,
        sampling,
        entropy=[*entropy, 1],
        replicates=plan["replicates"],
        counts=[plan["correction_nodes_per_replicate"] // len(parts)] * len(parts),
    )
    evidence = dict(
        sampling_sha256=sampling_hash(sampling),
        mixture_masses=masses,
        pilot_entropy=[*fitting_entropy, 30],
        coarse_entropy=[*entropy, 0],
        correction_entropy=[*entropy, 1],
        pilot_plain=pilot["plain_components"].tolist(),
        pilot_controlled=pilot["controlled_components"].tolist(),
        allocation=allocation,
        applied_counts=counts,
        adaptive=adaptive,
        coarse_components=evaluated["controlled_components"].tolist(),
        plain_components=evaluated["plain_components"].tolist(),
        correction_components=correction["plain_components"].tolist(),
    )
    return dict(
        coarse=evaluated["controlled"],
        plain_coarse=evaluated["plain"],
        correction=correction["plain"],
        fit=fitted.record(),
        components=evidence,
        total=combine(evaluated["controlled"], correction["plain"]),
    )


def validate_components(record, sampling, entropy, fitting_entropy, plan, adaptive):
    evidence = record["components"]
    masses = [p[0] for p in sampling.components(METHOD)]
    if (
        evidence["sampling_sha256"] != sampling_hash(sampling)
        or evidence["mixture_masses"] != masses
        or evidence["pilot_entropy"] != [*fitting_entropy, 30]
        or evidence["coarse_entropy"] != [*entropy, 0]
        or evidence["correction_entropy"] != [*entropy, 1]
        or evidence["adaptive"] is not adaptive
    ):
        raise ValueError("allocation proposal, random domains or arm differ")
    if any(
        np.asarray(evidence[key]).shape != (plan["allocation_replicates"], len(masses), 9)
        for key in ("pilot_plain", "pilot_controlled")
    ):
        raise ValueError("allocation pilot functional dimensions differ")
    allocation = pilot_allocation(
        evidence["pilot_plain"], evidence["pilot_controlled"], masses, plan
    )
    expected = (
        allocation["counts"]
        if adaptive
        else [plan["nodes_per_replicate"] // len(masses)] * len(masses)
    )
    if (
        json_bytes(allocation) != json_bytes(evidence["allocation"])
        or evidence["applied_counts"] != expected
    ):
        raise ValueError("allocation does not reproduce independent pilot")
    for key, target in (
        ("coarse_components", "coarse"),
        ("plain_components", "plain_coarse"),
        ("correction_components", "correction"),
    ):
        raw = np.asarray(evidence[key], float)
        if raw.shape != (plan["replicates"], len(masses), 9) or json_bytes(
            weighted_total(raw, masses).tolist()
        ) != json_bytes(record[target]):
            raise ValueError("component means do not reconstruct saved integrals")
