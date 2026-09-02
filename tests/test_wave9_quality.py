#!/usr/bin/env python3
"""Regression tests for Wave 9 rendered quality and bounded learning."""

from __future__ import annotations

import argparse
import binascii
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import design_quality as quality
import design_build as build
import design_state_commands as commands
from design_state_base import StateError
from design_state_validation import append_history, load_state, save_state, sha256

T0 = "2026-08-30T20:00:00Z"
T1 = "2026-08-30T20:01:00Z"
T2 = "2026-08-30T20:02:00Z"
T3 = "2026-08-30T20:03:00Z"


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, color: tuple[int, int, int] = (245, 244, 240)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = bytes([0]) + bytes(color) * width
    raw = row * height
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)
    return path


class Wave9QualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.email", "design-test@example.com")
        self.git("config", "user.name", "Design Test")
        self.write("src/app.txt", "initial product\n")
        self.write("src/other.txt", "unrelated approved product file\n")
        self.write("DESIGN.md", "# Design\n\nUse restrained hierarchy and clear task priority.\n")
        self.write(
            ".design/system/reference-lock.json",
            json.dumps({"schema_version": "1.0", "references": [{"id": "primary"}]}) + "\n",
        )
        self.write(
            ".design/system/ux-definition.json",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "screens": [{"id": "home", "name": "Home"}],
                    "states": [{"screen_id": "home", "default": "Ready state."}],
                }
            )
            + "\n",
        )
        self.write(
            ".design/implementation/plan.json",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "approved_direction_sha256": "1" * 64,
                    "reference_lock_sha256": sha256(self.project / ".design/system/reference-lock.json"),
                    "ux_definition_sha256": sha256(self.project / ".design/system/ux-definition.json"),
                    "design_md_sha256": sha256(self.project / "DESIGN.md"),
                    "quality_targets": [
                        {
                            "id": "home-default", "screen_id": "home", "route": "/", "state": "default",
                            "viewport": {"name": "small", "width": 320, "height": 240, "device_scale_factor": 1},
                            "theme": "light", "reduced_motion": True, "required": True,
                        }
                    ],
                    "repository_change_gate": "awaiting_approval",
                    "goal": "Implement and verify the approved test interface in one bounded wave.",
                    "prohibited_scope": ["Deployment and external publication."],
                    "waves": [
                        {
                            "id": "one", "dependencies": [], "goal": "Implement the approved local interface state.",
                            "inputs": ["Approved design authority."], "approved_requirements": ["Preserve the approved hierarchy."], "design_sections": ["Layout system"],
                            "allowed_files": ["src/app.txt", "src/other.txt"], "work_items": ["Implement the approved state."], "render_targets": ["Home default state."],
                            "tests": ["Run the local quality checks."], "completion_criteria": ["The approved state passes rendered QA."], "rollback": ["Revert the product file."],
                            "risks": ["Missing capture tooling may block rendering."], "status": "planned"
                        }
                    ],
                    "external_actions": [{"action": "Deploy the implementation.", "approval": "separate-required"}],
                    "approval_artifact": ".design/implementation/plan.md"
                }
            )
            + "\n",
        )
        self.advance_run_to_rendering()
        self.git("add", ".")
        self.git("commit", "-qm", "quality test baseline")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def ns(self, **values: object) -> argparse.Namespace:
        defaults: dict[str, object] = {
            "project_root": str(self.project),
            "at": T0,
            "reason": "test evidence",
        }
        defaults.update(values)
        return argparse.Namespace(**defaults)

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.project), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout.strip()

    def write(self, relative: str, content: str) -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def transition(self, target: str, at: str = T0) -> dict:
        return commands.command_transition(self.ns(to=target, at=at))

    def advance_run_to_rendering(self) -> None:
        commands.command_init(self.ns(workflow="run", route="standard"))
        self.transition("interviewing")
        self.transition("understanding_awaiting_approval")
        self.write(".design/shared-understanding.md", "# Shared Understanding\n\nApproved scope.\n")
        commands.command_record_gate(
            self.ns(
                gate="understanding",
                status="approved",
                artifact=".design/shared-understanding.md",
                decision_text="Approved",
                warning_acknowledged=False,
                scope="",
                assumption=[],
            )
        )
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        self.write(".design/directions/decision.md", "# Decision\n\nUse direction one.\n")
        self.write(".design/directions/direction-set.json", '{"directions":[{"id":"one"}]}\n')
        commands.command_record_gate(
            self.ns(
                gate="direction",
                status="approved",
                artifact=".design/directions/decision.md",
                decision_text="Direction approved",
                warning_acknowledged=False,
                scope="",
                assumption=[],
            )
        )
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        plan = json.loads((self.project / ".design/implementation/plan.json").read_text())
        self.write(".design/implementation/plan.md", build.compile_plan_markdown(plan))
        commands.command_record_gate(
            self.ns(
                gate="repository_changes",
                status="approved",
                artifact=".design/implementation/plan.md",
                decision_text="Repository changes approved",
                warning_acknowledged=False,
                scope="src/app.txt",
                assumption=[],
            )
        )
        self.transition("building")
        state = load_state(self.project)
        state["phase"] = "rendering"
        state["status"] = "active"
        state["active_wave"] = None
        append_history(state, "test_waves_completed", T0)
        save_state(self.project, state, T0)

    def render_request(self, *, workflow: str = "run", origin_kind: str = "local") -> dict:
        return {
            "schema_version": "1.0",
            "workflow": workflow,
            "origin": {"kind": origin_kind, "url": "http://127.0.0.1:3000"},
            "server": {
                "mode": "already-running",
                "command": [],
                "cwd": ".",
                "readiness_path": "/",
                "limitations": [],
            },
            "authority_artifacts": [
                {"path": ".design/system/reference-lock.json", "role": "approved roles"},
                {"path": ".design/system/ux-definition.json", "role": "approved screens and states"},
                {"path": ".design/implementation/plan.json", "role": "approved render targets"},
                {"path": "DESIGN.md", "role": "design authority"},
            ],
            "targets": [
                {
                    "id": "home-default",
                    "screen_id": "home",
                    "route": "/",
                    "state": "default",
                    "viewport": {"name": "small", "width": 320, "height": 240, "device_scale_factor": 1},
                    "theme": "light",
                    "reduced_motion": True,
                    "output": ".design/renders/captures/home-default.png",
                    "required": True,
                    "reference": {
                        "kind": "design-authority",
                        "path": "DESIGN.md",
                        "role": "design-system",
                        "comparison_dimensions": ["hierarchy", "spacing"],
                    },
                }
            ],
            "applicable_checks": ["visual", "responsive", "accessibility", "reference"],
            "capture_owner": "render-worker",
            "requested_at": T0,
        }

    def prepare_renders(self) -> tuple[Path, dict, Path]:
        request_path = write_json(self.project / ".design/renders/request.json", self.render_request())
        plan_path = self.project / ".design/renders/plan.json"
        plan = quality.create_render_plan(self.project, request_path, plan_path, at=T0)
        capture = write_png(self.project / plan["targets"][0]["output"], 320, 240)
        evidence = {
            "schema_version": "1.0",
            "status": "complete",
            "render_plan": {"path": ".design/renders/plan.json", "sha256": sha256(plan_path)},
            "capture_owner": "render-worker",
            "server_result": {"status": "pass", "method": "local server readiness check", "evidence": "The loopback route responded before capture."},
            "captures": [
                {
                    "target_id": "home-default",
                    "status": "pass",
                    "output": ".design/renders/captures/home-default.png",
                    "sha256": sha256(capture),
                    "width": 320,
                    "height": 240,
                    "method": "host-browser viewport capture",
                    "source_url": "http://127.0.0.1:3000/",
                    "evidence": "Current state recorded at the planned viewport.",
                    "limitations": [],
                }
            ],
            "limitations": [],
            "captured_at": T1,
        }
        evidence_path = write_json(self.project / ".design/renders/evidence.json", evidence)
        return plan_path, plan, evidence_path

    def accept_renders(self) -> tuple[Path, Path]:
        plan_path, _, evidence_path = self.prepare_renders()
        state = commands.command_accept_renders(
            self.ns(plan=str(plan_path), evidence=str(evidence_path), at=T1, reason="Current PNG target is complete")
        )
        self.assertEqual(state["phase"], "qa")
        return plan_path, evidence_path

    def qa_report(self, *, finding: bool = False, accepted: bool = False) -> tuple[Path, dict]:
        state, binding = quality._state_binding(self.project, allowed_phases={"qa"})
        capture = self.project / ".design/renders/captures/home-default.png"
        evidence_ref = [{"path": capture.relative_to(self.project).as_posix(), "sha256": sha256(capture)}]
        accessibility = write_json(
            self.project / ".design/qa/evidence/accessibility-home-default.json",
            {
                "schema_version": "1.0",
                "target_id": "home-default",
                "performed_by": "accessibility-reviewer",
                "checks": [
                    {"id": check_id, "status": "pass", "method": "manual inspection", "truth_class": "observed", "result": "Current check passed at the planned target.", "applicability_reason": None}
                    for check_id in ("semantics", "accessible-names", "focus", "contrast", "zoom-reflow", "keyboard", "touch-targets", "reduced-motion")
                ],
                "limitations": [],
                "created_at": T2,
            },
        )
        accessibility_ref = {"path": accessibility.relative_to(self.project).as_posix(), "sha256": sha256(accessibility)}
        reference_path = self.project / "DESIGN.md"
        reference_ref = {"path": "DESIGN.md", "sha256": sha256(reference_path)}
        checks = []
        for category in ("visual", "responsive", "accessibility", "reference"):
            current_finding = finding and category == "visual"
            checks.append(
                {
                    "id": f"check-{category}",
                    "target_id": "home-default",
                    "category": category,
                    "status": "pass-with-deviation" if current_finding and accepted else ("fail" if current_finding else "pass"),
                    "method": "accessibility inspection" if category == "accessibility" else f"current {category} inspection",
                    "truth_class": "observed" if category != "responsive" else "measured",
                    "confidence": "low" if category == "accessibility" else "high",
                    "reference_role": "design-system" if category == "reference" else None,
                    "comparison_dimensions": ["hierarchy", "spacing"] if category == "reference" else [],
                    "evidence": evidence_ref + ([reference_ref] if category == "reference" else []) + ([accessibility_ref] if category == "accessibility" else []),
                    "notes": "Current accessibility record is bound to the planned target." if category == "accessibility" else f"Current {category} result at the planned target.",
                }
            )
        findings = []
        if finding:
            findings.append(
                {
                    "id": "finding-spacing",
                    "source_check_id": "check-visual",
                    "target_id": "home-default",
                    "category": "visual",
                    "finding_type": "design-system-drift",
                    "severity": "P3" if accepted else "P2",
                    "status": "accepted-deviation" if accepted else "open",
                    "summary": "Primary spacing does not match the approved hierarchy.",
                    "observed": "The primary block is compressed in the current capture.",
                    "expected": "Restore the spacing rule recorded in DESIGN.md.",
                    "truth_class": "observed",
                    "confidence": "high",
                    "evidence": evidence_ref,
                    "repair_scope": ["src/app.txt"],
                }
            )
        open_findings = [item for item in findings if item["status"] == "open"]
        report = {
            "schema_version": "1.0",
            "workflow": state["workflow"],
            "repair_cycle": state["repair_cycle"],
            "repair_pass": state["repair_pass"],
            "state_binding": binding,
            "render_evidence": {"path": ".design/renders/evidence.json", "sha256": sha256(self.project / ".design/renders/evidence.json")},
            "prior_qa": None,
            "repair_plan": None,
            "repair_evaluation": None,
            "checks": checks,
            "findings": findings,
            "summary": {
                "status": "repair-required" if open_findings else "pass",
                "counts": {
                    "P0": 0,
                    "P1": 0,
                    "P2": sum(item["severity"] == "P2" for item in open_findings),
                    "P3": sum(item["severity"] == "P3" for item in open_findings),
                    "accepted_deviations": sum(item["status"] == "accepted-deviation" for item in findings),
                    "blocked_checks": 0,
                },
                "blockers": [],
                "limitations": [],
            },
            "qa_owner": "qa-worker",
            "created_at": T2,
        }
        path = write_json(self.project / f".design/qa/reports/cycle-{state['repair_cycle']}.json", report)
        return path, report

    def write_completion(self, qa_path: Path, report: dict) -> tuple[Path, Path]:
        qa_ref = {"path": qa_path.relative_to(self.project).as_posix(), "sha256": sha256(qa_path)}
        deviations = []
        for finding in report["findings"]:
            if finding["status"] == "accepted-deviation":
                deviations.append(
                    {
                        "finding_id": finding["id"],
                        "target_id": finding["target_id"],
                        "category": finding["category"],
                        "severity": finding["severity"],
                        "disposition": "accepted",
                        "rationale": "The bounded polish difference does not affect the approved job.",
                        "evidence": finding["evidence"],
                    }
                )
        deviations_path = write_json(
            self.project / ".design/qa/deviations.json",
            {"schema_version": "1.0", "qa_report": qa_ref, "deviations": deviations, "owner": "qa-worker", "created_at": T3},
        )
        dimensions = []
        for check in report["checks"]:
            dimensions.append(
                {
                    "category": check["category"],
                    "status": check["status"],
                    "evidence_checks": [check["id"]],
                    "notes": "Current evidence supports this final category result.",
                }
            )
        scorecard_path = write_json(
            self.project / ".design/qa/scorecard.json",
            {
                "schema_version": "1.0",
                "qa_report": qa_ref,
                "overall": "pass",
                "dimensions": dimensions,
                "blockers": [],
                "limitations": [],
                "owner": "qa-worker",
                "created_at": T3,
            },
        )
        return deviations_path, scorecard_path

    def begin_repair(self, qa_path: Path) -> Path:
        state = commands.command_begin_repair(
            self.ns(
                qa_report=str(qa_path),
                finding=["finding-spacing"],
                worker_id="repair-worker",
                allowed_file=["src/app.txt"],
                action=["Restore the approved spacing behavior."],
                check=["Inspect the changed source and rerender the target."],
                reason="P2 spacing finding is open",
                at=T3,
            )
        )
        self.assertEqual(state["phase"], "repairing")
        return self.project / f".design/qa/repairs/cycle-{state['repair_cycle']}.json"

    def test_render_plan_requires_loopback_for_local_work(self) -> None:
        request = self.render_request()
        request["origin"]["url"] = "https://example.com"
        request_path = write_json(self.project / ".design/renders/request.json", request)
        with self.assertRaisesRegex(quality.QualityError, "loopback-only"):
            quality.create_render_plan(self.project, request_path, ".design/renders/plan.json")

    def test_run_render_plan_requires_current_ux_plan_and_design_authority(self) -> None:
        request = self.render_request()
        request["authority_artifacts"] = [item for item in request["authority_artifacts"] if item["path"] != ".design/system/ux-definition.json"]
        request_path = write_json(self.project / ".design/renders/request.json", request)
        with self.assertRaisesRegex(quality.QualityError, "run render authority is missing"):
            quality.create_render_plan(self.project, request_path, ".design/renders/plan.json")

    def test_run_render_plan_requires_exact_approved_quality_targets(self) -> None:
        request = self.render_request()
        request["targets"][0].update({"id": "admin-default", "screen_id": "home"})
        request["targets"][0]["output"] = ".design/renders/captures/admin-default.png"
        request_path = write_json(self.project / ".design/renders/request.json", request)
        with self.assertRaisesRegex(quality.QualityError, "not an approved quality target"):
            quality.create_render_plan(self.project, request_path, ".design/renders/plan.json")

    def test_project_repair_finding_does_not_require_a_synthetic_render_target(self) -> None:
        self.assertEqual(
            quality._renderable_repair_targets({"rerender_targets": ["project", "home-default"]}),
            {"home-default"},
        )
        self.assertEqual(quality._renderable_repair_targets({"rerender_targets": ["project"]}), set())

    def test_render_plan_rejects_stale_authority_and_changed_source_url(self) -> None:
        plan_path, plan, _ = self.prepare_renders()
        self.write("DESIGN.md", "# Changed authority\n")
        with self.assertRaisesRegex(quality.QualityError, "stale"):
            quality.validate_render_plan(self.project, plan, check_current_state=True)
        self.write("DESIGN.md", "# Design\n\nUse restrained hierarchy and clear task priority.\n")
        plan = json.loads(plan_path.read_text())
        plan["targets"][0]["source_url"] = "http://127.0.0.1:3000/unplanned"
        with self.assertRaisesRegex(quality.QualityError, "does not match origin and route"):
            quality.validate_render_plan(self.project, plan, check_current_state=True)

    def test_run_render_plan_rejects_structured_plan_that_no_longer_matches_approval(self) -> None:
        plan_path, plan, _ = self.prepare_renders()
        structured_path = self.project / ".design/implementation/plan.json"
        structured = json.loads(structured_path.read_text())
        structured["goal"] = "Changed after approval, so this plan is no longer authorized."
        write_json(structured_path, structured)
        plan = json.loads(plan_path.read_text())
        authority = next(item for item in plan["authority_artifacts"] if item["path"] == ".design/implementation/plan.json")
        authority["sha256"] = sha256(structured_path)
        with self.assertRaisesRegex(quality.QualityError, "does not compile to the current repository approval"):
            quality.validate_render_plan(self.project, plan, check_current_state=True)

    def test_run_render_plan_rejects_ux_definition_changed_after_approval(self) -> None:
        plan_path, plan, _ = self.prepare_renders()
        ux_path = self.project / ".design/system/ux-definition.json"
        ux = json.loads(ux_path.read_text())
        ux["screens"].append({"id": "unapproved", "name": "Unapproved screen"})
        ux["states"].append({"screen_id": "unapproved", "default": "Unapproved state."})
        write_json(ux_path, ux)
        plan = json.loads(plan_path.read_text())
        authority = next(item for item in plan["authority_artifacts"] if item["path"] == ".design/system/ux-definition.json")
        authority["sha256"] = sha256(ux_path)
        with self.assertRaisesRegex(quality.QualityError, "UX definition differs from the approved implementation plan"):
            quality.validate_render_plan(self.project, plan, check_current_state=True)

    def test_render_evidence_binds_png_hash_and_dimensions(self) -> None:
        plan_path, _, evidence_path = self.prepare_renders()
        result = quality.verify_render_evidence(self.project, plan_path, evidence_path)
        self.assertEqual(result["status"], "complete")
        capture = self.project / ".design/renders/captures/home-default.png"
        capture.write_bytes(capture.read_bytes() + b"stale")
        with self.assertRaisesRegex(quality.QualityError, "hash is stale"):
            quality.verify_render_evidence(self.project, plan_path, evidence_path)

    def test_render_evidence_rejects_truncated_png_structure(self) -> None:
        plan_path, _, evidence_path = self.prepare_renders()
        capture = self.project / ".design/renders/captures/home-default.png"
        capture.write_bytes(capture.read_bytes()[:24])
        evidence = json.loads(evidence_path.read_text())
        evidence["captures"][0]["sha256"] = sha256(capture)
        write_json(evidence_path, evidence)
        with self.assertRaisesRegex(quality.QualityError, "truncated PNG chunk"):
            quality.verify_render_evidence(self.project, plan_path, evidence_path)

    def test_render_evidence_rejects_undecodable_png_payload(self) -> None:
        plan_path, _, evidence_path = self.prepare_renders()
        capture = self.project / ".design/renders/captures/home-default.png"
        capture.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 240, 8, 2, 0, 0, 0))
            + png_chunk(b"IDAT", b"not-zlib-data")
            + png_chunk(b"IEND", b"")
        )
        evidence = json.loads(evidence_path.read_text())
        evidence["captures"][0]["sha256"] = sha256(capture)
        write_json(evidence_path, evidence)
        with self.assertRaisesRegex(quality.QualityError, "cannot be decoded"):
            quality.verify_render_evidence(self.project, plan_path, evidence_path)

    def test_passing_render_record_cannot_explicitly_disclaim_browser_capture(self) -> None:
        plan_path, _, evidence_path = self.prepare_renders()
        evidence = json.loads(evidence_path.read_text())
        evidence["captures"][0]["method"] = "synthetic fixture"
        evidence["captures"][0]["limitations"] = ["No browser rendering was performed."]
        write_json(evidence_path, evidence)
        with self.assertRaisesRegex(quality.QualityError, "explicitly disclaims"):
            quality.verify_render_evidence(self.project, plan_path, evidence_path)

    def test_missing_required_capture_is_a_blocker(self) -> None:
        plan_path, _, evidence_path = self.prepare_renders()
        evidence = json.loads(evidence_path.read_text())
        evidence["status"] = "blocked"
        evidence["captures"][0].update({"status": "blocked", "sha256": None, "width": None, "height": None, "limitations": ["Browser capture capability is unavailable."]})
        (self.project / evidence["captures"][0]["output"]).unlink()
        write_json(evidence_path, evidence)
        result = quality.verify_render_evidence(self.project, plan_path, evidence_path)
        self.assertEqual(result["required_blockers"], ["home-default"])
        with self.assertRaisesRegex(StateError, "Required render evidence is blocked"):
            commands.command_accept_renders(self.ns(plan=str(plan_path), evidence=str(evidence_path)))

    def test_generic_render_to_qa_transition_cannot_bypass_evidence(self) -> None:
        before = (self.project / ".design/state.json").read_bytes()
        with self.assertRaisesRegex(StateError, "accept-renders"):
            self.transition("qa")
        self.assertEqual(before, (self.project / ".design/state.json").read_bytes())

    def test_structurally_valid_quality_records_advance_state(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        result = quality.validate_qa_report(self.project, qa_path)
        self.assertEqual(result["status"], "pass")
        deviations, scorecard = self.write_completion(qa_path, report)
        state = commands.command_complete_quality(
            self.ns(qa_report=str(qa_path), deviations=str(deviations), scorecard=str(scorecard), at=T3)
        )
        self.assertEqual(state["phase"], "complete")
        self.assertIn(".design/qa/verification.json", state["artifacts"])

    def test_qa_requires_every_applicable_target_category(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        report["checks"] = report["checks"][:-1]
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "cover every applicable category"):
            quality.validate_qa_report(self.project, qa_path)

    def test_reference_and_accessibility_checks_require_bounded_evidence(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        reference = next(item for item in report["checks"] if item["category"] == "reference")
        reference["reference_role"] = "screen"
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "planned reference role"):
            quality.validate_qa_report(self.project, qa_path)
        qa_path, report = self.qa_report()
        accessibility = next(item for item in report["checks"] if item["category"] == "accessibility")
        accessibility["evidence"] = [item for item in accessibility["evidence"] if not item["path"].startswith(".design/qa/evidence/")]
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "accessibility check artifact"):
            quality.validate_qa_report(self.project, qa_path)
        qa_path, report = self.qa_report()
        accessibility = next(item for item in report["checks"] if item["category"] == "accessibility")
        artifact_ref = next(item for item in accessibility["evidence"] if item["path"].startswith(".design/qa/evidence/"))
        artifact_path = self.project / artifact_ref["path"]
        write_json(artifact_path, {"status": "pass"})
        artifact_ref["sha256"] = sha256(artifact_path)
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "keys invalid"):
            quality.validate_qa_report(self.project, qa_path)

    def test_outer_accessibility_pass_cannot_hide_inner_failure(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        accessibility = next(item for item in report["checks"] if item["category"] == "accessibility")
        artifact_ref = next(item for item in accessibility["evidence"] if item["path"].startswith(".design/qa/evidence/"))
        artifact_path = self.project / artifact_ref["path"]
        artifact = json.loads(artifact_path.read_text())
        artifact["checks"][0]["status"] = "fail"
        artifact["checks"][0]["result"] = "Synthetic inner failure for aggregate-status testing."
        write_json(artifact_path, artifact)
        artifact_ref["sha256"] = sha256(artifact_path)
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "does not match its accessibility evidence"):
            quality.validate_qa_report(self.project, qa_path)

    def test_accessibility_checks_cannot_all_be_not_applicable(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        accessibility = next(item for item in report["checks"] if item["category"] == "accessibility")
        artifact_ref = next(item for item in accessibility["evidence"] if item["path"].startswith(".design/qa/evidence/"))
        artifact_path = self.project / artifact_ref["path"]
        artifact = json.loads(artifact_path.read_text())
        for check in artifact["checks"]:
            check["status"] = "not-applicable"
            check["applicability_reason"] = "Synthetic all-not-applicable claim for rejection testing."
        write_json(artifact_path, artifact)
        artifact_ref["sha256"] = sha256(artifact_path)
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "cannot all be not-applicable"):
            quality.validate_qa_report(self.project, qa_path)

    def test_scorecard_category_cannot_cite_another_category(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report()
        deviations, scorecard_path = self.write_completion(qa_path, report)
        scorecard = json.loads(scorecard_path.read_text())
        visual = next(item for item in scorecard["dimensions"] if item["category"] == "visual")
        visual["evidence_checks"] = ["check-accessibility"]
        write_json(scorecard_path, scorecard)
        with self.assertRaisesRegex(quality.QualityError, "another category"):
            quality.verify_completion(self.project, qa_path, deviations, scorecard_path)

    def test_unresolved_p2_blocks_completion_and_cannot_be_accepted(self) -> None:
        self.accept_renders()
        qa_path, report = self.qa_report(finding=True)
        self.assertEqual(quality.validate_qa_report(self.project, qa_path)["status"], "repair-required")
        deviations, scorecard = self.write_completion(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "passing QA"):
            quality.verify_completion(self.project, qa_path, deviations, scorecard)
        report["findings"][0]["status"] = "accepted-deviation"
        report["checks"][0]["status"] = "pass-with-deviation"
        report["summary"]["status"] = "pass"
        report["summary"]["counts"]["P2"] = 0
        report["summary"]["counts"]["accepted_deviations"] = 1
        write_json(qa_path, report)
        with self.assertRaisesRegex(quality.QualityError, "only P3"):
            quality.validate_qa_report(self.project, qa_path)

    def test_repair_is_finding_bound_scope_checked_and_requires_rerender(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        plan_path = self.begin_repair(qa_path)
        with self.assertRaisesRegex(StateError, "complete-repair"):
            self.transition("rendering")
        source = self.write("src/app.txt", "restored approved spacing\n")
        plan = json.loads(plan_path.read_text())
        handoff_path = write_json(
            self.project / f".design/qa/repairs/cycle-{plan['cycle_number']}-handoff.json",
            {
                "schema_version": "1.0",
                "cycle_number": plan["cycle_number"],
                "pass_number": plan["pass_number"],
                "status": "applied",
                "repair_plan_sha256": sha256(plan_path),
                "changed_files": [{"path": "src/app.txt", "change": "changed", "sha256": sha256(source), "evidence": "Spacing source updated."}],
                "completed_actions": plan["actions"],
                "completed_checks": [{"check": plan["checks"][0], "status": "pass", "evidence": "Changed source inspected."}],
                "target_results": [{"finding_id": "finding-spacing", "status": "implemented-awaiting-rerender", "evidence": "Implementation is ready for a fresh capture."}],
                "ended_at": T3,
            },
        )
        state = commands.command_complete_repair(
            self.ns(plan=str(plan_path), handoff=str(handoff_path), reason="Scoped repair applied", at=T3)
        )
        self.assertEqual(state["phase"], "rendering")
        self.assertEqual(state["repair_attempts"], {"home-default": 1})
        request = self.render_request()
        request["targets"][0]["id"] = "home-default-renamed"
        request["targets"][0]["output"] = ".design/renders/captures/home-default-renamed.png"
        request_path = write_json(self.project / ".design/renders/request.json", request)
        with self.assertRaisesRegex(quality.QualityError, "not an approved quality target"):
            quality.create_render_plan(self.project, request_path, ".design/renders/plan.json")

    def test_repair_allowed_files_cannot_widen_the_approved_plan(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        before = (self.project / ".design/state.json").read_bytes()
        with self.assertRaisesRegex(StateError, "exceed the approved implementation plan"):
            commands.command_begin_repair(
                self.ns(
                    qa_report=str(qa_path), finding=["finding-spacing"], worker_id="repair-worker",
                    allowed_file=["src"], action=["Change the whole source tree."], check=["Inspect source."], reason="test scope",
                )
            )
        self.assertEqual(before, (self.project / ".design/state.json").read_bytes())

    def test_repair_allowed_file_must_match_targeted_finding_scope(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        before = (self.project / ".design/state.json").read_bytes()
        with self.assertRaisesRegex(StateError, "unrelated to the targeted finding scope"):
            commands.command_begin_repair(
                self.ns(
                    qa_report=str(qa_path), finding=["finding-spacing"], worker_id="repair-worker",
                    allowed_file=["src/other.txt"], action=["Change an unrelated approved file."], check=["Inspect source."], reason="test finding scope",
                )
            )
        self.assertEqual(before, (self.project / ".design/state.json").read_bytes())

    def test_out_of_scope_repair_change_is_rejected(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        plan_path = self.begin_repair(qa_path)
        outside = self.write("outside.txt", "not approved\n")
        plan = json.loads(plan_path.read_text())
        handoff_path = write_json(
            self.project / f".design/qa/repairs/cycle-{plan['cycle_number']}-handoff.json",
            {
                "schema_version": "1.0", "cycle_number": plan["cycle_number"], "pass_number": plan["pass_number"], "status": "applied", "repair_plan_sha256": sha256(plan_path),
                "changed_files": [{"path": "outside.txt", "change": "changed", "sha256": sha256(outside), "evidence": "Unapproved change."}],
                "completed_actions": plan["actions"], "completed_checks": [{"check": plan["checks"][0], "status": "pass", "evidence": "Check ran."}],
                "target_results": [{"finding_id": "finding-spacing", "status": "implemented-awaiting-rerender", "evidence": "Pending."}], "ended_at": T3,
            },
        )
        with self.assertRaisesRegex(StateError, "outside approved scope"):
            commands.command_complete_repair(self.ns(plan=str(plan_path), handoff=str(handoff_path)))

    def test_repair_handoff_rejects_deletion_without_new_implementation_approval(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        plan_path = self.begin_repair(qa_path)
        (self.project / "src/app.txt").unlink()
        plan = json.loads(plan_path.read_text())
        handoff_path = write_json(
            self.project / f".design/qa/repairs/cycle-{plan['cycle_number']}-handoff.json",
            {
                "schema_version": "1.0", "cycle_number": plan["cycle_number"], "pass_number": plan["pass_number"], "status": "applied", "repair_plan_sha256": sha256(plan_path),
                "changed_files": [{"path": "src/app.txt", "change": "deleted", "sha256": None, "evidence": "Deletion attempted."}],
                "completed_actions": plan["actions"], "completed_checks": [{"check": plan["checks"][0], "status": "pass", "evidence": "Synthetic check record."}],
                "target_results": [{"finding_id": "finding-spacing", "status": "implemented-awaiting-rerender", "evidence": "Pending."}], "ended_at": T3,
            },
        )
        with self.assertRaisesRegex(StateError, "separately approved implementation plan"):
            commands.command_complete_repair(self.ns(plan=str(plan_path), handoff=str(handoff_path)))

    def test_fourth_attempt_is_rejected_without_state_mutation(self) -> None:
        self.accept_renders()
        qa_path, _ = self.qa_report(finding=True)
        state = load_state(self.project)
        state["repair_cycle"] = 3
        state["repair_pass"] = 3
        state["repair_attempts"] = {"home-default": 3}
        append_history(state, "test_three_attempts", T3)
        save_state(self.project, state, T3)
        before = (self.project / ".design/state.json").read_bytes()
        with mock.patch.object(quality, "validate_qa_report", return_value={"status": "repair-required"}):
            with self.assertRaisesRegex(StateError, "attempt 4"):
                commands.command_begin_repair(
                    self.ns(
                        qa_report=str(qa_path), finding=["finding-spacing"], worker_id="repair-worker",
                        allowed_file=["src/app.txt"], action=["Try again."], check=["Inspect again."], reason="test limit",
                    )
                )
        self.assertEqual(before, (self.project / ".design/state.json").read_bytes())

    def test_audit_repair_requires_repository_approval_before_qa_read(self) -> None:
        audit = Path(tempfile.mkdtemp(dir=self.project.parent)).resolve()
        try:
            commands.command_init(self.ns(project_root=str(audit), workflow="audit", route="standard"))
            state = load_state(audit)
            state["phase"] = "qa"
            state["status"] = "active"
            append_history(state, "test_audit_qa", T0)
            save_state(audit, state, T0)
            before = (audit / ".design/state.json").read_bytes()
            with self.assertRaisesRegex(StateError, "repository_changes gate"):
                commands.command_begin_repair(
                    self.ns(project_root=str(audit), qa_report="missing.json", finding=["finding"], worker_id="worker", allowed_file=["src"], action=["Fix."], check=["Check."], reason="audit repair")
                )
            self.assertEqual(before, (audit / ".design/state.json").read_bytes())
        finally:
            import shutil

            shutil.rmtree(audit)

    def learning_proposal(self) -> dict:
        evidence_a = write_json(
            self.project / ".design/learning/evidence/project-a.json",
            {"schema_version": "1.0", "summary": "Redacted evidence for project A."},
        )
        evidence_b = write_json(
            self.project / ".design/learning/evidence/project-b.json",
            {"schema_version": "1.0", "summary": "Redacted evidence for project B."},
        )
        privacy_review = write_json(
            self.project / ".design/learning/reviews/density-rule.json",
            {
                "schema_version": "1.0",
                "proposal_id": "density-rule",
                "reviewer": "privacy-reviewer",
                "reviewer_kind": "human",
                "status": "pass",
                "reviewed_artifacts": [
                    ".design/learning/proposals/density-rule.json",
                    ".design/learning/evidence/project-a.json",
                    ".design/learning/evidence/project-b.json",
                ],
                "checks": [
                    {"id": check_id, "status": "pass", "method": "manual review of the proposal and bound evidence", "notes": "Reviewed the proposal field and every bound evidence artifact."}
                    for check_id in ("private-details", "absolute-paths", "secrets", "benchmark-data")
                ],
                "limitations": [],
                "created_at": T3,
            },
        )
        return {
            "schema_version": "1.0",
            "proposal_id": "density-rule",
            "status": "proposal-only",
            "source_projects": [
                {"opaque_id": "project-a", "visibility": "private", "evidence_ref": "evidence-a"},
                {"opaque_id": "project-b", "visibility": "internal", "evidence_ref": "evidence-b"},
            ],
            "observations": [
                {"source_project_id": "project-a", "statement": "Dense controls need stronger grouping in project A."},
                {"source_project_id": "project-b", "statement": "Dense controls need stronger grouping in project B."},
            ],
            "evidence": [
                {"id": "evidence-a", "source_project_id": "project-a", "artifact": {"path": ".design/learning/evidence/project-a.json", "sha256": sha256(evidence_a)}, "summary": "Redacted project A render evidence."},
                {"id": "evidence-b", "source_project_id": "project-b", "artifact": {"path": ".design/learning/evidence/project-b.json", "sha256": sha256(evidence_b)}, "summary": "Redacted project B render evidence."},
            ],
            "proposed_rule": "Group dense controls by the user's current task boundary.",
            "exceptions": ["Do not add groups when scanning speed is the primary job."],
            "risks": ["Extra grouping may create unnecessary visual weight."],
            "conflicting_rules": [],
            "destination": {"kind": "none", "candidate": "Pending review.", "write_performed": False},
            "evaluation": ["Test on a third unrelated interface before approval."],
            "privacy_review": {
                "status": "pass", "reviewer": "privacy-reviewer", "redactions": ["Removed project names."],
                "review_artifact": {"path": ".design/learning/reviews/density-rule.json", "sha256": sha256(privacy_review)},
            },
            "approval": {"status": "pending", "decision_text": None, "decided_at": None},
            "created_at": T3,
        }

    def test_learning_validation_is_multi_project_and_read_only(self) -> None:
        proposal = self.learning_proposal()
        path = write_json(self.project / ".design/learning/proposals/density-rule.json", proposal)
        before = {file.relative_to(self.project).as_posix(): sha256(file) for file in self.project.rglob("*") if file.is_file()}
        result = quality.validate_learning_proposal(self.project, path)
        after = {file.relative_to(self.project).as_posix(): sha256(file) for file in self.project.rglob("*") if file.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["status"], "valid-proposal")
        self.assertEqual(result["bound_evidence_count"], 2)
        parser = quality.build_parser()
        subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
        self.assertNotIn("activate-learning", subparsers.choices)
        proposal["source_projects"] = proposal["source_projects"][:1]
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "at least two projects"):
            quality.validate_learning_proposal(self.project, path)

    def test_learning_rejects_destination_write_and_private_path(self) -> None:
        proposal = self.learning_proposal()
        proposal["destination"]["write_performed"] = True
        path = write_json(self.project / ".design/learning/proposals/density-rule.json", proposal)
        with self.assertRaisesRegex(quality.QualityError, "cannot write"):
            quality.validate_learning_proposal(self.project, path)
        proposal = self.learning_proposal()
        evidence_path = self.project / proposal["evidence"][0]["artifact"]["path"]
        write_json(evidence_path, {"summary": "Read /Users/private/client.txt"})
        proposal["evidence"][0]["artifact"]["sha256"] = sha256(evidence_path)
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "absolute user path, secret token, or private-key marker"):
            quality.validate_learning_proposal(self.project, path)

    def test_learning_rejects_empty_privacy_review_linux_path_and_secret_token(self) -> None:
        proposal = self.learning_proposal()
        path = write_json(self.project / ".design/learning/proposals/density-rule.json", proposal)
        review_path = self.project / proposal["privacy_review"]["review_artifact"]["path"]
        write_json(review_path, {})
        proposal["privacy_review"]["review_artifact"]["sha256"] = sha256(review_path)
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "keys invalid"):
            quality.validate_learning_proposal(self.project, path)

        proposal = self.learning_proposal()
        evidence_path = self.project / proposal["evidence"][0]["artifact"]["path"]
        write_json(evidence_path, {"summary": "Read /home/private/client.txt"})
        proposal["evidence"][0]["artifact"]["sha256"] = sha256(evidence_path)
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "absolute user path"):
            quality.validate_learning_proposal(self.project, path)

        proposal = self.learning_proposal()
        proposal["evidence"][0]["summary"] = "Credential marker sk-abcdefghijklmnopqrstuvwxyz123456 is forbidden."
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "secret token"):
            quality.validate_learning_proposal(self.project, path)

    def test_learning_rejects_duplicate_evidence_content_and_disclaimed_human_review(self) -> None:
        proposal = self.learning_proposal()
        path = write_json(self.project / ".design/learning/proposals/density-rule.json", proposal)
        first_path = self.project / proposal["evidence"][0]["artifact"]["path"]
        second_path = self.project / proposal["evidence"][1]["artifact"]["path"]
        second_path.write_bytes(first_path.read_bytes())
        proposal["evidence"][1]["artifact"]["sha256"] = sha256(second_path)
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "distinct content hashes"):
            quality.validate_learning_proposal(self.project, path)

        proposal = self.learning_proposal()
        review_path = self.project / proposal["privacy_review"]["review_artifact"]["path"]
        review = json.loads(review_path.read_text())
        review["limitations"] = ["This is not a human privacy review."]
        write_json(review_path, review)
        proposal["privacy_review"]["review_artifact"]["sha256"] = sha256(review_path)
        write_json(path, proposal)
        with self.assertRaisesRegex(quality.QualityError, "explicitly disclaims a human review"):
            quality.validate_learning_proposal(self.project, path)

    def test_wave9_assets_and_launchers_are_present_and_json_parses(self) -> None:
        for relative in (
            "core/schemas/render-plan.schema.json", "core/schemas/render-evidence.schema.json", "core/schemas/accessibility-evidence.schema.json", "core/schemas/qa-report.schema.json",
            "core/schemas/repair-plan.schema.json", "core/schemas/repair-handoff.schema.json", "core/schemas/deviations-report.schema.json",
            "core/schemas/quality-scorecard.schema.json", "core/schemas/learning-proposal.schema.json", "core/schemas/learning-privacy-review.schema.json",
            "core/templates/render-request.template.json", "core/templates/render-evidence.template.json", "core/templates/accessibility-evidence.template.json", "core/templates/qa-report.template.json",
            "core/templates/repair-handoff.template.json", "core/templates/deviations-report.template.json", "core/templates/quality-scorecard.template.json", "core/templates/learning-proposal.template.json", "core/templates/learning-privacy-review.template.json",
        ):
            self.assertIsInstance(json.loads((ROOT / relative).read_text()), dict, relative)
        for skill in ("render", "qa", "repair", "learn"):
            completed = subprocess.run(
                [sys.executable, str(ROOT / f"core/skills/{skill}/scripts/design_quality.py"), "--help"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
