#!/usr/bin/env python3
"""Regression tests for Design Wave 2 durable state and approval gates."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core/scripts/design_state.py"
SPEC = importlib.util.spec_from_file_location("design_state", SCRIPT)
assert SPEC and SPEC.loader
state_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state_tool)
T0 = "2026-08-30T20:00:00Z"


class StateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def ns(self, **values: object) -> argparse.Namespace:
        defaults: dict[str, object] = {
            "project_root": str(self.project),
            "at": T0,
            "workflow": "run",
            "route": "standard",
            "to": None,
            "reason": "test",
            "gate": None,
            "status": None,
            "artifact": None,
            "decision_text": None,
            "warning_acknowledged": False,
            "scope": "",
            "assumption": [],
        }
        defaults.update(values)
        return argparse.Namespace(**defaults)

    def init(self, workflow: str = "run") -> dict:
        return state_tool.command_init(self.ns(workflow=workflow))

    def transition(self, target: str, reason: str = "test", at: str = T0) -> dict:
        return state_tool.command_transition(self.ns(to=target, reason=reason, at=at))

    def write(self, relative: str, content: str) -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def enter_rendering_fixture(self) -> None:
        state = state_tool.command_show(self.ns())
        self.assertEqual(state["phase"], "building")
        state["phase"] = "rendering"
        state["status"] = "active"
        state["active_wave"] = None
        state_tool.append_history(state, "test_fixture", T0)
        state_tool.save_state(self.project, state, T0)

    def enter_qa_fixture(self) -> None:
        state = state_tool.command_show(self.ns())
        self.assertEqual(state["phase"], "rendering")
        state["phase"] = "qa"
        state["status"] = "active"
        state_tool.append_history(state, "test_quality_fixture", T0)
        state_tool.save_state(self.project, state, T0)

    def advance_to_understanding_gate(self) -> None:
        self.init()
        self.transition("interviewing")
        self.transition("understanding_awaiting_approval")

    def approve_understanding(self, status: str = "approved", warning: bool = False) -> dict:
        self.write(".design/shared-understanding.md", "# Shared Understanding\n\nApproved scope.\n")
        return state_tool.command_record_gate(
            self.ns(
                gate="understanding",
                status=status,
                artifact=".design/shared-understanding.md",
                decision_text="Approved" if status == "approved" else "Skip and proceed",
                warning_acknowledged=warning,
            )
        )

    def advance_standard_to_direction_gate(self) -> None:
        self.advance_to_understanding_gate()
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")

    def approve_direction(self) -> dict:
        self.write(".design/directions/decision.md", "# Direction Decision\n\nDirection 2 selected.\n")
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-2"}]}\n')
        return state_tool.command_record_gate(
            self.ns(
                gate="direction",
                status="approved",
                artifact=".design/directions/decision.md",
                decision_text="This direction is approved",
            )
        )

    def advance_to_repository_gate(self) -> None:
        self.advance_standard_to_direction_gate()
        self.approve_direction()
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")

    def approve_repository_changes(self) -> dict:
        self.write(".design/implementation/plan.md", "# Implementation Plan\n\nWave 1.\n")
        return state_tool.command_record_gate(
            self.ns(
                gate="repository_changes",
                status="approved",
                artifact=".design/implementation/plan.md",
                decision_text="These repository changes are approved",
            )
        )

    def test_init_and_legal_transition(self) -> None:
        state = self.init()
        self.assertEqual(state["phase"], "intake")
        state = self.transition("interviewing")
        self.assertEqual(state["phase"], "interviewing")
        self.assertEqual(state["revision"], 1)

    def test_illegal_transition_is_blocked_without_state_change(self) -> None:
        self.init()
        with self.assertRaisesRegex(state_tool.StateError, "Illegal transition"):
            self.transition("researching")
        state = state_tool.command_show(self.ns())
        self.assertEqual(state["phase"], "intake")

    def test_understanding_gate_is_required(self) -> None:
        self.advance_to_understanding_gate()
        with self.assertRaisesRegex(state_tool.StateError, "understanding gate"):
            self.transition("researching")

    def test_understanding_approval_phrase_and_transition(self) -> None:
        self.advance_to_understanding_gate()
        artifact = self.write(".design/shared-understanding.md", "approved scope")
        with self.assertRaisesRegex(state_tool.StateError, "must be 'Approved'"):
            state_tool.command_record_gate(
                self.ns(
                    gate="understanding",
                    status="approved",
                    artifact=str(artifact),
                    decision_text="Looks good",
                )
            )
        self.approve_understanding()
        state = self.transition("researching")
        self.assertEqual(state["phase"], "researching")

    def test_gate_artifacts_and_decisions_are_bound_to_their_authority(self) -> None:
        self.advance_to_understanding_gate()
        self.write("unrelated.txt", "not the shared understanding\n")
        with self.assertRaisesRegex(state_tool.StateError, "canonical artifact"):
            state_tool.command_record_gate(
                self.ns(
                    gate="understanding",
                    status="approved",
                    artifact="unrelated.txt",
                    decision_text="Approved",
                )
            )
        self.approve_understanding()
        self.transition("researching")
        self.transition("directions_awaiting_approval")
        self.write(".design/directions/decision.md", "# Direction\n")
        direction_set = self.write(
            ".design/directions/direction-set.json",
            '{"directions": [{"id": "direction-1"}]}\n',
        )
        self.write("notes.txt", "unrelated direction notes\n")
        with self.assertRaisesRegex(state_tool.StateError, "canonical artifact"):
            state_tool.command_record_gate(
                self.ns(
                    gate="direction",
                    status="approved",
                    artifact="notes.txt",
                    decision_text="This direction is approved",
                )
            )
        with self.assertRaisesRegex(state_tool.StateError, "approval decision"):
            state_tool.command_record_gate(
                self.ns(
                    gate="direction",
                    status="approved",
                    artifact=".design/directions/decision.md",
                    decision_text="Reject every direction",
                )
            )
        approved = state_tool.command_record_gate(
            self.ns(
                gate="direction",
                status="approved",
                artifact=".design/directions/decision.md",
                decision_text="Direction approved",
            )
        )
        self.assertEqual(
            approved["artifacts"][".design/directions/direction-set.json"],
            state_tool.sha256(direction_set),
        )
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        self.write(".design/implementation/plan.md", "# Plan\n")
        self.write("notes.txt", "unrelated plan notes\n")
        with self.assertRaisesRegex(state_tool.StateError, "canonical artifact"):
            state_tool.command_record_gate(
                self.ns(
                    gate="repository_changes",
                    status="approved",
                    artifact="notes.txt",
                    decision_text="These repository changes are approved",
                )
            )
        with self.assertRaisesRegex(state_tool.StateError, "approval decision"):
            state_tool.command_record_gate(
                self.ns(
                    gate="repository_changes",
                    status="approved",
                    artifact=".design/implementation/plan.md",
                    decision_text="Do not make repository changes",
                )
            )
        state_tool.command_record_gate(
            self.ns(
                gate="repository_changes",
                status="approved",
                artifact=".design/implementation/plan.md",
                decision_text="Repository changes approved",
            )
        )
        self.assertEqual(self.transition("building")["active_wave"], 1)

    def test_changed_bound_direction_set_makes_direction_gate_stale(self) -> None:
        self.advance_standard_to_direction_gate()
        self.approve_direction()
        self.write(".design/directions/direction-set.json", '{"directions": [{"id": "direction-3"}]}\n')
        with self.assertRaisesRegex(state_tool.StateError, "Stale approval gates"):
            self.transition("system_definition")

    def test_skip_requires_warning_acknowledgement(self) -> None:
        self.advance_to_understanding_gate()
        self.write(".design/shared-understanding.md", "assumptions recorded")
        with self.assertRaisesRegex(state_tool.StateError, "risk warning"):
            state_tool.command_record_gate(
                self.ns(
                    gate="understanding",
                    status="skipped",
                    artifact=".design/shared-understanding.md",
                    decision_text="Skip and proceed",
                )
            )
        self.approve_understanding(status="skipped", warning=True)
        state = self.transition("researching")
        self.assertEqual(state["phase"], "researching")

    def test_changed_artifact_marks_gate_stale_and_blocks(self) -> None:
        self.advance_to_understanding_gate()
        self.approve_understanding()
        self.write(".design/shared-understanding.md", "changed after approval")
        report, code = state_tool.command_verify(self.ns(at="2026-08-30T20:01:00Z"))
        self.assertEqual(code, 2)
        self.assertEqual(report["stale_gates"], ["understanding"])
        with self.assertRaisesRegex(state_tool.StateError, "Stale approval gates detected"):
            self.transition("researching")

    def test_stale_gate_can_be_reapproved_in_later_phase_and_cascades(self) -> None:
        self.advance_to_repository_gate()
        self.approve_repository_changes()
        self.transition("building")
        self.write(".design/shared-understanding.md", "materially changed scope")
        report, code = state_tool.command_verify(self.ns(at="2026-08-30T20:02:00Z"))
        self.assertEqual(code, 2)
        self.assertEqual(
            set(report["stale_gates"]),
            {"understanding", "direction", "repository_changes"},
        )
        state_tool.command_record_gate(
            self.ns(
                gate="understanding",
                status="approved",
                artifact=".design/shared-understanding.md",
                decision_text="This understanding is approved",
                at="2026-08-30T20:03:00Z",
            )
        )
        state = state_tool.command_show(self.ns())
        self.assertEqual(state["gates"]["understanding"]["status"], "approved")
        self.assertEqual(state["gates"]["direction"]["status"], "stale")
        self.assertEqual(state["gates"]["repository_changes"]["status"], "stale")

    def test_direction_and_repository_gates_are_enforced(self) -> None:
        self.advance_standard_to_direction_gate()
        with self.assertRaisesRegex(state_tool.StateError, "direction gate"):
            self.transition("system_definition")
        self.approve_direction()
        self.transition("system_definition")
        self.transition("implementation_plan_awaiting_approval")
        with self.assertRaisesRegex(state_tool.StateError, "repository_changes gate"):
            self.transition("building")
        self.approve_repository_changes()
        state = self.transition("building")
        self.assertEqual(state["active_wave"], 1)

    def test_pause_and_resume_preserve_phase(self) -> None:
        self.init()
        self.transition("interviewing")
        state = state_tool.command_pause(self.ns(reason="session ended"))
        self.assertEqual(state["status"], "paused")
        state = state_tool.command_resume(self.ns(reason="continue"))
        self.assertEqual(state["phase"], "interviewing")
        self.assertEqual(state["status"], "active")

    def test_block_and_unblock_restore_phase(self) -> None:
        self.init()
        self.transition("interviewing")
        state = state_tool.command_block(self.ns(reason="missing source"))
        self.assertEqual(state["phase"], "blocked")
        state = state_tool.command_unblock(self.ns(reason="source supplied"))
        self.assertEqual(state["phase"], "interviewing")
        self.assertEqual(state["blockers"][-1]["resolution"], "source supplied")

    def test_audit_route_skips_direction_phase(self) -> None:
        self.init(workflow="audit")
        self.transition("interviewing")
        self.transition("understanding_awaiting_approval")
        self.approve_understanding()
        self.transition("researching")
        state = self.transition("qa")
        self.assertEqual(state["workflow"], "audit")
        self.assertEqual(state["phase"], "qa")

    def test_generic_quality_transition_is_rejected(self) -> None:
        self.advance_to_repository_gate()
        self.approve_repository_changes()
        self.transition("building")
        self.enter_rendering_fixture()
        with self.assertRaisesRegex(state_tool.StateError, "Evidence-bound transition required"):
            self.transition("qa")
        self.enter_qa_fixture()
        with self.assertRaisesRegex(state_tool.StateError, "begin-repair"):
            self.transition("repairing")

    def test_existing_stale_gate_blocks_later_non_gated_transition(self) -> None:
        self.advance_to_repository_gate()
        self.approve_repository_changes()
        self.transition("building")
        self.write(".design/shared-understanding.md", "changed after build approval")
        report, code = state_tool.command_verify(self.ns(at="2026-08-30T20:10:00Z"))
        self.assertEqual(code, 2)
        self.assertIn("understanding", report["stale_gates"])
        with self.assertRaisesRegex(state_tool.StateError, "Stale approval gates detected"):
            self.transition("rendering", at="2026-08-30T20:11:00Z")
        state = state_tool.command_show(self.ns())
        self.assertEqual(state["phase"], "building")

    def test_verify_reports_already_stale_gates(self) -> None:
        self.advance_to_understanding_gate()
        self.approve_understanding()
        self.write(".design/shared-understanding.md", "changed")
        first, first_code = state_tool.command_verify(self.ns(at="2026-08-30T20:12:00Z"))
        second, second_code = state_tool.command_verify(self.ns(at="2026-08-30T20:13:00Z"))
        self.assertEqual(first_code, 2)
        self.assertEqual(second_code, 2)
        self.assertEqual(first["stale_gates"], ["understanding"])
        self.assertEqual(second["stale_gates"], ["understanding"])

    def test_resume_rejects_preexisting_stale_gate(self) -> None:
        self.advance_to_understanding_gate()
        self.approve_understanding()
        self.transition("researching")
        state_tool.command_pause(self.ns(reason="pause before source change"))
        self.write(".design/shared-understanding.md", "changed while paused")
        with self.assertRaisesRegex(state_tool.StateError, "Cannot resume with stale approval gates"):
            state_tool.command_resume(self.ns(reason="continue", at="2026-08-30T20:14:00Z"))
        with self.assertRaisesRegex(state_tool.StateError, "Cannot resume with stale approval gates"):
            state_tool.command_resume(self.ns(reason="retry", at="2026-08-30T20:15:00Z"))

    def test_corrupt_state_is_not_overwritten(self) -> None:
        path = self.project / ".design/state.json"
        path.parent.mkdir(parents=True)
        original = "{not-json\n"
        path.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(state_tool.StateError, "corrupted JSON"):
            state_tool.command_verify(self.ns())
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_artifact_outside_project_is_rejected(self) -> None:
        self.advance_to_understanding_gate()
        outside = Path(self.temp.name).parent / "outside-design-test.md"
        outside.write_text("outside", encoding="utf-8")
        try:
            with self.assertRaisesRegex(state_tool.StateError, "inside the project root"):
                state_tool.command_record_gate(
                    self.ns(
                        gate="understanding",
                        status="approved",
                        artifact=str(outside),
                        decision_text="Approved",
                    )
                )
        finally:
            outside.unlink(missing_ok=True)

    def test_existing_state_is_not_overwritten(self) -> None:
        first = self.init()
        with self.assertRaisesRegex(state_tool.StateError, "State already exists"):
            self.init()
        current = json.loads((self.project / ".design/state.json").read_text())
        self.assertEqual(current, first)


if __name__ == "__main__":
    unittest.main()
