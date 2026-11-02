"""Offline admission contracts; synthetic exposure never becomes an NFL score."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_value.admission import GATES, MODULES, SOURCE_PATHS, load_registry
from nfl_value.admission_cli import main
from nfl_value.benchmarks import ROLE_CODES
from nfl_value.eligibility import qualify
from nfl_value.ingestion import json_bytes, sha256
from test_eligibility import VALIDATED, season


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY = Path("config/admission-2026-v1.json")


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in (*SOURCE_PATHS.values(), str(REGISTRY)):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPOSITORY / relative).read_bytes())
        self.path = self.root / REGISTRY
        self.original = self.path.read_bytes()
        self.data = json.loads(self.original)
        for name in ("socket.socket.connect", "urllib.request.OpenerDirector.open"):
            p = patch(name, side_effect=AssertionError("admission must be offline"))
            p.start()
            self.addCleanup(p.stop)

    def load(self, data=None, *, expected_sha256=None):
        if data is not None:
            self.path.write_bytes(json_bytes(data))
        return load_registry(self.path, repository_root=self.root, expected_sha256=expected_sha256)

    def test_actual_registry_covers_every_role_and_only_missing_scores(self):
        registry = self.load(expected_sha256=sha256(self.original))
        self.assertEqual({m.role for m in registry.modules}, ROLE_CODES)
        self.assertEqual(len(registry.modules), len(ROLE_CODES))
        summary = registry.summary()
        self.assertFalse(summary["main_leaderboard_available"])
        self.assertFalse(summary["game_coverage_refreshed"])
        for m in summary["modules"]:
            self.assertIsNone(m["rank"])
            self.assertIsNone(m["cavaa_ep"])
            self.assertEqual(m["decision"], "not_admitted")
            self.assertTrue(m["blockers"])
            self.assertTrue(all(b["status"] != "passed" for b in m["blockers"]))
        qb = registry.module("qb_observed", "QB")
        self.assertEqual(
            dict(qb.model_spec_hashes),
            {r: self.data["sources"][r]["sha256"] for r in ("baseline_plan", "contrast_plan")},
        )
        self.assertEqual({f.gate for f in qb.findings}, set(GATES))
        self.assertEqual(next(f.status for f in qb.findings if f.gate == "accounting"), "passed")

    def test_participation_pass_does_not_grant_admission_or_change_thresholds(self):
        registry = self.load()
        for role, module, counts in (
            ("QB", "qb_observed", (40, 40, 40)),
            ("RB", "rb_on_ball", (20, 20, 20)),
            ("WR", "wr_targeted", (20, 20, 20)),
            ("TE", "te_targeted", (20, 20, 20)),
        ):
            for multiplier in (0.75, 1.0, 1.25):
                with self.subTest(role=role, multiplier=multiplier):
                    exposure = season(role, counts)
                    reference = qualify(
                        exposure, VALIDATED, historical_threshold_multiplier=multiplier
                    )
                    result = registry.qualify(
                        exposure, module, historical_threshold_multiplier=multiplier
                    )
                    self.assertTrue(reference.participation_qualified)
                    self.assertEqual(
                        result.participation_qualified, reference.participation_qualified
                    )
                    self.assertEqual(result.minimum_opportunities, reference.minimum_opportunities)
                    self.assertEqual(result.opportunities, reference.opportunities)
                    self.assertFalse(result.main_qualified)
                    self.assertIn("attribution_not_validated", result.main_exclusion_reasons)
        self.assertFalse(
            registry.qualify(season(counts=(100, 100)), "qb_observed").participation_qualified
        )

    def test_score_guard_rejects_every_module_even_after_summary_mutation(self):
        registry = self.load()
        summary = registry.summary()
        summary["main_leaderboard_available"] = True
        summary["modules"][0].update(decision="admitted", rank=1, cavaa_ep=0)
        for module in registry.modules:
            with (
                self.subTest(module=module.module_id),
                self.assertRaisesRegex(ValueError, "not admitted"),
            ):
                registry.require_score(module.module_id, module.role)
        self.assertFalse(registry.summary()["main_leaderboard_available"])
        self.assertIsNone(registry.summary()["modules"][0]["cavaa_ep"])

    def test_role_season_and_unknown_module_cannot_reuse_other_admission(self):
        registry = self.load()
        with self.assertRaisesRegex(ValueError, "role differs"):
            registry.require_score("wr_targeted", "QB")
        with self.assertRaisesRegex(ValueError, "unknown contribution"):
            registry.require_score("full_receiver_value", "WR")
        with self.assertRaisesRegex(ValueError, "role differs"):
            registry.qualify(season(), "wr_targeted")
        # Empty valid exposure allows testing the registry season independently
        # of the existing SeasonExposure game/season validation.
        with self.assertRaisesRegex(ValueError, "season differs"):
            registry.qualify(replace(season(), games=(), season=2027), "qb_observed")

    def test_registry_digest_prevents_rebinding_a_published_decision(self):
        changed = deepcopy(self.data)
        changed["findings"]["offense_attribution"]["reason"] += " Altered interpretation."
        with self.assertRaisesRegex(ValueError, "registry SHA-256 mismatch"):
            self.load(changed, expected_sha256=sha256(self.original))
        with self.assertRaisesRegex(ValueError, "SHA-256 digest"):
            self.load(expected_sha256="invalid")

    def test_every_source_is_verified_and_corruption_is_explicit(self):
        for source, relative in SOURCE_PATHS.items():
            target = self.root / relative
            original = target.read_bytes()
            target.write_bytes(original + b"\nchanged")
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(ValueError, f"evidence SHA-256 mismatch: {source}"),
            ):
                self.load()
            target.write_bytes(original)
        (self.root / SOURCE_PATHS["calibration_evidence"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.load()

    def test_evidence_paths_cannot_escape_the_repository(self):
        changed = deepcopy(self.data)
        changed["sources"]["baseline_plan"]["path"] = "../outside.json"
        with self.assertRaisesRegex(ValueError, "unexpected evidence path"):
            self.load(changed)
        self.path.write_bytes(self.original)
        with tempfile.TemporaryDirectory() as outside:
            target = self.root / SOURCE_PATHS["baseline_plan"]
            external = Path(outside) / "plan.json"
            external.write_bytes(target.read_bytes())
            target.unlink()
            target.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "escapes repository"):
                self.load()

    def test_duplicate_fields_nonfinite_and_oversized_json_fail(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1}',
            b'{"nested":{"status":"passed","status":"failed"}}',
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b" " * 1_000_001,
        ):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                self.load()

    def test_schema_dates_and_policy_changes_fail_closed(self):
        changes = [
            ("schema_version", True),
            ("schema_version", 2),
            ("season", True),
            ("season", 2025),
            ("decision_version", "future-v2"),
            ("decided_at", "2026-10-30T00:00:00+00:00"),
            ("decided_at", "2026-11-02T00:00:00"),
        ]
        for key, value in changes:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.load({**self.data, key: value})
        for key, value in (
            ("primary_benchmark", "replacement"),
            ("sensitivity_benchmarks", ["equal_player"]),
            ("eligibility_filters_benchmark", 0),
            ("eligibility_filters_benchmark", True),
            ("recency_discount", True),
        ):
            changed = deepcopy(self.data)
            changed["policy"][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "policy"):
                self.load(changed)

    def test_missing_unknown_or_relabelled_modules_and_model_specs_fail(self):
        for defect in (
            "omitted",
            "unknown",
            "full_scope",
            "wrong_model",
            "missing_gate",
            "extra_claim",
        ):
            changed = deepcopy(self.data)
            module = changed["modules"]["wr_targeted"]
            if defect == "omitted":
                del changed["modules"]["pr_returns"]
            elif defect == "unknown":
                changed["modules"]["extra"] = module
            elif defect == "full_scope":
                module["scope_label"] = "Full receiver value"
            elif defect == "wrong_model":
                module["model_spec_refs"] = ["defense_plan"]
            elif defect == "missing_gate":
                del module["gates"]["uncertainty"]
            else:
                module["main_qualified"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                self.load(changed)

    def test_passing_accounting_cannot_stand_in_for_uncertainty(self):
        changed = deepcopy(self.data)
        changed["modules"]["qb_observed"]["gates"]["uncertainty"] = "offense_accounting"
        with self.assertRaisesRegex(ValueError, "cannot establish this evidence gate"):
            self.load(changed)

    def test_invalid_findings_and_source_inventories_fail(self):
        for key, value in (
            ("status", True),
            ("status", []),
            ("reason", " "),
            ("evidence_refs", []),
            ("evidence_refs", ["invented"]),
            ("evidence_refs", ["offense_evidence", "offense_evidence"]),
            ("applies_to", ["fiction"]),
        ):
            changed = deepcopy(self.data)
            changed["findings"]["offense_attribution"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load(changed)
        changed = deepcopy(self.data)
        del changed["sources"]["decision_record"]
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.load(changed)

    def test_boolean_or_all_green_changes_cannot_admit_current_models(self):
        for value in (True, "admitted", "experimental"):
            changed = deepcopy(self.data)
            changed["modules"]["qb_observed"]["decision"] = value
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "cannot authorize positive"),
            ):
                self.load(changed)
        changed = deepcopy(self.data)
        for f in changed["findings"].values():
            f["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "unresolved gate"):
            self.load(changed)

    def test_cli_check_and_rejection_do_not_publish_or_replace_files(self):
        pointer = self.root / "public/latest.json"
        pointer.parent.mkdir()
        pointer.write_text('{"last_good":"unchanged"}\n')
        before = {
            p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        }
        args = ["--repository-root", str(self.root)]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(args + ["check"]), 0)
        summary = json.loads(out.getvalue())
        self.assertEqual(summary["registry_sha256"], sha256(self.original))
        self.assertEqual(len(summary["modules"]), len(MODULES))
        for digest in (sha256(self.original), "0" * 64):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(
                    main(
                        args
                        + [
                            "require-score",
                            "qb_observed",
                            "--role",
                            "QB",
                            "--registry-sha256",
                            digest,
                        ]
                    ),
                    1,
                )
            self.assertEqual(out.getvalue(), "")
            self.assertIn("Admission check failed", err.getvalue())
        after = {
            p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        }
        self.assertEqual(before, after)
        # This verifies this read-only gate, not a future publisher's atomicity.


if __name__ == "__main__":
    unittest.main()
