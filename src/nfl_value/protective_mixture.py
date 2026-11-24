"""Fixed protection of both fitted proposals; no functional-error selection."""

from dataclasses import dataclass

import numpy as np

from nfl_value.control_variates import METHOD
from nfl_value.ingestion import json_bytes
from nfl_value.mode_proposal import restore_modes
from nfl_value.replicated_reference import SamplingProposal
from nfl_value.tail_mixture import fit_tail_mixture, restore_tail_mixture
from nfl_value.two_level_reference import sampling_hash

KIND = "protective-mode-tail-mixture-v1"


@dataclass
class ProtectiveProposal(SamplingProposal):
    mode: SamplingProposal
    tail: SamplingProposal
    mode_mass: float

    def components(self, method):
        if method != METHOD or not np.isfinite(self.mode_mass) or not 0 < self.mode_mass < 1:
            raise ValueError("reviewed method and positive protective mixture masses required")
        return [
            (weight * mass, mean, covariance, df)
            for weight, proposal in ((self.mode_mass, self.mode), (1 - self.mode_mass, self.tail))
            for mass, mean, covariance, df in proposal.components(METHOD)
        ]


def protect(mode, tail, mass):
    """Keep ordered strata and exact full density; duplicates retain their mass."""
    if len(mode.mean) != len(tail.mean):
        raise ValueError("protective proposal dimensions differ")
    q = ProtectiveProposal(
        mode.mean.copy(),
        mode.covariance.copy(),
        mode.prior_mean.copy(),
        mode.prior_covariance.copy(),
        {},
        mode,
        tail,
        mass,
    )
    q.components(METHOD)
    return q


def bind(mode, tail, initial, plan):
    sampling = protect(mode, tail, plan["protective_mode_mass"])
    g = tail.diagnostics
    sampling.diagnostics = dict(
        kind=KIND,
        entropy=g["entropy"],
        initial_sampling_sha256=sampling_hash(initial),
        search_entropy=g["search_entropy"],
        pilot_entropy=g["pilot_entropy"],
        mode_mass=plan["protective_mode_mass"],
        mode_sampling_sha256=sampling_hash(mode),
        tail_sampling_sha256=sampling_hash(tail),
        sampling_sha256=sampling_hash(sampling),
        tail_geometry=g,
        geometry_uses_evaluation=False,
        fit_work=g["fit_work"],
    )
    return sampling


def fit_protective_mixture(log_density, initial, *, entropy, plan, work):
    tail = fit_tail_mixture(log_density, initial, entropy=entropy, plan=plan, work=work)
    mode = restore_modes(tail.diagnostics["mode_geometry"], initial)
    return bind(mode, tail, initial, plan)


def restore_protective_mixture(g, initial, plan):
    tail = restore_tail_mixture(g["tail_geometry"], initial, plan)
    mode = restore_modes(tail.diagnostics["mode_geometry"], initial)
    sampling = bind(mode, tail, initial, plan)
    if json_bytes(g) != json_bytes(sampling.diagnostics):
        raise ValueError("protective geometry, mass, provenance or work differs")
    return sampling
