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
            )
        )
    sampling = new_proposal(tail_proposal(), means, covariances, {})
    return dict(
        target=index,
        components=components,
        component_means=np.asarray(means).tolist(),
        component_covariances=np.asarray(covariances).tolist(),
        probe_points=target.means.tolist(),
        population_log_density_ratios_at_centers=(
            target.logpdf(target.means) - sampling.logpdf(target.means, "stabilized-mixture")
        ).tolist(),
        caveat="population envelope moments only; no finite-pilot shrinkage, candidate draws, oracle precision test or admission; point probes are not global bounds; quadrature errors are estimates for univariate moments, not certified bounds on final geometry",
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
