"""Frozen paired diagnostics for completed coarse-control known-answer trials."""

import argparse
import json
from pathlib import Path

import numpy as np

from nfl_value.coarse_control_study import load
from nfl_value.density_holdout import coverage_summary
from nfl_value.ingestion import SnapshotStore

TRUTH = np.array([1.0, 0, 0, 0.025, 0.025, 0.975, 0.975])


def ratios(a, b):
    return [float(x / y) if y > 0 else None for x, y in zip(a, b)]


def paired_errors(adjusted, plain, truth):
    adjusted, plain, truth = (np.asarray(x, float) for x in (adjusted, plain, truth))
    if (
        adjusted.ndim != 2
        or adjusted.shape != plain.shape
        or adjusted.shape[1:] != truth.shape
        or len(adjusted) < 2
        or not all(np.isfinite(x).all() for x in (adjusted, plain, truth))
    ):
        raise ValueError("complete finite paired estimate matrices required")
    variance = adjusted.var(axis=0, ddof=1)
    plain_variance = plain.var(axis=0, ddof=1)
    mse = np.mean((adjusted - truth) ** 2, axis=0)
    plain_mse = np.mean((plain - truth) ** 2, axis=0)
    return dict(
        paired_complete_trials=len(adjusted),
        adjusted_bias=(adjusted.mean(axis=0) - truth).tolist(),
        plain_bias=(plain.mean(axis=0) - truth).tolist(),
        adjusted_variance=variance.tolist(),
        plain_variance=plain_variance.tolist(),
        adjusted_to_plain_variance=ratios(variance, plain_variance),
        adjusted_rmse=np.sqrt(mse).tolist(),
        plain_rmse=np.sqrt(plain_mse).tolist(),
        adjusted_to_plain_mse=ratios(mse, plain_mse),
    )


def delta_variance(raw):
    """First-order diagnostic only; original Fieller gates remain authoritative."""
    raw = np.asarray(raw, float)[:, :, :7]
    mass = raw[:, :, 0]
    h = raw - mass[:, :, None] * TRUTH
    h[:, :, 0] = mass
    variance = h.var(axis=1, ddof=1) / raw.shape[1]
    variance[:, 1:] /= mass.mean(axis=1)[:, None] ** 2
    return variance.mean(axis=0)


def summary(result):
    output = {}
    for case in result["cases"]:
        records = case["records"]
        plain = [r.get("plain_assessment", {"status": "failed"}) for r in records]
        paired = [
            r
            for r in records
            if r["status"] == "complete"
            and r.get("plain_assessment", {}).get("status") == "complete"
        ]
        item = dict(
            adjusted_decision=case["decision"],
            plain_decision=coverage_summary(plain, result["plan"]),
            requested_trials=len(records),
            paired_complete_trials=len(paired),
            paired_subset_is_not_an_acceptance_gate=True,
        )
        if len(paired) >= 2:
            stats = paired_errors(
                [r["bounds"]["estimate"] for r in paired],
                [r["plain_assessment"]["bounds"]["estimate"] for r in paired],
                TRUTH,
            )
            adjusted = np.array([r["coarse"] for r in paired]) + np.array(
                [r["correction"] for r in paired]
            )
            unadjusted = np.array([r["plain_coarse"] for r in paired]) + np.array(
                [r["correction"] for r in paired]
            )
            stats.update(
                adjusted_estimated_to_empirical_variance=ratios(
                    delta_variance(adjusted), stats["adjusted_variance"]
                ),
                plain_estimated_to_empirical_variance=ratios(
                    delta_variance(unadjusted), stats["plain_variance"]
                ),
                minimum_adjusted_replicate_mass=float(adjusted[:, :, 0].min()),
                coefficient_norm_quantiles=np.quantile(
                    [r["fit"]["coefficient_norm"] for r in paired], [0, 0.5, 0.95, 1]
                ).tolist(),
                fit_rank_range=[
                    min(r["fit"]["numerical_rank"] for r in paired),
                    max(r["fit"]["numerical_rank"] for r in paired),
                ],
                mean_training_residual_rms=np.mean(
                    [r["fit"]["training_residual_rms"] for r in paired], axis=0
                ).tolist(),
                mean_training_response_rms=np.mean(
                    [r["fit"]["training_response_rms"] for r in paired], axis=0
                ).tolist(),
            )
            item.update(stats)
        output[str(case["target"])] = item
    return output


def verify_reconstruction(original, replica):
    counts = {}
    for kind in ("objects", "manifests"):
        names = {p.name for p in (original.root / kind).iterdir()}
        if names != {p.name for p in (replica.root / kind).iterdir()}:
            raise ValueError("independent reconstruction has different object set")
        for name in names:
            digest = name.removesuffix(".json") if kind == "manifests" else name
            if original.read(digest, manifest=kind == "manifests") != replica.read(
                digest, manifest=kind == "manifests"
            ):
                raise ValueError("independent reconstruction bytes differ")
        counts[kind] = len(names)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store", type=Path)
    parser.add_argument("report")
    parser.add_argument("--reconstruction", type=Path)
    args = parser.parse_args()
    output = SnapshotStore(args.store)
    manifest, result = load(output, args.report)
    audit = dict(
        report_id=args.report,
        manifest=manifest,
        cases=summary(result),
        controls_passed=result["controls_passed"],
        ranking_ready=False,
        analysis="paired_consumed_numerical_diagnostics_not_player_calibration",
        numerical_variance_diagnostic="sample variance of numerator minus known ratio times mass, divided by replicate count and squared mean mass; mass column uses direct variance",
    )
    if args.reconstruction:
        audit["independent_reconstruction_identical"] = verify_reconstruction(
            output, SnapshotStore(args.reconstruction)
        )
    print(json.dumps(audit, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
