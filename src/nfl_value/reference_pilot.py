"""Five predeclared numerical stress cases; no calibration or ranking admission."""

from copy import deepcopy
import json
from time import perf_counter

import numpy as np

from nfl_value.continuous_cli import load_context
from nfl_value.continuous_recovery import simulate
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.multiseason import accounting
from nfl_value.multiseason_math import contrast, design, GROUPS
from nfl_value.qb_math import row_digest
from nfl_value.variance_reference import (
    BoundedTarget,
    BudgetExceeded,
    build_transport,
    qmc_integrate,
    reference_integral,
)


CASES = [
    "real_evolving",
    "real_team",
    "continuous_prior_0",
    "continuous_hierarchy_0",
    "fixed_year_changes_0",
]
KEYS = set(
    "plan_version parent_report cases prior_mass_per_axis axis_grid_points prior_span_sd local_span_sd scramble_seeds sobol_powers minimum_effective_samples maximum_standardized_mean_difference maximum_standardized_endpoint_difference cubature_rule cubature_rtol cubature_atol cubature_max_subdivisions reference_mean_tolerance_sd reference_endpoint_cdf_tolerance maximum_target_evaluations_per_case maximum_seconds_per_case maximum_seconds_total failure_policy future_test".split()
)


def validate_plan(plan):
    if (
        set(plan) not in (KEYS, KEYS | {"reference_transport"})
        or type(plan["plan_version"]) is not int
        or plan["plan_version"] != 1
    ):
        raise ValueError("unsupported reference plan schema")
    if (
        "reference_transport" in plan
        and plan["reference_transport"] != "independent_student_t5_moments"
    ):
        raise ValueError("unreviewed reference transform")
    if (
        plan["cases"] != CASES
        or plan["failure_policy"] != "retain_all_cases_no_calibration_or_admission"
        or plan["future_test"] != {"season": 2026, "weeks": [10], "fitting_update_allowed": False}
    ):
        raise ValueError("unreviewed cases, admission or future-window policy")
    for key, low, high in [
        ("axis_grid_points", 9, 257),
        ("cubature_max_subdivisions", 1, 512),
        ("maximum_target_evaluations_per_case", 1, 90000),
        ("maximum_seconds_per_case", 1, 900),
        ("maximum_seconds_total", 1, 3600),
    ]:
        if type(plan[key]) is not int or not low <= plan[key] <= high:
            raise ValueError("invalid bounded reference size")
    for key in [
        "prior_mass_per_axis",
        "prior_span_sd",
        "local_span_sd",
        "minimum_effective_samples",
        "maximum_standardized_mean_difference",
        "maximum_standardized_endpoint_difference",
        "cubature_rtol",
        "cubature_atol",
        "reference_mean_tolerance_sd",
        "reference_endpoint_cdf_tolerance",
    ]:
        v = plan[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0:
            raise ValueError("positive finite reference policy required")
    if plan["prior_mass_per_axis"] >= 1 or plan["cubature_rule"] != "genz-malik":
        raise ValueError("full-support proposal and reviewed reference rule required")
    powers = plan["sobol_powers"]
    seeds = plan["scramble_seeds"]
    if (
        not powers
        or any(type(x) is not int or not 2 <= x <= 13 for x in powers)
        or powers != list(range(min(powers), max(powers) + 1))
        or len(seeds) != 2
        or len(set(seeds)) != 2
        or any(type(s) is not int or not 0 < s < 2**32 for s in seeds)
    ):
        raise ValueError("bounded nested powers and independent seeds required")


def prepare_case(context, model_plan, case):
    variant = "team" if case == "real_team" else "evolving"
    parent = context["parent"]
    weights = parent["season"]["benchmark_weights"]
    d, _ = design(
        context["rows"],
        variant,
        scoring_season=2026,
        extra_qbs=set().union(*(w.keys() for w in weights.values())),
    )
    old = context["models"][variant]
    if d.names != old["names"] or row_digest(context["rows"]) != old["training_rows_sha256"]:
        raise ValueError("reference design differs from frozen original")
    matrices = (
        {
            name: np.array(
                [
                    contrast(d.names, v["player_id"], v["opportunities"], w, season=2026)
                    for v in context["values"]
                ]
            )
            for name, w in weights.items()
        }
        if variant == "evolving"
        else {}
    )
    l = np.vstack(list(matrices.values())) if matrices else np.eye(len(d.names))
    y = np.asarray([r["offense_epa"] for r in context["rows"]])
    if not case.startswith("real_"):
        scenario = case.removesuffix("_0")
        _, responses = simulate(d, parent["plan"], model_plan, scenario)
        y = responses[:, 0]
        l = matrices["first_unit"]
    return d, y, l, variant, matrices


def season_outputs(context, d, fit, summaries, matrices, numerical_valid):
    values = deepcopy(context["values"])
    n = len(values)
    for i, v in enumerate(values):
        v["benchmarks"] = {
            name: {
                "expected_points": float(summaries[0.0]["mean"][j * n + i]),
                "integrated_95_interval": [
                    float(summaries[0.0][k][j * n + i]) for k in ["low", "high"]
                ],
            }
            for j, name in enumerate(matrices)
        }
        for g in v["game_ledger"]:
            g["expected_points"] = (
                v["benchmarks"]["first_unit"]["expected_points"]
                * g["opportunities"]
                / v["opportunities"]
            )
        if not np.isclose(
            sum(g["expected_points"] for g in v["game_ledger"]),
            v["benchmarks"]["first_unit"]["expected_points"],
            rtol=0,
            atol=1e-9,
        ):
            raise ValueError("game-to-player cumulative accounting failed")
        v.update(numerical_valid=numerical_valid, uncertainty_calibrated=False, ranking_ready=False)
    ledger, error = accounting(
        d,
        fit,
        context["rows"],
        context["current"],
        context["parent"]["season"]["benchmark_weights"]["first_unit"],
        2026,
    )
    if not np.isclose(
        sum(v["benchmarks"]["first_unit"]["expected_points"] for v in values),
        sum(p["qb_above_first_unit"] for p in ledger),
        atol=1e-8,
        rtol=0,
    ):
        raise ValueError("nonduplicated player/play totals differ")
    return values, ledger, error


def experiment(
    context, continuous_parent, plan, progress=lambda _: None, checkpoint=lambda *_: None
):
    validate_plan(plan)
    if continuous_parent["plan"]["future_test"] != plan["future_test"]:
        raise ValueError("sealed window differs from parent")
    start = perf_counter()
    reports, outputs, models, timings = {}, {}, {}, {}
    for name in plan["cases"]:
        begin = perf_counter()
        if begin - start >= plan["maximum_seconds_total"]:
            reports[name] = dict(
                status="unattempted",
                numerical_valid=False,
                reason="total pilot time budget exhausted",
            )
            continue
        progress("Pilot case: " + name)
        d, y, l, variant, matrices = prepare_case(context, continuous_parent["plan"], name)
        target = BoundedTarget(
            d,
            y,
            [g for g in GROUPS[variant] if g != "innovation"] + ["game"],
            context["parent"]["plan"],
            continuous_parent["plan"],
            evaluation_limit=plan["maximum_target_evaluations_per_case"],
            deadline=min(
                start + plan["maximum_seconds_total"], begin + plan["maximum_seconds_per_case"]
            ),
        )
        r = dict(
            status="failed",
            numerical_valid=False,
            response_sha256=sha256(y.astype("<f8").tobytes()),
            dimensions=len(target.groups),
            contrasts=len(l),
        )
        fit = summaries = None
        stage = "transport"
        try:
            transport = build_transport(target, plan)
            r["transport"] = dict(
                mode=transport.mode.tolist(),
                optimizer_attempts=transport.attempts,
                axis_knots=[len(a.grid) for a in transport.axes],
            )
            stage = "qmc"
            fit, summaries, r["qmc"] = qmc_integrate(
                target,
                l,
                transport,
                plan,
                sensitivities=name == "real_evolving",
                need_games=name.startswith("real_"),
                progress=progress,
            )
            checkpoint(name + "_qmc", r)
            stage = "reference"
            r["reference"] = reference_integral(target, l, transport, summaries, plan, progress)
            r["numerical_valid"] = bool(r["qmc"]["valid"] and r["reference"]["valid"])
            r["status"] = "passed" if r["numerical_valid"] else "failed"
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            r.update(
                failed_stage=stage, error=str(exc), budget_exhausted=isinstance(exc, BudgetExceeded)
            )
        r["target_evaluations"] = target.evaluations
        if fit is not None:
            outputs[name] = {
                "summaries": {
                    str(s): {k: np.asarray(v).tolist() for k, v in x.items()}
                    for s, x in summaries.items()
                },
                "numerical_valid": r["numerical_valid"],
            }
            if name.startswith("real_"):
                models[variant] = {
                    **context["models"][variant],
                    "coefficients": fit["coefficient_mean"].tolist(),
                    "game_coefficients": dict(zip(d.game_names, fit["game_mean"].tolist())),
                    "variance_method": "continuous-log-normal-prior-v1-axis-reference",
                    "numerical_valid": r["numerical_valid"],
                    "uncertainty_calibrated": False,
                    "ranking_ready": False,
                }
                models[variant].pop("precision_cells", None)
                models[variant].pop("posterior_cell_weights", None)
            if name == "real_evolving":
                values, ledger, error = season_outputs(
                    context, d, fit, summaries, matrices, r["numerical_valid"]
                )
                outputs.update(estimates=values, play_ledger=ledger)
                r["max_accounting_error_ep"] = error
        reports[name] = r
        timings[name] = perf_counter() - begin
        checkpoint(name, r)
        progress(
            f"{name}: {r['status']}; evaluations={target.evaluations}; seconds={timings[name]:.1f}"
        )
    report = dict(
        experiment="variance-reference-pilot-v1",
        plan=plan,
        plan_sha256=sha256(json_bytes(plan)),
        parent_report=plan["parent_report"],
        parent_code_revision=continuous_parent["code_revision"],
        source_provenance=continuous_parent["source_provenance"],
        input_reports=continuous_parent["input_reports"],
        evidence_cutoff=continuous_parent["evidence_cutoff"],
        season={
            **continuous_parent["season"],
            "negative_player_estimates": sum(
                v["benchmarks"]["first_unit"]["expected_points"] < 0 for v in outputs["estimates"]
            )
            if "estimates" in outputs
            else None,
        },
        cases=reports,
        numerical_pilot_passed=all(r["numerical_valid"] for r in reports.values()),
        calibration_completed=False,
        uncertainty_calibrated=False,
        ranking_ready=False,
        decision="Numerical pilot only. No calibration, prospective prediction or observational admission follows automatically; all failed/unattempted cases remain.",
    )
    return report, models, outputs, timings


def load_inputs(raw, inputs, multiseason, previous, plan, progress=lambda _: None):
    validate_plan(plan)
    parent = json.loads(previous.read(plan["parent_report"], manifest=True))
    if (
        parent["experiment"] != "continuous-variance-recovery-v1"
        or parent["ranking_ready"] is not False
        or parent["plan_sha256"] != sha256(json_bytes(parent["plan"]))
    ):
        raise ValueError("verified continuous diagnostic parent required")
    for digest in parent["objects"].values():
        previous.read(digest)
    return load_context(raw, inputs, multiseason, parent["plan"], progress), parent
