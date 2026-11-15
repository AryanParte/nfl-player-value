"""Replay the one frozen failed density fit without repairing or replacing it."""

import json
from pathlib import Path
from time import perf_counter

import numpy as np

from nfl_value.density_cli import load
from nfl_value.density_holdout import fit_pair
from nfl_value.ingest_cli import committed_revision
from nfl_value.ingestion import SnapshotStore, json_bytes, sha256
from nfl_value.multiseason_math import GROUPS
from nfl_value.reference_pilot import load_inputs, prepare_case
from nfl_value.variance_mixture import marginal_stats
from nfl_value.variance_reference import BoundedTarget


class TraceTarget(BoundedTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failures = []

    def conditional(self, eta, contrasts, need_games=False):
        try:
            return super().conditional(eta, contrasts, need_games)
        except np.linalg.LinAlgError as exc:
            values = np.exp(eta)
            penalty = np.zeros(len(self.prepared.names))
            game = None
            for group, value in zip(self.groups, values):
                if group == "game":
                    game = value
                else:
                    penalty[self.group_indices[group]] = value
            gram, _, _, _ = marginal_stats(self.prepared, self.stats, game)
            h = gram + np.diag(penalty)
            eigen = np.linalg.eigvalsh(h)
            self.failures.append(
                dict(
                    error=str(exc),
                    coordinates=np.asarray(eta).tolist(),
                    groups=self.groups,
                    precisions=values.tolist(),
                    evaluations=self.evaluations,
                    matrix_dimension=len(h),
                    matrix_sha256=sha256(h.astype("<f8").tobytes()),
                    matrix_symmetry_error=float(np.max(np.abs(h - h.T))),
                    eigenvalue_minimum=float(eigen.min()),
                    eigenvalue_maximum=float(eigen.max()),
                    nonpositive_eigenvalues=int(np.count_nonzero(eigen <= 0)),
                    smallest_random_penalty=float(penalty[self.prepared.fixed_count :].min()),
                    fixed_count=self.prepared.fixed_count,
                    matrix_maximum_absolute_entry=float(np.abs(h).max()),
                    matrix_scale_roundoff=float(np.finfo(float).eps * np.linalg.norm(h, 2)),
                )
            )
            raise


def main():
    revision = committed_revision()
    root = Path("data/derived")
    report_id = "d29590d4c9adb157b9343720c28614da9918fb5571ea927cb880aa4bf4421b30"
    _, report = load(SnapshotStore(root / "density-holdout"), report_id)
    expected = report["cases"]["continuous_prior_0"]["density"][0]
    if expected["status"] != "failed":
        raise ValueError("frozen failed trial required")
    stores = [SnapshotStore(Path("data/raw/source-snapshots"))] + [
        SnapshotStore(root / p)
        for p in ["offensive-inputs", "multiseason", "continuous-variance-diagnostic"]
    ]
    context, parent = load_inputs(*stores, report["primary_plan"], print)
    d, y, _, variant, _ = prepare_case(context, parent["plan"], "continuous_prior_0")
    target = TraceTarget(
        d,
        y,
        [g for g in GROUPS[variant] if g != "innovation"] + ["game"],
        context["parent"]["plan"],
        parent["plan"],
        evaluation_limit=90000,
        deadline=perf_counter() + 900,
    )
    error = None
    try:
        fit_pair(target, report["plan"], 102, 0)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        error = str(exc)
    result = dict(
        parent_density_report=report_id,
        code_revision=revision,
        response_sha256=sha256(y.astype("<f8").tobytes()),
        error=error,
        original_error=expected["error"],
        failures=target.failures,
        same_failure_reproduced=error == expected["error"],
        conditional_evaluations=target.evaluations,
        original_trial_replaced=False,
        numerical_repair_attempted=False,
        calibration_completed=False,
        ranking_ready=False,
    )
    output = SnapshotStore(root / "density-failure-trace")
    rid = output.put(json_bytes(result), manifest=True)
    print(json.dumps(dict(report_id=rid, result=result), indent=2))
    return 0 if result["same_failure_reproduced"] and target.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
