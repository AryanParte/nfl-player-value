"""Frozen arithmetic controls and bounded consumed-case equivalence diagnostics."""

from time import perf_counter

import numpy as np

from nfl_value.conditional_reference import as_float, decimal_cell, reference_agreement
from nfl_value.conditional_solver import SquareRootSystem
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.variance_mixture import cell, response_stats, system


FAMILIES = ["partition", "duplicates", "near_alias", "cold_player", "year_links", "game_means"]
FROZEN_PLAN_SHA256 = "e566d34f26979eca4993285c1c6e3a5d9ca8804a71694f03662a9085c7ebf797"


def validate_plan(plan):
    if sha256(json_bytes(plan)) not in (
        FROZEN_PLAN_SHA256,
        "c9738097c0e6cbcc791852e5d8d7e58feb2ef3ec3c11295ca367a6a05472d712",
    ):
        raise ValueError("conditional solver plan differs from the frozen design")


def serial(result):
    return {key: np.asarray(value).tolist() for key, value in result.items()}


def known_case(family, seed):
    if family not in FAMILIES:
        raise ValueError("unknown frozen control")
    i = np.arange(24)
    season = (i >= 12).astype(float)
    fixed = np.ones((24, 1))
    names = ["context/intercept"]
    b = (i % 3 == 0).astype(float)
    if family == "partition":
        random = np.eye(3)[i % 3]
    elif family == "duplicates":
        random = np.column_stack([b, b, (i % 3 == 1).astype(float)])
    elif family == "near_alias":
        random = np.column_stack([b, b + 1e-8 * (2 * (i % 2) - 1), (i % 3 == 1)])
    elif family == "cold_player":
        random = np.column_stack([b, (i % 3 == 1), np.zeros(24)])
    elif family == "year_links":
        fixed = np.column_stack([fixed, season])
        names += ["context/season_2025"]
        player = np.eye(2)[i % 2]
        random = np.column_stack([player, player * (1 - season[:, None]), player * season[:, None]])
    else:
        fixed = np.column_stack([fixed, season])
        names += ["context/season_2025"]
        random = np.eye(3)[(i // 4) % 3]
    r = fixed.shape[1]
    names += [f"qb/{j}" for j in range(random.shape[1])]
    x = np.column_stack([fixed, random])
    groups = {"qb": np.arange(r, x.shape[1])}
    if family == "game_means":
        x = np.column_stack([x, (i % 2).astype(float)])
        names += ["offense/other"]
        groups["offense"] = np.array([x.shape[1] - 1])
    prepared = system(x, names, r, [f"g{j // 4}" for j in i])
    rng = np.random.default_rng(np.random.SeedSequence([seed, FAMILIES.index(family)]))
    y = rng.normal(size=(24, 2))
    y[:, 0] -= 0.7 * b
    y[:, 1] += 0.3 * season
    contrast = np.zeros(len(names))
    contrast[r], contrast[r + 1] = 1, -1
    l = np.vstack([np.eye(len(names)), contrast, 2 * contrast, np.zeros(len(names))])
    return prepared, y, l, groups


def comparison(actual, reference, plan, *, archived=False):
    variance = (
        reference["diagonal"][:, None]
        * reference["posterior_scale"][None, :]
        / (float(reference["posterior_shape"]) - 1)
    )
    delta = np.abs(actual["location"] - reference["location"])
    standardized = np.divide(delta, np.sqrt(variance), out=np.zeros_like(delta), where=variance > 0)
    standardized[(variance == 0) & (delta != 0)] = np.inf
    d = reference["diagonal"]
    verror = np.divide(
        np.abs(actual["diagonal"] - d), np.abs(d), out=np.zeros_like(d), where=d != 0
    )
    verror[(d == 0) & (actual["diagonal"] != 0)] = np.inf
    ref_q = reference["residual_quadratic"]
    act_q = actual["residual_quadratic"]
    metrics = {
        "mean_error_sd": float(np.max(standardized, initial=0)),
        "variance_relative_error": float(np.max(verror, initial=0)),
        "quadratic_relative_error": float(np.max(np.abs(act_q - ref_q) / (1 + np.abs(ref_q)))),
        "log_likelihood_absolute_error": float(
            np.max(np.abs(actual["log_likelihood"] - reference["log_likelihood"]))
        ),
    }
    limits = [
        plan["mean_tolerance_sd"],
        plan["variance_relative_tolerance"],
        plan["quadratic_relative_tolerance"],
        plan[
            "archive_log_likelihood_absolute_tolerance"
            if archived
            else "log_likelihood_absolute_tolerance"
        ],
    ]
    passed = all(np.isfinite(v) and v <= limit for v, limit in zip(metrics.values(), limits))
    return {
        "passed": bool(passed),
        **{k: v if np.isfinite(v) else None for k, v in metrics.items()},
    }


def _known_seed(plan, seed, deadline, progress):
    cases = []
    timings = []
    for family in plan["known_families"]:
        began = perf_counter()
        d, y, l, groups = known_case(family, seed)
        solvers = {
            name: SquareRootSystem(
                d,
                y,
                groups,
                exact_aliases=name != "augmented_qr",
                original_residual=name == "exact_alias_residual",
            )
            for name in plan["candidates"]
        }
        stats = response_stats(d, y)
        for weak in plan["weak_precisions"]:
            penalty = np.zeros(len(d.names))
            for group, indices in groups.items():
                penalty[indices] = weak if group == "qb" else 7.0
            for game in plan["game_precisions"]:
                if perf_counter() >= min(deadline, began + plan["maximum_seconds_per_case"]):
                    cases.append(
                        {
                            "family": family,
                            "weak_precision": weak,
                            "game_precision": game,
                            "status": "unattempted",
                            "error": "declared preparation/solve budget exhausted",
                        }
                    )
                    continue
                refs = [
                    decimal_cell(
                        d.x.toarray(),
                        y,
                        d.fixed_count,
                        penalty,
                        d.game_codes,
                        game,
                        l,
                        3.0,
                        4.5,
                        digits=digits,
                    )
                    for digits in plan["decimal_digits"]
                ]
                reference_valid = reference_agreement(*refs)
                reference = as_float(refs[-1])
                results = {}
                for name, solver in solvers.items():
                    try:
                        result = solver.cell(penalty, game, l, 3.0, 4.5)
                        results[name] = {
                            **comparison(result, reference, plan),
                            "outputs": serial(result),
                        }
                    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                        results[name] = {"passed": False, "error": str(exc)}
                try:
                    old = cell(d, stats, penalty, game, l, 3.0, 4.5)
                    old["residual_quadratic"] = 2 * (old["posterior_scale"] - 4.5)
                    baseline = comparison(old, reference, plan)
                except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    baseline = {"passed": False, "error": str(exc)}
                cases.append(
                    {
                        "family": family,
                        "weak_precision": weak,
                        "game_precision": game,
                        "status": "complete",
                        "reference_valid": reference_valid,
                        "reference": refs[-1],
                        "reference_lower_precision": refs[0],
                        "response_sha256": sha256(y.astype("<f8").tobytes()),
                        "candidate_results": results,
                        "legacy": baseline,
                        "aliases": solvers[plan["preferred_candidate"]].certificates,
                    }
                )
        timings.append({"family": family, "seconds": perf_counter() - began})
        progress(f"Known controls complete: {family}")
    return cases, timings


def known_study(plan, progress=lambda _: None):
    validate_plan(plan)
    deadline = perf_counter() + plan["maximum_seconds_total"]
    cases, timings = [], []
    seeds = plan.get("seeds", [plan["seed"]])
    for seed in seeds:
        current, elapsed = _known_seed(plan, seed, deadline, progress)
        if "seeds" in plan:
            for item in current + elapsed:
                item["seed"] = seed
        cases.extend(current)
        timings.extend(elapsed)
    expected = (
        len(FAMILIES) * len(plan["weak_precisions"]) * len(plan["game_precisions"]) * len(seeds)
    )
    gates = {
        name: len(cases) == expected
        and all(c.get("reference_valid") and c["candidate_results"][name]["passed"] for c in cases)
        for name in plan["candidates"]
    }
    return {
        "requested_cases_per_candidate": expected,
        "cases": cases,
        "candidate_gates": gates,
        "ranking_ready": False,
    }, timings


def validate_known(report, plan):
    validate_plan(plan)
    expected = [
        (seed, family, weak, game)
        for seed in plan.get("seeds", [plan["seed"]])
        for family in FAMILIES
        for weak in plan["weak_precisions"]
        for game in plan["game_precisions"]
    ]
    cases = report["cases"]
    if (
        report["requested_cases_per_candidate"] != len(expected)
        or len(cases) != len(expected)
        or report["ranking_ready"] is not False
    ):
        raise ValueError("incomplete known-answer denominator or unsupported admission")
    gates = dict.fromkeys(plan["candidates"], True)
    fixtures = {}
    for c, identity in zip(cases, expected):
        if "seeds" in plan and "seed" not in c:
            raise ValueError("amended control requires an explicit response seed")
        if (
            c.get("seed", plan["seed"]),
            c["family"],
            c["weak_precision"],
            c["game_precision"],
        ) != identity:
            raise ValueError("known-answer case order or identity differs")
        if c["status"] == "unattempted":
            gates = dict.fromkeys(plan["candidates"], False)
            continue
        if c["status"] != "complete":
            raise ValueError("invalid known-answer case status")
        key = (identity[0], c["family"])
        if key not in fixtures:
            fixtures[key] = known_case(c["family"], identity[0])
        d, y, l, groups = fixtures[key]
        penalty = np.zeros(len(d.names))
        for group, indices in groups.items():
            penalty[indices] = c["weak_precision"] if group == "qb" else 7.0
        exact = decimal_cell(
            d.x.toarray(),
            y,
            d.fixed_count,
            penalty,
            d.game_codes,
            c["game_precision"],
            l,
            3.0,
            4.5,
            digits=plan["decimal_digits"][-1],
        )
        if c["response_sha256"] != sha256(y.astype("<f8").tobytes()) or json_bytes(
            exact
        ) != json_bytes(c["reference"]):
            raise ValueError("known-answer reference differs from the frozen fixture")
        valid = reference_agreement(c["reference_lower_precision"], c["reference"])
        if valid is not c["reference_valid"]:
            raise ValueError("Decimal reference decision differs")
        for name in gates:
            result = c["candidate_results"][name]
            if "outputs" in result:
                actual = comparison(as_float(result["outputs"]), as_float(c["reference"]), plan)
                if actual != {k: v for k, v in result.items() if k != "outputs"}:
                    raise ValueError("known-answer metrics do not reproduce")
            elif result.get("passed") is not False or not result.get("error"):
                raise ValueError("failed control must retain its exception")
            gates[name] = gates[name] and valid and result["passed"]
    if gates != report["candidate_gates"]:
        raise ValueError("known-answer authorization differs from all requested cases")
    return gates
