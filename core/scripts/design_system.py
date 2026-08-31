#!/usr/bin/env python3
"""Validate and compile Design Wave 6 system-definition artifacts.

Standard-library only. The runtime performs no network access, installs nothing, and
writes only the explicit output paths supplied by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_research import (
    ValidationError as ResearchValidationError,
    validate_direction_set as validate_research_direction_set,
)

DTCG_SCHEMA = "https://www.designtokens.org/schemas/2025.10/format.json"
DESIGN_EXTENSION = "com.houseofcuriosity.design"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
REFERENCE = re.compile(r"^\{([^{}]+)\}$")
CONFIDENCE = {"high", "medium", "low"}
NARROW_REFERENCE_ROLES = {
    "navigation behavior",
    "form behavior",
    "data visualization",
    "mobile behavior",
    "content hierarchy",
    "typography detail",
    "imagery treatment",
    "motion behavior",
    "component anatomy",
    "accessibility behavior",
    "flow structure",
    "density treatment",
}
RESPONSIVE_MODES = {"responsive-web", "cross-platform", "native-mobile", "multi-surface"}
FIGMA_MODES = {"not-applicable", "specification", "direct-when-authorized"}
DTCG_TYPES = {
    "color",
    "dimension",
    "fontFamily",
    "fontWeight",
    "duration",
    "cubicBezier",
    "number",
    "strokeStyle",
    "border",
    "transition",
    "shadow",
    "gradient",
    "typography",
}
COLOR_SPACES = {
    "srgb",
    "srgb-linear",
    "hsl",
    "hwb",
    "lab",
    "lch",
    "oklab",
    "oklch",
    "display-p3",
    "a98-rgb",
    "prophoto-rgb",
    "rec2020",
    "xyz-d65",
    "xyz-d50",
}
FONT_WEIGHT_NAMES = {
    "thin",
    "hairline",
    "extra-light",
    "ultra-light",
    "light",
    "normal",
    "regular",
    "book",
    "medium",
    "semi-bold",
    "demi-bold",
    "bold",
    "extra-bold",
    "ultra-bold",
    "black",
    "heavy",
    "extra-black",
    "ultra-black",
}
REQUIRED_DESIGN_SECTIONS = (
    "Provenance and Confidence",
    "Approved Shared Understanding",
    "Design North Star",
    "Product and User Principles",
    "Reference Foundation",
    "Reference Lock",
    "Information Architecture",
    "Screens and User Flows",
    "Layout and Grid",
    "Responsive Strategy",
    "Typography",
    "Color and Semantic Roles",
    "Spacing and Density",
    "Surfaces, Borders, Radius, and Elevation",
    "Components and States",
    "Navigation",
    "Forms and Validation",
    "Icons",
    "Imagery and Media",
    "Motion and Feedback",
    "Accessibility",
    "Content and Interface Copy",
    "Mobile-Specific Rules",
    "Figma Handoff Rules",
    "Implementation Rules",
    "Explicit Do Rules",
    "Explicit Do-Not Rules",
    "Decision Ledger",
    "Known Deviations",
    "Unknowns and Future Decisions",
)


class ValidationError(ValueError):
    """Raised when a Wave 6 artifact violates the approved contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{label} must be non-empty text")
    return value.strip()


def _string_list(value: Any, label: str, minimum: int = 0) -> list[str]:
    _require(isinstance(value, list) and len(value) >= minimum, f"{label} must contain at least {minimum} item(s)")
    return [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _hash(value: Any, label: str) -> str:
    digest = _text(value, label)
    _require(HEX64.fullmatch(digest) is not None, f"{label} must be a 64-character SHA-256 digest")
    return digest.lower()


def _relative_path(value: Any, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    _require(not path.is_absolute(), f"{label} must be relative")
    _require(".." not in path.parts, f"{label} cannot escape the project root")
    _require(not re.match(r"^[A-Za-z]:", raw), f"{label} must not use an absolute drive path")
    return path.as_posix()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_text(path: str | Path, text: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _write_json(path: str | Path, value: Any) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _verify_file_hash(path: str | Path, expected: str, label: str) -> None:
    actual = sha256(path)
    _require(actual == expected, f"{label} hash mismatch: expected {expected}, got {actual}")


def _validate_current_state_authority(
    project_root: str | Path | None,
    lock: dict[str, Any],
    decision_path: str | Path,
    direction_set_path: str | Path,
) -> None:
    if project_root is None:
        return
    root = Path(project_root).expanduser().resolve()
    if not (root / ".design/state.json").is_file():
        return

    from design_state_validation import load_state as load_design_state

    state = load_design_state(root)
    understanding_gate = state["gates"]["understanding"]
    direction_gate = state["gates"]["direction"]
    _require(
        isinstance(understanding_gate, dict)
        and understanding_gate.get("status") in {"approved", "skipped"},
        "Wave 6 requires a current understanding gate when Design state exists",
    )
    _require(
        isinstance(direction_gate, dict) and direction_gate.get("status") == "approved",
        "Wave 6 requires a current direction gate when Design state exists",
    )

    canonical_understanding = root / ".design/shared-understanding.md"
    canonical_decision = root / ".design/directions/decision.md"
    canonical_direction_set = root / ".design/directions/direction-set.json"
    _require(canonical_understanding.is_file(), "approved understanding artifact is missing")
    _require(Path(decision_path).resolve() == canonical_decision.resolve(), "direction decision path is not canonical")
    _require(Path(direction_set_path).resolve() == canonical_direction_set.resolve(), "direction-set path is not canonical")

    understanding_hash = sha256(canonical_understanding)
    decision_hash = sha256(canonical_decision)
    direction_set_hash = sha256(canonical_direction_set)
    _require(understanding_gate.get("artifact_sha256") == understanding_hash, "understanding gate is stale")
    _require(direction_gate.get("artifact_sha256") == decision_hash, "direction gate is stale")
    _require(
        state["artifacts"].get(".design/directions/direction-set.json") == direction_set_hash,
        "direction gate does not bind the current direction-set hash",
    )
    _require(
        lock["approved_understanding_sha256"] == understanding_hash,
        "reference lock approved understanding differs from current gate evidence",
    )
    _require(
        lock["approved_direction"]["decision_sha256"] == decision_hash,
        "reference lock approved direction differs from current gate evidence",
    )
    _require(
        lock["approved_direction"]["direction_set_sha256"] == direction_set_hash,
        "reference lock direction set differs from current gate evidence",
    )


def validate_reference_lock(
    lock: dict[str, Any],
    decision_path: str | Path | None = None,
    direction_set_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(lock, dict), "reference lock must be an object")
    _require(lock.get("schema_version") == "1.0", "reference lock schema_version must be 1.0")
    _hash(lock.get("approved_understanding_sha256"), "approved_understanding_sha256")

    approved = lock.get("approved_direction")
    _require(isinstance(approved, dict), "approved_direction must be an object")
    direction_id = _text(approved.get("id"), "approved_direction.id")
    decision_artifact = _relative_path(approved.get("decision_artifact"), "approved_direction.decision_artifact")
    _require(
        decision_artifact == ".design/directions/decision.md",
        "approved_direction.decision_artifact must be .design/directions/decision.md",
    )
    decision_hash = _hash(approved.get("decision_sha256"), "approved_direction.decision_sha256")
    direction_set_artifact = _relative_path(approved.get("direction_set_artifact"), "approved_direction.direction_set_artifact")
    _require(
        direction_set_artifact == ".design/directions/direction-set.json",
        "approved_direction.direction_set_artifact must be .design/directions/direction-set.json",
    )
    direction_set_hash = _hash(
        approved.get("direction_set_sha256"), "approved_direction.direction_set_sha256"
    )
    if decision_path is not None:
        _verify_file_hash(decision_path, decision_hash, "approved direction decision")
    if direction_set_path is not None:
        _verify_file_hash(direction_set_path, direction_set_hash, "approved direction set")

    primary = lock.get("dominant_reference")
    _require(isinstance(primary, dict), "dominant_reference must be an object")
    primary_slug = _text(primary.get("slug"), "dominant_reference.slug")
    _require(
        primary.get("responsibility") == "dominant visual foundation",
        "dominant_reference must own the dominant visual foundation",
    )

    supporting = lock.get("supporting_references")
    _require(isinstance(supporting, list) and len(supporting) <= 3, "supporting_references must contain at most 3 items")
    seen_slugs: set[str] = set()
    seen_roles: set[str] = set()
    for index, item in enumerate(supporting):
        _require(isinstance(item, dict), f"supporting_references[{index}] must be an object")
        slug = _text(item.get("slug"), f"supporting_references[{index}].slug")
        role = item.get("responsibility")
        _require(slug != primary_slug and slug not in seen_slugs, "supporting reference slugs must be distinct from the dominant source")
        _require(role in NARROW_REFERENCE_ROLES, f"supporting reference responsibility must be narrow: {sorted(NARROW_REFERENCE_ROLES)}")
        _require(role not in seen_roles, "supporting reference responsibilities must be distinct")
        _text(item.get("scope"), f"supporting_references[{index}].scope", 6)
        seen_slugs.add(slug)
        seen_roles.add(role)

    _string_list(lock.get("frozen_visual_traits"), "frozen_visual_traits", 3)
    _string_list(lock.get("allowed_variation"), "allowed_variation", 1)
    _string_list(lock.get("prohibited_drift"), "prohibited_drift", 3)
    _string_list(lock.get("assumptions"), "assumptions")
    _require(lock.get("confidence") in CONFIDENCE, "reference lock confidence is invalid")

    evidence = lock.get("evidence_links")
    _require(isinstance(evidence, list) and evidence, "evidence_links must be a non-empty list")
    for index, item in enumerate(evidence):
        _require(isinstance(item, dict), f"evidence_links[{index}] must be an object")
        _text(item.get("slug"), f"evidence_links[{index}].slug")
        _text(item.get("evidence_id"), f"evidence_links[{index}].evidence_id")

    if direction_set_path is not None:
        direction_set = load_json(direction_set_path)
        try:
            validate_research_direction_set(direction_set, project_root)
        except ResearchValidationError as exc:
            raise ValidationError(f"approved direction set is invalid: {exc}") from exc
        _require(
            direction_set.get("approved_understanding_sha256")
            == lock["approved_understanding_sha256"],
            "reference lock and direction set use different approved understandings",
        )
        matches = [item for item in direction_set.get("directions", []) if item.get("id") == direction_id]
        _require(len(matches) == 1, "approved direction id is not present exactly once in the direction set")
        chosen = matches[0]
        _require(
            chosen.get("primary_reference", {}).get("slug") == primary_slug,
            "reference lock dominant source does not match the approved direction",
        )
        direction_roles = {
            item.get("slug"): item.get("role") for item in chosen.get("secondary_references", [])
        }
        for item in supporting:
            _require(
                direction_roles.get(item["slug"]) == item["responsibility"],
                "reference lock changes a supporting source responsibility from the approved direction",
            )
    if decision_path is not None and direction_set_path is not None:
        _validate_current_state_authority(project_root, lock, decision_path, direction_set_path)
    return lock


def validate_ux_definition(ux: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(ux, dict), "UX definition must be an object")
    _require(ux.get("schema_version") == "1.0", "UX definition schema_version must be 1.0")
    _hash(ux.get("reference_lock_sha256"), "reference_lock_sha256")

    architecture = ux.get("information_architecture")
    _require(isinstance(architecture, list) and architecture, "information_architecture must be a non-empty list")
    node_ids: set[str] = set()
    for index, node in enumerate(architecture):
        _require(isinstance(node, dict), f"information_architecture[{index}] must be an object")
        node_id = _text(node.get("id"), f"information_architecture[{index}].id")
        _require(node_id not in node_ids, "information architecture ids must be unique")
        node_ids.add(node_id)
        _text(node.get("label"), f"information_architecture[{index}].label")
        _text(node.get("purpose"), f"information_architecture[{index}].purpose", 5)
    for node in architecture:
        parent = node.get("parent_id")
        _require(parent is None or parent in node_ids, "information architecture parent_id is unknown")
        _require(parent != node.get("id"), "information architecture node cannot parent itself")

    screens = ux.get("screens")
    _require(isinstance(screens, list) and screens, "screens must be a non-empty list")
    screen_ids: set[str] = set()
    for index, screen in enumerate(screens):
        _require(isinstance(screen, dict), f"screens[{index}] must be an object")
        screen_id = _text(screen.get("id"), f"screens[{index}].id")
        _require(screen_id not in screen_ids, "screen ids must be unique")
        screen_ids.add(screen_id)
        _text(screen.get("name"), f"screens[{index}].name")
        _text(screen.get("purpose"), f"screens[{index}].purpose", 5)
        _string_list(screen.get("primary_tasks"), f"screens[{index}].primary_tasks", 1)
        _string_list(screen.get("permissions"), f"screens[{index}].permissions", 1)
        _text(screen.get("responsive_behavior"), f"screens[{index}].responsive_behavior", 5)

    flows = ux.get("flows")
    _require(isinstance(flows, list) and flows, "flows must be a non-empty list")
    flow_ids: set[str] = set()
    for index, flow in enumerate(flows):
        _require(isinstance(flow, dict), f"flows[{index}] must be an object")
        flow_id = _text(flow.get("id"), f"flows[{index}].id")
        _require(flow_id not in flow_ids, "flow ids must be unique")
        flow_ids.add(flow_id)
        _text(flow.get("name"), f"flows[{index}].name")
        _require(flow.get("entry_screen") in screen_ids, f"flows[{index}].entry_screen is unknown")
        steps = _string_list(flow.get("steps"), f"flows[{index}].steps", 1)
        _require(set(steps) <= screen_ids, f"flows[{index}] contains an unknown screen")
        _text(flow.get("success_outcome"), f"flows[{index}].success_outcome", 5)
        _string_list(flow.get("error_paths"), f"flows[{index}].error_paths", 1)

    states = ux.get("states")
    _require(isinstance(states, list) and states, "states must be a non-empty list")
    state_screens: set[str] = set()
    for index, state in enumerate(states):
        _require(isinstance(state, dict), f"states[{index}] must be an object")
        screen_id = state.get("screen_id")
        _require(screen_id in screen_ids and screen_id not in state_screens, "states must cover known screens exactly once")
        state_screens.add(screen_id)
        for name in ("default", "loading", "empty", "error", "permission_denied"):
            _text(state.get(name), f"states[{index}].{name}", 4)
    _require(state_screens == screen_ids, "every screen must define default, loading, empty, error, and permission states")

    responsive = ux.get("responsive_strategy")
    _require(isinstance(responsive, dict), "responsive_strategy must be an object")
    _require(responsive.get("mode") in RESPONSIVE_MODES, "responsive_strategy.mode is invalid")
    _string_list(responsive.get("content_priority"), "responsive_strategy.content_priority", 1)
    _string_list(responsive.get("adaptation_rules"), "responsive_strategy.adaptation_rules", 1)
    breakpoints = responsive.get("breakpoints")
    _require(isinstance(breakpoints, list), "responsive_strategy.breakpoints must be a list")
    previous = -1
    for index, breakpoint in enumerate(breakpoints):
        _require(isinstance(breakpoint, dict), f"breakpoints[{index}] must be an object")
        _text(breakpoint.get("name"), f"breakpoints[{index}].name")
        width = breakpoint.get("min_width_px")
        _require(isinstance(width, int) and width >= 0 and width > previous, "breakpoints must have increasing non-negative widths")
        previous = width

    mobile = ux.get("mobile_task_model")
    _require(isinstance(mobile, dict), "mobile_task_model must be an object")
    _string_list(mobile.get("primary_tasks"), "mobile_task_model.primary_tasks", 1)
    _string_list(mobile.get("deferred_tasks"), "mobile_task_model.deferred_tasks")
    _string_list(mobile.get("device_capabilities"), "mobile_task_model.device_capabilities")
    _text(mobile.get("offline_requirements"), "mobile_task_model.offline_requirements", 3)
    _text(mobile.get("navigation_model"), "mobile_task_model.navigation_model", 3)

    accessibility = ux.get("accessibility")
    _require(isinstance(accessibility, dict), "accessibility must be an object")
    _require(
        accessibility.get("target") in {"WCAG 2.2 AA", "WCAG 2.2 AAA", "platform-native"},
        "accessibility.target must name the approved standard",
    )
    _string_list(accessibility.get("requirements"), "accessibility.requirements", 3)

    figma = ux.get("figma_handoff")
    _require(isinstance(figma, dict), "figma_handoff must be an object")
    mode = figma.get("mode")
    _require(mode in FIGMA_MODES, "figma_handoff.mode is invalid")
    if mode == "not-applicable":
        _text(figma.get("reason"), "figma_handoff.reason", 5)
    else:
        _string_list(figma.get("frames"), "figma_handoff.frames", 1)
        _string_list(figma.get("components"), "figma_handoff.components", 1)
        _string_list(figma.get("variables"), "figma_handoff.variables", 1)
        _string_list(figma.get("interactions"), "figma_handoff.interactions", 1)
    return ux


def validate_design_system(system: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(system, dict), "design system definition must be an object")
    _require(system.get("schema_version") == "1.0", "design system schema_version must be 1.0")
    for field in (
        "approved_understanding_sha256",
        "approved_direction_sha256",
        "reference_lock_sha256",
        "ux_definition_sha256",
    ):
        _hash(system.get(field), field)
    sections = system.get("sections")
    _require(isinstance(sections, dict), "design system sections must be an object")
    _require(set(REQUIRED_DESIGN_SECTIONS) <= set(sections), "design system is missing one or more canonical sections")
    _require(set(sections) <= set(REQUIRED_DESIGN_SECTIONS), "design system contains an unknown canonical section")
    for name in REQUIRED_DESIGN_SECTIONS:
        section = sections[name]
        _require(isinstance(section, dict), f"section {name} must be an object")
        rules = section.get("rules", [])
        not_applicable = section.get("not_applicable_reason")
        _require(
            (isinstance(rules, list) and bool(rules)) ^ (isinstance(not_applicable, str) and bool(not_applicable.strip())),
            f"section {name} must contain rules or one not_applicable_reason",
        )
        if rules:
            _string_list(rules, f"sections.{name}.rules", 1)
        evidence = section.get("evidence_refs", [])
        _string_list(evidence, f"sections.{name}.evidence_refs")
    return system


def compile_design_markdown(system: dict[str, Any]) -> str:
    validate_design_system(system)
    lines = [
        "# DESIGN",
        "",
        "Generated from the approved Design system definition. Recompile after changing the structured source.",
        "",
        "## Artifact bindings",
        "",
        f"- Approved understanding SHA-256: `{system['approved_understanding_sha256']}`",
        f"- Approved direction SHA-256: `{system['approved_direction_sha256']}`",
        f"- Reference lock SHA-256: `{system['reference_lock_sha256']}`",
        f"- UX definition SHA-256: `{system['ux_definition_sha256']}`",
    ]
    for name in REQUIRED_DESIGN_SECTIONS:
        section = system["sections"][name]
        lines.extend(["", f"## {name}", ""])
        if section.get("rules"):
            lines.extend(f"- {rule.strip()}" for rule in section["rules"])
        else:
            lines.append(f"Not applicable: {section['not_applicable_reason'].strip()}")
        if section.get("evidence_refs"):
            lines.extend(["", "Evidence:"])
            lines.extend(f"- `{item}`" for item in section["evidence_refs"])
    return "\n".join(lines) + "\n"


def validate_design_markdown(text: str) -> None:
    headings = [line[3:] for line in text.splitlines() if line.startswith("## ")]
    expected = ["Artifact bindings", *REQUIRED_DESIGN_SECTIONS]
    _require(headings == expected, "DESIGN.md canonical headings are missing, duplicated, or out of order")


def _collect_tokens(
    node: Any,
    path: tuple[str, ...] = (),
    inherited_type: str | None = None,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(node, dict), f"token group {'.'.join(path) or '<root>'} must be an object")
    if "$value" in node:
        token_type = node.get("$type", inherited_type)
        _require(token_type in DTCG_TYPES, f"token {'.'.join(path)} has no valid DTCG $type")
        return {
            ".".join(path): {
                "path": path,
                "type": token_type,
                "value": node["$value"],
                "description": node.get("$description"),
            }
        }
    group_type = node.get("$type", inherited_type)
    if group_type is not None:
        _require(group_type in DTCG_TYPES, f"token group {'.'.join(path) or '<root>'} has invalid $type")
    found: dict[str, dict[str, Any]] = {}
    for key, value in node.items():
        if key.startswith("$"):
            continue
        _require(isinstance(key, str) and key.strip(), "token names must be non-empty strings")
        found.update(_collect_tokens(value, (*path, key), group_type))
    return found


def _validate_token_value(token: dict[str, Any]) -> None:
    token_type = token["type"]
    value = token["value"]
    if isinstance(value, str) and REFERENCE.fullmatch(value):
        return
    label = ".".join(token["path"])
    if token_type == "color":
        _require(isinstance(value, dict), f"color token {label} must use the DTCG color object")
        _require(set(value) <= {"colorSpace", "components", "alpha", "hex"}, f"color token {label} contains an unknown property")
        _require(value.get("colorSpace") in COLOR_SPACES, f"color token {label} uses an unsupported color space")
        components = value.get("components")
        _require(isinstance(components, list) and len(components) == 3, f"color token {label} needs three components")
        space = value["colorSpace"]
        rules = {
            "srgb": ((0, 1, False),) * 3,
            "srgb-linear": ((0, 1, False),) * 3,
            "display-p3": ((0, 1, False),) * 3,
            "a98-rgb": ((0, 1, False),) * 3,
            "prophoto-rgb": ((0, 1, False),) * 3,
            "rec2020": ((0, 1, False),) * 3,
            "xyz-d65": ((0, 1, False),) * 3,
            "xyz-d50": ((0, 1, False),) * 3,
            "hsl": ((0, 360, True), (0, 100, False), (0, 100, False)),
            "hwb": ((0, 360, True), (0, 100, False), (0, 100, False)),
            "lab": ((0, 100, False), (None, None, False), (None, None, False)),
            "lch": ((0, 100, False), (0, None, False), (0, 360, True)),
            "oklab": ((0, 1, False), (None, None, False), (None, None, False)),
            "oklch": ((0, 1, False), (0, None, False), (0, 360, True)),
        }[space]
        for index, (component, rule) in enumerate(zip(components, rules)):
            _validate_component(component, f"color token {label} component {index}", *rule)
        alpha = value.get("alpha", 1)
        if not _is_property_reference(alpha):
            _require(isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and 0 <= alpha <= 1, f"color token {label} alpha must be from 0 to 1")
        if "hex" in value:
            fallback = value["hex"]
            _require(
                _is_property_reference(fallback)
                or (isinstance(fallback, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", fallback) is not None),
                f"color token {label} hex fallback must contain exactly six hexadecimal digits",
            )
    elif token_type == "dimension":
        _require(isinstance(value, dict), f"dimension token {label} must be an object")
        _require(isinstance(value.get("value"), (int, float)) and not isinstance(value.get("value"), bool), f"dimension token {label} needs a numeric value")
        _require(value.get("unit") in {"px", "rem"}, f"dimension token {label} unit must be px or rem")
    elif token_type == "fontFamily":
        _require(
            (isinstance(value, str) and bool(value.strip()))
            or (isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value)),
            f"fontFamily token {label} must be text or a non-empty text list",
        )
    elif token_type == "fontWeight":
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 1000
        named = isinstance(value, str) and value in FONT_WEIGHT_NAMES
        _require(numeric or named, f"fontWeight token {label} is invalid")
    elif token_type == "number":
        _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)), f"number token {label} must be finite")
    elif token_type == "duration":
        _require(isinstance(value, dict), f"duration token {label} must be an object")
        _require(isinstance(value.get("value"), (int, float)) and value.get("value") >= 0, f"duration token {label} must be non-negative")
        _require(value.get("unit") in {"ms", "s"}, f"duration token {label} unit must be ms or s")
    elif token_type == "cubicBezier":
        _require(isinstance(value, list) and len(value) == 4, f"cubicBezier token {label} needs four numbers")
        _require(all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value), f"cubicBezier token {label} must be numeric")
        _require(0 <= value[0] <= 1 and 0 <= value[2] <= 1, f"cubicBezier token {label} x coordinates must be from 0 to 1")
    else:
        _require(isinstance(value, (dict, list, str, int, float)), f"composite token {label} must contain JSON data")


def _is_property_reference(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"$ref"}
        and isinstance(value["$ref"], str)
        and value["$ref"].startswith("#/")
    )


def _validate_component(
    value: Any,
    label: str,
    minimum: float | None,
    maximum: float | None,
    exclusive_maximum: bool,
) -> None:
    if value == "none" or _is_property_reference(value):
        return
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric, none, or a JSON Pointer reference")
    if minimum is not None:
        _require(value >= minimum, f"{label} must be at least {minimum:g}")
    if maximum is not None:
        relation = value < maximum if exclusive_maximum else value <= maximum
        operator = "below" if exclusive_maximum else "at most"
        _require(relation, f"{label} must be {operator} {maximum:g}")


def _token_reference(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = REFERENCE.fullmatch(value)
    return match.group(1) if match else None


def _resolve_token(path: str, tokens: dict[str, dict[str, Any]], stack: tuple[str, ...] = ()) -> dict[str, Any]:
    _require(path in tokens, f"token reference {path} does not exist")
    _require(path not in stack, f"token reference cycle detected: {' -> '.join((*stack, path))}")
    token = tokens[path]
    reference = _token_reference(token["value"])
    if reference is None:
        return token
    resolved = _resolve_token(reference, tokens, (*stack, path))
    _require(resolved["type"] == token["type"], f"token reference {path} changes type from {token['type']} to {resolved['type']}")
    return resolved


def validate_token_source(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _require(isinstance(payload, dict), "token source must be an object")
    _require(payload.get("$schema") == DTCG_SCHEMA, f"token source must use {DTCG_SCHEMA}")
    extensions = payload.get("$extensions")
    _require(isinstance(extensions, dict), "token source must contain $extensions")
    design = extensions.get(DESIGN_EXTENSION)
    _require(isinstance(design, dict), f"token source must contain $extensions.{DESIGN_EXTENSION}")
    _hash(design.get("approved_direction_sha256"), "token extension approved_direction_sha256")
    strategy = design.get("existing_token_strategy")
    _require(strategy in {"new-project", "preserve", "map"}, "existing_token_strategy is invalid")
    mapping = design.get("existing_token_map", {})
    _require(isinstance(mapping, dict), "existing_token_map must be an object")
    if strategy == "map":
        _require(bool(mapping), "existing_token_strategy map requires existing_token_map entries")
    for source, target in mapping.items():
        _text(source, "existing_token_map source")
        _text(target, "existing_token_map target")

    tokens = _collect_tokens(payload)
    _require(tokens, "token source contains no tokens")
    semantic = [token for path, token in tokens.items() if path == "semantic" or path.startswith("semantic.")]
    _require(semantic, "token source must contain semantic role tokens under the semantic group")
    for token in tokens.values():
        _validate_token_value(token)
        reference = _token_reference(token["value"])
        if reference is not None:
            _resolve_token(".".join(token["path"]), tokens)
    for token in semantic:
        _require(isinstance(token.get("description"), str) and token["description"].strip(), "semantic tokens require $description role guidance")
    return tokens


def _slug(path: tuple[str, ...]) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", part.casefold()).strip("-") for part in path)


def _css_color(value: dict[str, Any]) -> str | None:
    if isinstance(value.get("hex"), str) and re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", value["hex"]):
        return value["hex"].lower()
    components = value["components"]
    alpha = value.get("alpha", 1)
    if any(_is_property_reference(component) for component in components) or _is_property_reference(alpha):
        return None
    formatted = [component if component == "none" else f"{float(component):g}" for component in components]
    alpha_suffix = "" if alpha == 1 else f" / {float(alpha):g}"
    space = value["colorSpace"]
    if space == "srgb" and all(component != "none" for component in components):
        rgb = [round(float(component) * 255) for component in components]
        if alpha < 1:
            return f"rgb({rgb[0]} {rgb[1]} {rgb[2]} / {float(alpha):g})"
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    if space in {"hsl", "hwb"}:
        return f"{space}({formatted[0]} {formatted[1]}% {formatted[2]}%{alpha_suffix})"
    if space in {"lab", "lch"}:
        return f"{space}({formatted[0]}% {formatted[1]} {formatted[2]}{alpha_suffix})"
    if space in {"oklab", "oklch"}:
        return f"{space}({formatted[0]} {formatted[1]} {formatted[2]}{alpha_suffix})"
    return f"color({space} {' '.join(formatted)}{alpha_suffix})"


def _css_value(path: str, token: dict[str, Any]) -> str | None:
    reference = _token_reference(token["value"])
    if reference is not None:
        return f"var(--design-{_slug(tuple(reference.split('.')))})"
    value = token["value"]
    if token["type"] == "color":
        return _css_color(value)
    if token["type"] in {"dimension", "duration"}:
        return f"{value['value']:g}{value['unit']}"
    if token["type"] == "fontFamily":
        values = [value] if isinstance(value, str) else value
        return ", ".join(item if item in {"serif", "sans-serif", "monospace", "system-ui"} else json.dumps(item) for item in values)
    if token["type"] in {"fontWeight", "number"}:
        return str(value)
    if token["type"] == "cubicBezier":
        return "cubic-bezier(" + ", ".join(f"{float(item):g}" for item in value) + ")"
    return None


def _tailwind_name(token: dict[str, Any]) -> str | None:
    path = token["path"]
    suffix = _slug(path[1:] if path and path[0] == "semantic" else path)
    if token["type"] == "color":
        return f"--color-{suffix}"
    if token["type"] == "fontFamily":
        return f"--font-{suffix}"
    if token["type"] == "fontWeight":
        return f"--font-weight-{suffix}"
    if token["type"] == "dimension":
        if "radius" in path:
            return f"--radius-{suffix}"
        return f"--spacing-{suffix}"
    return None


def _mobile_value(token: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    value = resolved["value"]
    result: dict[str, Any] = {
        "source_type": token["type"],
        "source_value": token["value"],
        "resolved_value": value,
    }
    reference = _token_reference(token["value"])
    if reference is not None:
        result["semantic_reference"] = reference
    if token["type"] == "dimension":
        number = float(value["value"])
        if value["unit"] == "px":
            result["android"] = {"value": number, "unit": "dp", "confidence": "high"}
            result["ios"] = {"value": number, "unit": "pt", "confidence": "high"}
        else:
            projected = number * 16
            result["android"] = {"value": projected, "unit": "dp", "confidence": "estimated"}
            result["ios"] = {"value": projected, "unit": "pt", "confidence": "estimated"}
            result["projection_note"] = "rem converted with a 16 px base; verify against the project root size"
    return result


def compile_token_outputs(payload: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    tokens = validate_token_source(payload)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "tokens.json", payload)

    css_lines = [":root {"]
    tailwind_lines = ["@theme {"]
    skipped_css: list[str] = []
    figma: list[dict[str, Any]] = []
    mobile: dict[str, Any] = {}
    for path in sorted(tokens):
        token = tokens[path]
        resolved = _resolve_token(path, tokens)
        css = _css_value(path, token)
        if css is None:
            skipped_css.append(path)
        else:
            css_lines.append(f"  --design-{_slug(token['path'])}: {css};")
            if path.startswith("semantic."):
                tailwind = _tailwind_name(token)
                if tailwind is not None:
                    tailwind_lines.append(f"  {tailwind}: var(--design-{_slug(token['path'])});")
        figma.append(
            {
                "name": "/".join(token["path"]),
                "collection": "Design semantic" if path.startswith("semantic.") else "Design foundation",
                "type": token["type"],
                "value": token["value"],
                "resolved_value": resolved["value"],
                "description": token.get("description") or "",
            }
        )
        mobile[path] = _mobile_value(token, resolved)
    css_lines.extend(["}", ""])
    tailwind_lines.extend(["}", ""])
    _write_text(root / "variables.css", "\n".join(css_lines))
    _write_text(root / "tailwind.css", "\n".join(tailwind_lines))
    _write_json(root / "figma.json", {"format": "figma-ready-variable-spec", "variables": figma})
    _write_json(root / "mobile.json", {"format": "platform-token-projection", "tokens": mobile})
    report = {
        "status": "pass",
        "dtcg_schema": DTCG_SCHEMA,
        "token_count": len(tokens),
        "semantic_token_count": sum(path.startswith("semantic.") for path in tokens),
        "css_token_count": len(tokens) - len(skipped_css),
        "css_skipped_composite_tokens": skipped_css,
        "outputs": [
            "tokens.json",
            "variables.css",
            "tailwind.css",
            "figma.json",
            "mobile.json",
            "projection-report.json",
        ],
    }
    _write_json(root / "projection-report.json", report)
    return report


def validate_implementation_plan(plan: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(plan, dict), "implementation plan must be an object")
    _require(plan.get("schema_version") == "1.0", "implementation plan schema_version must be 1.0")
    for field in ("approved_direction_sha256", "reference_lock_sha256", "ux_definition_sha256", "design_md_sha256"):
        _hash(plan.get(field), field)
    _require(
        plan.get("repository_change_gate") == "awaiting_approval",
        "new implementation plans must stop at repository_change_gate awaiting_approval",
    )
    _text(plan.get("goal"), "goal", 8)
    _string_list(plan.get("prohibited_scope"), "prohibited_scope", 1)
    quality_targets = plan.get("quality_targets")
    _require(isinstance(quality_targets, list) and quality_targets, "implementation plan quality_targets must not be empty")
    quality_ids: set[str] = set()
    for index, target in enumerate(quality_targets):
        label = f"quality_targets[{index}]"
        _require(isinstance(target, dict) and set(target) == {"id", "screen_id", "route", "state", "viewport", "theme", "reduced_motion", "required"}, f"{label} is invalid")
        target_id = _text(target["id"], f"{label}.id")
        _require(target_id not in quality_ids, "quality target ids must be unique")
        quality_ids.add(target_id)
        _text(target["screen_id"], f"{label}.screen_id")
        _require(_text(target["route"], f"{label}.route").startswith("/"), f"{label}.route must start with /")
        _text(target["state"], f"{label}.state")
        viewport = target["viewport"]
        _require(isinstance(viewport, dict) and set(viewport) == {"name", "width", "height", "device_scale_factor"}, f"{label}.viewport is invalid")
        _text(viewport["name"], f"{label}.viewport.name")
        for field, lower, upper in (("width", 240, 7680), ("height", 240, 12000)):
            value = viewport[field]
            _require(isinstance(value, int) and not isinstance(value, bool) and lower <= value <= upper, f"{label}.viewport.{field} is invalid")
        scale = viewport["device_scale_factor"]
        _require(isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0.5 <= scale <= 4, f"{label}.viewport.device_scale_factor is invalid")
        _require(target["theme"] in {"light", "dark", "system"}, f"{label}.theme is invalid")
        _require(isinstance(target["reduced_motion"], bool) and isinstance(target["required"], bool), f"{label} boolean fields are invalid")

    waves = plan.get("waves")
    _require(isinstance(waves, list) and 1 <= len(waves) <= 7, "implementation plan must contain 1 to 7 waves")
    known: set[str] = set()
    for index, wave in enumerate(waves):
        _require(isinstance(wave, dict), f"waves[{index}] must be an object")
        wave_id = _text(wave.get("id"), f"waves[{index}].id")
        _require(wave_id not in known, "wave ids must be unique")
        dependencies = _string_list(wave.get("dependencies"), f"waves[{index}].dependencies")
        _require(set(dependencies) <= known, f"waves[{index}] depends on a missing or later wave")
        known.add(wave_id)
        _text(wave.get("goal"), f"waves[{index}].goal", 8)
        _string_list(wave.get("inputs"), f"waves[{index}].inputs", 1)
        _string_list(wave.get("approved_requirements"), f"waves[{index}].approved_requirements", 1)
        _string_list(wave.get("design_sections"), f"waves[{index}].design_sections", 1)
        allowed = _string_list(wave.get("allowed_files"), f"waves[{index}].allowed_files", 1)
        for file_index, item in enumerate(allowed):
            _relative_path(item, f"waves[{index}].allowed_files[{file_index}]")
        _string_list(wave.get("work_items"), f"waves[{index}].work_items", 1)
        _string_list(wave.get("render_targets"), f"waves[{index}].render_targets", 1)
        _string_list(wave.get("tests"), f"waves[{index}].tests", 1)
        _string_list(wave.get("completion_criteria"), f"waves[{index}].completion_criteria", 1)
        _string_list(wave.get("rollback"), f"waves[{index}].rollback", 1)
        _string_list(wave.get("risks"), f"waves[{index}].risks", 1)
        _require(wave.get("status") == "planned", "implementation waves must begin with status planned")

    external = plan.get("external_actions")
    _require(isinstance(external, list), "external_actions must be a list")
    for index, item in enumerate(external):
        _require(isinstance(item, dict), f"external_actions[{index}] must be an object")
        _text(item.get("action"), f"external_actions[{index}].action")
        _require(item.get("approval") == "separate-required", "external actions must retain separate approval")
    _relative_path(plan.get("approval_artifact"), "approval_artifact")
    return plan


def compile_plan_markdown(plan: dict[str, Any]) -> str:
    validate_implementation_plan(plan)
    lines = [
        "# Design implementation plan",
        "",
        f"Goal: {plan['goal']}",
        "",
        "Repository-change gate: awaiting approval. Do not start implementation until this exact plan is approved.",
        "",
        "## Artifact bindings",
        "",
        f"- Approved direction SHA-256: `{plan['approved_direction_sha256']}`",
        f"- Reference lock SHA-256: `{plan['reference_lock_sha256']}`",
        f"- UX definition SHA-256: `{plan['ux_definition_sha256']}`",
        f"- DESIGN.md SHA-256: `{plan['design_md_sha256']}`",
        "",
        "## Approved quality targets",
        "",
    ]
    for target in plan["quality_targets"]:
        viewport = target["viewport"]
        lines.append(
            f"- `{target['id']}`: screen `{target['screen_id']}`, state `{target['state']}`, route `{target['route']}`, "
            f"viewport `{viewport['name']}` {viewport['width']}x{viewport['height']} at {viewport['device_scale_factor']}x, "
            f"theme `{target['theme']}`, reduced motion `{str(target['reduced_motion']).lower()}`, required `{str(target['required']).lower()}`"
        )
    lines.extend([
        "",
        "## Prohibited scope",
        "",
    ])
    lines.extend(f"- {item}" for item in plan["prohibited_scope"])
    for wave in plan["waves"]:
        lines.extend(["", f"## {wave['id']}: {wave['goal']}", ""])
        for label, key in (
            ("Dependencies", "dependencies"),
            ("Inputs", "inputs"),
            ("Approved design requirements", "approved_requirements"),
            ("Relevant DESIGN.md sections", "design_sections"),
            ("Files allowed to change", "allowed_files"),
            ("Work items", "work_items"),
            ("Render targets", "render_targets"),
            ("Tests", "tests"),
            ("Completion criteria", "completion_criteria"),
            ("Rollback", "rollback"),
            ("Risks", "risks"),
        ):
            lines.extend([f"### {label}", ""])
            items = wave[key]
            if items:
                lines.extend(f"- {item}" for item in items)
            else:
                lines.append("- None.")
            lines.append("")
    lines.extend(["## External actions", ""])
    if plan["external_actions"]:
        lines.extend(
            f"- {item['action']}: separate approval required." for item in plan["external_actions"]
        )
    else:
        lines.append("- None planned.")
    lines.extend(["", f"Approval artifact: `{plan['approval_artifact']}`", ""])
    return "\n".join(lines)


def verify_wave6(
    lock_path: str | Path,
    decision_path: str | Path,
    direction_set_path: str | Path,
    ux_path: str | Path,
    system_path: str | Path,
    design_md_path: str | Path,
    tokens_path: str | Path,
    token_output_dir: str | Path,
    plan_path: str | Path,
    plan_md_path: str | Path,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    if project_root is None:
        candidate = Path(lock_path).expanduser().resolve().parents[2]
        if (candidate / ".design/state.json").is_file():
            project_root = candidate
    lock = load_json(lock_path)
    validate_reference_lock(lock, decision_path, direction_set_path, project_root)
    lock_hash = sha256(lock_path)

    ux = load_json(ux_path)
    validate_ux_definition(ux)
    _require(ux["reference_lock_sha256"] == lock_hash, "UX definition is bound to a different reference lock")
    ux_hash = sha256(ux_path)

    system = load_json(system_path)
    validate_design_system(system)
    _require(
        system["approved_understanding_sha256"] == lock["approved_understanding_sha256"],
        "design system is bound to a different approved understanding",
    )
    approved_hash = lock["approved_direction"]["decision_sha256"]
    _require(
        system["approved_direction_sha256"] == approved_hash,
        "design system is bound to a different approved direction",
    )
    _require(system["reference_lock_sha256"] == lock_hash, "design system is bound to a different reference lock")
    _require(system["ux_definition_sha256"] == ux_hash, "design system is bound to a different UX definition")
    design_text = Path(design_md_path).read_text(encoding="utf-8")
    validate_design_markdown(design_text)
    _require(design_text == compile_design_markdown(system), "DESIGN.md is stale or was not compiled from the supplied system definition")

    token_payload = load_json(tokens_path)
    token_report = compile_token_outputs(token_payload, token_output_dir)
    token_extension = token_payload["$extensions"][DESIGN_EXTENSION]
    _require(token_extension["approved_direction_sha256"] == approved_hash, "tokens are bound to a different approved direction")

    plan = load_json(plan_path)
    validate_implementation_plan(plan)
    _require(plan["approved_direction_sha256"] == approved_hash, "implementation plan is bound to a different direction")
    _require(plan["reference_lock_sha256"] == lock_hash, "implementation plan is bound to a different reference lock")
    _require(plan["ux_definition_sha256"] == ux_hash, "implementation plan is bound to a different UX definition")
    _require(plan["design_md_sha256"] == sha256(design_md_path), "implementation plan is bound to a different DESIGN.md")
    ux_screens = {item["id"] for item in ux["screens"]}
    ux_states = {item["screen_id"]: set(item).difference({"screen_id"}) for item in ux["states"]}
    for target in plan["quality_targets"]:
        _require(target["screen_id"] in ux_screens, f"quality target {target['id']} uses an unknown UX screen")
        _require(target["state"] in ux_states.get(target["screen_id"], set()), f"quality target {target['id']} uses an unknown UX state")
    plan_text = Path(plan_md_path).read_text(encoding="utf-8")
    _require(
        plan_text == compile_plan_markdown(plan),
        "implementation plan Markdown is stale or was not compiled from the supplied structured plan",
    )
    return {
        "status": "pass",
        "reference_lock_sha256": lock_hash,
        "ux_definition_sha256": ux_hash,
        "design_md_sha256": sha256(design_md_path),
        "implementation_plan_sha256": sha256(plan_md_path),
        "token_report": token_report,
        "implementation_waves": len(plan["waves"]),
        "repository_change_gate": plan["repository_change_gate"],
    }


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and compile Design reference lock, UX, DESIGN.md, tokens, and implementation plans."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("validate-lock")
    command.add_argument("path")
    command.add_argument("--decision")
    command.add_argument("--direction-set")
    command.add_argument("--project-root", default=".")

    command = sub.add_parser("validate-ux")
    command.add_argument("path")

    command = sub.add_parser("compile-design")
    command.add_argument("source")
    command.add_argument("output")

    command = sub.add_parser("validate-design")
    command.add_argument("path")

    command = sub.add_parser("compile-tokens")
    command.add_argument("source")
    command.add_argument("output_dir")

    command = sub.add_parser("validate-plan")
    command.add_argument("path")

    command = sub.add_parser("compile-plan")
    command.add_argument("source")
    command.add_argument("output")

    command = sub.add_parser("verify-wave6")
    command.add_argument("--lock", required=True)
    command.add_argument("--decision", required=True)
    command.add_argument("--direction-set", required=True)
    command.add_argument("--ux", required=True)
    command.add_argument("--system", required=True)
    command.add_argument("--design-md", required=True)
    command.add_argument("--tokens", required=True)
    command.add_argument("--token-output-dir", required=True)
    command.add_argument("--plan", required=True)
    command.add_argument("--plan-md", required=True)
    command.add_argument("--project-root")

    args = parser.parse_args()
    try:
        if args.command == "validate-lock":
            validate_reference_lock(
                load_json(args.path),
                args.decision,
                args.direction_set,
                args.project_root,
            )
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "validate-ux":
            validate_ux_definition(load_json(args.path))
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-design":
            text = compile_design_markdown(load_json(args.source))
            _write_text(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        elif args.command == "validate-design":
            validate_design_markdown(Path(args.path).read_text(encoding="utf-8"))
            _dump({"status": "pass", "artifact": args.path, "sha256": sha256(args.path)})
        elif args.command == "compile-tokens":
            _dump(compile_token_outputs(load_json(args.source), args.output_dir))
        elif args.command == "validate-plan":
            validate_implementation_plan(load_json(args.path))
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "compile-plan":
            text = compile_plan_markdown(load_json(args.source))
            _write_text(args.output, text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        else:
            _dump(
                verify_wave6(
                    args.lock,
                    args.decision,
                    args.direction_set,
                    args.ux,
                    args.system,
                    args.design_md,
                    args.tokens,
                    args.token_output_dir,
                    args.plan,
                    args.plan_md,
                    args.project_root,
                )
            )
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Design system validation failed: {exc}") from exc


if __name__ == "__main__":
    main()
