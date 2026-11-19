"""Analytic population-moment diagnostic; never a candidate or admission gate."""

import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import stdtr
from scipy.stats import norm, t

from nfl_value.adaptive_proposal import bounded_covariance
from nfl_value.functional_proposal import new_proposal
from nfl_value.ingestion import sha256
from nfl_value.tail_controls import TailTarget, tail_proposal, tail_truth_bytes


def projection_moments(mean, covariance, contrast, function, *, cusp=None):
    """Integrate g(a'X), X*g(a'X), and XX'*g(a'X) by normal conditioning."""
    mu, cov, a = (np.asarray(x, float) for x in (mean, covariance, contrast))
    if (
        mu.ndim != 1
        or a.shape != mu.shape
        or cov.shape != (len(mu), len(mu))
        or not all(np.isfinite(v).all() for v in (mu, cov, a))
    ):
        raise ValueError("finite normal mean, covariance and contrast required")
    np.linalg.cholesky(cov)
    location = float(a @ mu)
    variance = float(a @ cov @ a)
    if variance <= 0:
        raise ValueError("positive projection variance required")
    sd = np.sqrt(variance)
    b = cov @ a / sd

    def integrand(z):
        value = float(function(location + sd * z))
        return norm.pdf(z) * value * np.array([1, z, z * z])

    limits = [-np.inf, np.inf] if cusp is None else [-np.inf, (cusp - location) / sd, np.inf]
    integrals, error = np.zeros(3), 0.0
    for low, high in zip(limits[:-1], limits[1:]):
        value, estimate = quad_vec(integrand, low, high, epsabs=1e-10, epsrel=1e-10)
        integrals += value
        error += estimate
    if not np.isfinite(integrals).all() or not np.isfinite(error) or error > 1e-8:
        raise ValueError("population quadrature unresolved")
    m0, m1, m2 = integrals
    first = mu * m0 + b * m1
    second = (cov - np.outer(b, b) + np.outer(mu, mu)) * m0
    second += (np.outer(mu, b) + np.outer(b, mu)) * m1 + np.outer(b, b) * m2
    return float(m0), first, second, float(error)


def tilted_mean_displacement_bound(covariance, amplitude):
    """Bound mean movement under any positive multiplicative 1+amplitude*h tilt.

    Requires |h|<=1; this does not bound covariance or estimator error.
    """
    cov = np.asarray(covariance, float)
    if (
        cov.ndim != 2
        or cov.shape[0] != cov.shape[1]
        or not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T, rtol=0, atol=1e-12)
        or not np.isfinite(amplitude)
        or not 0 <= amplitude < 1
    ):
        raise ValueError("finite covariance and bounded positive tilt required")
    np.linalg.cholesky(cov)
    return float(amplitude * np.sqrt(np.trace(cov)) / (1 - amplitude))


def initial_pilot_box(index):
    """Gaussian allocation calculation, not an iid/QMC discovery experiment."""
    target, initial = TailTarget(index), tail_proposal()
    center = target.means[1, :2]
    radius = np.sqrt(np.diag(target.covariances[1])[:2])
    low, high = center - radius, center + radius

    def probability(mean, covariance):
        c = np.asarray(covariance)[:2, :2]
        if c[0, 1] != 0 or c[1, 0] != 0:
            raise ValueError("independent first two coordinates required for box formula")
        sd, mu = np.sqrt(np.diag(c)), np.asarray(mean)[:2]
        return float(np.prod(norm.sf((low - mu) / sd) - norm.sf((high - mu) / sd)))

    components = initial.components("stabilized-mixture")
    probabilities = [probability(m, c) for _, m, c, _ in components]
    # Equal point allocation differs from the proposal mixture's probability mass.
    counts = [2048 * p for p in probabilities]
    return dict(
        coordinates=[0, 1],
        lower=low.tolist(),
        upper=high.tolist(),
        other_coordinates="unrestricted",
        first_round_nodes_per_stratum=2048,
        target_probability=sum(
            p * probability(m, c)
            for p, m, c in zip(target.probabilities, target.means, target.covariances)
        ),
        proposal_probability=sum(p * q for (p, _, _, _), q in zip(components, probabilities)),
        stratum_probabilities=probabilities,
        expected_points_by_stratum=counts,
        expected_total_points=sum(counts),
        any_point_probability_upper_bound=min(1.0, sum(counts)),
        caveat="initial allocation only, using declared Gaussian point marginals and Markov's inequality; no iid independence assumption, actual discovery frequency, second-round or precision conclusion",
    )


def population_geometry(index):
    target = TailTarget(index)
    truth = json.loads(tail_truth_bytes(index))
    d = len(target.groups)
    base_mass = float(target.probabilities.sum())
    base_first = target.probabilities @ target.means
    base_second = sum(
        p * (c + np.outer(m, m))
        for p, m, c in zip(target.probabilities, target.means, target.covariances)
    )
    components = []
    means, covariances = [], []
    for family in ("mean_mass", "lower", "upper"):
        if family == "mean_mass":
            mass, first, second = base_mass, base_first.copy(), base_second.copy()
        else:
            mass, first, second = 0.0, np.zeros(d), np.zeros((d, d))
        error = 0.0
        terms = []
        for j, a in enumerate(target.contrasts):
            if family == "mean_mass":
                center, scale = truth["mean"][j], truth["sd"][j]
                terms.append((a, lambda x, c=center, s=scale: abs((x - c) / s), center))
            else:
                anchor = 0.025 if family == "lower" else 0.975
                scale = np.sqrt(target.noise[j])
                endpoint = truth["low" if family == "lower" else "high"][j]
                for q in [endpoint] if family == "lower" else [endpoint, endpoint - 0.5]:
                    terms.append(
                        (
                            a,
                            lambda x, q=q, s=scale, r=anchor: abs(stdtr(20, (q - x) / s) - r),
                            q - scale * t.ppf(anchor, 20),
                        )
                    )
        for a, g, cusp in terms:
            for p, mu, cov in zip(target.probabilities, target.means, target.covariances):
                z, one, two, e = projection_moments(mu, cov, a, g, cusp=cusp)
                factor = p / len(terms)
                mass += factor * z
                first += factor * one
                second += factor * two
                error += factor * e
        mean = first / mass
        covariance = second / mass - np.outer(mean, mean)
        final, clipped = bounded_covariance(covariance)
        final *= 1.5
        means.append(mean)
        covariances.append(final)
        components.append(
            dict(
                family=family,
                envelope_mass=float(mass),
                mean=mean.tolist(),
                covariance=covariance.tolist(),
                proposal_covariance=final.tolist(),
                clipped_eigenvalues=clipped,
                estimated_univariate_quadrature_error=float(error),
                coarse_surrogate_mean_displacement_bound=tilted_mean_displacement_bound(
                    covariance, 0.001
                ),
            )
        )
    sampling = new_proposal(tail_proposal(), means, covariances, {})
    return dict(
        target=index,
        components=components,
        component_means=np.asarray(means).tolist(),
        component_covariances=np.asarray(covariances).tolist(),
        population_target="unperturbed_fine_target_envelopes",
        coarse_surrogate_amplitude=0.001,
        initial_pilot_box=initial_pilot_box(index),
        probe_points=target.means.tolist(),
        population_log_density_ratios_at_centers=(
            target.logpdf(target.means) - sampling.logpdf(target.means, "stabilized-mixture")
        ).tolist(),
        caveat="unperturbed fine-target envelope moments, not exact coarse-pilot population moments; comparison gaps also include bounded surrogate tilt and finite-pilot covariance shrinkage; no candidate draws, oracle precision test or admission; center probes are not global bounds; quadrature errors and evaluated tilt bounds are not certified floating-point-error-inclusive bounds; tilt bounds concern means only, not covariance or numerical accuracy",
    )


def main():
    print(
        json.dumps(
            dict(
                diagnostic="population_moments_not_a_candidate",
                source_sha256=sha256(Path(__file__).read_bytes()),
                cases={str(i): population_geometry(i) for i in (5, 6, 7)},
                ranking_ready=False,
            ),
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
