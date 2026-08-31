#!/usr/bin/env python3
"""Wave 6 regression tests for reference lock, UX, DESIGN.md, tokens, and planning."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core/scripts/design_system.py"
spec = importlib.util.spec_from_file_location("design_system", MODULE_PATH)
system_tool = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(system_tool)

UNDERSTANDING_HASH = "a" * 64


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def role_invariants() -> list[dict]:
    return [
        {
            "domain": "color",
            "source_role": "Accent is reserved for action and focus.",
            "target_role": "Brand accent remains action and focus only.",
            "action": "adapt",
            "reason": "Preserve semantic scarcity while adapting the literal hue.",
        },
        {
            "domain": "media",
            "source_role": "Imagery carries the primary narrative hierarchy.",
            "target_role": "Project imagery remains the narrative carrier.",
            "action": "preserve",
            "reason": "Demoting imagery would collapse the source composition logic.",
        },
        {
            "domain": "density",
            "source_role": "Dense regions support expert scanning and throughput.",
            "target_role": "Operational screens remain compact while narrative screens can open up.",
            "action": "adapt",
            "reason": "Density follows the user task rather than a universal spacious default.",
        },
    ]


def direction_set(understanding_hash: str = UNDERSTANDING_HASH) -> dict:
    return {
        "schema_version": "1.0",
        "approved_understanding_sha256": understanding_hash,
        "mode": "bounded-repair",
        "directions": [
            {
                "id": "A",
                "title": "Direction A",
                "thesis": "A focused product system grounded in the approved brief.",
                "primary_reference": {
                    "slug": "primary-reference",
                    "responsibility": "dominant visual foundation",
                },
                "preserved_primary_traits": [
                    "Primary hierarchy relationship",
                    "Characteristic density behavior",
                    "Source-specific composition logic",
                ],
                "secondary_references": [
                    {
                        "slug": "mobile-reference",
                        "role": "mobile behavior",
                        "scope": "Navigation compression below tablet width only.",
                    }
                ],
                "dimension_signatures": {
                    name: f"focused-{name}" for name in (
                        "composition",
                        "typography",
                        "color",
                        "density",
                        "imagery",
                        "motion",
                        "interaction",
                        "hierarchy",
                        "surfaces",
                    )
                },
                "role_invariants": role_invariants(),
                "signature_traits": [
                    "Distinct hierarchy",
                    "Intentional density",
                    "Bounded color roles",
                ],
                "forbidden_drift": [
                    "Do not replace hierarchy with generic cards.",
                    "Do not round every surface by default.",
                    "Do not turn semantic accent into decoration.",
                ],
                "risks": ["Requires disciplined content and component prioritization."],
                "rejected_alternatives": [
                    {
                        "alternative": "Safe midpoint",
                        "reason": "It averages away the dominant reference relationships.",
                    }
                ],
                "evidence_refs": [{"slug": "primary-reference", "evidence_id": "E1"}],
                "feasibility": "Feasible in the approved environment without new dependencies.",
                "presentation": {
                    "summary": "Focused composition and interaction rules define the result.",
                    "fit": "It matches the approved audience, task density, and product posture.",
                    "risk": "The main risk is losing its sharp primary trait.",
                    "expert_detail": "Full role maps and forensic evidence remain in the artifact.",
                },
            }
        ],
    }


def valid_lock(
    decision_hash: str,
    direction_set_hash: str,
    understanding_hash: str = UNDERSTANDING_HASH,
) -> dict:
    return {
        "schema_version": "1.0",
        "approved_understanding_sha256": understanding_hash,
        "approved_direction": {
            "id": "A",
            "decision_artifact": ".design/directions/decision.md",
            "decision_sha256": decision_hash,
            "direction_set_artifact": ".design/directions/direction-set.json",
            "direction_set_sha256": direction_set_hash,
        },
        "dominant_reference": {
            "slug": "primary-reference",
            "responsibility": "dominant visual foundation",
        },
        "supporting_references": [
            {
                "slug": "mobile-reference",
                "responsibility": "mobile behavior",
                "scope": "Navigation compression below tablet width only.",
            }
        ],
        "frozen_visual_traits": [
            "Primary content owns the dominant canvas.",
            "Utility controls retain compact density.",
            "Accent color remains limited to action and focus.",
        ],
        "allowed_variation": ["Literal brand hue may adapt while keeping its semantic role."],
        "prohibited_drift": [
            "Do not replace hierarchy with a generic card grid.",
            "Do not round every surface by default.",
            "Do not turn the action accent into decoration.",
        ],
        "evidence_links": [
            {"slug": "primary-reference", "evidence_id": "E1"},
            {"slug": "mobile-reference", "evidence_id": "E2"},
        ],
        "assumptions": ["Authenticated edge states remain unavailable."],
        "confidence": "high",
    }


def valid_ux(lock_hash: str) -> dict:
    return {
        "schema_version": "1.0",
        "reference_lock_sha256": lock_hash,
        "information_architecture": [
            {"id": "root", "label": "Product", "purpose": "Own the product structure.", "parent_id": None},
            {"id": "workspace", "label": "Workspace", "purpose": "Contain the primary work area.", "parent_id": "root"},
        ],
        "screens": [
            {
                "id": "home",
                "name": "Home",
                "purpose": "Orient the user and start the primary task.",
                "primary_tasks": ["Start the primary task."],
                "permissions": ["Signed-in project member."],
                "responsive_behavior": "Stack utility controls below the primary canvas on narrow screens.",
            },
            {
                "id": "result",
                "name": "Result",
                "purpose": "Review and confirm the completed result.",
                "primary_tasks": ["Review the result."],
                "permissions": ["Signed-in project member."],
                "responsive_behavior": "Preserve result priority and move secondary metadata below it.",
            },
        ],
        "flows": [
            {
                "id": "primary-flow",
                "name": "Complete the primary task",
                "entry_screen": "home",
                "steps": ["home", "result"],
                "success_outcome": "The user reviews a complete and saved result.",
                "error_paths": ["Return to home with preserved input and a specific recovery action."],
            }
        ],
        "states": [
            {
                "screen_id": screen_id,
                "default": "Ready state with the primary task available.",
                "loading": "Bounded progress appears beside the affected content.",
                "empty": "Explain what is absent and show the primary next action.",
                "error": "Name the failure and preserve a direct recovery action.",
                "permission_denied": "Explain the missing permission and identify its owner.",
            }
            for screen_id in ("home", "result")
        ],
        "responsive_strategy": {
            "mode": "responsive-web",
            "breakpoints": [
                {"name": "base", "min_width_px": 0},
                {"name": "medium", "min_width_px": 720},
                {"name": "wide", "min_width_px": 1200},
            ],
            "content_priority": ["Primary work", "Current status", "Secondary metadata"],
            "adaptation_rules": ["Recompose utility regions around the primary task instead of shrinking every region."],
        },
        "mobile_task_model": {
            "primary_tasks": ["Start, inspect, and confirm the primary result."],
            "deferred_tasks": ["Bulk administration."],
            "device_capabilities": ["Share sheet when the host platform supports it."],
            "offline_requirements": "Retain draft input locally and state when synchronization is pending.",
            "navigation_model": "Use one task-first stack with contextual return actions.",
        },
        "accessibility": {
            "target": "WCAG 2.2 AA",
            "requirements": [
                "All actions are keyboard reachable with visible focus.",
                "Status and errors use text in addition to color.",
                "Names, roles, values, and error recovery are exposed to assistive technology.",
            ],
        },
        "figma_handoff": {
            "mode": "not-applicable",
            "reason": "This test run produces a repository specification only.",
        },
    }


def valid_design(
    lock_hash: str,
    ux_hash: str,
    decision_hash: str,
    understanding_hash: str = UNDERSTANDING_HASH,
) -> dict:
    sections = {
        name: {
            "rules": [f"Apply the approved {name.casefold()} rule without weakening its source role."],
            "evidence_refs": ["E1"],
        }
        for name in system_tool.REQUIRED_DESIGN_SECTIONS
    }
    return {
        "schema_version": "1.0",
        "approved_understanding_sha256": understanding_hash,
        "approved_direction_sha256": decision_hash,
        "reference_lock_sha256": lock_hash,
        "ux_definition_sha256": ux_hash,
        "sections": sections,
    }


def valid_tokens(decision_hash: str) -> dict:
    return {
        "$schema": system_tool.DTCG_SCHEMA,
        "$extensions": {
            system_tool.DESIGN_EXTENSION: {
                "approved_direction_sha256": decision_hash,
                "existing_token_strategy": "new-project",
                "existing_token_map": {},
            }
        },
        "foundation": {
            "color": {
                "$type": "color",
                "ink": {"$value": {"colorSpace": "srgb", "components": [0.1, 0.1, 0.1], "alpha": 1}},
            },
            "space": {
                "$type": "dimension",
                "small": {"$value": {"value": 8, "unit": "px"}},
                "large": {"$value": {"value": 1.5, "unit": "rem"}},
            },
        },
        "semantic": {
            "color": {
                "$type": "color",
                "text": {"$value": "{foundation.color.ink}", "$description": "Default readable text."},
            },
            "space": {
                "$type": "dimension",
                "control": {"$value": "{foundation.space.small}", "$description": "Compact control gap."},
            },
        },
    }


def valid_plan(decision_hash: str, lock_hash: str, ux_hash: str, design_hash: str) -> dict:
    return {
        "schema_version": "1.0",
        "approved_direction_sha256": decision_hash,
        "reference_lock_sha256": lock_hash,
        "ux_definition_sha256": ux_hash,
        "design_md_sha256": design_hash,
        "quality_targets": [
            {
                "id": "home-default-small", "screen_id": "home", "route": "/", "state": "default",
                "viewport": {"name": "small", "width": 390, "height": 844, "device_scale_factor": 1},
                "theme": "light", "reduced_motion": True, "required": True,
            }
        ],
        "repository_change_gate": "awaiting_approval",
        "goal": "Implement the approved product interface in two bounded waves.",
        "prohibited_scope": ["Deployment and external publication."],
        "waves": [
            {
                "id": "foundation",
                "dependencies": [],
                "goal": "Install approved local tokens and structural primitives.",
                "inputs": ["Approved reference lock, DESIGN.md, and token projections."],
                "approved_requirements": ["Use only approved semantic tokens and structural rules."],
                "design_sections": ["Tokens and variables", "Layout system"],
                "allowed_files": ["src/styles", "src/components/layout"],
                "work_items": ["Map approved tokens into the existing project conventions."],
                "render_targets": ["Desktop and mobile shell states."],
                "tests": ["Run token, layout, and accessibility checks."],
                "completion_criteria": ["Both shells render from approved tokens without prohibited drift."],
                "rollback": ["Revert the foundation wave commit."],
                "risks": ["Existing token aliases may require an explicit mapping decision."],
                "status": "planned",
            },
            {
                "id": "primary-flow",
                "dependencies": ["foundation"],
                "goal": "Implement and render the approved primary user flow.",
                "inputs": ["Completed foundation handoff and approved UX definition."],
                "approved_requirements": ["Implement every approved state and recovery path."],
                "design_sections": ["Information architecture", "Interaction states"],
                "allowed_files": ["src/routes", "src/components/flow"],
                "work_items": ["Build default, loading, empty, error, and denied states."],
                "render_targets": ["Desktop, tablet, and mobile primary flow states."],
                "tests": ["Run interaction, responsive, visual, and accessibility checks."],
                "completion_criteria": ["Every approved state and recovery path passes its direct check."],
                "rollback": ["Revert the primary-flow wave commit."],
                "risks": ["Missing product behavior may require a return to shared understanding."],
                "status": "planned",
            },
        ],
        "external_actions": [
            {"action": "Deploy the approved implementation.", "approval": "separate-required"}
        ],
        "approval_artifact": ".design/implementation/plan.md",
    }


def build_artifacts(root: Path) -> dict[str, Path]:
    understanding = root / ".design/shared-understanding.md"
    understanding.parent.mkdir(parents=True, exist_ok=True)
    understanding.write_text("# Shared understanding\n\nApproved test scope.\n", encoding="utf-8")
    understanding_hash = system_tool.sha256(understanding)
    decision = root / ".design/directions/decision.md"
    direction_set_path = root / ".design/directions/direction-set.json"
    decision.parent.mkdir(parents=True, exist_ok=True)
    decision.write_text("# Approved direction\n\nDirection A is approved.\n", encoding="utf-8")
    write_json(direction_set_path, direction_set(understanding_hash))

    lock_path = root / ".design/system/reference-lock.json"
    write_json(
        lock_path,
        valid_lock(
            system_tool.sha256(decision),
            system_tool.sha256(direction_set_path),
            understanding_hash,
        ),
    )

    ux_path = root / ".design/system/ux-definition.json"
    write_json(ux_path, valid_ux(system_tool.sha256(lock_path)))

    system_path = root / ".design/system/design-system.json"
    payload = valid_design(
        system_tool.sha256(lock_path),
        system_tool.sha256(ux_path),
        system_tool.sha256(decision),
        understanding_hash,
    )
    write_json(system_path, payload)
    design_md = root / "DESIGN.md"
    design_md.write_text(system_tool.compile_design_markdown(payload), encoding="utf-8")

    tokens_path = root / ".design/system/tokens.source.json"
    write_json(tokens_path, valid_tokens(system_tool.sha256(decision)))

    plan_path = root / ".design/implementation/plan.json"
    plan_payload = valid_plan(system_tool.sha256(decision), system_tool.sha256(lock_path), system_tool.sha256(ux_path), system_tool.sha256(design_md))
    write_json(plan_path, plan_payload)
    plan_md_path = root / ".design/implementation/plan.md"
    plan_md_path.write_text(system_tool.compile_plan_markdown(plan_payload), encoding="utf-8")
    state = {
        "schema_version": "1.0",
        "plugin": "design",
        "revision": 0,
        "workflow": "run",
        "route": "standard",
        "phase": "system_definition",
        "status": "active",
        "phase_before_block": None,
        "gates": {
            "understanding": {
                "gate": "understanding",
                "status": "approved",
                "artifact_path": ".design/shared-understanding.md",
                "artifact_sha256": understanding_hash,
                "decided_at": "2026-08-30T00:00:00Z",
                "decision_text": "Approved",
                "warning_acknowledged": False,
                "scope": "Approved test scope.",
                "assumptions_accepted": [],
                "stale_reason": None,
                "stale_at": None,
            },
            "direction": {
                "gate": "direction",
                "status": "approved",
                "artifact_path": ".design/directions/decision.md",
                "artifact_sha256": system_tool.sha256(decision),
                "decided_at": "2026-08-30T00:00:00Z",
                "decision_text": "This direction is approved",
                "warning_acknowledged": False,
                "scope": "Approved direction A.",
                "assumptions_accepted": [],
                "stale_reason": None,
                "stale_at": None,
            },
            "repository_changes": None,
        },
        "artifacts": {
            ".design/shared-understanding.md": understanding_hash,
            ".design/directions/decision.md": system_tool.sha256(decision),
            ".design/directions/direction-set.json": system_tool.sha256(direction_set_path),
        },
        "active_wave": None,
        "repair_cycle": 0,
        "repair_pass": 0,
        "repair_attempts": {},
        "blockers": [],
        "history": [{"event": "test_system_definition_fixture", "at": "2026-08-30T00:00:00Z"}],
        "created_at": "2026-08-30T00:00:00Z",
        "updated_at": "2026-08-30T00:00:00Z",
    }
    write_json(root / ".design/state.json", state)
    return {
        "understanding": understanding,
        "state": root / ".design/state.json",
        "decision": decision,
        "direction_set": direction_set_path,
        "lock": lock_path,
        "ux": ux_path,
        "system": system_path,
        "design_md": design_md,
        "tokens": tokens_path,
        "token_output": root / ".design/system/generated-tokens",
        "plan": plan_path,
        "plan_md": plan_md_path,
    }


class Wave6SystemDefinitionTests(unittest.TestCase):
    def test_schemas_and_json_templates_parse(self) -> None:
        for path in [*sorted((ROOT / "core/schemas").glob("*.json")), *sorted((ROOT / "core/templates").glob("*.json"))]:
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_exit_gate_validates_complete_bound_artifact_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            report = system_tool.verify_wave6(
                paths["lock"], paths["decision"], paths["direction_set"], paths["ux"],
                paths["system"], paths["design_md"], paths["tokens"], paths["token_output"], paths["plan"], paths["plan_md"],
            )
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["repository_change_gate"], "awaiting_approval")
            self.assertEqual(report["implementation_waves"], 2)

    def test_reference_lock_rejects_changed_direction_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            paths["decision"].write_text("changed", encoding="utf-8")
            with self.assertRaises(system_tool.ValidationError):
                system_tool.validate_reference_lock(json.loads(paths["lock"].read_text()), paths["decision"], paths["direction_set"])

    def test_reference_lock_rejects_broad_supporting_role(self) -> None:
        item = valid_lock("b" * 64, "c" * 64)
        item["supporting_references"][0]["responsibility"] = "overall style"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_reference_lock(item)

    def test_reference_lock_must_match_approved_primary_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            item = json.loads(paths["lock"].read_text())
            item["dominant_reference"]["slug"] = "different-primary"
            with self.assertRaises(system_tool.ValidationError):
                system_tool.validate_reference_lock(item, paths["decision"], paths["direction_set"])

    def test_ux_requires_states_for_every_screen(self) -> None:
        item = valid_ux("d" * 64)
        item["states"].pop()
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_ux_definition(item)

    def test_ux_rejects_unknown_flow_screen(self) -> None:
        item = valid_ux("d" * 64)
        item["flows"][0]["steps"].append("missing")
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_ux_definition(item)

    def test_ux_requires_accessibility_requirements(self) -> None:
        item = valid_ux("d" * 64)
        item["accessibility"]["requirements"] = []
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_ux_definition(item)

    def test_design_system_rejects_missing_canonical_section(self) -> None:
        item = valid_design("e" * 64, "f" * 64, "1" * 64)
        del item["sections"][system_tool.REQUIRED_DESIGN_SECTIONS[-1]]
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_design_system(item)

    def test_design_markdown_requires_exact_heading_order(self) -> None:
        item = valid_design("e" * 64, "f" * 64, "1" * 64)
        text = system_tool.compile_design_markdown(item)
        system_tool.validate_design_markdown(text)
        altered = text.replace("## Typography", "## Typography changed")
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_design_markdown(altered)

    def test_tokens_require_stable_dtcg_schema(self) -> None:
        item = valid_tokens("2" * 64)
        item["$schema"] = "https://example.com/unstable.json"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_tokens_require_design_binding_extension(self) -> None:
        item = valid_tokens("2" * 64)
        del item["$extensions"][system_tool.DESIGN_EXTENSION]
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_token_map_strategy_requires_entries(self) -> None:
        item = valid_tokens("2" * 64)
        item["$extensions"][system_tool.DESIGN_EXTENSION]["existing_token_strategy"] = "map"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_tokens_require_documented_semantic_roles(self) -> None:
        item = valid_tokens("2" * 64)
        del item["semantic"]
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_stable_dtcg_color_spaces_compile_without_srgb_flattening(self) -> None:
        item = valid_tokens("2" * 64)
        item["foundation"]["color"]["wide"] = {
            "$value": {"colorSpace": "display-p3", "components": [0.9, 0.2, 0.1], "alpha": 1}
        }
        item["foundation"]["color"]["perceptual"] = {
            "$value": {"colorSpace": "oklch", "components": [0.65, 0.18, 35], "alpha": 0.8}
        }
        with tempfile.TemporaryDirectory() as directory:
            system_tool.compile_token_outputs(item, directory)
            css = (Path(directory) / "variables.css").read_text()
            self.assertIn("color(display-p3 0.9 0.2 0.1)", css)
            self.assertIn("oklch(0.65 0.18 35 / 0.8)", css)

    def test_dtcg_color_component_ranges_are_enforced(self) -> None:
        item = valid_tokens("2" * 64)
        item["foundation"]["color"]["ink"]["$value"] = {
            "colorSpace": "hsl",
            "components": [360, 50, 50],
            "alpha": 1,
        }
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_unknown_token_alias_is_rejected(self) -> None:
        item = valid_tokens("2" * 64)
        item["semantic"]["color"]["text"]["$value"] = "{foundation.color.missing}"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_token_alias_cycle_is_rejected(self) -> None:
        item = valid_tokens("2" * 64)
        item["foundation"]["space"]["small"]["$value"] = "{foundation.space.large}"
        item["foundation"]["space"]["large"]["$value"] = "{foundation.space.small}"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_token_source(item)

    def test_token_compiler_writes_all_deterministic_projections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = system_tool.compile_token_outputs(valid_tokens("2" * 64), directory)
            outputs = {path.name for path in Path(directory).iterdir()}
            self.assertEqual(outputs, set(report["outputs"]))
            self.assertEqual(report["semantic_token_count"], 2)
            css = (Path(directory) / "variables.css").read_text()
            self.assertIn("var(--design-foundation-color-ink)", css)

    def test_mobile_projection_marks_px_direct_and_rem_estimated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            system_tool.compile_token_outputs(valid_tokens("2" * 64), directory)
            mobile = json.loads((Path(directory) / "mobile.json").read_text())["tokens"]
            self.assertEqual(mobile["foundation.space.small"]["android"]["confidence"], "high")
            self.assertEqual(mobile["foundation.space.large"]["ios"]["confidence"], "estimated")
            self.assertEqual(mobile["foundation.space.large"]["ios"]["value"], 24)

    def test_plan_cannot_self_approve_repository_change(self) -> None:
        item = valid_plan("3" * 64, "4" * 64, "5" * 64, "6" * 64)
        item["repository_change_gate"] = "approved"
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_implementation_plan(item)

    def test_plan_rejects_dependency_on_later_wave(self) -> None:
        item = valid_plan("3" * 64, "4" * 64, "5" * 64, "6" * 64)
        item["waves"][0]["dependencies"] = ["primary-flow"]
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_implementation_plan(item)

    def test_plan_rejects_path_traversal(self) -> None:
        item = valid_plan("3" * 64, "4" * 64, "5" * 64, "6" * 64)
        item["waves"][0]["allowed_files"] = ["../outside"]
        with self.assertRaises(system_tool.ValidationError):
            system_tool.validate_implementation_plan(item)

    def test_aggregate_gate_rejects_changed_upstream_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            payload = json.loads(paths["system"].read_text())
            payload["approved_direction_sha256"] = "9" * 64
            write_json(paths["system"], payload)
            with self.assertRaises(system_tool.ValidationError):
                system_tool.verify_wave6(
                    paths["lock"], paths["decision"], paths["direction_set"], paths["ux"],
                    paths["system"], paths["design_md"], paths["tokens"], paths["token_output"], paths["plan"], paths["plan_md"],
                )

    def test_wave6_rejects_invented_direction_set_gate_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            state = json.loads(paths["state"].read_text())
            state["artifacts"][".design/directions/direction-set.json"] = "f" * 64
            write_json(paths["state"], state)
            with self.assertRaisesRegex(system_tool.ValidationError, "current direction-set hash"):
                system_tool.verify_wave6(
                    paths["lock"], paths["decision"], paths["direction_set"], paths["ux"],
                    paths["system"], paths["design_md"], paths["tokens"], paths["token_output"],
                    paths["plan"], paths["plan_md"],
                )

    def test_cli_verifies_complete_wave6_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "verify-wave6",
                    "--lock", str(paths["lock"]),
                    "--decision", str(paths["decision"]),
                    "--direction-set", str(paths["direction_set"]),
                    "--ux", str(paths["ux"]),
                    "--system", str(paths["system"]),
                    "--design-md", str(paths["design_md"]),
                    "--tokens", str(paths["tokens"]),
                    "--token-output-dir", str(paths["token_output"]),
                    "--plan", str(paths["plan"]),
                    "--plan-md", str(paths["plan_md"]),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(json.loads(completed.stdout)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
