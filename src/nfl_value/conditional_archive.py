"""Gated, bounded equivalence on consumed NFL designs, with full failure retention."""

from time import perf_counter

import numpy as np

from nfl_value.conditional_solver import SquareRootSystem
from nfl_value.conditional_study import comparison, serial, validate_known, validate_plan
from nfl_value.continuous_math import Target
from nfl_value.density_holdout import fit_pair
from nfl_value.ingestion import sha256
from nfl_value.multiseason_math import GROUPS
from nfl_value.reference_pilot import CASES, prepare_case
from nfl_value.variance_reference import BudgetExceeded


class SquareRootTarget(Target):
    def __init__(
        self,
        *args,
        evaluation_limit,
        deadline,
        exact_aliases=True,
        original_residual=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.evaluations = 0
        self.evaluation_limit, self.deadline = evaluation_limit, deadline
        self.solver = SquareRootSystem(
            self.prepared,
            args[1],
            self.group_indices,
            exact_aliases=exact_aliases,
            original_residual=original_residual,
        )

    def conditional(self, eta, contrasts, need_games=False, *, compressed=True):
        if self.evaluations >= self.evaluation_limit or perf_counter() >= self.deadline:
            raise BudgetExceeded("declared target evaluation/time budget exhausted")
        self.evaluations += 1
        eta = np.asarray(eta, dtype=float)
        if eta.shape != (len(self.groups),) or not np.isfinite(eta).all():
            raise ValueError("finite log variance coordinates required")
        values = np.exp(eta)
        if not np.isfinite(values).all() or np.any(values <= 0):
            raise ValueError("unrepresentable continuous precision")
        penalty = np.zeros(len(self.prepared.names))
        game = None
        for group, value in zip(self.groups, values):
            if group == "game":
                game = value
            else:
                penalty[self.group_indices[group]] = value
        return self.solver.cell(
            penalty,
            game,
            contrasts,
            self.parent_plan["noise_prior_shape"],
            self.parent_plan["noise_prior_scale"],
            compressed=compressed,
            need_games=need_games,
        )


def accounting(target, eta, result):
    """Independent row-space penalized residual sum, including random games."""
    prepared, y = target.prepared, target.solver.y
    prediction = np.asarray(prepared.x @ result["mean"])
    if prepared.game_names:
        prediction += result["game_mean"][prepared.game_codes]
    residual = y - prediction
    q = np.sum(residual**2, axis=0)
    for group, value in zip(target.groups, np.exp(eta)):
        beta = (
            result["game_mean"] if group == "game" else result["mean"][target.group_indices[group]]
        )
        q += value * np.sum(beta**2, axis=0)
    return {
        "row_reconstruction_maximum_error": float(np.abs(prediction + residual - y).max()),
        "penalized_quadratic_relative_error": float(
            np.max(np.abs(q - result["residual_quadratic"]) / (1 + np.abs(q)))
        ),
    }


def archived_study(
    context,
    parent,
    density,
    trace,
    controls,
    plan,
    progress=lambda _: None,
    checkpoint=lambda *_: None,
):
    validate_plan(plan)
    gates = validate_known(controls, plan)
    approved = [name for name in plan["candidates"] if gates[name]]
    if not approved:
        raise ValueError("no candidate passes every frozen known-answer control")
    start = perf_counter()
    global_deadline = start + plan["maximum_seconds_total"]
    cases, timings = {}, {}
    for index, name in enumerate(CASES):
        began = perf_counter()
        deadline = min(global_deadline, began + plan["maximum_seconds_per_case"])
        d, y, l, variant, _ = prepare_case(context, parent["plan"], name)
        group_names = [g for g in GROUPS[variant] if g != "innovation"] + ["game"]
        original = Target(d, y, group_names, context["parent"]["plan"], parent["plan"])
        rng = np.random.default_rng(np.random.SeedSequence([plan["archive_seed"], index]))
        center = np.full(len(group_names), parent["plan"]["log_precision_mean"])
        coordinates = np.vstack(
            [
                center,
                rng.normal(
                    center,
                    plan["archive_coordinate_sd"],
                    (plan["archive_random_coordinates"], len(center)),
                ),
            ]
        )
        records = {}
        for candidate in approved:
            progress(f"Preparing {name} / {candidate}")
            try:
                if perf_counter() >= deadline:
                    raise BudgetExceeded("declared preparation/solve budget exhausted")
                target = SquareRootTarget(
                    d,
                    y,
                    group_names,
                    context["parent"]["plan"],
                    parent["plan"],
                    evaluation_limit=plan["maximum_trace_evaluations"],
                    deadline=deadline,
                    exact_aliases=candidate != "augmented_qr",
                    original_residual=candidate == "exact_alias_residual",
                )
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                records[candidate] = {
                    "equivalence_passed": False,
                    "preparation_error": str(exc),
                    "coordinates": [
                        {
                            "coordinates": coordinate.tolist(),
                            "status": "unattempted",
                            "error": "candidate preparation failed",
                        }
                        for coordinate in coordinates
                    ],
                    "recorded_failure_point": {"status": "unattempted", "passed": False},
                }
                continue
            trials = []
            for coordinate in coordinates:
                record = {"coordinates": coordinate.tolist(), "status": "failed"}
                if perf_counter() >= deadline:
                    record.update(
                        status="unattempted", error="declared preparation/solve budget exhausted"
                    )
                else:
                    try:
                        result = target.conditional(coordinate, l, need_games=True)
                        record.update(
                            outputs=serial(result),
                            accounting=accounting(target, coordinate, result),
                        )
                        old = original.conditional(coordinate, l, need_games=True)
                        old["residual_quadratic"] = 2 * (
                            old["posterior_scale"] - context["parent"]["plan"]["noise_prior_scale"]
                        )
                        record.update(
                            status="complete",
                            legacy=serial(old),
                            comparison=comparison(result, old, plan, archived=True),
                        )
                    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                        record["error"] = str(exc)
                trials.append(record)
            records[candidate] = {
                "coordinates": trials,
                "aliases": target.solver.certificates,
                "original_columns": len(d.names),
                "retained_columns": target.solver.p,
                "equivalence_passed": all(
                    r["status"] == "complete"
                    and r["comparison"]["passed"]
                    and r["accounting"]["penalized_quadratic_relative_error"]
                    <= plan["quadratic_relative_tolerance"]
                    for r in trials
                ),
            }
            if name == "continuous_prior_0":
                special = {"status": "failed"}
                try:
                    failure = trace["failures"][0]
                    if (
                        sha256(y.astype("<f8").tobytes()) != trace["response_sha256"]
                        or group_names != failure["groups"]
                    ):
                        raise ValueError("recorded failure target differs")
                    coordinate = np.array(failure["coordinates"])
                    try:
                        original.conditional(coordinate, l, need_games=True)
                        special["legacy_point"] = {"status": "complete"}
                    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                        special["legacy_point"] = {"status": "failed", "error": str(exc)}
                    result = target.conditional(coordinate, l, need_games=True)
                    raw = target.conditional(coordinate, l, need_games=True, compressed=False)
                    reverse = SquareRootSystem(
                        d,
                        y,
                        target.group_indices,
                        exact_aliases=candidate != "augmented_qr",
                        original_residual=candidate == "exact_alias_residual",
                        reverse_basis=True,
                    )
                    if perf_counter() >= deadline:
                        raise BudgetExceeded("declared failure-check budget exhausted")
                    penalty = np.zeros(len(d.names))
                    for g, value in zip(group_names, np.exp(coordinate)):
                        if g != "game":
                            penalty[target.group_indices[g]] = value
                    reordered = reverse.cell(
                        penalty,
                        np.exp(coordinate[-1]),
                        l,
                        context["parent"]["plan"]["noise_prior_shape"],
                        context["parent"]["plan"]["noise_prior_scale"],
                    )
                    del reverse
                    row_check = accounting(target, coordinate, result)
                    raw_check = comparison(result, raw, plan, archived=True)
                    basis_check = comparison(result, reordered, plan, archived=True)
                    special.update(
                        status="complete",
                        outputs=serial(result),
                        raw_outputs=serial(raw),
                        reordered_outputs=serial(reordered),
                        raw_comparison=raw_check,
                        basis_comparison=basis_check,
                        accounting=row_check,
                        coordinates=coordinate.tolist(),
                        response_sha256=sha256(y.astype("<f8").tobytes()),
                        passed=raw_check["passed"]
                        and basis_check["passed"]
                        and row_check["penalized_quadratic_relative_error"]
                        <= plan["quadratic_relative_tolerance"],
                    )
                except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    special["error"] = str(exc)
                records[candidate]["recorded_failure_point"] = special
            del target
        cases[name] = {
            "candidate_results": records,
            "response_sha256": sha256(y.astype("<f8").tobytes()),
            "requested_coordinates_per_candidate": len(coordinates),
        }
        timings[name] = perf_counter() - began
        checkpoint(name, cases[name])
        progress(
            f"{name}: "
            + str({c: r["equivalence_passed"] for c, r in records.items()})
            + f"; seconds={timings[name]:.1f}"
        )
    # The original failed fit is attempted only after every equivalence and point
    # check passes. Never choose a different candidate based on archived outcomes.
    preferred = plan["preferred_candidate"]
    eligible = (
        preferred in approved
        and all(c["candidate_results"][preferred]["equivalence_passed"] for c in cases.values())
        and cases["continuous_prior_0"]["candidate_results"][preferred][
            "recorded_failure_point"
        ].get("passed", False)
    )
    replay = {"status": "blocked", "reason": "known/equivalence/recorded-point gate did not pass"}
    if eligible:
        began = perf_counter()
        deadline = min(global_deadline, began + plan["maximum_seconds_per_case"])
        if perf_counter() >= deadline:
            replay = {"status": "unattempted", "reason": "declared study budget exhausted"}
        else:
            d, y, _, variant, _ = prepare_case(context, parent["plan"], "continuous_prior_0")
            target = SquareRootTarget(
                d,
                y,
                [g for g in GROUPS[variant] if g != "innovation"] + ["game"],
                context["parent"]["plan"],
                parent["plan"],
                evaluation_limit=plan["maximum_trace_evaluations"],
                deadline=deadline,
                exact_aliases=preferred != "augmented_qr",
                original_residual=preferred == "exact_alias_residual",
            )
            try:
                pairs, gain = fit_pair(target, density["plan"], 102, 0)
                replay = {
                    "status": "complete",
                    "training_log_score_gain": gain,
                    "geometries": {label: p.diagnostics for p, label in pairs},
                }
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                replay = {"status": "failed", "error": str(exc)}
            replay["conditional_evaluations"] = target.evaluations
            del target
        timings["failed_fit_replay"] = perf_counter() - began
        progress(f"Failed-fit replay: {replay['status']}")
    result = {
        "cases": cases,
        "approved_candidates": approved,
        "failed_fit_replay": replay,
        "source_provenance": parent["source_provenance"],
        "input_reports": parent["input_reports"],
        "evidence_cutoff": parent["evidence_cutoff"],
        "parent_code_revision": parent["code_revision"],
        "model_plan": parent["plan"],
        "known_gates": gates,
        "original_failure_replaced": False,
        "calibration_completed": False,
        "ranking_ready": False,
    }
    return result, timings
