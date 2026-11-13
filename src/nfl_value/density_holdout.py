"""Paired density-only holdouts; no player scores or model-prior changes."""

from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from scipy.special import stdtr
from scipy.stats import binomtest, t

from nfl_value.adaptive_proposal import AdaptiveProposal, weighted_mixture
from nfl_value.ingestion import json_bytes, sha256
from nfl_value.randomized_controls import KnownTarget, assess_trial, coverage_decision
from nfl_value.replicated_reference import SamplingProposal, fit_proposal, replicate_integrals


def validate_plan(p):
    expected = dict(
        plan_version=2,
        base_seed=2026111301,
        known_density_trials=32,
        archived_density_trials=4,
        pilot_replicates=4,
        pilot_nodes_per_replicate=1024,
        holdout_replicates=4,
        holdout_nodes_per_replicate=2048,
        coverage_trials=1024,
        replicates=32,
        nodes_per_replicate=2048,
        reference_mean_tolerance_sd=0.01,
        reference_endpoint_cdf_tolerance=0.001,
        coverage_lower_bound=0.9,
        minimum_precision_fraction=0.9,
        marginal_undercoverage_alpha=0.01 / 35,
        joint_undercoverage_alpha=0.01 / 5,
        shrinkage_pseudo_count="dimensions_plus_two",
        curvature=0.5,
        curved_transform="bounded_sine",
        known_targets=list(range(5)),
        parent_plan="config/variance-reference-sparse-v1.json",
        maximum_seconds_per_case=900,
        maximum_target_evaluations_per_case=90000,
        failure_policy="retain_all_no_retry_no_admission",
        future_test=dict(season=2026, weeks=[10], fitting_update_allowed=False),
    )
    if json_bytes(p) != json_bytes(expected):
        raise ValueError("density study differs from frozen design")


class CurvedTarget(KnownTarget):
    """Unit-Jacobian curved normal; functionals use the explicit latent inverse."""

    def __init__(self, model_plan):
        super().__init__(2, model_plan)
        self.means = np.zeros((1, 4))
        self.covariances = np.array([np.eye(4)])
        self.probabilities = np.ones(1)

    @staticmethod
    def inverse(points):
        z = np.atleast_2d(points).astype(float).copy()
        z[:, 1] -= 0.5 * np.sin(z[:, 0])
        z[:, 3] -= 0.5 * np.sin(z[:, 2])
        return z

    def logpdf(self, points):
        z = self.inverse(points)
        return -0.5 * np.sum(z * z, axis=1) - 2 * np.log(2 * np.pi)

    def integrand(self, exact):
        def f(points, logq):
            weights = np.exp(self.logpdf(points) - logq)
            location = self.inverse(points) @ self.contrasts.T
            return weights[:, None] * np.column_stack(
                [
                    np.ones(len(points)),
                    (location - exact["mean"]) / exact["sd"],
                    stdtr(20, (exact["low"] - location) / np.sqrt(self.noise)),
                    stdtr(20, (exact["high"] - location) / np.sqrt(self.noise)),
                    stdtr(20, (exact["high"] - 0.5 - location) / np.sqrt(self.noise)),
                ]
            )

        return f


def known_target(index, model_plan):
    if index not in range(5):
        raise ValueError("unknown density target")
    return CurvedTarget(model_plan) if index == 4 else KnownTarget(index, model_plan)


@lru_cache(maxsize=5)
def known_truth_bytes(index):
    return json_bytes({k: v.tolist() for k, v in known_target(index, {}).exact().items()})


class StabilizedProposal(AdaptiveProposal):
    def components(self, method):
        if method != "stabilized-mixture":
            raise ValueError("unreviewed stabilized proposal")
        return super().components("adaptive-mixture")


@dataclass
class PairedProposal(SamplingProposal):
    pairs: list

    def components(self, method):
        if method != "paired":
            raise ValueError("unreviewed paired proposal")
        return [
            (mass / 2, mean, cov, df)
            for proposal, label in self.pairs
            for mass, mean, cov, df in proposal.components(label)
        ]


def target_logpdf(target, points):
    return (
        target.logpdf(points)
        if hasattr(target, "logpdf")
        else np.array([target.log_target(x) for x in points])
    )


def fit_pair(target, plan, index, trial):
    initial = fit_proposal(target)
    offset = target.log_target(initial.mean) - initial.logpdf(initial.mean, "defensive-mixture")[0]
    batches = []

    def f(points, logq):
        weights = np.exp(target_logpdf(target, points) - logq - offset)
        batches.append((points.copy(), weights.copy()))
        return weights[:, None]

    entropy = [plan["base_seed"], 10, index, trial]
    replicate_integrals(
        f,
        initial,
        "defensive-mixture",
        entropy=entropy,
        replicates=plan["pilot_replicates"],
        nodes=plan["pilot_nodes_per_replicate"],
    )
    x = np.vstack([x for x, w in batches])
    w = np.concatenate([(0.9 if j % 2 == 0 else 0.1) * w for j, (x, w) in enumerate(batches)])
    if not np.isfinite(w).all() or not np.isfinite(w.sum()) or w.sum() <= 0:
        raise ValueError("invalid pilot mass")
    w /= w.sum()
    pairs = []
    for stable in [False, True]:
        options = dict(reference_covariance=initial.covariance / 1.5) if stable else {}
        means, covs, masses, d = weighted_mixture(
            x, w, [plan["base_seed"], 11, index, trial], **options
        )
        covs *= 1.5
        d.update(
            density_pilot_entropy=entropy,
            pilot_nodes=len(x),
            pilot_effective_samples=float(1 / (w @ w)),
            pilot_initial_geometry=initial.diagnostics,
            geometry_uses_primary_qmc=False,
            component_means=means.tolist(),
            component_covariances=covs.tolist(),
            component_masses=masses.tolist(),
            learning_is_target_density_only=True,
            pilot_points_sha256=sha256(x.astype("<f8").tobytes()),
            pilot_weights_sha256=sha256(w.astype("<f8").tobytes()),
        )
        cls = StabilizedProposal if stable else AdaptiveProposal
        pairs.append(
            (
                cls(
                    initial.mean,
                    initial.covariance,
                    initial.prior_mean,
                    initial.prior_covariance,
                    d,
                    means,
                    covs,
                    masses,
                ),
                "stabilized-mixture" if stable else "adaptive-mixture",
            )
        )
    training_gain = float(
        w @ (pairs[1][0].logpdf(x, pairs[1][1]) - pairs[0][0].logpdf(x, pairs[0][1]))
    )
    return pairs, training_gain


def density_metrics(raw):
    x = np.asarray(raw, float)
    if (
        x.ndim != 2
        or x.shape[1] != 4
        or len(x) < 2
        or not np.isfinite(x).all()
        or np.any(x[:, [0, 2, 3]] <= 0)
    ):
        raise ValueError("finite positive density mass and second moments required")
    pooled = x.mean(axis=0)
    mass = pooled[0]
    c2 = pooled[2:] / mass**2
    return dict(
        heldout_log_score_gain=float(pooled[1] / mass),
        c2_existing=float(c2[0]),
        c2_stabilized=float(c2[1]),
        log_c2_ratio=float(np.log(c2[1] / c2[0])),
    )


def holdout(target, pairs, plan, index, trial):
    first = pairs[0][0]
    joint = PairedProposal(
        first.mean, first.covariance, first.prior_mean, first.prior_covariance, {}, pairs
    )
    offset = target.log_target(first.mean)

    def f(x, logq):
        logp = target_logpdf(target, x) - offset
        old, new = [p.logpdf(x, label) for p, label in pairs]
        w = np.exp(logp - logq)
        return np.column_stack(
            [w, w * (new - old), np.exp(2 * logp - old - logq), np.exp(2 * logp - new - logq)]
        )

    raw = replicate_integrals(
        f,
        joint,
        "paired",
        entropy=[plan["base_seed"], 12, index, trial],
        replicates=plan["holdout_replicates"],
        nodes=plan["holdout_nodes_per_replicate"],
    )
    return dict(replicate_integrals=raw.tolist(), **density_metrics(raw))


def paired_summary(records):
    valid = [r for r in records if r["status"] == "complete"]
    result = dict(
        requested=len(records),
        complete=len(valid),
        failed=sum(r["status"] == "failed" for r in records),
        unattempted=sum(r["status"] == "unattempted" for r in records),
        diagnostic_only=True,
    )
    for key in ["training_log_score_gain", "heldout_log_score_gain", "log_c2_ratio"]:
        x = np.array([r[key] for r in valid])
        half = (
            float(t.isf(0.025, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))
            if len(x) > 1
            else None
        )
        result[key] = dict(
            mean=float(x.mean()) if len(x) else None,
            descriptive_95_interval=[float(x.mean() - half), float(x.mean() + half)]
            if half is not None
            else None,
        )
    return result


def coverage_summary(records, plan):
    d = coverage_decision(records, plan)
    k = sum(r.get("simultaneous_covered", False) for r in records)
    d["joint_undercoverage_pvalue"] = float(
        binomtest(k, len(records), 0.95, alternative="less").pvalue
    )
    d["passed"] = bool(
        d["passed"] and d["joint_undercoverage_pvalue"] >= plan["joint_undercoverage_alpha"]
    )
    return d


def known_experiment(plan, model_plan, progress=lambda _: None, checkpoint=lambda *_: None):
    validate_plan(plan)
    cases = []
    for index in plan["known_targets"]:
        target = known_target(index, model_plan)
        truth = target.exact()
        density = []
        selected = None
        for trial in range(plan["known_density_trials"]):
            record = dict(status="failed")
            try:
                pairs, gain = fit_pair(target, plan, index, trial)
                if trial == 0:
                    selected = pairs[1][0]
                record.update(
                    training_log_score_gain=gain,
                    geometries={label: p.diagnostics for p, label in pairs},
                )
                record.update(status="complete", **holdout(target, pairs, plan, index, trial))
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                record.update(status="failed", error=str(exc))
            density.append(dict(trial=trial, **record))
        progress(f"Known target {index} density: {paired_summary(density)}")
        checkpoint(f"density_{index}", density)
        coverage = []
        for trial in range(plan["coverage_trials"]):
            entropy = [plan["base_seed"], 13, index, trial]
            try:
                if selected is None:
                    raise ValueError("trial zero proposal unavailable")
                raw = replicate_integrals(
                    target.integrand(truth),
                    selected,
                    "stabilized-mixture",
                    entropy=entropy,
                    replicates=plan["replicates"],
                    nodes=plan["nodes_per_replicate"],
                )
                record = dict(**assess_trial(raw, plan), replicate_integrals=raw.tolist())
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                record = dict(status="failed", error=str(exc))
            coverage.append(dict(trial=trial, entropy=entropy, **record))
            if (trial + 1) % 128 == 0:
                progress(f"Known target {index} coverage: {trial + 1}/{plan['coverage_trials']}")
        case = dict(
            target=index,
            dimensions=len(target.groups),
            exact={k: v.tolist() for k, v in truth.items()},
            density=density,
            density_summary=paired_summary(density),
            coverage=coverage,
            coverage_geometry_sha256=sha256(json_bytes(selected.diagnostics)) if selected else None,
            coverage_decision=coverage_summary(coverage, plan),
        )
        cases.append(case)
        checkpoint(f"known_{index}", case)
        progress(f"Known target {index} coverage decision: {case['coverage_decision']}")
    return dict(
        experiment="density-holdout-controls-v1",
        plan=plan,
        cases=cases,
        controls_passed=all(
            c["coverage_decision"]["passed"]
            and c["density_summary"]["complete"] == plan["known_density_trials"]
            for c in cases
        ),
        calibration_completed=False,
        ranking_ready=False,
        nfl_data_used=False,
    )


def validate_density(records, count):
    if [r["trial"] for r in records] != list(range(count)):
        raise ValueError("missing or duplicate density trials")
    for record in records:
        if record["status"] == "complete":
            if np.asarray(record["replicate_integrals"]).shape != (4, 4):
                raise ValueError("incomplete density holdout replicates")
            actual = density_metrics(record["replicate_integrals"])
            if json_bytes(actual) != json_bytes({k: record[k] for k in actual}):
                raise ValueError("density moments do not reproduce")
            geometries = record["geometries"]
            if set(geometries) != {"adaptive-mixture", "stabilized-mixture"} or any(
                geometries["adaptive-mixture"][k] != geometries["stabilized-mixture"][k]
                for k in ["density_pilot_entropy", "pilot_points_sha256", "pilot_weights_sha256"]
            ):
                raise ValueError("paired proposals have different training evidence")
        elif record["status"] not in {"failed", "unattempted"} or not record.get("error"):
            raise ValueError("unrecorded density trial failure")


def validate_known(result, model_plan):
    plan = result["plan"]
    validate_plan(plan)
    if result["experiment"] != "density-holdout-controls-v1" or any(
        result[k] is not False for k in ["nfl_data_used", "calibration_completed", "ranking_ready"]
    ):
        raise ValueError("incorrect known-study scope")
    if [c["target"] for c in result["cases"]] != list(range(5)):
        raise ValueError("missing or duplicated known target")
    for index, case in enumerate(result["cases"]):
        target = known_target(index, model_plan)
        if case["dimensions"] != len(target.groups) or json_bytes(
            case["exact"]
        ) != known_truth_bytes(index):
            raise ValueError("known answers or dimensions changed")
        validate_density(case["density"], plan["known_density_trials"])
        if json_bytes(case["density_summary"]) != json_bytes(paired_summary(case["density"])):
            raise ValueError("density summary does not reproduce")
        g = case["density"][0].get("geometries", {}).get("stabilized-mixture")
        if case["coverage_geometry_sha256"] != (sha256(json_bytes(g)) if g else None):
            raise ValueError("coverage must use the declared trial-zero proposal")
        for trial, r in enumerate(case["density"]):
            if "geometries" in r and any(
                d["density_pilot_entropy"] != [plan["base_seed"], 10, index, trial]
                for d in r["geometries"].values()
            ):
                raise ValueError("changed density entropy")
        coverage = case["coverage"]
        if [r["trial"] for r in coverage] != list(range(plan["coverage_trials"])):
            raise ValueError("missing or duplicate coverage trial")
        for trial, r in enumerate(coverage):
            if r["entropy"] != [plan["base_seed"], 13, index, trial]:
                raise ValueError("changed coverage entropy")
            if r["status"] == "complete":
                raw = np.asarray(r["replicate_integrals"], float)
                if raw.shape != (plan["replicates"], 9):
                    raise ValueError("incomplete coverage replicates")
                actual = assess_trial(raw, plan)
                if json_bytes(actual) != json_bytes({k: r[k] for k in actual}):
                    raise ValueError("coverage evidence changed")
            elif r["status"] != "failed" or not r.get("error"):
                raise ValueError("unrecorded coverage failure")
        if json_bytes(case["coverage_decision"]) != json_bytes(coverage_summary(coverage, plan)):
            raise ValueError("coverage decision changed")
    passed = all(
        c["coverage_decision"]["passed"]
        and c["density_summary"]["complete"] == plan["known_density_trials"]
        for c in result["cases"]
    )
    if result["controls_passed"] is not passed:
        raise ValueError("false reference authorization")
    return passed
