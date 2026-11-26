"""Frozen computation-budget selection; never a numerical or scoring certificate."""

from nfl_value.ingestion import json_bytes

EXPERIMENT = "coarse-work-preflight-v1"
PLAN_HASH = "873954f7cc6fab574a6b09dcd81250abb5019ae93d3d5b586258cb203ef8eb28"


def work_plan(plan):
    return plan["experiment"] == EXPERIMENT


def execution_plan(plan, arm):
    """Only the declared coarse count and operational call ceiling may vary."""
    if not work_plan(plan):
        return plan
    if arm not in plan["work_budget_order"] or arm not in plan["work_budgets"]:
        raise ValueError("undeclared computation-budget arm")
    changes = plan["work_budgets"][arm]
    if set(changes) != {"nodes_per_replicate", "maximum_target_evaluations"} or any(
        type(x) is not int or x <= 0 for x in changes.values()
    ):
        raise ValueError("only positive coarse count and call ceiling may change")
    n = changes["nodes_per_replicate"]
    if n < 2 or n & (n - 1):
        raise ValueError("power-of-two coarse budget required")
    return {**plan, **changes}


def budget_decision(cases, plan):
    """A single global setting for fresh confirmation, never per-case winners."""
    expected = [(a, i) for a in plan["work_budget_order"] for i in plan["known_targets"]]
    if [(c["arm"], c["target"]) for c in cases] != expected:
        raise ValueError("complete ordered computation-budget case universe required")
    passed = {
        a: all(c["decision"]["screen_passed"] is True for c in cases if c["arm"] == a)
        for a in plan["work_budget_order"]
    }
    selected = next((a for a in plan["work_budget_order"] if passed[a]), None)
    return dict(
        arm_passed=passed,
        selected_arm=selected,
        selected_coarse_nodes=(
            execution_plan(plan, selected)["nodes_per_replicate"] if selected is not None else None
        ),
        policy=plan["selection_policy"],
        fresh_confirmation_required=True,
        numerical_certified=False,
        ranking_ready=False,
    )


def validate_matched_work(cases, plan):
    """Fitting/pilot values are identical; allocations and evaluation draws differ."""
    by_key = {(c["arm"], c["target"]): c for c in cases}
    for i in plan["known_targets"]:
        baseline = by_key[("candidate", i)]["records"]
        for arm in plan["work_budget_order"][1:]:
            other = by_key[(arm, i)]["records"]
            if len(baseline) != len(other):
                raise ValueError("matched budget denominator differs")
            for a, b in zip(baseline, other):
                if a["trial"] != b["trial"]:
                    raise ValueError("matched budget trial identities differ")
                for key in ("geometry", "fit"):
                    if key in a and key in b and json_bytes(a[key]) != json_bytes(b[key]):
                        raise ValueError("matched budget fitting evidence differs")
                if "components" not in a or "components" not in b:
                    continue
                x, y = a["components"], b["components"]
                for key in ("pilot_entropy", "pilot_plain", "pilot_controlled", "mixture_masses"):
                    if json_bytes(x[key]) != json_bytes(y[key]):
                        raise ValueError("matched budget pilot evidence differs")
                for key in ("anchors", "residual_variances", "scores"):
                    if json_bytes(x["allocation"][key]) != json_bytes(y["allocation"][key]):
                        raise ValueError("matched budget allocation inputs differ")
                for key in ("coarse_entropy", "correction_entropy"):
                    if x[key] == y[key]:
                        raise ValueError("budget evaluation domains must differ")
