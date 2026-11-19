"""Paired diagnostics for the frozen numerical study; never a new acceptance gate."""

import argparse
import json
from pathlib import Path
import runpy

import numpy as np

from nfl_value.coarse_control_study import assessment_plan, load
from nfl_value.density_holdout import coverage_summary
from nfl_value.ingestion import SnapshotStore
from nfl_value.replicated_reference import confidence_sets, diagnose_reference

TRUTH = np.array([1.0, 0, 0, 0.025, 0.025, 0.975, 0.975])


def proposal_diagnostics(records, target_index):
    """Describe all retained fits, including failed numerical intervals.

    Point probes at analytic mixture centers are diagnostics, not bounds on the
    density ratio, a variance theorem, or a basis for changing this candidate.
    """
    from nfl_value.functional_proposal import restore_functional
    from nfl_value.tail_controls import TailTarget, tail_proposal

    fits = [r["fit"]["proposal_fit"] for r in records if "proposal_fit" in r.get("fit", {})]
    result = dict(requested=len(records), retained_fits=len(fits), rounds=[])

    def quantiles(values):
        return (
            np.quantile(values, [0, 0.05, 0.5, 0.95, 1], axis=0).tolist() if len(values) else None
        )

    for iteration in range(2):
        stages = [fit["stages"][iteration] for fit in fits]
        parts = []
        for j in range(3):
            moments = [s["moments"][j] for s in stages if s["moments"][j]["active"]]
            parts.append(
                dict(
                    active=len(moments),
                    inactive=len(stages) - len(moments),
                    effective_weight_quantiles=quantiles([m["effective_weights"] for m in moments]),
                    maximum_weight_quantiles=quantiles([m["maximum_weight"] for m in moments]),
                    mean_coordinate_quantiles=quantiles([s["component_means"][j] for s in stages]),
                )
            )
        result["rounds"].append(
            dict(
                prior_mass_quantiles=quantiles([s["prior_mass_estimates"] for s in stages]),
                components=parts,
            )
        )
    if target_index in (5, 6, 7):
        target = TailTarget(target_index)
        logp = target.logpdf(target.means)
        probes = [
            (logp - restore_functional(g).logpdf(target.means, "stabilized-mixture")).tolist()
            for g in fits
        ]
        result["center_probes"] = dict(
            points=target.means.tolist(),
            initial_log_density_ratios=(
                logp - tail_proposal().logpdf(target.means, "stabilized-mixture")
            ).tolist(),
            fitted_log_density_ratio_quantiles=quantiles(probes),
        )
        helper = Path(__file__).with_name("functional_population_diagnostic.py")
        population = runpy.run_path(str(helper))["population_geometry"](target_index)
        result["population_moment_reference"] = population
        result["population_mean_gap_quantiles"] = quantiles(
            [
                np.linalg.norm(
                    np.asarray(g["component_means"]) - population["component_means"], axis=1
                )
                for g in fits
            ]
        )
        result["population_covariance_gap_quantiles"] = quantiles(
            [
                np.linalg.norm(
                    np.asarray(g["component_covariances"]) - population["component_covariances"],
                    axis=(1, 2),
                )
                for g in fits
            ]
        )
    result["caveat"] = (
        "descriptive retained fitting evidence; effective weights are not independent observations; center probes are not global density-ratio bounds; no selection or admission"
    )
    return result


def initial_stress_diagnostics(records):
    shares = []
    for r in records:
        raw = np.asarray(r["raw"], float)
        if (
            raw.ndim != 2
            or raw.shape[1] != 9
            or np.any(raw[:, 0] < 0)
            or not np.isfinite(raw).all()
            or raw[:, 0].sum() <= 0
        ):
            raise ValueError("finite nonnegative initial-stress mass replicates required")
        shares.append(float(raw[:, 0].max() / raw[:, 0].sum()))
    return dict(
        trials=len(records),
        replicate_mass_maximum_share_quantiles=np.quantile(
            shares, [0, 0.05, 0.5, 0.95, 1]
        ).tolist(),
        trials_reaching_previous_hierarchy_share=sum(s >= 0.103866 for s in shares),
        comparison_share=0.103866,
        caveat="fixed initial proposal only; descriptive stress check, not a new acceptance gate or independent player evidence",
    )


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


def integration_diagnostics(fits):
    """Descriptive training evidence, never validation or selection."""
    records = [fit["integration_fit"] for fit in fits]
    alpha = np.asarray([r["alpha"] for r in records], float)
    f = np.asarray([r["function_means"] for r in records], float)
    h = np.asarray([r["control_means"] for r in records], float)
    if (
        alpha.ndim != 2
        or f.ndim != 3
        or f.shape != h.shape
        or alpha.shape != (f.shape[0], f.shape[2])
        or f.shape[1] < 2
        or not all(np.isfinite(x).all() for x in (alpha, f, h))
    ):
        raise ValueError("complete finite integration training records required")
    fc, hc = f - f.mean(axis=1, keepdims=True), h - h.mean(axis=1, keepdims=True)
    residual = fc - alpha[:, None, :] * hc
    before, after = np.sum(fc * fc, axis=1), np.sum(residual * residual, axis=1)
    valid = before > 0
    relative = after[valid] / before[valid]
    return dict(
        fits=len(fits),
        functionals_per_fit=alpha.shape[1],
        training_replicates=f.shape[1],
        alpha_quantiles=np.quantile(alpha, [0, 0.05, 0.5, 0.95, 1], axis=0).tolist(),
        negative_alpha_count=int(np.count_nonzero(alpha < 0)),
        zero_alpha_count=int(np.count_nonzero(alpha == 0)),
        defined_training_variance_ratios=int(valid.sum()),
        undefined_training_variance_ratios=int((~valid).sum()),
        training_variance_ratio_quantiles=(
            np.quantile(relative, [0, 0.05, 0.5, 0.95, 1]).tolist() if relative.size else None
        ),
        caveat="correlated training diagnostics; not held-out variance, independent evidence counts or gates",
    )


def training_integrals(fit):
    if "joint_fit" in fit:
        stage = fit["joint_fit"]
        f, h = (np.asarray(stage[k], float) for k in ("function_means", "control_means"))
        adjustment = h * np.asarray(stage["numerator_slopes"])
        adjustment += h[:, stage["layout"]["mass_columns"]] * np.asarray(stage["mass_slopes"])
        return f - adjustment, f
    stage = fit["integration_fit"]
    f, h = (np.asarray(stage[k], float) for k in ("function_means", "control_means"))
    return f - h * np.asarray(stage["alpha"]), f


def joint_known_diagnostics(records):
    # Include retained arrays even when Fieller construction failed. Every
    # requested trial remains in the actual coverage/precision denominator.
    usable = [
        r for r in records if all(k in r for k in ("fit", "coarse", "plain_coarse", "correction"))
    ]
    result = dict(retained_trials=len(usable), requested_trials=len(records), phases={})
    for phase in ("training", "evaluation"):
        rows = []
        for r in usable:
            if phase == "training":
                adjusted, plain = training_integrals(r["fit"])
            else:
                adjusted = np.asarray(r["coarse"]) + r["correction"]
                plain = np.asarray(r["plain_coarse"]) + r["correction"]
            rows.append(
                fixed_ratio_variance(
                    adjusted, plain, r["fit"]["joint_fit"]["layout"]["anchors"][1:]
                )
            )
        stats = {}
        for kind in ("unnormalized", "fixed_ratio_influence"):
            columns = list(zip(*(row[kind] for row in rows))) if rows else []
            stats[kind] = [
                dict(
                    defined=len([v for v in column if v is not None]),
                    undefined=sum(v is None for v in column),
                    worse=sum(v > 1 for v in column if v is not None),
                    quantiles=np.quantile(
                        [v for v in column if v is not None], [0, 0.05, 0.5, 0.95, 1]
                    ).tolist()
                    if any(v is not None for v in column)
                    else None,
                )
                for column in columns
            ]
        result["phases"][phase] = stats
    result["caveat"] = (
        "descriptive correlated per-trial ratios, including retained failed trials; no selection or admission"
    )
    return result


def raw_estimator_diagnostics(records):
    """Do not condition point-error summaries on successful interval construction."""
    output = {}
    for label, key in (("adjusted", "coarse"), ("plain", "plain_coarse")):
        estimates, failed_confidence = [], 0
        for record in records:
            if key not in record or "correction" not in record:
                continue
            raw = np.asarray(record[key], float) + np.asarray(record["correction"], float)
            if raw.ndim != 2 or raw.shape[1] != 9 or not np.isfinite(raw).all():
                raise ValueError("malformed retained known-answer integrals")
            average = raw.mean(axis=0)[:7]
            if average[0] <= 0:
                continue
            estimate = np.r_[average[0], average[1:] / average[0]]
            if not np.isfinite(estimate).all():
                continue
            estimates.append(estimate)
            status = record if label == "adjusted" else record.get("plain_assessment", {})
            failed_confidence += status.get("status") != "complete"
        matrix = np.asarray(estimates)
        output[label] = dict(
            requested_trials=len(records),
            defined_estimates=len(estimates),
            unavailable_estimates=len(records) - len(estimates),
            included_failed_confidence_trials=failed_confidence,
            bias=(matrix.mean(axis=0) - TRUTH).tolist() if len(matrix) else None,
            rmse=np.sqrt(np.mean((matrix - TRUTH) ** 2, axis=0)).tolist() if len(matrix) else None,
            empirical_sd=matrix.std(axis=0, ddof=1).tolist() if len(matrix) > 1 else None,
            caveat="finite positive average masses only; failed confidence trials retained when estimates exist; not coverage or admission",
        )
    return output


def isolated_wrong_endpoint_diagnostics(records, tolerance):
    """A failing joint vector alone does not identify which endpoints are wrong."""
    available, any_excluded, both_excluded = 0, 0, 0
    for r in records:
        if "coarse" not in r or "correction" not in r:
            continue
        raw = np.asarray(r["coarse"]) + np.asarray(r["correction"])
        try:
            bounds = confidence_sets(raw[:, [0, 1, 2, 3, 4, 7, 8]], [-1, 0, 0, 0, 0, 0, 0])
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            continue
        available += 1
        # Use the original seven-functional joint critical value, then inspect
        # only the two deliberately shifted endpoints, excluding nuisance failures.
        excluded = (bounds["high"][-2:] < 0.975 - tolerance) | (
            bounds["low"][-2:] > 0.975 + tolerance
        )
        any_excluded += bool(excluded.any())
        both_excluded += bool(excluded.all())
    return dict(
        requested_trials=len(records),
        available_confidence_trials=available,
        at_least_one_wrong_endpoint_excluded_trials=any_excluded,
        both_wrong_endpoints_excluded_trials=both_excluded,
        caveat="diagnostic only; original joint-vector rejection gate unchanged; no mean or lower-endpoint failure counted here",
    )


def known_gate_decomposition(records, plan):
    complete = [r for r in records if r["status"] == "complete"]
    out = dict(
        requested_trials=len(records),
        complete_confidence_trials=len(complete),
        failed_confidence_trials=len(records) - len(complete),
        groups={},
    )
    if not complete:
        return out
    estimate, low, high = (
        np.asarray([r["bounds"][k] for r in complete]) for k in ("estimate", "low", "high")
    )
    gap = np.abs(estimate - TRUTH)
    radius = np.maximum(np.abs(low - estimate), np.abs(high - estimate))
    for name, indices, tol in (
        ("mean_sd", slice(1, 3), plan["reference_mean_tolerance_sd"]),
        ("endpoint_cdf", slice(3, 7), plan["reference_endpoint_cdf_tolerance"]),
    ):
        g, e = gap[:, indices], radius[:, indices]
        out["groups"][name] = dict(
            point_only_failed_trials=int(np.any(g > tol, axis=1).sum()),
            error_only_failed_trials=int(np.any(e > tol, axis=1).sum()),
            discrepancy_plus_error_failed_trials=int(np.any(g + e > tol, axis=1).sum()),
            interval_excludes_tolerance_trials=int(
                np.any(
                    (high[:, indices] < TRUTH[indices] - tol)
                    | (low[:, indices] > TRUTH[indices] + tol),
                    axis=1,
                ).sum()
            ),
            maximum_point_gap_quantiles=np.quantile(g.max(axis=1), [0, 0.5, 0.95, 1]).tolist(),
            maximum_error_allowance_quantiles=np.quantile(
                e.max(axis=1), [0, 0.5, 0.95, 1]
            ).tolist(),
            maximum_combined_quantiles=np.quantile((g + e).max(axis=1), [0, 0.5, 0.95, 1]).tolist(),
        )
    return out


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
            plain_decision=coverage_summary(plain, assessment_plan(result["plan"], case["target"])),
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
            if result["plan"]["plan_version"] == 2:
                item["integration_fit"] = integration_diagnostics([r["fit"] for r in paired])
        if result["plan"]["plan_version"] == 3:
            item["joint_objective"] = joint_known_diagnostics(records)
        if result["plan"]["plan_version"] in (3, 4):
            item["all_retained_point_errors"] = raw_estimator_diagnostics(records)
            item["gate_decomposition"] = known_gate_decomposition(records, result["plan"])
            item["isolated_wrong_endpoints"] = isolated_wrong_endpoint_diagnostics(
                records, result["plan"]["reference_endpoint_cdf_tolerance"]
            )
        if result["plan"]["plan_version"] == 4:
            item["proposal_fit"] = proposal_diagnostics(records, case["target"])
        output[str(case["target"])] = item
    return output


def fixed_ratio_variance(adjusted, plain, anchors):
    """Local ratio influence around fixed anchors; diagnostic, not a new estimator."""
    adjusted, plain, anchors = (np.asarray(v, float) for v in (adjusted, plain, anchors))
    if (
        adjusted.ndim != 2
        or adjusted.shape != plain.shape
        or len(adjusted) < 2
        or anchors.shape != (adjusted.shape[1] - 1,)
        or anchors.size == 0
        or not all(np.isfinite(v).all() for v in (adjusted, plain, anchors))
    ):
        raise ValueError("finite paired integrals and fixed ratio anchors required")
    ah = adjusted[:, 1:] - adjusted[:, [0]] * anchors
    ph = plain[:, 1:] - plain[:, [0]] * anchors
    return dict(
        unnormalized=ratios(adjusted.var(axis=0, ddof=1), plain.var(axis=0, ddof=1)),
        fixed_ratio_influence=ratios(ah.var(axis=0, ddof=1), ph.var(axis=0, ddof=1)),
    )


def ratio_objective_diagnostics(record):
    """Post-result failure diagnosis only: no refitting, selection or new gates."""
    n = record["contrasts"]
    anchors = np.r_[np.zeros(n), np.full(n, 0.025), np.full(n, 0.975)]
    adjusted_training, plain_training = training_integrals(record["fit"])
    phases = dict(
        training=(adjusted_training, plain_training),
        evaluation=(
            np.asarray(record["coarse"]) + np.asarray(record["correction"]),
            np.asarray(record["plain_coarse"]) + np.asarray(record["correction"]),
        ),
    )

    def describe(values):
        defined = [v for v in values if v is not None]
        return dict(
            defined=len(defined),
            undefined=len(values) - len(defined),
            worse=sum(v > 1 for v in defined),
            quantiles=np.quantile(defined, [0, 0.5, 1]).tolist() if defined else None,
        )

    output = {}
    width = 1 + 3 * n
    for phase, (a, p) in phases.items():
        output[phase] = {}
        for k, shift in enumerate(record["shifts"]):
            sl = slice(k * width, (k + 1) * width)
            raw = fixed_ratio_variance(a[:, sl], p[:, sl], anchors)
            groups = {"mass_variance_ratio": raw["unnormalized"][0]}
            for j, name in enumerate(("mean_sd", "lower_cdf", "upper_cdf")):
                start, end = j * n, (j + 1) * n
                groups[name] = dict(
                    unnormalized=describe(raw["unnormalized"][start + 1 : end + 1]),
                    fixed_ratio_influence=describe(raw["fixed_ratio_influence"][start:end]),
                )
            output[phase][str(shift)] = groups
    return dict(
        phases=output,
        anchors="fixed primary standardized means 0 and endpoint CDFs 0.025/0.975",
        caveat="post-result covariance diagnosis, no fitting or new evidence; common unknown normalization cancels in variance ratios; anchors are not known true NFL ratios",
    )


def influence_diagnostics(record):
    """Conditional delta-method variance, not repeated-trial or player uncertainty."""
    n, shifts = record["contrasts"], record["shifts"]
    base, plain, correction = (
        np.asarray(record[k], float) for k in ("coarse", "plain_coarse", "correction")
    )
    width = 1 + 3 * n
    if (
        type(n) is not int
        or n < 1
        or not shifts
        or len(set(shifts)) != len(shifts)
        or base.ndim != 2
        or base.shape[0] < 2
        or base.shape[1] != width * len(shifts)
        or plain.shape != base.shape
        or correction.shape != base.shape
        or not all(np.isfinite(v).all() for v in (base, plain, correction))
    ):
        raise ValueError("complete finite levels and ordered functionals required")
    output = {}
    for k, shift in enumerate(shifts):
        block = slice(k * width, (k + 1) * width)
        b, p, c = (v[:, block] for v in (base, plain, correction))
        a, u = b + c, p + c
        if min(a[:, 0].mean(), u[:, 0].mean()) <= 0:
            raise ValueError("positive mean normalizing masses required")
        ar, ur = (v[:, 1:].mean(axis=0) / v[:, 0].mean() for v in (a, u))

        def variance(v, ratio):
            return (v[:, 1:] - v[:, [0]] * ratio).var(axis=0, ddof=1)

        av = variance(a, ar) / len(a) / a[:, 0].mean() ** 2
        uv = variance(u, ur) / len(u) / u[:, 0].mean() ** 2
        bv, cv = variance(b, ar), variance(c, ar)
        values = {}
        for label, sl in (
            ("mean_sd", slice(0, n)),
            ("lower_cdf", slice(n, 2 * n)),
            ("upper_cdf", slice(2 * n, 3 * n)),
        ):
            values[label] = dict(
                adjusted_standard_error=np.sqrt(av[sl]).tolist(),
                plain_standard_error=np.sqrt(uv[sl]).tolist(),
                adjusted_to_plain_variance=ratios(av[sl], uv[sl]),
                correction_to_coarse_standard_error=ratios(np.sqrt(cv[sl]), np.sqrt(bv[sl])),
                coarse_fraction_of_separate_variance=ratios(bv[sl], (bv + cv)[sl]),
            )
        values["adjusted_mass_mean"] = float(a[:, 0].mean())
        values["plain_mass_mean"] = float(u[:, 0].mean())
        values["minimum_adjusted_replicate_mass"] = float(a[:, 0].min())
        output[str(shift)] = values
    return output


def archive_summary(result):
    output = {}
    for name in result["plan"]["cases"]:
        r = result["cases"][name]
        item = {k: r[k] for k in ("status", "numerical_valid", "evaluations", "error") if k in r}
        if r["status"] == "complete":
            item.update(
                primary_qmc_valid=r["primary_qmc_valid"],
                adjusted_checks=r["reference"]["checks"],
                adjusted_diagnosis=r["diagnosis"],
                influence=influence_diagnostics(r),
                fit={
                    k: v
                    for k, v in r["fit"].items()
                    if k not in ("coefficients", "integration_fit", "joint_fit")
                },
                plain_status=r["plain_reference"]["status"],
                maximum_relative_mass_correction=r["maximum_relative_mass_correction"],
            )
            if result["plan"]["plan_version"] == 2:
                item["fit"]["integration_fit"] = integration_diagnostics([r["fit"]])
            if result["plan"]["plan_version"] in (2, 3):
                item["ratio_objective"] = ratio_objective_diagnostics(r)
            if r["plain_reference"]["status"] == "complete":
                reference = r["plain_reference"]["reference"]
                item.update(
                    plain_checks=reference["checks"],
                    plain_diagnosis=diagnose_reference(
                        reference,
                        contrasts=r["contrasts"],
                        shifts=r["shifts"],
                        plan=result["plan"],
                    ),
                )
            else:
                item["plain_error"] = r["plain_reference"]["error"]
        output[name] = item
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
    archived = result["experiment"] == f"coarse-control-archive-v{result['plan']['plan_version']}"
    audit = dict(
        report_id=args.report,
        manifest=manifest,
        cases=archive_summary(result) if archived else summary(result),
        controls_passed=result.get("controls_passed"),
        numerical_pilot_passed=result.get("numerical_pilot_passed"),
        calibration_completed=result["calibration_completed"],
        ranking_ready=False,
        analysis="paired_consumed_numerical_diagnostics_not_player_calibration",
        numerical_variance_diagnostic=(
            "conditional influence variance at each method's own normalized estimate; separate-level variances at the adjusted total estimate; diagnostic only"
            if archived
            else "sample variance of numerator minus known ratio times mass, divided by replicate count and squared mean mass; mass column uses direct variance"
        ),
    )
    if archived:
        audit.update(
            {
                k: result[k]
                for k in (
                    "control_report",
                    "previous_reference",
                    "primary_objects",
                    "source_provenance",
                    "evidence_cutoff",
                    "season",
                )
            }
        )
    if "initial_stress" in result:
        audit["initial_stress"] = initial_stress_diagnostics(result["initial_stress"])
    if args.reconstruction:
        audit["independent_reconstruction_identical"] = verify_reconstruction(
            output, SnapshotStore(args.reconstruction)
        )
    print(json.dumps(audit, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
