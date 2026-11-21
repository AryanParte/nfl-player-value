"""Failure-inclusive mode diagnostics; no new acceptance gate or estimator."""

import argparse
from collections import Counter
import json
from pathlib import Path
import runpy

import numpy as np

from nfl_value.ingestion import SnapshotStore
from nfl_value.mode_preflight import inputs, load, summarize
from nfl_value.mode_proposal import restore_modes

HELPERS = runpy.run_path(str(Path(__file__).with_name("analyze_coarse_controls.py")))


def quantiles(values):
    return np.quantile(values, [0, 0.05, 0.5, 0.95, 1], axis=0).tolist() if len(values) else None


def case_summary(case, plan, target, initial):
    records = case["records"]
    fitted = [r for r in records if "geometry" in r]
    complete_pairs = [
        r
        for r in records
        if r["status"] == "complete" and r.get("plain_assessment", {}).get("status") == "complete"
    ]
    work = [r["work"]["total"] for r in records if "work" in r]
    g = [r["geometry"] for r in fitted]
    modes = [r.get("fit_trace", {}).get("discovered_modes", []) for r in records]
    mode_counts = Counter(len(m) for m in modes)
    result = dict(
        decision=case["decision"],
        plain_decision=summarize(
            [r.get("plain_assessment", dict(status="unattempted")) for r in records], plan
        ),
        retained_fits=len(fitted),
        raw_integral_trials=sum("coarse" in r for r in records),
        failure_reasons=dict(Counter(r.get("error") for r in records if r["status"] != "complete")),
        target_evaluation_quantiles=quantiles(work),
        mode_count_frequencies={str(k): v for k, v in sorted(mode_counts.items())}
        if case["arm"] == "candidate"
        else None,
        optimizer_usable_counts=quantiles(
            [sum(a["usable"] for a in r.get("fit_trace", {}).get("attempts", [])) for r in records]
        )
        if case["arm"] == "candidate"
        else None,
        pilot_mass_quantiles=quantiles([x["pilot_mass"] for x in g if "pilot_mass" in x]),
        pilot_maximum_weight_quantiles=quantiles(
            [x["pilot_maximum_weight"] for x in g if "pilot_maximum_weight" in x]
        ),
        raw_errors=HELPERS["raw_estimator_diagnostics"](records),
        isolated_wrong_endpoints=HELPERS["isolated_wrong_endpoint_diagnostics"](
            records, plan["reference_endpoint_cdf_tolerance"]
        ),
    )
    decomposition = HELPERS["known_gate_decomposition"](records, plan)
    decomposition["incomplete_trials"] = decomposition.pop("failed_confidence_trials")
    decomposition["failed_confidence_with_raw"] = sum(
        r["status"] == "failed" and "coarse" in r for r in records
    )
    decomposition["without_raw_integrals"] = sum("coarse" not in r for r in records)
    result["precision_decomposition"] = decomposition
    if len(complete_pairs) > 1:
        result["paired_complete_errors"] = HELPERS["paired_errors"](
            [r["bounds"]["estimate"] for r in complete_pairs],
            [r["plain_assessment"]["bounds"]["estimate"] for r in complete_pairs],
            HELPERS["TRUTH"],
        )
    if case["target"] >= 5:
        centers = target.means
        result["component_centers"] = dict(
            points=centers.tolist(),
            fitted_log_density_ratio_quantiles=quantiles(
                [
                    target.logpdf(centers)
                    - restore_modes(x, initial).logpdf(centers, "stabilized-mixture")
                    for x in g
                ]
            ),
            minimum_discovered_distance_quantiles=quantiles(
                [
                    np.min(
                        np.linalg.norm(np.array(m)[:, None, :] - centers[None, :, :], axis=2),
                        axis=0,
                    )
                    for m in modes
                    if m
                ]
            ),
            caveat="Fine-target component means are diagnostic probes, not necessarily density modes; distances are latent coordinates; no oracle selection or global variance bound",
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store", type=Path)
    parser.add_argument("report_id")
    parser.add_argument("--reconstruction", type=Path)
    args = parser.parse_args()
    store = SnapshotStore(args.store)
    manifest, result = load(store, args.report_id)
    fixtures = inputs(result["plan"])
    audit = dict(
        report_id=args.report_id,
        manifest=manifest,
        screen_passed=result["screen_passed"],
        numerical_certified=False,
        ranking_ready=False,
        cases={},
    )
    for c in result["cases"]:
        target, initial, _ = fixtures[c["target"]]
        audit["cases"][f"{c['arm']}-{c['target']}"] = case_summary(
            c, result["plan"], target, initial
        )
    if args.reconstruction:
        replica = SnapshotStore(args.reconstruction)
        load(replica, args.report_id)
        audit["independent_reconstruction_identical"] = HELPERS["verify_reconstruction"](
            store, replica
        )
    print(json.dumps(audit, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
