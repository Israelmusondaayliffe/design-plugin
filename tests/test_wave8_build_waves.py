#!/usr/bin/env python3
"""Wave 8 regression tests for controlled implementation waves."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load_module("design_build_wave8", SCRIPTS / "design_build.py")
system = load_module("design_system_wave8", SCRIPTS / "design_system.py")
state_commands = load_module("design_state_commands_wave8", SCRIPTS / "design_state_commands.py")
T0 = "2026-08-30T00:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def gate(name: str, artifact: str, digest: str) -> dict:
    decisions = {
        "understanding": "Approved",
        "direction": "This direction is approved",
        "repository_changes": "These repository changes are approved",
    }
    return {
        "gate": name,
        "status": "approved",
        "artifact_path": artifact,
        "artifact_sha256": digest,
        "decided_at": T0,
        "decision_text": decisions[name],
        "warning_acknowledged": False,
        "scope": "Approved test scope.",
        "assumptions_accepted": [],
        "stale_reason": None,
        "stale_at": None,
    }


def planned_wave(identifier: str, allowed: str, dependencies: list[str]) -> dict:
    return {
        "id": identifier,
        "dependencies": dependencies,
        "goal": f"Implement the bounded {identifier} product outcome.",
        "inputs": ["Approved artifacts and current repository evidence."],
        "approved_requirements": [f"The {identifier} behavior follows the approved design rules."],
        "design_sections": ["Interaction states", "Responsive behavior"],
        "allowed_files": [allowed],
        "work_items": [f"Implement the exact {identifier} change."],
        "render_targets": [f"{identifier} desktop state"],
        "tests": [f"{identifier} direct test"],
        "completion_criteria": [f"{identifier} behavior is implemented and verified."],
        "rollback": [f"Revert the {identifier} product change."],
        "risks": [f"Stop {identifier} if approved behavior is missing."],
        "status": "planned",
    }


class Wave8BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        git(self.project, "init", "-q")
        git(self.project, "config", "user.email", "design-test@example.com")
        git(self.project, "config", "user.name", "Design Test")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build_project(self, *, waves: int = 1) -> dict[str, Path]:
        understanding = self.project / ".design/shared-understanding.md"
        understanding.parent.mkdir(parents=True, exist_ok=True)
        understanding.write_text("# Shared Understanding\n\nApproved test product.\n", encoding="utf-8")
        direction = self.project / ".design/directions/decision.md"
        direction.parent.mkdir(parents=True, exist_ok=True)
        direction.write_text("# Direction\n\nApproved direction.\n", encoding="utf-8")
        direction_set = self.project / ".design/directions/direction-set.json"
        write_json(direction_set, {"directions": [{"id": "approved-direction"}]})
        lock = self.project / ".design/system/reference-lock.json"
        write_json(lock, {"approved": True})
        ux = self.project / ".design/system/ux-definition.json"
        write_json(ux, {"schema_version": "1.0", "screens": [{"id": "home"}], "states": [{"screen_id": "home", "default": "Ready."}]})
        design = self.project / "DESIGN.md"
        design.write_text("# DESIGN\n\nApproved rules.\n", encoding="utf-8")

        wave_items = [planned_wave("foundation", "src/foundation.txt", [])]
        if waves == 2:
            wave_items.append(planned_wave("behavior", "src/behavior.txt", ["foundation"]))
        plan = {
            "schema_version": "1.0",
            "approved_direction_sha256": build.sha256(direction),
            "reference_lock_sha256": build.sha256(lock),
            "ux_definition_sha256": build.sha256(ux),
            "design_md_sha256": build.sha256(design),
            "quality_targets": [
                {
                    "id": "home-default-small", "screen_id": "home", "route": "/", "state": "default",
                    "viewport": {"name": "small", "width": 390, "height": 844, "device_scale_factor": 1},
                    "theme": "light", "reduced_motion": True, "required": True,
                }
            ],
            "repository_change_gate": "awaiting_approval",
            "goal": "Implement the approved test product in bounded waves.",
            "prohibited_scope": ["Deployment and external publication."],
            "waves": wave_items,
            "external_actions": [],
            "approval_artifact": ".design/implementation/plan.md",
        }
        plan_json = self.project / ".design/implementation/plan.json"
        plan_md = self.project / ".design/implementation/plan.md"
        write_json(plan_json, plan)
        plan_md.write_text(system.compile_plan_markdown(plan), encoding="utf-8")

        state = {
            "schema_version": "1.0",
            "plugin": "design",
            "revision": 0,
            "workflow": "run",
            "route": "standard",
            "phase": "building",
            "status": "active",
            "phase_before_block": None,
            "gates": {
                "understanding": gate("understanding", ".design/shared-understanding.md", build.sha256(understanding)),
                "direction": gate("direction", ".design/directions/decision.md", build.sha256(direction)),
                "repository_changes": gate("repository_changes", ".design/implementation/plan.md", build.sha256(plan_md)),
            },
            "artifacts": {
                ".design/directions/direction-set.json": build.sha256(direction_set),
            },
            "active_wave": 1,
            "repair_cycle": 0,
            "repair_pass": 0,
            "repair_attempts": {},
            "blockers": [],
            "history": [{"event": "test_building_fixture", "at": T0}],
            "created_at": T0,
            "updated_at": T0,
        }
        write_json(self.project / ".design/state.json", state)
        git(self.project, "add", ".")
        git(self.project, "commit", "-qm", "approved baseline")
        return {
            "understanding": understanding,
            "direction": direction,
            "direction_set": direction_set,
            "lock": lock,
            "design": design,
            "plan_json": plan_json,
            "plan_md": plan_md,
        }

    def prepare(self, wave_id: str = "foundation") -> tuple[Path, dict]:
        manifest_path = self.project / f".design/implementation/waves/{wave_id}/manifest.json"
        manifest = build.prepare_wave(
            self.project,
            ".design/implementation/plan.json",
            manifest_path.relative_to(self.project),
            "primary-worker",
        )
        return manifest_path, manifest

    def complete_handoff(self, manifest_path: Path, product_path: str) -> tuple[Path, dict]:
        manifest = build.load_json(manifest_path)
        target = self.project / product_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"implemented {manifest['wave_id']}\n", encoding="utf-8")
        handoff = {
            "schema_version": "1.0",
            "wave_id": manifest["wave_id"],
            "wave_number": manifest["wave_number"],
            "status": "complete",
            "manifest_sha256": build.sha256(manifest_path),
            "changed_files": [
                {
                    "path": product_path,
                    "change": "changed",
                    "sha256": build.sha256(target),
                    "evidence": "Repository comparison records the new product file.",
                }
            ],
            "completed_checks": [
                {"name": manifest["tests"][0], "command": "test-command", "status": "pass", "evidence": "The direct test passed."}
            ],
            "render_results": [
                {"target": manifest["render_targets"][0], "status": "pass", "evidence": "The planned state was inspected."}
            ],
            "completion_criteria": [
                {"criterion": manifest["completion_criteria"][0], "status": "pass", "evidence": "The criterion is observable in the product file."}
            ],
            "known_deviations": [],
            "new_risks": [],
            "review_results": [
                {"reviewer_id": "independent-verifier", "role": "independent-verifier", "status": "pass", "evidence": "Independent behavior and scope review passed."},
                {"reviewer_id": "unslop-reviewer", "role": "unslop-reviewer", "status": "pass", "evidence": "Independent writing-quality review passed."},
            ],
            "next_inputs": ["Use the approved next wave or enter rendering after the final wave."],
            "rollback_notes": ["Remove the added product file or revert its wave commit."],
            "ended_at": "2026-08-30T00:10:00Z",
        }
        handoff_path = manifest_path.parent / "handoff.json"
        write_json(handoff_path, handoff)
        (manifest_path.parent / "handoff.md").write_text(
            build.compile_handoff(handoff, manifest), encoding="utf-8"
        )
        return handoff_path, handoff

    def complete_state_wave(self, manifest: Path, handoff: Path) -> dict:
        return state_commands.command_complete_wave(
            argparse.Namespace(
                project_root=str(self.project),
                manifest=str(manifest),
                handoff=str(handoff),
                reason="Independent verification and Unslop review passed.",
                at="2026-08-30T00:11:00Z",
            )
        )

    def test_schemas_and_templates_parse(self) -> None:
        for path in sorted((ROOT / "core/schemas").glob("*.json")):
            with self.subTest(schema=path.name):
                self.assertIsInstance(json.loads(path.read_text()), dict)
        for name in ("wave-manifest.template.json", "wave-handoff.template.json"):
            self.assertIsInstance(json.loads((ROOT / "core/templates" / name).read_text()), dict)

    def test_prepare_binds_manifest_and_engine_control_is_not_product_scope(self) -> None:
        self.build_project()
        manifest_path, manifest = self.prepare()
        state = json.loads((self.project / ".design/state.json").read_text())
        relative = manifest_path.relative_to(self.project).as_posix()
        self.assertEqual(state["artifacts"][relative], build.sha256(manifest_path))
        self.assertEqual(manifest["worker_id"], "primary-worker")
        self.assertEqual(build.check_scope(self.project, manifest)["changed_files"], [])

    def test_changed_plan_json_cannot_widen_scope_after_approval(self) -> None:
        paths = self.build_project()
        plan = json.loads(paths["plan_json"].read_text())
        plan["waves"][0]["allowed_files"] = ["src"]
        write_json(paths["plan_json"], plan)
        with self.assertRaisesRegex(build.ValidationError, "does not compile to the approved"):
            self.prepare()

    def test_changed_manifest_is_rejected_after_state_binding(self) -> None:
        self.build_project()
        manifest_path, manifest = self.prepare()
        manifest["allowed_files"] = ["src"]
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(build.ValidationError, "not immutably bound"):
            build.verify_wave8(self.project, manifest_path, manifest_path.parent / "handoff.json")

    def test_out_of_scope_product_change_blocks_wave(self) -> None:
        self.build_project()
        _, manifest = self.prepare()
        target = self.project / "outside.txt"
        target.write_text("outside\n", encoding="utf-8")
        report = build.check_scope(self.project, manifest)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["outside_allowed_scope"], ["outside.txt"])

    def test_handoff_must_cover_every_planned_test(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        handoff_path, handoff = self.complete_handoff(manifest_path, "src/foundation.txt")
        handoff["completed_checks"][0]["name"] = "invented passing check"
        with self.assertRaisesRegex(build.ValidationError, "every planned test"):
            build.validate_handoff(handoff, build.load_json(manifest_path))

    def test_handoff_rejects_unverified_change_kind_claim(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        _, handoff = self.complete_handoff(manifest_path, "src/foundation.txt")
        handoff["changed_files"][0]["change"] = "renamed"
        with self.assertRaisesRegex(build.ValidationError, "change is invalid"):
            build.validate_handoff(handoff, build.load_json(manifest_path))

    def test_worker_cannot_verify_or_unslop_review_same_wave(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        _, handoff = self.complete_handoff(manifest_path, "src/foundation.txt")
        handoff["review_results"][0]["reviewer_id"] = "primary-worker"
        with self.assertRaisesRegex(build.ValidationError, "cannot verify"):
            build.validate_handoff(handoff, build.load_json(manifest_path))
        handoff["review_results"][0]["reviewer_id"] = "independent-verifier"
        handoff["review_results"][1]["status"] = "fail"
        with self.assertRaisesRegex(build.ValidationError, "every recorded review"):
            build.validate_handoff(handoff, build.load_json(manifest_path))

    def test_complete_handoff_requires_distinct_unslop_reviewer(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        _, handoff = self.complete_handoff(manifest_path, "src/foundation.txt")
        handoff["review_results"] = [handoff["review_results"][0]]
        with self.assertRaisesRegex(build.ValidationError, "requires an Unslop review"):
            build.validate_handoff(handoff, build.load_json(manifest_path))
        _, handoff = self.complete_handoff(manifest_path, "src/foundation.txt")
        handoff["review_results"][1]["reviewer_id"] = "primary-worker"
        with self.assertRaisesRegex(build.ValidationError, "cannot verify or Unslop-review"):
            build.validate_handoff(handoff, build.load_json(manifest_path))

    def test_forged_minimal_handoff_cannot_advance_state(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        handoff_path = manifest_path.parent / "handoff.json"
        write_json(handoff_path, {"status": "complete", "wave_number": 1})
        with self.assertRaisesRegex(state_commands.StateError, "Wave verification failed"):
            self.complete_state_wave(manifest_path, handoff_path)
        state = json.loads((self.project / ".design/state.json").read_text())
        self.assertEqual(state["phase"], "building")
        self.assertEqual(state["active_wave"], 1)

    def test_complete_final_wave_enters_rendering_and_binds_receipt(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        handoff_path, _ = self.complete_handoff(manifest_path, "src/foundation.txt")
        report = build.verify_wave8(self.project, manifest_path, handoff_path)
        self.assertTrue(report["ready_for_state_completion"])
        state = self.complete_state_wave(manifest_path, handoff_path)
        self.assertEqual(state["phase"], "rendering")
        self.assertIsNone(state["active_wave"])
        receipt = manifest_path.parent / "verification.json"
        self.assertTrue(receipt.is_file())
        self.assertEqual(state["artifacts"][receipt.relative_to(self.project).as_posix()], build.sha256(receipt))
        handoff_markdown = manifest_path.parent / "handoff.md"
        self.assertEqual(
            state["artifacts"][handoff_markdown.relative_to(self.project).as_posix()],
            build.sha256(handoff_markdown),
        )

    def test_total_wave_count_comes_from_approved_plan_and_dependency_receipt(self) -> None:
        self.build_project(waves=2)
        first_manifest, _ = self.prepare("foundation")
        first_handoff, _ = self.complete_handoff(first_manifest, "src/foundation.txt")
        state = self.complete_state_wave(first_manifest, first_handoff)
        self.assertEqual(state["phase"], "building")
        self.assertEqual(state["active_wave"], 2)
        second_manifest, second = self.prepare("behavior")
        self.assertEqual(second["previous_handoff"]["path"], ".design/implementation/waves/foundation/handoff.json")
        second_handoff, _ = self.complete_handoff(second_manifest, "src/behavior.txt")
        final = self.complete_state_wave(second_manifest, second_handoff)
        self.assertEqual(final["phase"], "rendering")

    def test_next_wave_rejects_changed_product_from_completed_dependency(self) -> None:
        self.build_project(waves=2)
        first_manifest, _ = self.prepare("foundation")
        first_handoff, _ = self.complete_handoff(first_manifest, "src/foundation.txt")
        self.complete_state_wave(first_manifest, first_handoff)
        (self.project / "src/foundation.txt").write_text("changed after verification\n", encoding="utf-8")
        with self.assertRaisesRegex(build.ValidationError, "changed file hash is stale"):
            self.prepare("behavior")

    def test_next_wave_rejects_changed_readable_dependency_handoff(self) -> None:
        self.build_project(waves=2)
        first_manifest, _ = self.prepare("foundation")
        first_handoff, _ = self.complete_handoff(first_manifest, "src/foundation.txt")
        self.complete_state_wave(first_manifest, first_handoff)
        (first_manifest.parent / "handoff.md").write_text("forged readable handoff\n", encoding="utf-8")
        with self.assertRaisesRegex(build.ValidationError, "verification receipt is invalid|state-bound verified"):
            self.prepare("behavior")

    def test_direct_building_to_rendering_transition_is_forbidden(self) -> None:
        self.build_project()
        with self.assertRaisesRegex(state_commands.StateError, "Illegal transition"):
            state_commands.command_transition(
                argparse.Namespace(
                    project_root=str(self.project),
                    to="rendering",
                    reason="skip waves",
                    at=T0,
                )
            )

    def test_stale_handoff_markdown_blocks_verification(self) -> None:
        self.build_project()
        manifest_path, _ = self.prepare()
        handoff_path, _ = self.complete_handoff(manifest_path, "src/foundation.txt")
        (manifest_path.parent / "handoff.md").write_text("stale\n", encoding="utf-8")
        with self.assertRaisesRegex(build.ValidationError, "Markdown is stale"):
            build.verify_wave8(self.project, manifest_path, handoff_path)


if __name__ == "__main__":
    unittest.main()
