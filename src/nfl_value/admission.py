"""Versioned non-admission decisions, separate from participation and research fits.

Version 1 deliberately cannot grant score admission. A positive decision requires
a reviewed contract revision, evidence, and ranking-release validation. Hashes bind
the reviewed evidence; they do not certify scientific truth or live data readiness.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import re

from nfl_value.eligibility import ModuleStatus, SeasonExposure, qualify
from nfl_value.ingestion import sha256
from nfl_value.source_audit import aware_time


GATES = (
    "data",
    "benchmark",
    "denominator",
    "accounting",
    "attribution",
    "uncertainty",
    "comparability",
)
POLICY = {
    "metric": "cumulative_expected_point_cavaa",
    "primary_benchmark": "first_unit",
    "sensitivity_benchmarks": ["equal_player", "opportunity_weighted"],
    "first_unit_weighting": "equal-team-completed-game-role-slot-v1",
    "eligibility_policy": "provisional-2026-v1",
    "eligibility_filters_benchmark": False,
    "recency_discount": False,
}
# Each entry is one contribution module, not an assertion of full-position value.
MODULES = {
    "qb_observed": (
        "QB",
        "Observed QB dropback and carry components",
        ("baseline_plan", "contrast_plan"),
    ),
    "rb_on_ball": (
        "RB",
        "Observed RB carries and recorded targets only",
        ("baseline_plan", "contrast_plan"),
    ),
    "wr_targeted": (
        "WR",
        "Recorded WR targets only; partial receiving coverage",
        ("baseline_plan", "contrast_plan"),
    ),
    "te_targeted": (
        "TE",
        "Recorded TE targets only; partial receiving coverage",
        ("baseline_plan", "contrast_plan"),
    ),
    "ot_blocking": ("OT", "Offensive tackle blocking contribution", ()),
    "og_blocking": ("OG", "Offensive guard blocking contribution", ()),
    "c_blocking": ("C", "Center blocking contribution", ()),
    "idl_defense": ("IDL", "Interior defensive line contribution", ("defense_plan",)),
    "edge_defense": ("EDGE", "Edge defender contribution", ("defense_plan",)),
    "lb_defense": ("LB", "Linebacker contribution", ("defense_plan",)),
    "cb_defense": ("CB", "Cornerback contribution", ("defense_plan",)),
    "s_defense": ("S", "Safety contribution", ("defense_plan",)),
    "k_kicking": ("K", "Placekicking contribution", ()),
    "p_punting": ("P", "Punting contribution", ()),
    "ls_snapping": ("LS", "Long-snapping contribution", ()),
    "kr_returns": ("KR", "Kickoff return contribution", ()),
    "pr_returns": ("PR", "Punt return contribution", ()),
}
SOURCE_PATHS = {
    "baseline_plan": "config/baseline-2025-v1.json",
    "contrast_plan": "config/contrasts-v1.json",
    "defense_plan": "config/defense-2025-v1.json",
    "benchmark_contract": "src/nfl_value/benchmarks.py",
    "eligibility_contract": "src/nfl_value/eligibility.py",
    "offense_evidence": "docs/audits/2026-10-23-offensive-baseline.json",
    "defense_evidence": "docs/audits/2026-10-24-defensive-model.json",
    "explorer_evidence": "docs/audits/2026-10-25-defense-explorer.json",
    "roster_evidence": "docs/audits/2026-10-26-roster-evidence.json",
    "contrast_evidence": "docs/audits/2026-10-27-positional-contrasts.json",
    "calibration_evidence": "docs/audits/2026-10-28-calibration.json",
    "transition_evidence": "docs/audits/2026-10-29-transitions.json",
    "decision_record": "docs/decisions/2026-11-02-module-admission.md",
}


def _keys(value, expected, label):
    if not isinstance(value, dict) or value.keys() != set(expected):
        raise ValueError(f"invalid {label} fields")


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("expected a lowercase SHA-256 digest")
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"nonempty {label} required")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


@dataclass(frozen=True)
class Finding:
    gate: str
    status: str
    reason: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ModuleDecision:
    module_id: str
    role: str
    scope_label: str
    model_spec_hashes: tuple[tuple[str, str], ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class AdmissionRegistry:
    registry_sha256: str
    decision_version: str
    decided_at: str
    season: int
    modules: tuple[ModuleDecision, ...]

    def module(self, module_id: str, role: str) -> ModuleDecision:
        for module in self.modules:
            if module.module_id == module_id:
                if module.role != role:
                    raise ValueError("requested role differs from module scope")
                return module
        raise ValueError("unknown contribution module")

    def require_score(self, module_id: str, role: str) -> None:
        module = self.module(module_id, role)
        blockers = [f.gate for f in module.findings if f.status != "passed"]
        raise ValueError(
            f"module {module_id} is not admitted for CAVAA scores; blockers: {', '.join(blockers)}"
        )

    def qualify(
        self, exposure: SeasonExposure, module_id: str, *, historical_threshold_multiplier=1.0
    ):
        if exposure.season != self.season:
            raise ValueError("exposure season differs from admission registry")
        module = self.module(module_id, exposure.role)
        # Real source coverage for this value module differs from availability of
        # observed events in the Explorer. All v1 attribution/admission is closed.
        status = ModuleStatus(
            next(f.status for f in module.findings if f.gate == "data") == "passed",
            False,
            False,
            module.scope_label,
        )
        return qualify(
            exposure, status, historical_threshold_multiplier=historical_threshold_multiplier
        )

    def summary(self):
        return {
            "schema_version": 1,
            "registry_sha256": self.registry_sha256,
            "decision_version": self.decision_version,
            "decided_at": self.decided_at,
            "season": self.season,
            "metric": POLICY["metric"],
            "main_leaderboard_available": False,
            "game_coverage_refreshed": False,
            "modules": [
                {
                    "module_id": m.module_id,
                    "role": m.role,
                    "scope_label": m.scope_label,
                    "decision": "not_admitted",
                    "cavaa_ep": None,
                    "rank": None,
                    "model_spec_hashes": dict(m.model_spec_hashes),
                    "blockers": [
                        {
                            "gate": f.gate,
                            "status": f.status,
                            "reason": f.reason,
                            "evidence_refs": list(f.evidence_refs),
                        }
                        for f in m.findings
                        if f.status != "passed"
                    ],
                }
                for m in self.modules
            ],
        }


def load_registry(path: Path, *, repository_root: Path, expected_sha256: str | None = None):
    """Read strict JSON and verify every bound source. Never fetch or publish."""
    with path.open("rb") as handle:
        raw = handle.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("admission registry exceeds size limit")
    digest = sha256(raw)
    if expected_sha256 is not None and digest != _hash(expected_sha256):
        raise ValueError("admission registry SHA-256 mismatch")
    data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    _keys(
        data,
        {
            "schema_version",
            "decision_version",
            "decided_at",
            "season",
            "policy",
            "sources",
            "findings",
            "modules",
        },
        "registry",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported admission schema")
    if type(data["season"]) is not int or data["season"] != 2026:
        raise ValueError("version 1 is a 2026 admission decision")
    if data["decision_version"] != "2026-11-02-v1":
        raise ValueError("unsupported admission decision version")
    _text(data["decided_at"], "decision time")
    if aware_time(data["decided_at"]).date().isoformat() != "2026-11-02":
        raise ValueError("decision date must not be backdated to the planned freeze")
    # JSON serialization distinguishes booleans from equal-valued integers.
    if json.dumps(data["policy"], sort_keys=True) != json.dumps(POLICY, sort_keys=True):
        raise ValueError("unsupported metric, benchmark or eligibility policy")
    _keys(data["sources"], SOURCE_PATHS, "source inventory")
    root = repository_root.resolve()
    for source_id, relative in SOURCE_PATHS.items():
        source = data["sources"][source_id]
        _keys(source, {"path", "sha256"}, "source reference")
        if source["path"] != relative:
            raise ValueError(f"unexpected evidence path for {source_id}")
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ValueError("evidence path escapes repository")
        if sha256(target.read_bytes()) != _hash(source["sha256"]):
            raise ValueError(f"evidence SHA-256 mismatch: {source_id}")
    findings = data["findings"]
    if not isinstance(findings, dict) or not findings:
        raise ValueError("documented admission findings required")
    for finding in findings.values():
        _keys(finding, {"status", "reason", "evidence_refs", "applies_to"}, "finding")
        if not isinstance(finding["status"], str) or finding["status"] not in {
            "passed",
            "failed",
            "insufficient",
            "not_evaluated",
        }:
            raise ValueError("unknown evidence status")
        applies_to = finding["applies_to"]
        if (
            not isinstance(applies_to, list)
            or not applies_to
            or any(not isinstance(g, str) or g not in GATES for g in applies_to)
            or len(set(applies_to)) != len(applies_to)
        ):
            raise ValueError("known unique applicable gates required")
        _text(finding["reason"], "finding reason")
        refs = finding["evidence_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(r, str) or r not in SOURCE_PATHS for r in refs)
            or len(set(refs)) != len(refs)
        ):
            raise ValueError("nonempty unique known evidence references required")
    _keys(data["modules"], MODULES, "module inventory")
    modules = []
    for module_id, (role, scope, specs) in MODULES.items():
        m = data["modules"][module_id]
        _keys(m, {"role", "scope_label", "decision", "model_spec_refs", "gates"}, "module")
        if m["role"] != role or m["scope_label"] != scope or m["model_spec_refs"] != list(specs):
            raise ValueError("module role, scope or model specification differs")
        if m["decision"] != "not_admitted":
            raise ValueError("version 1 cannot authorize positive score admission")
        _keys(m["gates"], GATES, "module gates")
        resolved = []
        for gate in GATES:
            ref = m["gates"][gate]
            if not isinstance(ref, str) or ref not in findings:
                raise ValueError("unknown gate finding")
            f = findings[ref]
            if gate not in f["applies_to"]:
                raise ValueError("finding cannot establish this evidence gate")
            resolved.append(Finding(gate, f["status"], f["reason"], tuple(f["evidence_refs"])))
        if all(f.status == "passed" for f in resolved):
            raise ValueError("non-admission requires an explicit unresolved gate")
        modules.append(
            ModuleDecision(
                module_id,
                role,
                scope,
                tuple((s, data["sources"][s]["sha256"]) for s in specs),
                tuple(resolved),
            )
        )
    return AdmissionRegistry(
        digest, data["decision_version"], data["decided_at"], data["season"], tuple(modules)
    )
