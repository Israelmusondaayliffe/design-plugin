#!/usr/bin/env python3
"""Validate and compile Design Wave 7 imagery, Figma, and mobile artifacts.

Standard-library only. This runtime prepares local specifications and prompts. It
does not call image tools, write to Figma, install software, or modify product code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_system import ValidationError as Wave6ValidationError, verify_wave6

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
CONFIDENCE = {"high", "medium", "low"}
GENERATION_PURPOSES = {
    "no-generation",
    "prompt-only",
    "direction-board",
    "production-batch",
    "repair-batch",
}
GENERATION_STATUSES = {"not-required", "awaiting-approval", "approved"}
MEDIA_CHOICES = {
    "code-native",
    "actual-screenshot",
    "standard-icon",
    "chart",
    "bitmap-generation",
}
ASSET_TYPES = {
    "visual-direction-board",
    "hero-concept",
    "production-bitmap",
    "illustration",
    "texture",
    "editorial-graphic",
    "image-led-ui-asset",
    "prompt-only",
    "code-native",
    "screenshot",
    "icon",
    "chart",
}
GENERATED_ASSET_TYPES = {
    "visual-direction-board",
    "hero-concept",
    "production-bitmap",
    "illustration",
    "texture",
    "editorial-graphic",
    "image-led-ui-asset",
    "prompt-only",
}
RIGHTS_STATUSES = {"owned", "licensed", "public-reference", "review-required"}
FIGMA_CAPABILITIES = {
    "unavailable",
    "available-not-authorized",
    "available-authorized",
    "unknown",
}
IMAGERY_APPROVAL_CONTRACT = "design-imagery-generation-approval-v2"
FIGMA_APPROVAL_CONTRACT = "design-figma-write-approval-v2"
MOBILE_OPTIONS = ("responsive-web", "cross-platform", "native-mobile")
MOBILE_FACTORS = {
    "device-features",
    "app-store-requirements",
    "offline-behavior",
    "performance",
    "current-codebase",
    "team-ability",
    "budget",
    "maintenance",
    "desired-experience",
}


class ValidationError(ValueError):
    """Raised when a Wave 7 artifact violates the approved contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{label} must be non-empty text")
    return value.strip()


def _strings(value: Any, label: str, minimum: int = 0) -> list[str]:
    _require(isinstance(value, list) and len(value) >= minimum, f"{label} must contain at least {minimum} item(s)")
    return [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _hash(value: Any, label: str) -> str:
    digest = _text(value, label)
    _require(HEX64.fullmatch(digest) is not None, f"{label} must be a 64-character SHA-256 digest")
    return digest.lower()


def _timestamp(value: Any, label: str) -> str:
    timestamp = _text(value, label)
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label} must be ISO-8601") from exc
    _require(parsed.year >= 2020, f"{label} cannot be a scaffold timestamp")
    return timestamp


def _attested_text(value: Any, label: str) -> str:
    text = _text(value, label)
    lowered = text.casefold()
    scaffold_markers = ("replace with", "not checked", "placeholder", "test value")
    _require(not any(marker in lowered for marker in scaffold_markers), f"{label} contains scaffold text")
    return text


def _attested_strings(value: Any, label: str, minimum: int = 1) -> list[str]:
    items = _strings(value, label, minimum)
    for index, item in enumerate(items):
        _attested_text(item, f"{label}[{index}]")
    return items


def _relative(value: Any, label: str) -> str:
    raw = _text(value, label)
    candidate = Path(raw)
    _require(not candidate.is_absolute(), f"{label} must be relative")
    _require(".." not in candidate.parts, f"{label} cannot escape the project root")
    _require(re.match(r"^[A-Za-z]:", raw) is None, f"{label} cannot use an absolute drive path")
    return candidate.as_posix()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: str | Path, text: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _verify_hash(path: str | Path, expected: str, label: str) -> None:
    actual = sha256(path)
    _require(actual == expected, f"{label} hash mismatch: expected {expected}, got {actual}")


def _verify_declared_approval(
    approval_path: str | Path | None,
    project_root: str | Path | None,
    declared_artifact: str,
    expected: str,
    label: str,
) -> Path:
    _require(approval_path is not None, f"{label} requires the approval file")
    _require(project_root is not None, f"{label} requires the project root")
    root = Path(project_root).expanduser().resolve()
    declared = (root / declared_artifact).resolve()
    try:
        declared.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"{label} approval artifact escapes the project root") from exc
    supplied = Path(approval_path).expanduser()
    supplied = supplied.resolve() if supplied.is_absolute() else (root / supplied).resolve()
    _require(supplied == declared, f"{label} approval path does not match {declared_artifact}")
    _require(supplied.is_file(), f"{label} approval file does not exist: {declared_artifact}")
    _verify_hash(supplied, expected, label)
    return supplied


def _approval_contract_text(title: str, payload: dict[str, Any]) -> str:
    return (
        f"# {title}\n\n"
        "```json\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)}\n"
        "```\n"
    )


def _canonical_request_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def imagery_generation_request_payload(document: dict[str, Any]) -> dict[str, Any]:
    if "plan_id" in document:
        request_type = "imagery-plan"
    elif "asset_id" in document and "repair_pass" in document:
        request_type = "image-edit"
    else:
        raise ValidationError("imagery approval request must be an imagery plan or image edit")
    boundary = document.get("generation_boundary")
    _require(isinstance(boundary, dict), "imagery approval request requires generation_boundary")
    payload = {
        key: value
        for key, value in document.items()
        if key != "generation_boundary"
    }
    payload["generation_boundary"] = {
        "output_ceiling": boundary.get("output_ceiling"),
        "purpose": boundary.get("purpose"),
    }
    return {
        "request_type": request_type,
        "payload": payload,
    }


def imagery_generation_approval_text(document: dict[str, Any]) -> str:
    request = imagery_generation_request_payload(document)
    return _approval_contract_text(
        "Imagery generation approval",
        {
            "contract": IMAGERY_APPROVAL_CONTRACT,
            "decision": "approved",
            "request_sha256": _canonical_request_sha256(request),
            "request_type": request["request_type"],
        },
    )


def figma_write_request_payload(handoff: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": handoff.get("schema_version"),
        "design_md_sha256": handoff.get("design_md_sha256"),
        "tokens_source_sha256": handoff.get("tokens_source_sha256"),
        "mode": handoff.get("mode"),
        "target_file": handoff.get("target_file"),
        "destructive_action_classification": handoff.get(
            "destructive_action_classification"
        ),
        "direct_actions": handoff.get("direct_actions"),
        "specification": handoff.get("specification"),
    }
    return {
        "request_type": "figma-direct-write",
        "payload": payload,
    }


def figma_write_approval_text(handoff: dict[str, Any]) -> str:
    request = figma_write_request_payload(handoff)
    return _approval_contract_text(
        "Figma external-write approval",
        {
            "contract": FIGMA_APPROVAL_CONTRACT,
            "decision": "approved",
            "request_sha256": _canonical_request_sha256(request),
            "request_type": request["request_type"],
        },
    )


def _verify_approval_contract(path: Path, expected_text: str, label: str) -> None:
    actual = path.read_text(encoding="utf-8")
    _require(
        actual == expected_text,
        f"{label} does not exactly bind the complete canonical request",
    )


def _verify_project_file(
    project_root: str | Path | None,
    declared_artifact: str,
    expected: str,
    label: str,
) -> Path:
    _require(project_root is not None, f"{label} requires the project root")
    root = Path(project_root).expanduser().resolve()
    artifact = (root / declared_artifact).resolve()
    try:
        artifact.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"{label} escapes the project root") from exc
    _require(artifact.is_file(), f"{label} does not exist: {declared_artifact}")
    _verify_hash(artifact, expected, label)
    return artifact


def _require_acyclic(graph: dict[str, set[str]], label: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValidationError(f"{label} contains a cycle at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, set()):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _validate_external_boundary(
    boundary: Any,
    label: str,
    request_document: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(boundary, dict), f"{label} must be an object")
    purpose = boundary.get("purpose")
    status = boundary.get("status")
    _require(purpose in GENERATION_PURPOSES, f"{label}.purpose is invalid")
    _require(status in GENERATION_STATUSES, f"{label}.status is invalid")
    ceiling = boundary.get("output_ceiling")
    _require(isinstance(ceiling, int) and not isinstance(ceiling, bool) and 0 <= ceiling <= 50, f"{label}.output_ceiling must be from 0 to 50")
    artifact = boundary.get("approval_artifact")
    digest = boundary.get("approval_sha256")
    request_digest = boundary.get("request_sha256")
    current_request_digest = _canonical_request_sha256(
        imagery_generation_request_payload(request_document)
    )
    if purpose in {"no-generation", "prompt-only"}:
        _require(status == "not-required", f"{label} prompt-only or no-generation work needs status not-required")
        _require(ceiling == 0, f"{label} prompt-only or no-generation work must have output_ceiling 0")
        _require(
            artifact is None and digest is None and request_digest is None,
            f"{label} must not invent an approval record",
        )
    elif status == "awaiting-approval":
        _require(ceiling > 0, f"{label} generation work must define a positive output ceiling")
        _require(artifact is None and digest is None, f"{label} awaiting approval cannot claim an approval artifact")
        _require(
            _hash(request_digest, f"{label}.request_sha256") == current_request_digest,
            f"{label} request hash is stale",
        )
    elif status == "approved":
        _require(ceiling > 0, f"{label} approved generation work must define a positive output ceiling")
        _require(
            _hash(request_digest, f"{label}.request_sha256") == current_request_digest,
            f"{label} request hash is stale",
        )
        declared = _relative(artifact, f"{label}.approval_artifact")
        expected = _hash(digest, f"{label}.approval_sha256")
        approval = _verify_declared_approval(
            approval_path,
            project_root,
            declared,
            expected,
            f"{label} approval",
        )
        _verify_approval_contract(
            approval,
            imagery_generation_approval_text(request_document),
            f"{label} approval contract",
        )
    else:
        raise ValidationError(f"{label} generation work cannot use status not-required")
    return boundary


def validate_imagery_plan(
    plan: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(plan, dict), "imagery plan must be an object")
    _require(plan.get("schema_version") == "1.0", "imagery plan schema_version must be 1.0")
    _require(plan.get("artifact_status") == "ready", "imagery plan scaffold must be completed before validation")
    for field in ("approved_direction_sha256", "reference_lock_sha256", "design_md_sha256"):
        _hash(plan.get(field), field)
    _text(plan.get("plan_id"), "plan_id")

    medium = plan.get("medium_decision")
    _require(isinstance(medium, dict), "medium_decision must be an object")
    selected_medium = medium.get("selected")
    _require(selected_medium in MEDIA_CHOICES, "medium_decision.selected is invalid")
    _text(medium.get("reason"), "medium_decision.reason", 12)
    considered = _strings(medium.get("considered"), "medium_decision.considered", 2)
    _require(selected_medium in considered, "selected medium must appear in considered")
    _require(set(considered) <= MEDIA_CHOICES, "medium_decision.considered contains an unknown option")

    boundary = _validate_external_boundary(
        plan.get("generation_boundary"),
        "generation_boundary",
        plan,
        approval_path,
        project_root,
    )
    if selected_medium == "bitmap-generation":
        _require(boundary["purpose"] != "no-generation", "bitmap generation needs a prompt or generation purpose")
    else:
        _require(boundary["purpose"] in {"no-generation", "prompt-only"}, "non-bitmap media cannot authorize a bitmap batch")

    references = plan.get("references")
    _require(isinstance(references, list), "references must be a list")
    reference_ids: set[str] = set()
    for index, item in enumerate(references):
        _require(isinstance(item, dict), f"references[{index}] must be an object")
        identifier = _text(item.get("id"), f"references[{index}].id")
        _require(identifier not in reference_ids, "reference ids must be unique")
        reference_ids.add(identifier)
        _require(item.get("kind") in {"user-provided", "project-local", "public-source", "generated-parent"}, f"references[{index}].kind is invalid")
        _text(item.get("locator"), f"references[{index}].locator")
        _require(item.get("rights_status") in RIGHTS_STATUSES, f"references[{index}].rights_status is invalid")

    assets = plan.get("assets")
    _require(isinstance(assets, list) and assets, "assets must be a non-empty list")
    asset_ids: set[str] = set()
    prompt_ids: set[str] = set()
    for index, asset in enumerate(assets):
        _require(isinstance(asset, dict), f"assets[{index}] must be an object")
        identifier = _text(asset.get("id"), f"assets[{index}].id")
        _require(identifier not in asset_ids, "asset ids must be unique")
        asset_ids.add(identifier)
        lineage = asset.get("lineage")
        _require(isinstance(lineage, dict), f"assets[{index}].lineage must be an object")
        prompt_id = _text(lineage.get("prompt_id"), f"assets[{index}].lineage.prompt_id")
        _require(prompt_id not in prompt_ids, "prompt ids must be unique")
        prompt_ids.add(prompt_id)
    generated_count = 0
    output_names: set[str] = set()
    prompt_graph: dict[str, set[str]] = {}
    source_graph: dict[str, set[str]] = {}
    for index, asset in enumerate(assets):
        identifier = _text(asset.get("id"), f"assets[{index}].id")
        _text(asset.get("role"), f"assets[{index}].role", 5)
        _text(asset.get("slot"), f"assets[{index}].slot", 3)
        asset_type = asset.get("type")
        _require(asset_type in ASSET_TYPES, f"assets[{index}].type is invalid")
        if asset_type in GENERATED_ASSET_TYPES and asset_type != "prompt-only":
            generated_count += 1
        dimensions = asset.get("dimensions")
        _require(isinstance(dimensions, dict), f"assets[{index}].dimensions must be an object")
        _require(isinstance(dimensions.get("width"), int) and dimensions["width"] > 0, f"assets[{index}] width must be positive")
        _require(isinstance(dimensions.get("height"), int) and dimensions["height"] > 0, f"assets[{index}] height must be positive")
        _strings(asset.get("source_hierarchy"), f"assets[{index}].source_hierarchy", 1)

        lock = asset.get("asset_lock")
        _require(isinstance(lock, dict), f"assets[{index}].asset_lock must be an object")
        for field in ("composition", "subject", "color", "lighting", "visible_text"):
            _text(lock.get(field), f"assets[{index}].asset_lock.{field}", 3)
        _strings(lock.get("materials"), f"assets[{index}].asset_lock.materials", 1)
        _strings(lock.get("frozen_properties"), f"assets[{index}].asset_lock.frozen_properties", 3)
        _strings(lock.get("allowed_variation"), f"assets[{index}].asset_lock.allowed_variation", 1)
        _strings(lock.get("prohibited_drift"), f"assets[{index}].asset_lock.prohibited_drift", 3)
        _strings(lock.get("verification_criteria"), f"assets[{index}].asset_lock.verification_criteria", 3)

        prompts = asset.get("prompts")
        _require(isinstance(prompts, dict), f"assets[{index}].prompts must be an object")
        gpt_prompt = prompts.get("gpt_image_2")
        midjourney_prompt = prompts.get("midjourney")
        not_applicable = prompts.get("not_applicable_reason")
        if asset_type in GENERATED_ASSET_TYPES:
            _text(gpt_prompt, f"assets[{index}].prompts.gpt_image_2", 20)
            _require(midjourney_prompt is None or (isinstance(midjourney_prompt, str) and len(midjourney_prompt.strip()) >= 20), f"assets[{index}].prompts.midjourney must be null or detailed text")
            _require(not_applicable is None, f"assets[{index}] generated asset cannot mark prompts not applicable")
        else:
            _text(not_applicable, f"assets[{index}].prompts.not_applicable_reason", 8)
            _require(gpt_prompt is None and midjourney_prompt is None, f"assets[{index}] code-native or sourced asset cannot carry generation prompts")

        lineage = asset.get("lineage")
        _require(isinstance(lineage, dict), f"assets[{index}].lineage must be an object")
        prompt_id = _text(lineage.get("prompt_id"), f"assets[{index}].lineage.prompt_id")
        parent_prompts = _strings(lineage.get("prompt_parent_ids"), f"assets[{index}].lineage.prompt_parent_ids")
        _require(set(parent_prompts) <= prompt_ids - {prompt_id}, f"assets[{index}] cites an unknown or self prompt parent")
        prompt_graph[prompt_id] = set(parent_prompts)
        cited = _strings(lineage.get("reference_ids"), f"assets[{index}].lineage.reference_ids")
        _require(set(cited) <= reference_ids, f"assets[{index}] cites an unknown reference")
        source_assets = _strings(lineage.get("source_asset_ids"), f"assets[{index}].lineage.source_asset_ids")
        _require(set(source_assets) <= asset_ids - {identifier}, f"assets[{index}] cites an unknown or self source asset")
        source_graph[identifier] = set(source_assets)
        output_name = _relative(lineage.get("output_name"), f"assets[{index}].lineage.output_name")
        _require(output_name not in output_names, "asset output names must be unique")
        output_names.add(output_name)

        review = asset.get("rights_and_privacy")
        _require(isinstance(review, dict), f"assets[{index}].rights_and_privacy must be an object")
        _require(review.get("rights_status") in RIGHTS_STATUSES, f"assets[{index}].rights_status is invalid")
        _text(review.get("privacy_review"), f"assets[{index}].privacy_review", 8)

    _require_acyclic(prompt_graph, "prompt lineage")
    _require_acyclic(source_graph, "source-asset lineage")

    if boundary["status"] == "approved":
        _require(generated_count <= boundary["output_ceiling"], "approved asset count exceeds the generation output ceiling")

    series = plan.get("series")
    _require(isinstance(series, dict) and isinstance(series.get("enabled"), bool), "series must declare enabled")
    if series["enabled"]:
        _require(len(assets) >= 2, "an enabled series must contain at least two assets")
        _text(series.get("shared_visual_dna"), "series.shared_visual_dna", 12)
        _strings(series.get("frozen_properties"), "series.frozen_properties", 3)
        _strings(series.get("allowed_variation"), "series.allowed_variation", 1)
        _require(series.get("batch_size") == len(assets), "series.batch_size must match the planned asset count")
        _text(series.get("naming_pattern"), "series.naming_pattern", 5)
        _strings(series.get("prompt_lineage"), "series.prompt_lineage", 1)
        _strings(series.get("reference_lineage"), "series.reference_lineage", 1)
        _strings(series.get("acceptance_criteria"), "series.acceptance_criteria", 3)
    else:
        _require(series.get("batch_size") in {0, 1}, "disabled series batch_size must be 0 or 1")

    repair = plan.get("repair_policy")
    _require(isinstance(repair, dict), "repair_policy must be an object")
    _require(repair.get("targeted_repairs_only") is True, "repair policy must require targeted repairs")
    _require(repair.get("renewed_approval_for_material_batch") is True, "material repair batches require renewed approval")
    _require(repair.get("max_automated_passes_per_state") == 3, "imagery repair is limited to three passes per affected state")
    return plan


def compile_imagery_prompts(
    plan: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> str:
    validate_imagery_plan(plan, approval_path, project_root)
    boundary = plan["generation_boundary"]
    lines = [
        "# Design imagery package",
        "",
        f"Plan: `{plan['plan_id']}`",
        f"Medium: `{plan['medium_decision']['selected']}`",
        f"Generation purpose: `{boundary['purpose']}`",
        f"Generation status: `{boundary['status']}`",
        f"Output ceiling: {boundary['output_ceiling']}",
        "",
        "This package prepares prompts and acceptance criteria. It does not generate assets.",
    ]
    for asset in plan["assets"]:
        lock = asset["asset_lock"]
        lines.extend(
            [
                "",
                f"## {asset['id']}: {asset['role']}",
                "",
                f"Slot: {asset['slot']}",
                f"Output: `{asset['lineage']['output_name']}`",
                f"Dimensions: {asset['dimensions']['width']} x {asset['dimensions']['height']}",
                "",
                "### Asset lock",
                "",
                f"- Composition: {lock['composition']}",
                f"- Subject: {lock['subject']}",
                f"- Materials: {', '.join(lock['materials'])}",
                f"- Color: {lock['color']}",
                f"- Lighting: {lock['lighting']}",
                f"- Visible text: {lock['visible_text']}",
                "",
                "Frozen properties:",
            ]
        )
        lines.extend(f"- {item}" for item in lock["frozen_properties"])
        lines.extend(["", "Allowed variation:"])
        lines.extend(f"- {item}" for item in lock["allowed_variation"])
        lines.extend(["", "Prohibited drift:"])
        lines.extend(f"- {item}" for item in lock["prohibited_drift"])
        if asset["prompts"].get("gpt_image_2"):
            lines.extend(["", "### GPT Image 2 prompt", "", "```text", asset["prompts"]["gpt_image_2"].strip(), "```"])
        if asset["prompts"].get("midjourney"):
            lines.extend(["", "### Midjourney prompt", "", "```text", asset["prompts"]["midjourney"].strip(), "```"])
        if asset["prompts"].get("not_applicable_reason"):
            lines.extend(["", f"Prompts not applicable: {asset['prompts']['not_applicable_reason'].strip()}"])
        lines.extend(["", "### Verification"])
        lines.extend(f"- {item}" for item in lock["verification_criteria"])
    return "\n".join(lines) + "\n"


def validate_image_edit(
    edit: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(edit, dict), "image edit must be an object")
    _require(edit.get("schema_version") == "1.0", "image edit schema_version must be 1.0")
    _require(edit.get("artifact_status") == "ready", "image edit scaffold must be completed before validation")
    _hash(edit.get("imagery_plan_sha256"), "imagery_plan_sha256")
    _text(edit.get("asset_id"), "asset_id")
    source_artifact = _relative(edit.get("source_artifact"), "source_artifact")
    source_hash = _hash(edit.get("source_sha256"), "source_sha256")
    _verify_project_file(project_root, source_artifact, source_hash, "image edit source artifact")
    boundary = _validate_external_boundary(
        edit.get("generation_boundary"),
        "generation_boundary",
        edit,
        approval_path,
        project_root,
    )
    _require(boundary["purpose"] == "repair-batch", "image edits that call a generator must use repair-batch purpose")
    _strings(edit.get("lock"), "LOCK", 1)
    _strings(edit.get("change"), "CHANGE", 1)
    _strings(edit.get("verify"), "VERIFY", 1)
    _text(edit.get("prompt"), "prompt", 20)
    _require(edit.get("repair_pass") in {1, 2, 3}, "repair_pass must be 1, 2, or 3")
    return edit


def compile_image_edit(
    edit: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> str:
    validate_image_edit(edit, approval_path, project_root)
    lines = [f"# Targeted image edit: {edit['asset_id']}", "", "## LOCK", ""]
    lines.extend(f"- {item}" for item in edit["lock"])
    lines.extend(["", "## CHANGE", ""])
    lines.extend(f"- {item}" for item in edit["change"])
    lines.extend(["", "## VERIFY", ""])
    lines.extend(f"- {item}" for item in edit["verify"])
    lines.extend(["", "## Edit prompt", "", "```text", edit["prompt"].strip(), "```", ""])
    return "\n".join(lines)


def _validate_figma_write_boundary(
    boundary: Any,
    handoff: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(boundary, dict), "external_write_boundary must be an object")
    status = boundary.get("status")
    _require(status in {"not-required", "awaiting-approval", "approved"}, "external_write_boundary.status is invalid")
    artifact = boundary.get("approval_artifact")
    digest = boundary.get("approval_sha256")
    request_digest = boundary.get("request_sha256")
    current_request_digest = _canonical_request_sha256(
        figma_write_request_payload(handoff)
    )
    if status == "not-required":
        _require(
            artifact is None and digest is None and request_digest is None,
            "a no-write Figma specification cannot claim approval",
        )
    elif status == "awaiting-approval":
        _require(artifact is None and digest is None, "awaiting Figma approval cannot claim an approval artifact")
        _require(
            _hash(request_digest, "external_write_boundary.request_sha256")
            == current_request_digest,
            "Figma external-write request hash is stale",
        )
    else:
        _require(
            _hash(request_digest, "external_write_boundary.request_sha256")
            == current_request_digest,
            "Figma external-write request hash is stale",
        )
        declared = _relative(artifact, "external_write_boundary.approval_artifact")
        expected = _hash(digest, "external_write_boundary.approval_sha256")
        approval = _verify_declared_approval(
            approval_path,
            project_root,
            declared,
            expected,
            "Figma external-write approval",
        )
        _verify_approval_contract(
            approval,
            figma_write_approval_text(handoff),
            "Figma external-write approval contract",
        )
    return boundary


def _validate_figma_direct_actions(value: Any) -> list[dict[str, Any]]:
    _require(isinstance(value, list), "direct_actions must be a list")
    actions: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, item in enumerate(value):
        _require(isinstance(item, dict), f"direct_actions[{index}] must be an object")
        _require(
            set(item) == {"id", "description", "target", "destructive"},
            f"direct_actions[{index}] must define only id, description, target, and destructive",
        )
        identifier = _text(item.get("id"), f"direct_actions[{index}].id")
        _require(identifier not in identifiers, "direct action ids must be unique")
        identifiers.add(identifier)
        _text(item.get("description"), f"direct_actions[{index}].description", 8)
        _text(item.get("target"), f"direct_actions[{index}].target", 3)
        _require(
            isinstance(item.get("destructive"), bool),
            f"direct_actions[{index}].destructive must be a boolean",
        )
        actions.append(item)
    return actions


def validate_figma_handoff(
    handoff: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(handoff, dict), "Figma handoff must be an object")
    _require(handoff.get("schema_version") == "1.0", "Figma handoff schema_version must be 1.0")
    _require(handoff.get("artifact_status") == "ready", "Figma handoff scaffold must be completed before validation")
    for field in ("design_md_sha256", "tokens_source_sha256"):
        _hash(handoff.get(field), field)

    capability = handoff.get("capability")
    _require(isinstance(capability, dict), "capability must be an object")
    status = capability.get("status")
    _require(status in FIGMA_CAPABILITIES, "capability.status is invalid")
    provider = capability.get("provider")
    environment_path = capability.get("environment_report_path")
    environment_hash = capability.get("environment_report_sha256")
    if status in {"unavailable", "unknown"}:
        _require(provider is None, "unavailable or unknown Figma capability cannot claim a provider")
    else:
        _text(provider, "capability.provider")
    if status == "unknown":
        _require(environment_path is None and environment_hash is None, "unknown Figma capability cannot claim environment proof")
    else:
        declared_environment = _relative(environment_path, "capability.environment_report_path")
        expected_environment = _hash(environment_hash, "capability.environment_report_sha256")
        environment_report = _verify_project_file(
            project_root,
            declared_environment,
            expected_environment,
            "Figma capability environment report",
        )
        report = load_json(environment_report)
        _require(isinstance(report, dict) and report.get("schema_version") == "1.0", "Figma capability report is invalid")
        _require(report.get("artifact_status") == "ready", "Figma capability report scaffold must be completed before use")
        _timestamp(report.get("inspected_at"), "Figma capability report inspected_at")
        _attested_text(report.get("inspector"), "Figma capability report inspector")
        report_surfaces = _attested_strings(report.get("surfaces"), "Figma capability report surfaces")
        capabilities = report.get("capabilities")
        figma_attestation = capabilities.get("figma") if isinstance(capabilities, dict) else report.get("figma")
        _require(isinstance(figma_attestation, dict), "Figma capability report lacks figma attestation")
        _require(figma_attestation.get("status") == status, "Figma capability status contradicts the environment report")
        _require(figma_attestation.get("provider") == provider, "Figma capability provider contradicts the environment report")
        _attested_strings(figma_attestation.get("evidence"), "Figma capability report evidence")
        _require(capability.get("checked_surfaces") == report_surfaces, "Figma checked surfaces contradict the environment report")
        _attested_strings(capability.get("checked_surfaces"), "capability.checked_surfaces")
        _attested_strings(capability.get("evidence"), "capability.evidence")
    if status == "unknown":
        _strings(capability.get("checked_surfaces"), "capability.checked_surfaces", 1)
        _strings(capability.get("evidence"), "capability.evidence", 1)
    _require(capability.get("bundled_mcp_required") is False, "the Design package cannot require a bundled Figma MCP")

    mode = handoff.get("mode")
    _require(mode in {"specification", "direct-when-authorized"}, "Figma handoff mode is invalid")
    target_file = handoff.get("target_file")
    classification = handoff.get("destructive_action_classification")
    _require(
        classification in {"not-applicable", "non-destructive", "contains-destructive-actions"},
        "destructive_action_classification is invalid",
    )
    actions = _validate_figma_direct_actions(handoff.get("direct_actions"))
    boundary = _validate_figma_write_boundary(
        handoff.get("external_write_boundary"), handoff, approval_path, project_root
    )
    if mode == "direct-when-authorized":
        _require(status == "available-authorized", "direct Figma mode requires an available authorized connection")
        _require(boundary["status"] in {"awaiting-approval", "approved"}, "direct Figma mode needs an explicit external-write boundary")
        _require(bool(actions), "direct Figma mode must list bounded direct actions")
        _text(target_file, "target_file", 3)
        expected_classification = (
            "contains-destructive-actions"
            if any(item["destructive"] for item in actions)
            else "non-destructive"
        )
        _require(
            classification == expected_classification,
            "destructive_action_classification does not match the direct action batch",
        )
    else:
        _require(boundary["status"] == "not-required", "specification-only Figma mode must not claim write approval")
        _require(not actions, "specification-only Figma mode cannot list direct actions")
        _require(target_file is None, "specification-only Figma mode cannot claim a target file")
        _require(
            classification == "not-applicable",
            "specification-only Figma mode must use not-applicable destructive classification",
        )

    specification = handoff.get("specification")
    _require(isinstance(specification, dict), "specification must be an object")
    frames = specification.get("frames")
    _require(isinstance(frames, list) and frames, "specification.frames must be a non-empty list")
    frame_names: set[str] = set()
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict), f"frames[{index}] must be an object")
        name = _text(frame.get("name"), f"frames[{index}].name")
        _require(name not in frame_names, "Figma frame names must be unique")
        frame_names.add(name)
        _require(isinstance(frame.get("width"), int) and frame["width"] > 0, f"frames[{index}].width must be positive")
        _require(isinstance(frame.get("height"), int) and frame["height"] > 0, f"frames[{index}].height must be positive")
        _text(frame.get("purpose"), f"frames[{index}].purpose", 8)

    grids = specification.get("grids")
    _require(isinstance(grids, list) and grids, "specification.grids must be a non-empty list")
    for index, grid in enumerate(grids):
        _require(isinstance(grid, dict), f"grids[{index}] must be an object")
        _text(grid.get("name"), f"grids[{index}].name")
        for field in ("columns", "gutter", "margin"):
            _require(isinstance(grid.get(field), int) and grid[field] >= 0, f"grids[{index}].{field} must be a non-negative integer")
        _require(grid["columns"] > 0, f"grids[{index}].columns must be positive")

    variables = specification.get("variables")
    _require(isinstance(variables, list) and variables, "specification.variables must be a non-empty list")
    for index, variable in enumerate(variables):
        _require(isinstance(variable, dict), f"variables[{index}] must be an object")
        _text(variable.get("collection"), f"variables[{index}].collection")
        _text(variable.get("name"), f"variables[{index}].name")
        _require(variable.get("type") in {"color", "number", "string", "boolean"}, f"variables[{index}].type is invalid")
        _strings(variable.get("modes"), f"variables[{index}].modes", 1)

    components = specification.get("components")
    _require(isinstance(components, list) and components, "specification.components must be a non-empty list")
    for index, component in enumerate(components):
        _require(isinstance(component, dict), f"components[{index}] must be an object")
        _text(component.get("name"), f"components[{index}].name")
        _strings(component.get("variants"), f"components[{index}].variants", 1)
        _strings(component.get("states"), f"components[{index}].states", 1)

    _strings(specification.get("interaction_states"), "specification.interaction_states", 1)
    _strings(specification.get("responsive_rules"), "specification.responsive_rules", 1)
    _strings(specification.get("content_guidance"), "specification.content_guidance", 1)
    _strings(specification.get("measurements"), "specification.measurements", 1)
    assets = specification.get("asset_manifest")
    _require(isinstance(assets, list), "specification.asset_manifest must be a list")
    for index, asset in enumerate(assets):
        _require(isinstance(asset, dict), f"asset_manifest[{index}] must be an object")
        _text(asset.get("id"), f"asset_manifest[{index}].id")
        _text(asset.get("type"), f"asset_manifest[{index}].type")
        _text(asset.get("source"), f"asset_manifest[{index}].source")
        _require(asset.get("rights_status") in RIGHTS_STATUSES, f"asset_manifest[{index}].rights_status is invalid")
    return handoff


def compile_figma_specification(
    handoff: dict[str, Any],
    approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> str:
    validate_figma_handoff(handoff, approval_path, project_root)
    spec = handoff["specification"]
    lines = [
        "# Figma handoff specification",
        "",
        f"Capability: `{handoff['capability']['status']}`",
        f"Mode: `{handoff['mode']}`",
        "",
        "This is a structurally valid handoff scaffold. It is not a complete or rebuild-ready specification unless project-specific cross-artifact coverage is separately verified.",
        "",
        "## Frames",
        "",
    ]
    lines.extend(f"- {item['name']}: {item['width']} x {item['height']}. {item['purpose']}" for item in spec["frames"])
    lines.extend(["", "## Grids", ""])
    lines.extend(f"- {item['name']}: {item['columns']} columns, {item['gutter']} px gutter, {item['margin']} px margin." for item in spec["grids"])
    lines.extend(["", "## Variables", ""])
    lines.extend(f"- {item['collection']} / {item['name']}: {item['type']}; modes: {', '.join(item['modes'])}." for item in spec["variables"])
    lines.extend(["", "## Components", ""])
    lines.extend(f"- {item['name']}: variants {', '.join(item['variants'])}; states {', '.join(item['states'])}." for item in spec["components"])
    for title, key in (
        ("Interaction states", "interaction_states"),
        ("Responsive rules", "responsive_rules"),
        ("Content guidance", "content_guidance"),
        ("Measurements", "measurements"),
    ):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in spec[key])
    lines.extend(["", "## Asset manifest", ""])
    if spec["asset_manifest"]:
        lines.extend(f"- {item['id']}: {item['type']} from {item['source']} ({item['rights_status']})." for item in spec["asset_manifest"])
    else:
        lines.append("- No external assets required.")
    if handoff["direct_actions"]:
        lines.extend(["", "## Authorized connection actions", ""])
        lines.append(f"- Target file: {handoff['target_file']}")
        lines.append(
            f"- Destructive classification: {handoff['destructive_action_classification']}"
        )
        lines.extend(
            f"- {item['id']}: {item['description']} Target: {item['target']}. Destructive: {str(item['destructive']).lower()}."
            for item in handoff["direct_actions"]
        )
    return "\n".join(lines) + "\n"


def validate_mobile_decision(decision: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(decision, dict), "mobile decision must be an object")
    _require(decision.get("schema_version") == "1.0", "mobile decision schema_version must be 1.0")
    _require(decision.get("artifact_status") == "ready", "mobile decision scaffold must be completed before validation")
    for field in ("approved_understanding_sha256", "ux_definition_sha256", "design_md_sha256"):
        _hash(decision.get(field), field)

    factors = decision.get("project_factors")
    _require(isinstance(factors, list), "project_factors must be a list")
    seen_factors: set[str] = set()
    for index, factor in enumerate(factors):
        _require(isinstance(factor, dict), f"project_factors[{index}] must be an object")
        name = factor.get("factor")
        _require(name in MOBILE_FACTORS and name not in seen_factors, "project factors must be complete and unique")
        seen_factors.add(name)
        _text(factor.get("finding"), f"project_factors[{index}].finding", 8)
        _text(factor.get("evidence"), f"project_factors[{index}].evidence", 5)
        _require(factor.get("confidence") in CONFIDENCE, f"project_factors[{index}].confidence is invalid")
    _require(seen_factors == MOBILE_FACTORS, "all nine mobile decision factors are required")

    options = decision.get("options")
    _require(isinstance(options, list) and all(isinstance(item, dict) for item in options), "options must be a list of objects")
    _require([item.get("id") for item in options] == list(MOBILE_OPTIONS), "options must explain responsive web, cross-platform, and native mobile in order")
    for index, option in enumerate(options):
        _require(isinstance(option, dict), f"options[{index}] must be an object")
        _text(option.get("meaning"), f"options[{index}].meaning", 12)
        consequences = option.get("consequences")
        _require(isinstance(consequences, dict) and set(consequences) == MOBILE_FACTORS, f"options[{index}] must explain all nine decision factors")
        for factor, explanation in consequences.items():
            _text(explanation, f"options[{index}].consequences.{factor}", 8)

    requirements = decision.get("requirements")
    _require(isinstance(requirements, list) and requirements, "requirements must be a non-empty list")
    requirement_ids: set[str] = set()
    linked_factors: set[str] = set()
    for index, requirement in enumerate(requirements):
        _require(isinstance(requirement, dict), f"requirements[{index}] must be an object")
        identifier = _text(requirement.get("id"), f"requirements[{index}].id")
        _require(identifier not in requirement_ids, "mobile requirement ids must be unique")
        requirement_ids.add(identifier)
        _text(requirement.get("statement"), f"requirements[{index}].statement", 8)
        _require(isinstance(requirement.get("hard"), bool), f"requirements[{index}].hard must be boolean")
        factor_ids = _strings(requirement.get("factor_ids"), f"requirements[{index}].factor_ids", 1)
        _require(set(factor_ids) <= MOBILE_FACTORS, f"requirements[{index}] cites an unknown project factor")
        linked_factors.update(factor_ids)
        compatibility = requirement.get("compatibility")
        _require(isinstance(compatibility, dict) and set(compatibility) == set(MOBILE_OPTIONS), f"requirements[{index}] must assess all mobile options")
        _require(all(isinstance(value, bool) for value in compatibility.values()), f"requirements[{index}] compatibility values must be boolean")
    _require(linked_factors == MOBILE_FACTORS, "every mobile project factor must inform at least one compatibility requirement")

    viable = [
        option
        for option in MOBILE_OPTIONS
        if all(not item["hard"] or item["compatibility"][option] for item in requirements)
    ]
    result = decision.get("routing_result")
    _require(isinstance(result, dict), "routing_result must be an object")
    status = result.get("status")
    _require(status in {"recommendation", "return-to-grilling"}, "routing_result.status is invalid")
    framework = result.get("framework_decision")
    _require(isinstance(framework, dict), "framework_decision must be an object")
    framework_status = framework.get("status")
    _require(framework_status in {"deferred", "proposed"}, "framework_decision.status is invalid")
    if framework_status == "deferred":
        _require(framework.get("name") is None, "deferred framework decision cannot name a framework")
        _text(framework.get("reason"), "framework_decision.reason", 8)
    else:
        _text(framework.get("name"), "framework_decision.name")
        _text(framework.get("reason"), "framework_decision.reason", 12)

    if viable:
        _require(status == "recommendation", "a viable mobile path must produce a recommendation")
        _require(result.get("selected") == viable[0], "mobile recommendation must choose the simplest viable option")
        _require(result.get("simplest_valid") is True, "mobile recommendation must record simplest_valid true")
        _text(result.get("rationale"), "routing_result.rationale", 12)
        _strings(result.get("questions"), "routing_result.questions")
    else:
        _require(status == "return-to-grilling", "no viable mobile path must return to grilling")
        _require(result.get("selected") is None, "return-to-grilling cannot select a mobile path")
        _require(result.get("simplest_valid") is False, "return-to-grilling must record simplest_valid false")
        _text(result.get("rationale"), "routing_result.rationale", 12)
        _strings(result.get("questions"), "routing_result.questions", 1)
        _require(framework_status == "deferred", "framework selection must remain deferred while product requirements conflict")
    return decision


def compile_mobile_decision(decision: dict[str, Any]) -> str:
    validate_mobile_decision(decision)
    result = decision["routing_result"]
    lines = [
        "# Mobile implementation decision",
        "",
        "## What mobile can mean",
        "",
    ]
    for option in decision["options"]:
        lines.extend([f"### {option['id']}", "", option["meaning"], ""])
        lines.extend(f"- {factor}: {explanation}" for factor, explanation in option["consequences"].items())
        lines.append("")
    lines.extend(["## Project evidence", ""])
    lines.extend(f"- {item['factor']}: {item['finding']} Evidence: {item['evidence']} Confidence: {item['confidence']}." for item in decision["project_factors"])
    lines.extend(["", "## Routing result", "", f"Status: `{result['status']}`"])
    if result["selected"] is not None:
        lines.append(f"Selected path: `{result['selected']}`")
    lines.extend(["", result["rationale"]])
    if result["questions"]:
        lines.extend(["", "Questions that must return to shared understanding:"])
        lines.extend(f"- {item}" for item in result["questions"])
    framework = result["framework_decision"]
    lines.extend(["", "## Framework decision", "", f"Status: `{framework['status']}`", framework["reason"]])
    if framework["name"] is not None:
        lines.append(f"Named framework: `{framework['name']}`")
    return "\n".join(lines) + "\n"


def verify_wave7(
    lock_path: str | Path,
    design_md_path: str | Path,
    tokens_path: str | Path,
    ux_path: str | Path,
    imagery_path: str | Path,
    figma_path: str | Path,
    mobile_path: str | Path,
    decision_path: str | Path | None = None,
    direction_set_path: str | Path | None = None,
    system_path: str | Path | None = None,
    token_output_dir: str | Path | None = None,
    plan_path: str | Path | None = None,
    plan_md_path: str | Path | None = None,
    generation_approval_path: str | Path | None = None,
    figma_approval_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    wave6_inputs = {
        "decision": decision_path,
        "direction set": direction_set_path,
        "design system": system_path,
        "token output directory": token_output_dir,
        "implementation plan": plan_path,
        "compiled implementation plan": plan_md_path,
    }
    missing = [name for name, value in wave6_inputs.items() if value is None]
    _require(not missing, f"Wave 7 verification requires the full Wave 6 chain; missing {missing}")
    try:
        wave6_report = verify_wave6(
            lock_path,
            decision_path,
            direction_set_path,
            ux_path,
            system_path,
            design_md_path,
            tokens_path,
            token_output_dir,
            plan_path,
            plan_md_path,
            project_root,
        )
    except Wave6ValidationError as exc:
        raise ValidationError(f"Wave 6 chain is invalid: {exc}") from exc
    lock = load_json(lock_path)
    _require(isinstance(lock, dict), "reference lock must be an object")
    lock_hash = sha256(lock_path)
    design_hash = sha256(design_md_path)
    tokens_hash = sha256(tokens_path)
    ux_hash = sha256(ux_path)
    approved_direction = _hash(lock.get("approved_direction", {}).get("decision_sha256"), "lock approved direction")
    approved_understanding = _hash(lock.get("approved_understanding_sha256"), "lock approved understanding")

    imagery = load_json(imagery_path)
    validate_imagery_plan(imagery, generation_approval_path, project_root)
    _require(imagery["approved_direction_sha256"] == approved_direction, "imagery plan is bound to a different direction")
    _require(imagery["reference_lock_sha256"] == lock_hash, "imagery plan is bound to a different reference lock")
    _require(imagery["design_md_sha256"] == design_hash, "imagery plan is bound to a different DESIGN.md")

    figma = load_json(figma_path)
    validate_figma_handoff(figma, figma_approval_path, project_root)
    _require(figma["design_md_sha256"] == design_hash, "Figma handoff is bound to a different DESIGN.md")
    _require(figma["tokens_source_sha256"] == tokens_hash, "Figma handoff is bound to a different token source")

    mobile = load_json(mobile_path)
    validate_mobile_decision(mobile)
    _require(mobile["approved_understanding_sha256"] == approved_understanding, "mobile decision is bound to a different approved understanding")
    _require(mobile["ux_definition_sha256"] == ux_hash, "mobile decision is bound to a different UX definition")
    _require(mobile["design_md_sha256"] == design_hash, "mobile decision is bound to a different DESIGN.md")
    return {
        "status": "pass",
        "wave6_status": wave6_report["status"],
        "imagery_generation_status": imagery["generation_boundary"]["status"],
        "imagery_output_ceiling": imagery["generation_boundary"]["output_ceiling"],
        "figma_capability": figma["capability"]["status"],
        "figma_mode": figma["mode"],
        "mobile_routing_status": mobile["routing_result"]["status"],
        "mobile_selected": mobile["routing_result"]["selected"],
    }


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and compile Design imagery, Figma, and mobile adapter artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("validate-imagery")
    command.add_argument("path")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("compile-imagery")
    command.add_argument("source")
    command.add_argument("output")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("validate-edit")
    command.add_argument("path")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("compile-edit")
    command.add_argument("source")
    command.add_argument("output")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("validate-figma")
    command.add_argument("path")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("compile-figma")
    command.add_argument("source")
    command.add_argument("output")
    command.add_argument("--approval")
    command.add_argument("--project-root", default=".")
    command = sub.add_parser("validate-mobile")
    command.add_argument("path")
    command = sub.add_parser("compile-mobile")
    command.add_argument("source")
    command.add_argument("output")
    command = sub.add_parser("verify-wave7")
    command.add_argument("--lock", required=True)
    command.add_argument("--decision", required=True)
    command.add_argument("--direction-set", required=True)
    command.add_argument("--design-md", required=True)
    command.add_argument("--tokens", required=True)
    command.add_argument("--ux", required=True)
    command.add_argument("--system", required=True)
    command.add_argument("--token-output-dir", required=True)
    command.add_argument("--plan", required=True)
    command.add_argument("--plan-md", required=True)
    command.add_argument("--imagery", required=True)
    command.add_argument("--figma", required=True)
    command.add_argument("--mobile", required=True)
    command.add_argument("--generation-approval")
    command.add_argument("--figma-approval")
    command.add_argument("--project-root")

    args = parser.parse_args()
    try:
        if args.command == "validate-imagery":
            validate_imagery_plan(load_json(args.path), args.approval, args.project_root)
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-imagery":
            text = compile_imagery_prompts(load_json(args.source), args.approval, args.project_root)
            _write(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        elif args.command == "validate-edit":
            validate_image_edit(load_json(args.path), args.approval, args.project_root)
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-edit":
            text = compile_image_edit(load_json(args.source), args.approval, args.project_root)
            _write(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        elif args.command == "validate-figma":
            validate_figma_handoff(load_json(args.path), args.approval, args.project_root)
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-figma":
            text = compile_figma_specification(load_json(args.source), args.approval, args.project_root)
            _write(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        elif args.command == "validate-mobile":
            validate_mobile_decision(load_json(args.path))
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-mobile":
            text = compile_mobile_decision(load_json(args.source))
            _write(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        else:
            _dump(
                verify_wave7(
                    args.lock,
                    args.design_md,
                    args.tokens,
                    args.ux,
                    args.imagery,
                    args.figma,
                    args.mobile,
                    args.decision,
                    args.direction_set,
                    args.system,
                    args.token_output_dir,
                    args.plan,
                    args.plan_md,
                    args.generation_approval,
                    args.figma_approval,
                    args.project_root,
                )
            )
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Design adapter validation failed: {exc}") from exc


if __name__ == "__main__":
    main()
