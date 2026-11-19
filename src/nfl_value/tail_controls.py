"""Frozen analytic mixtures with broader or displaced mass than their proposal."""

from functools import lru_cache

import numpy as np

from nfl_value.density_holdout import StabilizedProposal
from nfl_value.ingestion import json_bytes
from nfl_value.randomized_controls import KnownTarget


class TailTarget(KnownTarget):
    def __init__(self, index):
        if type(index) is not int or index not in (5, 6):
            raise ValueError("unknown tail fixture")
        super().__init__(2, {})
        self.means = np.zeros((2, 4))
        self.covariances = np.array([np.eye(4), np.diag([4.0, 1, 1, 1])])
        self.probabilities = np.array([0.9, 0.1])
        if index == 6:
            self.means[1] = [4, 4, 0, 0]
            self.covariances[1] = np.diag([0.5, 0.5, 1, 1])


def tail_proposal():
    geometry = dict(
        kind="fixed-analytic-tail-design-v1",
        central_mean=[0.0] * 4,
        central_covariance=np.eye(4).tolist(),
        defensive_mean=[0.0] * 4,
        defensive_covariance=(9 * np.eye(4)).tolist(),
        central_strata=3,
        central_mass=0.9,
        defensive_mass=0.1,
        fitted=False,
        geometry_uses_primary_qmc=False,
    )
    return StabilizedProposal(
        np.zeros(4),
        np.eye(4),
        np.zeros(4),
        9 * np.eye(4),
        geometry,
        np.zeros((3, 4)),
        np.array([np.eye(4)] * 3),
        np.ones(3) / 3,
    )


@lru_cache(maxsize=2)
def tail_truth_bytes(index):
    return json_bytes({k: v.tolist() for k, v in TailTarget(index).exact().items()})
