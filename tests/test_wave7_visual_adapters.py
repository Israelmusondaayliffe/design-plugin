#!/usr/bin/env python3
"""Wave 7 regression tests for imagery, Figma, and mobile adapters."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_wave6_system_definition import build_artifacts as build_wave6_artifacts

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core/scripts/design_adapters.py"
spec = importlib.util.spec_from_file_location("design_adapters", MODULE_PATH)
adapters = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(adapters)

FIGMA_ACTIONS = [
    {
        "id": "create-approved-structure",
        "description": "Create the listed frames, variables, and components.",
        "target": "Approved page and named nodes",
        "destructive": False,
    }
]


def load_template(name: str, *, ready: bool = True) -> dict:
    item = json.loads((ROOT / "core/templates" / name).read_text(encoding="utf-8"))
    if ready and "artifact_status" in item:
        item["artifact_status"] = "ready"
    return item


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def approved_batch(approval_path: Path) -> dict:
    item = load_template("imagery-plan.template.json")
    item["assets"][0]["type"] = "production-bitmap"
    item["generation_boundary"] = {
        "purpose": "production-batch",
        "status": "awaiting-approval",
        "output_ceiling": 1,
        "request_sha256": None,
        "approval_artifact": None,
        "approval_sha256": None,
    }
    authorize_imagery(item, approval_path)
    return item


def authorize_imagery(item: dict, approval_path: Path) -> None:
    item["generation_boundary"].update(
        {
            "status": "awaiting-approval",
            "request_sha256": None,
            "approval_artifact": None,
            "approval_sha256": None,
        }
    )
    item["generation_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
        adapters.imagery_generation_request_payload(item)
    )
    write_imagery_approval(approval_path, item)
    item["generation_boundary"].update(
        {
            "status": "approved",
            "approval_artifact": ".design/imagery/generation-approval.md",
            "approval_sha256": adapters.sha256(approval_path),
        }
    )


def direct_figma(approval_path: Path, root: Path) -> dict:
    item = load_template("figma-handoff.template.json")
    report = root / ".design/environment-capabilities.json"
    write_json(
        report,
        {
            "schema_version": "1.0",
            "artifact_status": "ready",
            "inspected_at": "2026-08-30T00:00:00Z",
            "inspector": "test-host-agent",
            "surfaces": ["Host-visible connected tools."],
            "figma": {
                "status": "available-authorized",
                "provider": "Host Figma connector",
                "evidence": ["A compatible authenticated connection is visible."],
            },
        },
    )
    item["capability"] = {
        "status": "available-authorized",
        "provider": "Host Figma connector",
        "environment_report_path": ".design/environment-capabilities.json",
        "environment_report_sha256": adapters.sha256(report),
        "checked_surfaces": ["Host-visible connected tools."],
        "evidence": ["A compatible authenticated connection is visible."],
        "bundled_mcp_required": False,
    }
    item["mode"] = "direct-when-authorized"
    item["target_file"] = "figma-file-key:approved-design-file"
    item["destructive_action_classification"] = "non-destructive"
    item["direct_actions"] = copy.deepcopy(FIGMA_ACTIONS)
    item["external_write_boundary"] = {
        "status": "awaiting-approval",
        "request_sha256": None,
        "approval_artifact": None,
        "approval_sha256": None,
    }
    authorize_figma(item, approval_path)
    return item


def authorize_figma(item: dict, approval_path: Path) -> None:
    item["external_write_boundary"].update(
        {
            "status": "awaiting-approval",
            "request_sha256": None,
            "approval_artifact": None,
            "approval_sha256": None,
        }
    )
    item["external_write_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
        adapters.figma_write_request_payload(item)
    )
    write_figma_approval(approval_path, item)
    item["external_write_boundary"].update(
        {
            "status": "approved",
            "approval_artifact": ".design/handoff/figma-approval.md",
            "approval_sha256": adapters.sha256(approval_path),
        }
    )


def write_imagery_approval(
    path: Path,
    item: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        adapters.imagery_generation_approval_text(item),
        encoding="utf-8",
    )


def write_figma_approval(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        adapters.figma_write_approval_text(item),
        encoding="utf-8",
    )


def responsive_mobile() -> dict:
    item = load_template("mobile-decision.template.json")
    item["requirements"][0]["compatibility"] = {
        "responsive-web": True,
        "cross-platform": True,
        "native-mobile": True,
    }
    item["routing_result"] = {
        "status": "recommendation",
        "selected": "responsive-web",
        "simplest_valid": True,
        "rationale": "Responsive web is the simplest option that satisfies the supplied hard compatibility evidence.",
        "questions": [],
        "framework_decision": {
            "status": "deferred",
            "name": None,
            "reason": "Framework selection remains separate from the supported platform path.",
        },
    }
    return item


def build_artifacts(root: Path) -> dict[str, Path]:
    paths = build_wave6_artifacts(root)
    lock = json.loads(paths["lock"].read_text())

    imagery = load_template("imagery-plan.template.json")
    imagery["approved_direction_sha256"] = lock["approved_direction"]["decision_sha256"]
    imagery["reference_lock_sha256"] = adapters.sha256(paths["lock"])
    imagery["design_md_sha256"] = adapters.sha256(paths["design_md"])
    imagery_path = root / ".design/imagery/plan.json"
    write_json(imagery_path, imagery)

    figma = load_template("figma-handoff.template.json")
    figma["design_md_sha256"] = adapters.sha256(paths["design_md"])
    figma["tokens_source_sha256"] = adapters.sha256(paths["tokens"])
    figma_path = root / ".design/handoff/figma.json"
    write_json(figma_path, figma)

    mobile = responsive_mobile()
    mobile["approved_understanding_sha256"] = lock["approved_understanding_sha256"]
    mobile["ux_definition_sha256"] = adapters.sha256(paths["ux"])
    mobile["design_md_sha256"] = adapters.sha256(paths["design_md"])
    mobile_path = root / ".design/mobile/decision.json"
    write_json(mobile_path, mobile)
    return {
        **paths,
        "imagery": imagery_path,
        "figma": figma_path,
        "mobile": mobile_path,
    }


def verify_artifacts(paths: dict[str, Path]) -> dict:
    return adapters.verify_wave7(
        paths["lock"],
        paths["design_md"],
        paths["tokens"],
        paths["ux"],
        paths["imagery"],
        paths["figma"],
        paths["mobile"],
        paths["decision"],
        paths["direction_set"],
        paths["system"],
        paths["token_output"],
        paths["plan"],
        paths["plan_md"],
    )


class Wave7VisualAdapterTests(unittest.TestCase):
    def test_schemas_and_templates_parse_and_validate(self) -> None:
        for path in sorted((ROOT / "core/schemas").glob("*.json")):
            with self.subTest(schema=path.name):
                self.assertIsInstance(json.loads(path.read_text()), dict)
        for name, validator in (
            ("imagery-plan.template.json", adapters.validate_imagery_plan),
            ("image-edit.template.json", adapters.validate_image_edit),
            ("figma-handoff.template.json", adapters.validate_figma_handoff),
            ("mobile-decision.template.json", adapters.validate_mobile_decision),
        ):
            with self.subTest(scaffold=name), self.assertRaises(adapters.ValidationError):
                validator(load_template(name, ready=False))
        adapters.validate_imagery_plan(load_template("imagery-plan.template.json"))
        adapters.validate_figma_handoff(load_template("figma-handoff.template.json"))
        adapters.validate_mobile_decision(load_template("mobile-decision.template.json"))

    def test_prompt_only_imagery_compiles_without_claiming_generation(self) -> None:
        item = load_template("imagery-plan.template.json")
        text = adapters.compile_imagery_prompts(item)
        self.assertIn("Generation status: `not-required`", text)
        self.assertIn("does not generate assets", text)
        self.assertIn("### GPT Image 2 prompt", text)

    def test_non_bitmap_medium_cannot_authorize_bitmap_batch(self) -> None:
        item = load_template("imagery-plan.template.json")
        item["medium_decision"]["selected"] = "code-native"
        item["generation_boundary"] = {
            "purpose": "production-batch",
            "status": "awaiting-approval",
            "output_ceiling": 1,
            "request_sha256": "0" * 64,
            "approval_artifact": None,
            "approval_sha256": None,
        }
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_direction_board_generation_requires_approval_state(self) -> None:
        item = load_template("imagery-plan.template.json")
        item["generation_boundary"]["purpose"] = "direction-board"
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_approved_generation_batch_binds_approval_and_output_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/imagery/generation-approval.md"
            item = approved_batch(approval)
            adapters.validate_imagery_plan(item, approval, root)
            item["assets"].append(copy.deepcopy(item["assets"][0]))
            item["assets"][1]["id"] = "hero-02"
            item["assets"][1]["lineage"]["prompt_id"] = "hero-02-prompt-v1"
            item["assets"][1]["lineage"]["output_name"] = ".design/imagery/generated/hero-02.png"
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_imagery_plan(item, approval, root)

    def test_approved_generation_batch_requires_exact_approval_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/imagery/generation-approval.md"
            item = approved_batch(approval)
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_imagery_plan(item, project_root=root)
            wrong = root / "wrong.md"
            wrong.write_text(approval.read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_imagery_plan(item, wrong, root)

    def test_changed_generation_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/imagery/generation-approval.md"
            item = approved_batch(approval)
            approval.write_text("Changed approval.\n", encoding="utf-8")
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_imagery_plan(item, approval, root)

    def test_generation_approval_rejects_purpose_and_ceiling_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/imagery/generation-approval.md"
            item = approved_batch(approval)
            adapters.validate_imagery_plan(item, approval, root)
            item["generation_boundary"]["output_ceiling"] = 50
            with self.assertRaisesRegex(adapters.ValidationError, "request hash is stale"):
                adapters.validate_imagery_plan(item, approval, root)
            item["generation_boundary"]["output_ceiling"] = 1
            item["generation_boundary"]["purpose"] = "repair-batch"
            with self.assertRaisesRegex(adapters.ValidationError, "request hash is stale"):
                adapters.validate_imagery_plan(item, approval, root)

    def test_generation_approval_binds_complete_batch_scope(self) -> None:
        mutations = {
            "asset id": lambda item: item["assets"][0].__setitem__("id", "hero-renamed"),
            "prompt": lambda item: item["assets"][0]["prompts"].__setitem__(
                "gpt_image_2", "Generate a materially different approved-looking image prompt."
            ),
            "output target": lambda item: item["assets"][0]["lineage"].__setitem__(
                "output_name", ".design/imagery/generated/other-target.png"
            ),
            "source lineage": lambda item: item["assets"][0]["lineage"].__setitem__(
                "source_asset_ids", ["unapproved-source"]
            ),
            "reference lineage": lambda item: item["assets"][0]["lineage"].__setitem__(
                "reference_ids", []
            ),
            "reference source": lambda item: item["references"][0].__setitem__(
                "locator", ".design/research/dossiers/different-reference.json#E2"
            ),
            "asset lock scope": lambda item: item["assets"][0]["asset_lock"].__setitem__(
                "subject", "A changed subject outside the approved generation request."
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(field=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                approval = root / ".design/imagery/generation-approval.md"
                item = approved_batch(approval)
                adapters.validate_imagery_plan(item, approval, root)
                mutate(item)
                with self.assertRaisesRegex(adapters.ValidationError, "request hash is stale"):
                    adapters.validate_imagery_plan(item, approval, root)

    def test_generation_approval_note_rejects_rehashed_mutated_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/imagery/generation-approval.md"
            item = approved_batch(approval)
            item["assets"][0]["prompts"]["gpt_image_2"] = (
                "Generate a different executable prompt after approval was recorded."
            )
            item["generation_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
                adapters.imagery_generation_request_payload(item)
            )
            with self.assertRaisesRegex(adapters.ValidationError, "complete canonical request"):
                adapters.validate_imagery_plan(item, approval, root)

    def test_code_native_asset_rejects_generation_prompt(self) -> None:
        item = load_template("imagery-plan.template.json")
        item["medium_decision"]["selected"] = "code-native"
        item["generation_boundary"]["purpose"] = "no-generation"
        item["assets"][0]["type"] = "code-native"
        item["assets"][0]["prompts"]["not_applicable_reason"] = "The graphic must remain editable in code."
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_series_requires_matching_batch_and_shared_visual_dna(self) -> None:
        item = load_template("imagery-plan.template.json")
        item["series"]["enabled"] = True
        item["series"]["batch_size"] = 1
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_unknown_reference_lineage_is_rejected(self) -> None:
        item = load_template("imagery-plan.template.json")
        item["assets"][0]["lineage"]["reference_ids"] = ["missing"]
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_prompt_and_source_lineage_must_be_unique_and_acyclic(self) -> None:
        item = load_template("imagery-plan.template.json")
        second = copy.deepcopy(item["assets"][0])
        second["id"] = "hero-02"
        second["lineage"]["prompt_id"] = "hero-02-prompt-v1"
        second["lineage"]["output_name"] = ".design/imagery/generated/hero-02.png"
        item["assets"].append(second)
        item["assets"][0]["lineage"]["prompt_parent_ids"] = ["hero-02-prompt-v1"]
        item["assets"][1]["lineage"]["prompt_parent_ids"] = ["hero-01-prompt-v1"]
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)
        item["assets"][0]["lineage"]["prompt_parent_ids"] = []
        item["assets"][1]["lineage"]["prompt_parent_ids"] = []
        item["assets"][0]["lineage"]["source_asset_ids"] = ["hero-02"]
        item["assets"][1]["lineage"]["source_asset_ids"] = ["hero-01"]
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_imagery_plan(item)

    def test_image_edit_compiles_lock_change_verify_and_limits_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / ".design/imagery/generated/hero-01.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"asset")
            item = load_template("image-edit.template.json")
            item["source_sha256"] = adapters.sha256(source)
            item["generation_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
                adapters.imagery_generation_request_payload(item)
            )
            text = adapters.compile_image_edit(item, project_root=root)
            self.assertLess(text.index("## LOCK"), text.index("## CHANGE"))
            self.assertLess(text.index("## CHANGE"), text.index("## VERIFY"))
            item["repair_pass"] = 4
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_image_edit(item, project_root=root)

    def test_image_edit_requires_current_source_artifact(self) -> None:
        item = load_template("image-edit.template.json")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_image_edit(item, project_root=directory)

    def test_no_figma_connection_compiles_structural_handoff_scaffold(self) -> None:
        item = load_template("figma-handoff.template.json")
        text = adapters.compile_figma_specification(item)
        self.assertIn("structurally valid handoff scaffold", text)
        self.assertIn("## Frames", text)
        self.assertIn("## Variables", text)

    def test_direct_figma_mode_requires_authorized_connection(self) -> None:
        item = load_template("figma-handoff.template.json")
        item["mode"] = "direct-when-authorized"
        item["target_file"] = "figma-file-key:test"
        item["destructive_action_classification"] = "non-destructive"
        item["direct_actions"] = copy.deepcopy(FIGMA_ACTIONS)
        item["external_write_boundary"]["status"] = "awaiting-approval"
        item["external_write_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
            adapters.figma_write_request_payload(item)
        )
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_figma_handoff(item)

    def test_direct_figma_actions_bind_external_write_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            adapters.validate_figma_handoff(item, approval, root)
            approval.write_text("Changed approval.\n", encoding="utf-8")
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_figma_handoff(item, approval, root)

    def test_figma_approval_rejects_an_unapproved_action_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            adapters.validate_figma_handoff(item, approval, root)
            item["direct_actions"] = [
                {
                    "id": "delete-unrelated-pages",
                    "description": "Delete every page in an unrelated Figma file.",
                    "target": "Every unrelated page",
                    "destructive": True,
                }
            ]
            item["destructive_action_classification"] = "contains-destructive-actions"
            with self.assertRaisesRegex(adapters.ValidationError, "request hash is stale"):
                adapters.validate_figma_handoff(item, approval, root)

    def test_figma_approval_binds_target_spec_and_destructive_scope(self) -> None:
        mutations = {
            "target file": lambda item: item.__setitem__(
                "target_file", "figma-file-key:different-file"
            ),
            "action target": lambda item: item["direct_actions"][0].__setitem__(
                "target", "An unrelated page"
            ),
            "specification frame": lambda item: item["specification"]["frames"][0].__setitem__(
                "name", "Mutated frame"
            ),
            "destructive addition": lambda item: (
                item["direct_actions"].append(
                    {
                        "id": "delete-existing-page",
                        "description": "Delete an existing page before creating new frames.",
                        "target": "Existing production page",
                        "destructive": True,
                    }
                ),
                item.__setitem__(
                    "destructive_action_classification", "contains-destructive-actions"
                ),
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(field=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                approval = root / ".design/handoff/figma-approval.md"
                item = direct_figma(approval, root)
                adapters.validate_figma_handoff(item, approval, root)
                mutate(item)
                with self.assertRaisesRegex(adapters.ValidationError, "request hash is stale"):
                    adapters.validate_figma_handoff(item, approval, root)

    def test_figma_approval_note_rejects_rehashed_mutated_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            item["target_file"] = "figma-file-key:different-file"
            item["external_write_boundary"]["request_sha256"] = adapters._canonical_request_sha256(
                adapters.figma_write_request_payload(item)
            )
            with self.assertRaisesRegex(adapters.ValidationError, "complete canonical request"):
                adapters.validate_figma_handoff(item, approval, root)

    def test_direct_figma_actions_require_exact_approval_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            with self.assertRaises(adapters.ValidationError):
                adapters.validate_figma_handoff(item, project_root=root)

    def test_figma_host_report_scaffold_cannot_support_capability_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            report = root / item["capability"]["environment_report_path"]
            host = json.loads(report.read_text())
            host["artifact_status"] = "scaffold"
            write_json(report, host)
            item["capability"]["environment_report_sha256"] = adapters.sha256(report)
            with self.assertRaisesRegex(adapters.ValidationError, "scaffold"):
                adapters.validate_figma_handoff(item, approval, root)

    def test_figma_host_report_cannot_contradict_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approval = root / ".design/handoff/figma-approval.md"
            item = direct_figma(approval, root)
            report = root / item["capability"]["environment_report_path"]
            host = json.loads(report.read_text())
            host["figma"]["status"] = "available-not-authorized"
            write_json(report, host)
            item["capability"]["environment_report_sha256"] = adapters.sha256(report)
            with self.assertRaisesRegex(adapters.ValidationError, "contradicts"):
                adapters.validate_figma_handoff(item, approval, root)

    def test_figma_adapter_forbids_bundled_mcp_requirement(self) -> None:
        item = load_template("figma-handoff.template.json")
        item["capability"]["bundled_mcp_required"] = True
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_figma_handoff(item)

    def test_figma_fallback_rejects_incomplete_specification(self) -> None:
        item = load_template("figma-handoff.template.json")
        item["specification"]["variables"] = []
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_figma_handoff(item)

    def test_mobile_template_selects_responsive_web_as_simplest_valid(self) -> None:
        item = responsive_mobile()
        adapters.validate_mobile_decision(item)
        self.assertEqual(item["routing_result"]["selected"], "responsive-web")
        self.assertIn("## What mobile can mean", adapters.compile_mobile_decision(item))

    def test_mobile_selects_cross_platform_when_web_fails_hard_requirement(self) -> None:
        item = responsive_mobile()
        link = item["requirements"][0]["compatibility"]
        link["responsive-web"] = False
        link["cross-platform"] = True
        item["routing_result"]["selected"] = "cross-platform"
        adapters.validate_mobile_decision(item)

    def test_mobile_selects_native_only_when_simpler_paths_fail(self) -> None:
        item = responsive_mobile()
        link = item["requirements"][0]["compatibility"]
        link["responsive-web"] = False
        link["cross-platform"] = False
        link["native-mobile"] = True
        item["routing_result"]["selected"] = "native-mobile"
        adapters.validate_mobile_decision(item)

    def test_mobile_rejects_overcomplex_recommendation(self) -> None:
        item = responsive_mobile()
        item["routing_result"]["selected"] = "cross-platform"
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_mobile_decision(item)

    def test_no_viable_mobile_path_returns_to_grilling(self) -> None:
        item = load_template("mobile-decision.template.json")
        item["requirements"][0]["compatibility"] = {option: False for option in adapters.MOBILE_OPTIONS}
        item["routing_result"] = {
            "status": "return-to-grilling",
            "selected": None,
            "simplest_valid": False,
            "rationale": "The current hard requirements conflict, so the product definition must be resolved before platform selection.",
            "questions": ["Which hard requirement may change, or which delivery surface owns the primary task?"],
            "framework_decision": {"status": "deferred", "name": None, "reason": "Product requirements are unresolved."},
        }
        adapters.validate_mobile_decision(item)

    def test_mobile_requires_all_nine_evidence_factors(self) -> None:
        item = load_template("mobile-decision.template.json")
        item["project_factors"].pop()
        with self.assertRaises(adapters.ValidationError):
            adapters.validate_mobile_decision(item)

    def test_aggregate_gate_validates_all_adapter_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            report = verify_artifacts(paths)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["wave6_status"], "pass")
            self.assertEqual(report["imagery_generation_status"], "not-required")
            self.assertEqual(report["figma_mode"], "specification")
            self.assertEqual(report["mobile_selected"], "responsive-web")

    def test_aggregate_gate_rejects_stale_design_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            item = json.loads(paths["imagery"].read_text())
            item["design_md_sha256"] = "f" * 64
            write_json(paths["imagery"], item)
            with self.assertRaises(adapters.ValidationError):
                verify_artifacts(paths)

    def test_aggregate_gate_rejects_malformed_wave6_inputs(self) -> None:
        cases = {
            "reference lock": ("lock", lambda item: item.__setitem__("frozen_visual_traits", [])),
            "UX definition": ("ux", lambda item: item.__setitem__("screens", [])),
            "design system": ("system", lambda item: item.__setitem__("sections", {})),
            "token source": ("tokens", lambda item: item.pop("semantic")),
        }
        for label, (key, mutate) in cases.items():
            with self.subTest(upstream=label), tempfile.TemporaryDirectory() as directory:
                paths = build_artifacts(Path(directory))
                item = json.loads(paths[key].read_text())
                mutate(item)
                write_json(paths[key], item)
                with self.assertRaises(adapters.ValidationError):
                    verify_artifacts(paths)

    def test_cli_verifies_complete_wave7_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = build_artifacts(Path(directory))
            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH), "verify-wave7",
                    "--lock", str(paths["lock"]),
                    "--decision", str(paths["decision"]),
                    "--direction-set", str(paths["direction_set"]),
                    "--design-md", str(paths["design_md"]),
                    "--tokens", str(paths["tokens"]),
                    "--ux", str(paths["ux"]),
                    "--system", str(paths["system"]),
                    "--token-output-dir", str(paths["token_output"]),
                    "--plan", str(paths["plan"]),
                    "--plan-md", str(paths["plan_md"]),
                    "--imagery", str(paths["imagery"]),
                    "--figma", str(paths["figma"]),
                    "--mobile", str(paths["mobile"]),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(json.loads(completed.stdout)["status"], "pass")

    def test_cli_rejects_approved_external_actions_without_approval_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = build_artifacts(root)
            generation_approval = root / ".design/imagery/generation-approval.md"
            figma_approval = root / ".design/handoff/figma-approval.md"
            imagery = approved_batch(generation_approval)
            lock = json.loads(paths["lock"].read_text())
            imagery["approved_direction_sha256"] = lock["approved_direction"]["decision_sha256"]
            imagery["reference_lock_sha256"] = adapters.sha256(paths["lock"])
            imagery["design_md_sha256"] = adapters.sha256(paths["design_md"])
            authorize_imagery(imagery, generation_approval)
            write_json(paths["imagery"], imagery)
            figma = direct_figma(figma_approval, root)
            figma["design_md_sha256"] = adapters.sha256(paths["design_md"])
            figma["tokens_source_sha256"] = adapters.sha256(paths["tokens"])
            authorize_figma(figma, figma_approval)
            write_json(paths["figma"], figma)
            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH), "verify-wave7",
                    "--lock", str(paths["lock"]),
                    "--decision", str(paths["decision"]),
                    "--direction-set", str(paths["direction_set"]),
                    "--design-md", str(paths["design_md"]),
                    "--tokens", str(paths["tokens"]),
                    "--ux", str(paths["ux"]),
                    "--system", str(paths["system"]),
                    "--token-output-dir", str(paths["token_output"]),
                    "--plan", str(paths["plan"]),
                    "--plan-md", str(paths["plan_md"]),
                    "--imagery", str(paths["imagery"]),
                    "--figma", str(paths["figma"]),
                    "--mobile", str(paths["mobile"]),
                    "--project-root", str(root),
                ],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("approval", completed.stderr.casefold())


if __name__ == "__main__":
    unittest.main()
