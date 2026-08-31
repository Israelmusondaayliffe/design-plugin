#!/usr/bin/env python3
"""Regression tests for the Wave 2 durable workflow controller."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_TOOL = ROOT / "core/scripts/design_state.py"


class StateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name).resolve()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def cli(self, command: str, *args: str, expected: int = 0) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(STATE_TOOL),
                command,
                "--project-root",
                str(self.project),
                *args,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout={completed.stdout}\nstderr={completed.stderr}",
        )
        stream = completed.stdout if completed.stdout.strip() else completed.stderr
        return json.loads(stream)

    def write(self, relative: str, content: str) -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def transition(self, target: str, expected: int = 0) -> dict:
        return self.cli(
            "transition",
            "--to",
            target,
            "--reason",
            f"test transition to {target}",
            expected=expected,
        )

    def enter_rendering_fixture(self) -> None:
        path = self.project / ".design/state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "building")
        state["phase"] = "rendering"
        state["status"] = "active"
        state["active_wave"] = None
        state["revision"] += 1
        state["history"].append({"event": "test_fixture", "at": state["updated_at"]})
        path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def enter_qa_fixture(self) -> None:
        path = self.project / ".design/state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "rendering")
        state["phase"] = "qa"
        state["status"] = "active"
        state["revision"] += 1
        state["history"].append({"event": "test_quality_fixture", "at": state["updated_at"]})
        path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def init_to_understanding_gate(self, workflow: str = "run") -> None:
        self.cli("init", "--workflow", workflow)
        self.transition("interviewing")
        self.transition("understanding_awaiting_approval")
        self.write(".design/shared-understanding.md", "# Shared Understanding\n\nConfirmed.\n")

    def approve_understanding(self) -> dict:
        return self.cli(
            "record-gate",
            "--gate",
            "understanding",
            "--status",
            "approved",
            "--artifact",
            ".design/shared-understanding.md",
            "--decision-text",
            "Approved",
        )

    def advance_run_to_qa(self) -> None:
        self.init_to_understanding_gate("run")
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        self.write(".design/directions/decision.md", "# Direction Decision\n\nDirection 2.\n")
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-2"}]}\n')
        self.cli(
            "record-gate",
            "--gate",
            "direction",
            "--status",
            "approved",
            "--artifact",
            ".design/directions/decision.md",
            "--decision-text",
            "This direction is approved",
        )
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        self.write(".design/implementation/plan.md", "# Implementation Plan\n\nWave 1.\n")
        self.cli(
            "record-gate",
            "--gate",
            "repository_changes",
            "--status",
            "approved",
            "--artifact",
            ".design/implementation/plan.md",
            "--decision-text",
            "These repository changes are approved",
        )
        building = self.transition("building")
        self.assertEqual(building["active_wave"], 1)
        self.enter_rendering_fixture()
        self.enter_qa_fixture()

    def test_full_run_requires_all_gates_and_completes(self) -> None:
        self.init_to_understanding_gate("run")
        blocked = self.transition("researching", expected=1)
        self.assertIn("understanding gate", blocked["error"])
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        blocked = self.transition("system_definition", expected=1)
        self.assertIn("direction gate", blocked["error"])

        self.write(".design/directions/decision.md", "# Direction\n")
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-1"}]}\n')
        self.cli(
            "record-gate",
            "--gate",
            "direction",
            "--status",
            "approved",
            "--artifact",
            ".design/directions/decision.md",
            "--decision-text",
            "Direction approved",
        )
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        blocked = self.transition("building", expected=1)
        self.assertIn("repository_changes gate", blocked["error"])

        self.write(".design/implementation/plan.md", "# Plan\n")
        self.cli(
            "record-gate",
            "--gate",
            "repository_changes",
            "--status",
            "approved",
            "--artifact",
            ".design/implementation/plan.md",
            "--decision-text",
            "Repository changes approved",
        )
        self.transition("building")
        blocked = self.transition("rendering", expected=1)
        self.assertIn("Illegal transition", blocked["error"])

    def test_skip_understanding_requires_acknowledged_warning(self) -> None:
        self.init_to_understanding_gate("run")
        blocked = self.cli(
            "record-gate",
            "--gate",
            "understanding",
            "--status",
            "skipped",
            "--artifact",
            ".design/shared-understanding.md",
            "--decision-text",
            "Skip",
            expected=1,
        )
        self.assertIn("risk warning", blocked["error"])
        state = self.cli(
            "record-gate",
            "--gate",
            "understanding",
            "--status",
            "skipped",
            "--artifact",
            ".design/shared-understanding.md",
            "--decision-text",
            "Skip after warning",
            "--warning-acknowledged",
        )
        self.assertEqual(state["gates"]["understanding"]["status"], "skipped")
        self.transition("researching")

    def test_understanding_approval_phrase_is_exact(self) -> None:
        self.init_to_understanding_gate("run")
        blocked = self.cli(
            "record-gate",
            "--gate",
            "understanding",
            "--status",
            "approved",
            "--artifact",
            ".design/shared-understanding.md",
            "--decision-text",
            "Looks good",
            expected=1,
        )
        self.assertIn("must be 'Approved'", blocked["error"])

    def test_gate_artifacts_and_decisions_are_bound_to_their_authority(self) -> None:
        self.init_to_understanding_gate("run")
        self.write("unrelated.txt", "not the shared understanding\n")
        blocked = self.cli(
            "record-gate",
            "--gate",
            "understanding",
            "--status",
            "approved",
            "--artifact",
            "unrelated.txt",
            "--decision-text",
            "Approved",
            expected=1,
        )
        self.assertIn("canonical artifact", blocked["error"])
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        self.write(".design/directions/decision.md", "# Direction\n")
        direction_set = self.write(
            ".design/directions/direction-set.json",
            '{"directions": [{"id": "direction-1"}]}\n',
        )
        self.write("notes.txt", "unrelated direction notes\n")
        for artifact, decision in (
            ("notes.txt", "This direction is approved"),
            (".design/directions/decision.md", "Reject every direction"),
        ):
            blocked = self.cli(
                "record-gate",
                "--gate",
                "direction",
                "--status",
                "approved",
                "--artifact",
                artifact,
                "--decision-text",
                decision,
                expected=1,
            )
            self.assertIn("canonical artifact" if artifact == "notes.txt" else "approval decision", blocked["error"])
        approved = self.cli(
            "record-gate",
            "--gate",
            "direction",
            "--status",
            "approved",
            "--artifact",
            ".design/directions/decision.md",
            "--decision-text",
            "This direction is approved",
        )
        self.assertEqual(
            approved["artifacts"][".design/directions/direction-set.json"],
            hashlib.sha256(direction_set.read_bytes()).hexdigest(),
        )
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        self.write(".design/implementation/plan.md", "# Plan\n")
        self.write("notes.txt", "unrelated plan notes\n")
        for artifact, decision in (
            ("notes.txt", "These repository changes are approved"),
            (".design/implementation/plan.md", "Do not make repository changes"),
        ):
            blocked = self.cli(
                "record-gate",
                "--gate",
                "repository_changes",
                "--status",
                "approved",
                "--artifact",
                artifact,
                "--decision-text",
                decision,
                expected=1,
            )
            self.assertIn("canonical artifact" if artifact == "notes.txt" else "approval decision", blocked["error"])
        self.cli(
            "record-gate",
            "--gate",
            "repository_changes",
            "--status",
            "approved",
            "--artifact",
            ".design/implementation/plan.md",
            "--decision-text",
            "These repository changes are approved",
        )
        self.transition("building")

    def test_changed_bound_direction_set_makes_direction_gate_stale(self) -> None:
        self.init_to_understanding_gate("run")
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        self.write(".design/directions/decision.md", "# Direction\n")
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-1"}]}\n')
        self.cli(
            "record-gate",
            "--gate",
            "direction",
            "--status",
            "approved",
            "--artifact",
            ".design/directions/decision.md",
            "--decision-text",
            "Direction approved",
        )
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-2"}]}\n')
        blocked = self.transition("system_definition", expected=1)
        self.assertIn("Stale approval gates", blocked["error"])

    def test_changed_artifact_marks_gate_stale_and_blocks_transition(self) -> None:
        self.init_to_understanding_gate("run")
        self.approve_understanding()
        self.write(".design/shared-understanding.md", "# Changed understanding\n")
        blocked = self.transition("researching", expected=1)
        self.assertIn("Stale approval gates", blocked["error"])
        state = self.cli("show")
        self.assertEqual(state["gates"]["understanding"]["status"], "stale")

    def test_understanding_staleness_propagates_downstream(self) -> None:
        self.advance_run_to_qa()
        self.write(".design/shared-understanding.md", "# Changed after build approval\n")
        report = self.cli("verify", expected=2)
        self.assertEqual(
            report["stale_gates"],
            ["understanding", "direction", "repository_changes"],
        )
        self.assertEqual(
            report["next_legal"],
            [
                "reapprove:understanding",
                "reapprove:direction",
                "reapprove:repository_changes",
            ],
        )

    def test_paused_workflow_can_reapprove_stale_gate_then_resume(self) -> None:
        self.init_to_understanding_gate("run")
        self.approve_understanding()
        self.cli("pause", "--reason", "checkpoint before research")
        self.write(".design/shared-understanding.md", "# Revised while paused\n")

        report = self.cli("verify", expected=2)
        self.assertEqual(report["status"], "paused")
        self.assertEqual(report["next_legal"], ["reapprove:understanding"])

        reapproved = self.approve_understanding()
        self.assertEqual(reapproved["status"], "paused")
        self.assertEqual(reapproved["gates"]["understanding"]["status"], "approved")

        report = self.cli("verify")
        self.assertEqual(report["next_legal"], ["resume"])
        resumed = self.cli("resume", "--reason", "approved revision captured")
        self.assertEqual(resumed["phase"], "understanding_awaiting_approval")
        self.assertEqual(resumed["status"], "awaiting_approval")
        self.transition("researching")

    def test_pause_resume_block_and_unblock_preserve_phase(self) -> None:
        self.cli("init", "--workflow", "run")
        self.transition("interviewing")
        paused = self.cli("pause", "--reason", "intentional checkpoint")
        self.assertEqual(paused["status"], "paused")
        self.transition("understanding_awaiting_approval", expected=1)
        self.cli("block", "--reason", "cannot block paused work", expected=1)
        resumed = self.cli("resume", "--reason", "continue")
        self.assertEqual(resumed["phase"], "interviewing")
        blocked = self.cli("block", "--reason", "missing source")
        self.assertEqual(blocked["phase"], "blocked")
        restored = self.cli("unblock", "--reason", "source supplied")
        self.assertEqual(restored["phase"], "interviewing")
        self.assertEqual(restored["status"], "active")

    def test_corrupted_phase_status_is_rejected_without_rewrite(self) -> None:
        self.cli("init", "--workflow", "run")
        path = self.project / ".design/state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["status"] = "complete"
        corrupted = json.dumps(state, indent=2, sort_keys=True) + "\n"
        path.write_text(corrupted, encoding="utf-8")
        blocked = self.cli("verify", expected=1)
        self.assertIn("cannot have status", blocked["error"])
        self.assertEqual(path.read_text(encoding="utf-8"), corrupted)

    def test_generic_quality_transitions_are_forbidden(self) -> None:
        self.advance_run_to_qa()
        blocked = self.transition("repairing", expected=1)
        self.assertIn("Evidence-bound transition required", blocked["error"])
        state = self.cli("show")
        self.assertEqual(state["phase"], "qa")
        self.assertEqual(state["repair_pass"], 0)

    def test_audit_cannot_repair_without_repository_approval(self) -> None:
        self.init_to_understanding_gate("audit")
        self.approve_understanding()
        self.transition("researching")
        self.transition("qa")
        blocked = self.transition("repairing", expected=1)
        self.assertIn("Evidence-bound transition required", blocked["error"])

        self.transition("implementation_plan_awaiting_approval")
        self.write(".design/implementation/plan.md", "# Audit Repair Plan\n")
        self.cli(
            "record-gate",
            "--gate",
            "repository_changes",
            "--status",
            "approved",
            "--artifact",
            ".design/implementation/plan.md",
            "--decision-text",
            "These repository changes are approved",
        )
        self.transition("building")
        self.enter_rendering_fixture()
        self.enter_qa_fixture()
        blocked = self.transition("repairing", expected=1)
        self.assertIn("begin-repair", blocked["error"])

    def test_artifact_outside_project_is_rejected(self) -> None:
        self.init_to_understanding_gate("run")
        outside = Path(self.tempdir.name).parent / "outside-design-approval.md"
        outside.write_text("outside", encoding="utf-8")
        try:
            blocked = self.cli(
                "record-gate",
                "--gate",
                "understanding",
                "--status",
                "approved",
                "--artifact",
                str(outside),
                "--decision-text",
                "Approved",
                expected=1,
            )
            self.assertIn("inside the project root", blocked["error"])
        finally:
            outside.unlink(missing_ok=True)

    def test_init_rejects_nonexistent_project_root(self) -> None:
        missing = self.project / "missing"
        completed = subprocess.run(
            [
                sys.executable,
                str(STATE_TOOL),
                "init",
                "--project-root",
                str(missing),
                "--workflow",
                "run",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("Project root does not exist", completed.stderr)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
