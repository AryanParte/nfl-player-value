"""Failure-inclusive mode diagnostics; no new acceptance gate or estimator."""

import argparse
from collections import Counter
import json
from pathlib import Path
import runpy

import numpy as np

from nfl_value.coarse_work import execution_plan, work_plan
from nfl_value.ingestion import SnapshotStore
from nfl_value.mode_preflight import (
    fitting_plan,
    inputs,
    load,
    mode_geometry,
    restore_proposal,
    summarize,
)
from nfl_value.protective_mixture import KIND as PROTECTIVE_KIND
from nfl_value.tail_mixture import KIND as TAIL_KIND

HELPERS = runpy.run_path(str(Path(__file__).with_name("analyze_coarse_controls.py")))


def quantiles(values):
    return np.quantile(values, [0, 0.05, 0.5, 0.95, 1], axis=0).tolist() if len(values) else None


def matched_comparison(candidate, baseline, *, matched_geometry=True):
    a, b = candidate["records"], baseline["records"]
    if len(a) != len(b) or any(x["trial"] != y["trial"] for x, y in zip(a, b)):
        raise ValueError("matched trial denominator differs")
    cross, groups, points = Counter(), {}, []
    failed_ci_pairs = 0
    for x, y in zip(a, b):
        flags = (bool(x.get("precision_passed", False)), bool(y.get("precision_passed", False)))
        cross[str(flags)] += 1
        modes = str(len(x.get("fit_trace", {}).get("discovered_modes", [])))
        group = groups.setdefault(modes, dict(trials=0, candidate_precise=0, baseline_precise=0))
        group["trials"] += 1
        group["candidate_precise"] += flags[0]
        group["baseline_precise"] += flags[1]
        estimates = []
        for r in (x, y):
            if "coarse" not in r or "correction" not in r:
                continue
            average = (np.asarray(r["coarse"]) + np.asarray(r["correction"])).mean(axis=0)[:7]
            if np.isfinite(average).all() and average[0] > 0:
                estimates.append(np.r_[average[0], average[1:] / average[0]])
        if len(estimates) == 2:
            points.append(estimates)
            failed_ci_pairs += x["status"] != "complete" or y["status"] != "complete"
    error = (
        HELPERS["paired_errors"]([p[0] for p in points], [p[1] for p in points], HELPERS["TRUTH"])
        if len(points) > 1
        else None
    )
    return dict(
        requested_pairs=len(a),
        defined_point_pairs=len(points),
        included_failed_confidence_pairs=failed_ci_pairs,
        precision_cross_tab=dict(cross),
        initial_mode_groups=groups,
        paired_point_errors=error,
        diagnostic_arm=baseline.get("arm", "baseline"),
        caveat=(
            "Matched fitting geometry"
            if matched_geometry
            else "Common fitting entropy but changed search and geometry"
        )
        + "; separate evaluation randomness; adjusted labels denote the first named arm, plain labels denote the named diagnostic. All defined point estimates include failed confidence sets. Groups and comparisons are descriptive, never selectable validation subsets or NFL causal effects.",
    )


def allocation_diagnostics(records, plan):
    available = [r for r in records if "components" in r]
    counts, rows = Counter(), []
    for r in available:
        e = r["components"]
        n = e["applied_counts"]
        counts[str(n)] += 1
        anchors = np.asarray(e["allocation"]["anchors"])
        c = np.asarray(e["coarse_components"])
        columns = plan["allocation_ratio_columns"]
        residual = c[:, :, columns] - c[:, :, 0, None] * anchors
        # Saved masses have been checked against the reconstructed proposal.
        # Both pilot and evaluation variance remain descriptive.
        masses = np.asarray(e["mixture_masses"])
        scales = np.asarray(plan["allocation_tolerances"])
        pilot_var = np.asarray(e["allocation"]["residual_variances"])
        observed_var = np.var(residual, axis=0, ddof=1)
        predicted_var = pilot_var * plan["allocation_component_nodes"] / np.asarray(n)[:, None]
        total = np.asarray(r["coarse"])
        total_residual = total[:, columns] - total[:, 0, None] * anchors
        rows.append(
            dict(
                trial=r["trial"],
                predicted_component_variance=predicted_var.tolist(),
                observed_component_variance=observed_var.tolist(),
                observed_total_residual_variance=np.var(total_residual, axis=0, ddof=1).tolist(),
                observed_component_loss=float(
                    np.sum(masses[:, None] ** 2 * observed_var / scales**2)
                ),
                observed_total_loss=float(
                    np.sum(np.var(total_residual, axis=0, ddof=1) / scales**2)
                ),
                pilot_allocation_loss=e["allocation"]["predicted_loss"],
                applied_predicted_loss=float(
                    sum(s / count for s, count in zip(e["allocation"]["scores"], n))
                ),
            )
        )
    return dict(
        retained=len(available),
        counts_frequencies=dict(counts),
        pilot_score_quantiles=quantiles(
            [r["components"]["allocation"]["scores"] for r in available]
        ),
        component_variance_comparisons=rows,
        caveat="Pilot anchors are reused only for diagnosis. Independent pilot and evaluation nets; inverse-count prediction is a heuristic, not QMC optimality or a coverage certificate. All raw confidence failures are retained; no diagnostic estimator selection.",
    )


def endpoint_diagnostics(records):
    """Saved-array diagnostics only; oracle probabilities never enter fitting."""
    rows = []
    truth = np.array([0.025, 0.025, 0.975, 0.975])
    for r in records:
        if "coarse" not in r or "correction" not in r or "plain_coarse" not in r:
            continue
        variances = {}
        for name in ("coarse", "plain_coarse", "correction"):
            raw = np.asarray(r[name])
            residual = raw[:, 3:7] - raw[:, 0, None] * truth
            variances[name] = np.var(residual, axis=0, ddof=1)
        c, p, d = (variances[k] for k in ("coarse", "plain_coarse", "correction"))
        row = dict(
            trial=r["trial"],
            status=r["status"],
            residual_variances={k: v.tolist() for k, v in variances.items()},
            controlled_plain_variance_ratio=[float(a / b) if b > 0 else None for a, b in zip(c, p)],
            correction_variance_fraction=[
                float(b / (a + b)) if a + b > 0 else None for a, b in zip(c, d)
            ],
            coefficient_norm=r["fit"]["coefficient_norm"],
        )
        e = r["fit"].get("endpoint_basis")
        if e is not None:
            row["auxiliary_fit"] = dict(
                positive_mass_rows=e["positive_mass_rows"],
                zero_mass_rows=e["zero_mass_rows"],
                clipped_low=e["clipped_low"],
                clipped_high=e["clipped_high"],
                largest_absolute_direction=float(np.max(np.abs(e["directions"]))),
            )
        rows.append(row)
    return dict(
        retained_raw_trials=len(rows),
        requested=len(records),
        trials=rows,
        caveat="Conditional-on-fit residual variance at known endpoint probabilities; diagnostic only, not ratio confidence coverage. Null ratios denote zero denominator variance. Retains raw evidence from failed confidence constructions; clipping describes auxiliary fitting, never target clipping.",
    )


def case_summary(case, plan, target, initial):
    plan = execution_plan(plan, case["arm"])
    fit_plan = fitting_plan(plan, case["arm"])
    records = case["records"]
    fitted = [r for r in records if "geometry" in r]
    complete_pairs = [
        r
        for r in records
        if r["status"] == "complete" and r.get("plain_assessment", {}).get("status") == "complete"
    ]
    work = [r["work"]["total"] for r in records if "work" in r]
    g = [r["geometry"] for r in fitted]
    base_geometry = [mode_geometry(x) for x in g]
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
        control_feature_counts=dict(
            Counter(str(r["fit"]["feature_count"]) for r in records if "fit" in r)
        ),
        control_rank_quantiles=quantiles(
            [r["fit"]["numerical_rank"] for r in records if "fit" in r]
        ),
        target_evaluation_quantiles=quantiles(work),
        mode_count_frequencies={str(k): v for k, v in sorted(mode_counts.items())},
        optimizer_usable_counts=quantiles(
            [sum(a["usable"] for a in r.get("fit_trace", {}).get("attempts", [])) for r in records]
        ),
        pilot_mass_quantiles=quantiles(
            [x["pilot_mass"] for x in base_geometry if "pilot_mass" in x]
        ),
        pilot_maximum_weight_quantiles=quantiles(
            [x["pilot_maximum_weight"] for x in base_geometry if "pilot_maximum_weight" in x]
        ),
        raw_errors=HELPERS["raw_estimator_diagnostics"](records),
        isolated_wrong_endpoints=HELPERS["isolated_wrong_endpoint_diagnostics"](
            records, plan["reference_endpoint_cdf_tolerance"]
        ),
    )
    result["endpoint_residuals"] = endpoint_diagnostics(records)
    if any("components" in r for r in records):
        result["allocation"] = allocation_diagnostics(records, plan)
    adapted = [x.get("tail_geometry", x) for x in g if x["kind"] in (TAIL_KIND, PROTECTIVE_KIND)]
    if adapted:
        result["tail_adaptation"] = dict(
            broad_slot_available=sum(x["broad_slot_available"] for x in adapted),
            rounds=[
                dict(
                    log_mass_quantiles=quantiles([x["stages"][k]["log_mass"] for x in adapted]),
                    maximum_weight_quantiles=quantiles(
                        [x["stages"][k]["maximum_weight"] for x in adapted]
                    ),
                    effective_weight_quantiles=quantiles(
                        [x["stages"][k]["effective_weights"] for x in adapted]
                    ),
                    objective_decreases=sum(
                        s["objective_after"] < s["objective_before"]
                        for x in adapted
                        for s in x["stages"][k]["steps"]
                    ),
                )
                for k in range(plan["em_rounds"])
            ],
            fitted_means_quantiles=quantiles([x["component_means"] for x in adapted]),
            fitted_masses_quantiles=quantiles([x["component_masses"] for x in adapted]),
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
                    - restore_proposal(x, initial, fit_plan).logpdf(centers, "stabilized-mixture")
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
        protected = [
            restore_proposal(x, initial, fit_plan) for x in g if x["kind"] == PROTECTIVE_KIND
        ]
        if protected:
            result["protective_density_probes"] = {
                name: quantiles(
                    [
                        np.exp(
                            getattr(q, name).logpdf(centers, "stabilized-mixture")
                            - q.logpdf(centers, "stabilized-mixture")
                        )
                        for q in protected
                    ]
                )
                for name in ("mode", "tail")
            }
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
    by_key = {(c["arm"], c["target"]): c for c in result["cases"]}
    audit["matched_comparisons"] = {
        str(i): matched_comparison(by_key[("candidate", i)], by_key[("baseline", i)])
        for i in result["plan"].get("baseline_targets", [])
    }
    audit["tail_comparisons"] = {
        str(i): matched_comparison(by_key[("candidate", i)], by_key[("tail", i)])
        for i in result["plan"].get("tail_targets", [])
    }
    audit["allocation_comparisons"] = {
        str(i): matched_comparison(by_key[("candidate", i)], by_key[("equal", i)])
        for i in result["plan"].get("equal_targets", [])
    }
    audit["discovery_comparisons"] = {
        str(i): matched_comparison(
            by_key[("equal", i)], by_key[("previous", i)], matched_geometry=False
        )
        for i in result["plan"].get("previous_targets", [])
    }
    audit["endpoint_comparisons"] = {
        str(i): matched_comparison(by_key[("candidate", i)], by_key[("polynomial", i)])
        for i in result["plan"].get("polynomial_targets", [])
    }
    if work_plan(result["plan"]):
        audit["work_decision"] = result["work_decision"]
        audit["work_comparisons"] = {
            arm: {
                str(i): matched_comparison(by_key[(arm, i)], by_key[("candidate", i)])
                for i in result["plan"]["known_targets"]
            }
            for arm in result["plan"]["work_budget_order"][1:]
        }
    if args.reconstruction:
        replica = SnapshotStore(args.reconstruction)
        load(replica, args.report_id)
        audit["independent_reconstruction_identical"] = HELPERS["verify_reconstruction"](
            store, replica
        )
    print(json.dumps(audit, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
