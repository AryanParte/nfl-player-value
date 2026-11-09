"""One continuous-variance candidate; numerical and scientific success stay separate."""

from collections import Counter
import json
from math import isfinite

import numpy as np

from nfl_value.continuous_math import Target, integrate
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.multiseason import accounting, predict
from nfl_value.multiseason_math import GROUPS, contrast, design
from nfl_value.multiseason_simulation import simulate as previous_simulate, summary
from nfl_value.qb_math import row_digest


KEYS = set(
    "plan_version parent_report variants log_precision_mean log_precision_sd qb_prior_mean_shifts proposal_prior_mass proposal_covariance_multiplier proposal_covariance_eigen_bounds optimizer_start_offsets optimizer_bound_prior_sds optimizer_max_iterations hessian_step sobol_powers scramble_seeds minimum_effective_samples maximum_standardized_mean_difference maximum_standardized_endpoint_difference quantile_iterations simulation_replicates simulation_seed simulation_scenarios failure_policy future_test".split()
)


def validate_plan(plan):
    if set(plan) != KEYS or type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ValueError("unsupported continuous recovery plan")
    if (
        plan["variants"] != ["evolving", "team"]
        or plan["simulation_scenarios"]
        != ["continuous_prior", "continuous_hierarchy", "fixed_year_changes"]
        or plan["failure_policy"] != "retain_failed_trials_no_calibration_pass"
    ):
        raise ValueError("unreviewed continuous model/decision policy")
    for key, lo, hi in [
        ("simulation_seed", 1, 2**31),
        ("simulation_replicates", 2, 256),
        ("optimizer_max_iterations", 1, 500),
        ("quantile_iterations", 16, 64),
    ]:
        if type(plan[key]) is not int or not lo <= plan[key] <= hi:
            raise ValueError("invalid bounded numerical/calibration size")
    values = [
        plan[k]
        for k in [
            "log_precision_sd",
            "proposal_prior_mass",
            "proposal_covariance_multiplier",
            "optimizer_bound_prior_sds",
            "hessian_step",
            "minimum_effective_samples",
            "maximum_standardized_mean_difference",
            "maximum_standardized_endpoint_difference",
        ]
    ] + plan["proposal_covariance_eigen_bounds"]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v <= 0
        for v in values
    ):
        raise ValueError("positive finite numerical policy required")
    if (
        not np.isfinite(plan["log_precision_mean"])
        or plan["proposal_prior_mass"] >= 1
        or len(plan["proposal_covariance_eigen_bounds"]) != 2
        or not plan["proposal_covariance_eigen_bounds"][0]
        < plan["proposal_covariance_eigen_bounds"][1]
    ):
        raise ValueError("invalid prior/proposal policy")
    powers = plan["sobol_powers"]
    if (
        not powers
        or any(type(p) is not int or not 2 <= p <= 11 for p in powers)
        or powers != list(range(min(powers), max(powers) + 1))
    ):
        raise ValueError("bounded consecutive Sobol powers required")
    seeds = plan["scramble_seeds"]
    if (
        len(seeds) != 2
        or len(set(seeds)) != 2
        or any(type(s) is not int or not 1 <= s < 2**32 - 10000 for s in seeds)
    ):
        raise ValueError("two independent numerical scramble seeds required")
    if plan["qb_prior_mean_shifts"] != [-float(np.log(4)), float(np.log(4))] or plan[
        "optimizer_start_offsets"
    ] != [-2.0, 0.0, 2.0]:
        raise ValueError("unreviewed prior sensitivity or optimizer starts")
    if plan["future_test"] != {"season": 2026, "weeks": [10], "fitting_update_allowed": False}:
        raise ValueError("the sealed Week 10 window must remain unchanged")


def simulate(prepared, parent_plan, plan, scenario):
    if scenario not in plan["simulation_scenarios"]:
        raise ValueError("undeclared fresh generator")
    p = {
        **parent_plan,
        "simulation_replicates": plan["simulation_replicates"],
        "simulation_seed": plan["simulation_seed"],
        "simulation_scenarios": plan["simulation_scenarios"],
    }
    if scenario != "continuous_prior":
        return previous_simulate(prepared, p, scenario)
    truth, responses = [], []
    for replicate in range(plan["simulation_replicates"]):
        rng = np.random.default_rng([plan["simulation_seed"], 0, replicate])
        sigma = np.sqrt(
            parent_plan["noise_prior_scale"] / rng.gamma(parent_plan["noise_prior_shape"])
        )
        ratios = dict(
            zip(
                ["qb", "offense", "defense", "game"],
                np.exp(rng.normal(plan["log_precision_mean"], plan["log_precision_sd"], 4)),
            )
        )
        beta = np.zeros(len(prepared.names))
        for j, name in enumerate(prepared.names):
            group = name.split("/")[0]
            beta[j] = (
                0.1 * (1 if int(sha256(name.encode()), 16) % 2 else -1)
                if group == "context"
                else rng.normal(
                    0, sigma / np.sqrt(ratios["qb" if group == "innovation" else group])
                )
            )
        game = rng.normal(0, sigma / np.sqrt(ratios["game"]), len(prepared.game_names))
        truth.append(beta)
        responses.append(
            prepared.x @ beta
            + game[prepared.game_codes]
            + rng.normal(0, sigma, prepared.x.shape[0])
        )
    return np.asarray(truth).T, np.asarray(responses).T


def summarize_trials(trials, requested, players):
    valid = [t for t in trials if t.get("numerical_valid")]
    report = {
        "requested_replicates": requested,
        "numerically_valid_replicates": len(valid),
        "failed_replicates": requested - len(valid),
        "all_numerically_valid": len(valid) == requested,
        "passes_admission": False,
    }
    if len(valid) >= 2:
        arrays = {
            key: np.array([t[key] for t in valid]).T
            for key in ["truth", "mean", "low", "high", "mode_mean", "mode_low", "mode_high"]
        }
        report["success_only_integrated"] = summary(
            arrays["truth"], arrays["mean"], arrays["low"], arrays["high"]
        )
        report["success_only_mode"] = summary(
            arrays["truth"], arrays["mode_mean"], arrays["mode_low"], arrays["mode_high"]
        )
        s = report["success_only_integrated"]
        report["nominal_shortfall_exceeds_two_mcse"] = bool(
            0.95 - s["coverage"] > 2 * s["monte_carlo_se"]
        )
    covered = sum(
        np.sum(
            (np.array(t["low"]) <= np.array(t["truth"]))
            & (np.array(t["truth"]) <= np.array(t["high"]))
        )
        for t in valid
    )
    report["all_trial_coverage_bounds"] = [
        float(covered / (requested * players)),
        float((covered + (requested - len(valid)) * players) / (requested * players)),
    ]
    report["failure_examples"] = [
        {"replicate": t["replicate"], "error": t.get("error"), "diagnostics": t.get("diagnostics")}
        for t in trials
        if not t.get("numerical_valid")
    ][:3]
    report["meaning"] = (
        "Success-only summaries condition on numerical convergence; any failed trial prevents a calibration pass. Bounds retain all requested trials."
    )
    return report


def calibration(prepared, l, parent_plan, plan, progress, checkpoint):
    reports, all_trials = {}, {}
    for scenario in plan["simulation_scenarios"]:
        beta, y = simulate(prepared, parent_plan, plan, scenario)
        trials = []
        for rep in range(plan["simulation_replicates"]):
            progress(f"{scenario}: replicate {rep + 1}/{plan['simulation_replicates']}")
            trial = {"replicate": rep, "truth": (l @ beta[:, rep]).tolist()}
            try:
                target = Target(
                    prepared, y[:, rep], ["qb", "offense", "defense", "game"], parent_plan, plan
                )
                _, s, mode, diagnostic = integrate(
                    target,
                    l,
                    plan,
                    seed_offset=1000 + 100 * plan["simulation_scenarios"].index(scenario) + rep,
                )
                trial.update(
                    numerical_valid=diagnostic["valid"],
                    diagnostics=diagnostic,
                    **{k: s[k].tolist() for k in ["mean", "low", "high"]},
                    **{"mode_" + k: mode[k].tolist() for k in ["mean", "low", "high"]},
                )
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                trial.update(numerical_valid=False, error=str(exc))
            trials.append(trial)
            checkpoint(scenario, trial)
        reports[scenario] = {
            **summarize_trials(trials, plan["simulation_replicates"], len(l)),
            "synthetic_responses_sha256": sha256(y.astype("<f8").tobytes()),
        }
        all_trials[scenario] = trials
    return reports, all_trials


def predict_frozen(model, rows):
    if model.get("numerical_valid") is not True:
        raise ValueError(
            "numerically invalid continuous model cannot be evaluated as frozen candidate"
        )
    return predict(model, rows)


def experiment(context, plan, progress=lambda _: None, checkpoint=lambda *_: None):
    validate_plan(plan)
    parent = context["parent"]
    old_models = context["models"]
    parent_plan = parent["plan"]
    if parent_plan["future_test"] != plan["future_test"]:
        raise ValueError("future window differs from parent")
    rows, current = context["rows"], context["current"]
    weights = parent["season"]["benchmark_weights"]
    players = [v["player_id"] for v in context["values"]]
    counts = Counter(p["qb"] for p in current)
    fits, models, results = {}, {}, {}
    primary = None
    for variant in plan["variants"]:
        progress("Continuous real-data candidate: " + variant)
        d, _ = design(
            rows,
            variant,
            scoring_season=2026,
            extra_qbs=set().union(*(w.keys() for w in weights.values())),
        )
        if (
            d.names != old_models[variant]["names"]
            or row_digest(rows) != old_models[variant]["training_rows_sha256"]
        ):
            raise ValueError("continuous candidate must retain parent design and observations")
        matrices = (
            {
                name: np.array([contrast(d.names, p, counts[p], w, season=2026) for p in players])
                for name, w in weights.items()
            }
            if variant == "evolving"
            else {}
        )
        l = np.vstack(list(matrices.values())) if matrices else np.eye(len(d.names))
        target = Target(
            d,
            [p["offense_epa"] for p in rows],
            [g for g in GROUPS[variant] if g != "innovation"] + ["game"],
            parent_plan,
            plan,
        )
        fit, s, _, diagnostic = integrate(
            target,
            l,
            plan,
            seed_offset=0 if variant == "evolving" else 100,
            need_games=True,
            sensitivities=variant == "evolving",
            progress=progress,
        )
        fits[variant] = diagnostic
        model = {
            **old_models[variant],
            "coefficients": fit["coefficient_mean"].tolist(),
            "game_coefficients": dict(zip(d.game_names, fit["game_mean"].tolist())),
            "numerical_valid": diagnostic["valid"],
            "variance_method": "continuous-log-normal-prior-v1",
            "prior": {
                "log_precision_mean": plan["log_precision_mean"],
                "log_precision_sd": plan["log_precision_sd"],
            },
            "ranking_ready": False,
        }
        model.pop("precision_cells", None)
        model.pop("posterior_cell_weights", None)
        models[variant] = model
        if variant == "evolving":
            primary = (d, matrices["first_unit"])
            estimates = []
            for i, old in enumerate(context["values"]):
                benchmarks = {
                    name: {
                        "expected_points": float(s["mean"][j * len(players) + i]),
                        "integrated_95_interval": [
                            float(s[k][j * len(players) + i]) for k in ["low", "high"]
                        ],
                    }
                    for j, name in enumerate(matrices)
                }
                ledger = [
                    {
                        **g,
                        "expected_points": benchmarks["first_unit"]["expected_points"]
                        * g["opportunities"]
                        / old["opportunities"],
                    }
                    for g in old["game_ledger"]
                ]
                if not np.isclose(
                    sum(g["expected_points"] for g in ledger),
                    benchmarks["first_unit"]["expected_points"],
                    atol=1e-9,
                    rtol=0,
                ):
                    raise ValueError("current-season game ledger differs")
                estimates.append(
                    {
                        **old,
                        "benchmarks": benchmarks,
                        "game_ledger": ledger,
                        "numerical_valid": diagnostic["valid"],
                        "uncertainty_calibrated": False,
                    }
                )
            play_ledger, error = accounting(d, fit, rows, current, weights["first_unit"], 2026)
            if not np.isclose(
                sum(v["benchmarks"]["first_unit"]["expected_points"] for v in estimates),
                sum(p["qb_above_first_unit"] for p in play_ledger),
                atol=1e-8,
                rtol=0,
            ):
                raise ValueError("player totals differ from nonduplicated play contributions")
            results.update(estimates=estimates, play_ledger=play_ledger)
            fits[variant]["max_accounting_error_ep"] = error
    trials, results["calibration_trials"] = calibration(
        *primary, parent_plan, plan, progress, checkpoint
    )
    report = {
        "experiment": "continuous-variance-recovery-v1",
        "plan": plan,
        "plan_sha256": sha256(json_bytes(plan)),
        "parent_report": plan["parent_report"],
        "parent_code_revision": parent["code_revision"],
        "input_reports": parent["input_reports"],
        "evidence_cutoff": parent["evidence_cutoff"],
        "source_provenance": parent["source_provenance"],
        "fits": fits,
        "calibration": trials,
        "season": {
            **parent["season"],
            "negative_player_estimates": sum(
                v["benchmarks"]["first_unit"]["expected_points"] < 0 for v in results["estimates"]
            ),
        },
        "identification": parent["evaluation"]["evolving"]["identification"],
        "allocation_witness": parent["evaluation"]["evolving"]["allocation_witness"],
        "decision": "No admission. Numerical integration, simulation calibration, predictive evidence and observational attribution are separate requirements; Week 10 is still sealed.",
        "ranking_ready": False,
    }
    return report, models, json.loads(json_bytes(results))
