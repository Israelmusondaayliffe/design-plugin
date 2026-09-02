#!/usr/bin/env python3
"""Validate rendering, QA, repair, deviation, scorecard, and learning evidence.

The runtime is host-neutral and standard-library only. It never installs tools,
starts servers, opens browsers, edits product files, activates learning, or
accesses the network. Host capabilities create captures and check evidence;
this runtime binds those artifacts to the approved Design state.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import struct
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_state_validation import load_state, sha256


class QualityError(RuntimeError):
    """Raised when quality evidence is incomplete, stale, or unsafe."""


HASH_CHARS = set("0123456789abcdef")
QUALITY_CATEGORIES = {
    "visual",
    "typography",
    "spacing",
    "color-roles",
    "media",
    "hierarchy",
    "responsive",
    "accessibility",
    "states",
    "overflow",
    "touch",
    "motion",
    "interaction",
    "content",
    "code",
    "reference",
}
SEVERITIES = {"P0", "P1", "P2", "P3"}
TRUTH_CLASSES = {"observed", "measured", "inferred", "estimated", "recommended", "unknown"}
CONFIDENCE_LEVELS = {"high", "medium", "low", "unknown"}
EVIDENCE_STATUSES = {"pass", "pass-with-deviation", "fail", "blocked"}
FINDING_TYPES = {
    "implementation-defect",
    "usability-defect",
    "accessibility-defect",
    "responsive-defect",
    "design-system-drift",
    "content-defect",
    "evidence-limitation",
    "subjective-opportunity",
}
FORBIDDEN_LEARNING_TEXT = (
    "/Users/",
    "C:\\Users\\",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
)
FORBIDDEN_LEARNING_KEYS = {
    "access_token",
    "api_key",
    "client_secret",
    "password",
    "private_key",
    "refresh_token",
    "benchmark",
    "benchmark_data",
}
ABSOLUTE_PATH_PATTERN = re.compile(r"(^|[\s`'\"(])/(?:Users|home|root|private|var|etc|opt|srv|tmp)/[^\s`'\")]+")
SECRET_TOKEN_PATTERN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"
)
EVIDENCE_DISCLAIMER_PATTERN = re.compile(
    r"\b(?:synthetic|fixture|no browser|no visual inspection|no accessibility inspection|not runtime|not performed|unavailable)\b",
    re.IGNORECASE,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QualityError(message)


def _text(value: Any, label: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{label} must be non-empty")
    _require("\x00" not in value and "\n" not in value, f"{label} must be one line")
    return value.strip()


def _strings(value: Any, label: str, minimum: int = 0) -> list[str]:
    _require(isinstance(value, list) and len(value) >= minimum, f"{label} must contain at least {minimum} items")
    for index, item in enumerate(value):
        _text(item, f"{label}[{index}]")
    return value


def _hash(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and len(value) == 64 and set(value) <= HASH_CHARS,
        f"{label} must be a lowercase SHA-256",
    )
    return value


def _timestamp(value: Any, label: str) -> str:
    text = _text(value, label)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityError(f"{label} must be ISO-8601") from exc
    return text


def _scan_learning_value(value: Any, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            _require(normalized not in FORBIDDEN_LEARNING_KEYS, f"{label} contains a forbidden secret field: {key}")
            _scan_learning_value(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_learning_value(item, f"{label}[{index}]")
    elif isinstance(value, str):
        _require(
            not any(marker in value for marker in FORBIDDEN_LEARNING_TEXT)
            and ABSOLUTE_PATH_PATTERN.search(value) is None
            and SECRET_TOKEN_PATTERN.search(value) is None,
            f"{label} contains an absolute user path, secret token, or private-key marker",
        )


def _reject_passing_disclaimer(values: list[str], label: str) -> None:
    _require(
        all(EVIDENCE_DISCLAIMER_PATTERN.search(value) is None for value in values),
        f"{label} explicitly disclaims the observation required for a passing result",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative_path(value: Any, label: str) -> str:
    text = _text(value, label).replace("\\", "/")
    pure = PurePosixPath(text)
    _require(not pure.is_absolute() and ".." not in pure.parts, f"{label} must stay inside the project")
    _require(not (pure.parts and ":" in pure.parts[0]), f"{label} must not be drive-qualified")
    return pure.as_posix()


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QualityError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QualityError(f"Invalid JSON in {path}: {exc}") from exc
    _require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def _resolve_inside(root: Path, value: str | Path, label: str, *, must_exist: bool = True) -> tuple[Path, str]:
    raw = Path(value).expanduser()
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise QualityError(f"{label} must stay inside the project root") from exc
    relative_path(relative, label)
    if must_exist:
        _require(path.is_file(), f"{label} does not exist: {relative}")
    return path, relative


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".design-quality-", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected.difference(value))
    extra = sorted(set(value).difference(expected))
    _require(not missing and not extra, f"{label} keys invalid; missing={missing}, extra={extra}")


def _state_binding(root: Path, *, allowed_phases: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    state = load_state(root)
    _require(state["phase"] in allowed_phases, f"State phase must be one of {sorted(allowed_phases)}")
    _require(state["status"] == "active", "Quality work requires active state")
    relative = ".design/state.json"
    path = root / relative
    return state, {
        "path": relative,
        "sha256": sha256(path),
        "revision": state["revision"],
        "workflow": state["workflow"],
        "phase": state["phase"],
        "repair_cycle": state["repair_cycle"],
        "repair_pass": state["repair_pass"],
        "repair_attempts": dict(sorted(state.get("repair_attempts", {}).items())),
    }


def _validate_state_binding(
    root: Path,
    binding: Any,
    label: str,
    *,
    allowed_phases: set[str],
    check_current: bool,
) -> dict[str, Any]:
    _require(isinstance(binding, dict), f"{label} must be an object")
    _exact_keys(
        binding,
        {"path", "sha256", "revision", "workflow", "phase", "repair_cycle", "repair_pass", "repair_attempts"},
        label,
    )
    _require(relative_path(binding["path"], f"{label}.path") == ".design/state.json", f"{label}.path must be .design/state.json")
    _hash(binding["sha256"], f"{label}.sha256")
    _require(isinstance(binding["revision"], int) and not isinstance(binding["revision"], bool) and binding["revision"] >= 0, f"{label}.revision must be non-negative")
    _require(binding["workflow"] in {"run", "audit"}, f"{label}.workflow is invalid")
    _require(binding["phase"] in allowed_phases, f"{label}.phase is invalid")
    _require(isinstance(binding["repair_cycle"], int) and not isinstance(binding["repair_cycle"], bool) and binding["repair_cycle"] >= 0, f"{label}.repair_cycle is invalid")
    _require(isinstance(binding["repair_pass"], int) and not isinstance(binding["repair_pass"], bool) and 0 <= binding["repair_pass"] <= 3, f"{label}.repair_pass is invalid")
    attempts = binding["repair_attempts"]
    _require(isinstance(attempts, dict), f"{label}.repair_attempts must be an object")
    for target, count in attempts.items():
        _text(target, f"{label}.repair_attempts key")
        _require(isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= 3, f"{label}.repair_attempts[{target}] must be 1 to 3")
    if check_current:
        state = load_state(root)
        _require(state["phase"] in allowed_phases and state["status"] == "active", f"Current state does not permit {label}")
        _require(sha256(root / ".design/state.json") == binding["sha256"], f"{label} is stale")
        _require(state["revision"] == binding["revision"], f"{label}.revision is stale")
        _require(state["workflow"] == binding["workflow"], f"{label}.workflow changed")
        _require(state["repair_cycle"] == binding["repair_cycle"], f"{label}.repair_cycle changed")
        _require(state["repair_pass"] == binding["repair_pass"], f"{label}.repair_pass changed")
        _require(state.get("repair_attempts", {}) == attempts, f"{label}.repair_attempts changed")
        return state
    return binding


def _artifact_ref(root: Path, value: Any, label: str, *, state: dict[str, Any] | None = None) -> tuple[Path, str]:
    _require(isinstance(value, dict), f"{label} must be an object")
    _exact_keys(value, {"path", "sha256"}, label)
    path, relative = _resolve_inside(root, value["path"], f"{label}.path")
    digest = _hash(value["sha256"], f"{label}.sha256")
    _require(sha256(path) == digest, f"{label} hash is stale")
    if state is not None:
        _require(state["artifacts"].get(relative) == digest, f"{label} is not bound in state")
    return path, relative


def _validate_origin(origin: Any, workflow: str) -> dict[str, Any]:
    _require(isinstance(origin, dict), "origin must be an object")
    _exact_keys(origin, {"kind", "url"}, "origin")
    _require(origin["kind"] in {"local", "external-read", "existing-captures"}, "origin.kind is invalid")
    url = _text(origin["url"], "origin.url")
    parsed = urlparse(url)
    if origin["kind"] == "local":
        _require(parsed.scheme in {"http", "https"}, "local origin must use http or https")
        _require(parsed.hostname in {"localhost", "127.0.0.1", "::1"}, "local origin must be loopback-only")
    elif origin["kind"] == "external-read":
        _require(workflow == "audit", "external-read origins are audit-only")
        _require(parsed.scheme in {"http", "https"} and bool(parsed.hostname), "external-read origin must be a valid http URL")
    else:
        _require(url == "not-applicable", "existing-captures origin URL must be not-applicable")
    return origin


def _validate_server(server: Any, origin_kind: str) -> dict[str, Any]:
    _require(isinstance(server, dict), "server must be an object")
    _exact_keys(server, {"mode", "command", "cwd", "readiness_path", "limitations"}, "server")
    _require(server["mode"] in {"managed", "already-running", "not-applicable"}, "server.mode is invalid")
    command = _strings(server["command"], "server.command")
    cwd = relative_path(server["cwd"], "server.cwd")
    readiness = _text(server["readiness_path"], "server.readiness_path")
    _strings(server["limitations"], "server.limitations")
    if server["mode"] == "managed":
        _require(origin_kind == "local" and command, "managed server requires a local origin and an explicit argv command")
        for index, item in enumerate(command):
            _require("\x00" not in item and "\n" not in item, f"server.command[{index}] is invalid")
    else:
        _require(not command, f"server.command must be empty for {server['mode']}")
    if server["mode"] == "not-applicable":
        _require(origin_kind != "local" or bool(server["limitations"]), "a local render without a server needs a limitation note")
    _require(readiness.startswith("/") or readiness == "not-applicable", "server.readiness_path must be a route or not-applicable")
    return {**server, "cwd": cwd}


def _validate_viewport(viewport: Any, label: str) -> dict[str, Any]:
    _require(isinstance(viewport, dict), f"{label} must be an object")
    _exact_keys(viewport, {"name", "width", "height", "device_scale_factor"}, label)
    _text(viewport["name"], f"{label}.name")
    for key, lower, upper in (("width", 240, 7680), ("height", 240, 12000)):
        value = viewport[key]
        _require(isinstance(value, int) and not isinstance(value, bool) and lower <= value <= upper, f"{label}.{key} must be {lower} to {upper}")
    scale = viewport["device_scale_factor"]
    _require(isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0.5 <= scale <= 4, f"{label}.device_scale_factor must be 0.5 to 4")
    return viewport


def _validate_reference(root: Path, value: Any, label: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object")
    _exact_keys(value, {"kind", "path", "sha256", "role", "comparison_dimensions"}, label)
    _require(value["kind"] in {"reference-lock", "design-authority", "baseline-render", "bounded-external"}, f"{label}.kind is invalid")
    path, relative = _resolve_inside(root, value["path"], f"{label}.path")
    digest = _hash(value["sha256"], f"{label}.sha256")
    _require(sha256(path) == digest, f"{label} is stale")
    _require(value["role"] in {"screen", "flow", "style", "design-system", "baseline"}, f"{label}.role is invalid")
    dimensions = _strings(value["comparison_dimensions"], f"{label}.comparison_dimensions", 1)
    _require(len(dimensions) == len(set(dimensions)), f"{label}.comparison_dimensions must be unique")
    return {**value, "path": relative}


def _renderable_repair_targets(repair_plan: dict[str, Any]) -> set[str]:
    """Return repair targets that can map to approved screen captures.

    ``project`` is the QA sentinel for code-level findings. It remains in the
    repair record, but it is not a screen and cannot be a render target. Run
    workflows already require the complete approved quality-target matrix, so
    a project-level repair still receives the full fresh capture set.
    """
    return {target_id for target_id in repair_plan["rerender_targets"] if target_id != "project"}


def create_render_plan(root: Path, request_path: str | Path, output_path: str | Path, *, at: str | None = None) -> dict[str, Any]:
    request = load_json(request_path)
    _exact_keys(
        request,
        {
            "schema_version",
            "workflow",
            "origin",
            "server",
            "authority_artifacts",
            "targets",
            "applicable_checks",
            "capture_owner",
            "requested_at",
        },
        "render request",
    )
    _require(request["schema_version"] == "1.0", "render request schema_version must be 1.0")
    _require(request["workflow"] in {"run", "audit"}, "render request workflow is invalid")
    allowed_phases = {"rendering"} if request["workflow"] == "run" else {"qa", "rendering"}
    state, binding = _state_binding(root, allowed_phases=allowed_phases)
    _require(state["workflow"] == request["workflow"], "render request workflow does not match state")
    origin = _validate_origin(request["origin"], request["workflow"])
    server = _validate_server(request["server"], origin["kind"])
    owner = _text(request["capture_owner"], "capture_owner")
    _timestamp(request["requested_at"], "requested_at")

    authority = request["authority_artifacts"]
    _require(isinstance(authority, list) and authority, "authority_artifacts must contain at least one item")
    authority_rows: list[dict[str, Any]] = []
    authority_paths: set[str] = set()
    for index, item in enumerate(authority):
        _require(isinstance(item, dict), f"authority_artifacts[{index}] must be an object")
        _exact_keys(item, {"path", "role"}, f"authority_artifacts[{index}]")
        path, relative = _resolve_inside(root, item["path"], f"authority_artifacts[{index}].path")
        _require(relative not in authority_paths, "authority artifact paths must be unique")
        authority_paths.add(relative)
        role = _text(item["role"], f"authority_artifacts[{index}].role")
        authority_rows.append({"path": relative, "sha256": sha256(path), "role": role})

    checks = _strings(request["applicable_checks"], "applicable_checks", 1)
    _require(set(checks) <= QUALITY_CATEGORIES, "applicable_checks contains an unknown category")
    _require(len(checks) == len(set(checks)), "applicable_checks must be unique")
    for required in ("visual", "responsive", "accessibility", "reference"):
        _require(required in checks, f"applicable_checks must include {required}")

    targets = request["targets"]
    _require(isinstance(targets, list) and targets, "targets must contain at least one render target")
    target_rows: list[dict[str, Any]] = []
    target_ids: set[str] = set()
    outputs: set[str] = set()
    for index, item in enumerate(targets):
        label = f"targets[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(
            item,
            {"id", "screen_id", "route", "state", "viewport", "theme", "reduced_motion", "output", "required", "reference"},
            label,
        )
        target_id = _text(item["id"], f"{label}.id")
        _require(target_id not in target_ids, "render target IDs must be unique")
        target_ids.add(target_id)
        screen_id = _text(item["screen_id"], f"{label}.screen_id")
        route = _text(item["route"], f"{label}.route")
        _require(route.startswith("/") or route == "not-applicable", f"{label}.route must be a route or not-applicable")
        if origin["kind"] != "existing-captures":
            _require(route != "not-applicable", f"{label}.route is required for browser captures")
        state_label = _text(item["state"], f"{label}.state")
        viewport = _validate_viewport(item["viewport"], f"{label}.viewport")
        _require(item["theme"] in {"light", "dark", "system"}, f"{label}.theme is invalid")
        _require(isinstance(item["reduced_motion"], bool), f"{label}.reduced_motion must be boolean")
        output = relative_path(item["output"], f"{label}.output")
        _require(output.startswith(".design/renders/captures/") and output.endswith(".png"), f"{label}.output must be a PNG under .design/renders/captures/")
        _require(output not in outputs, "render outputs must be unique")
        outputs.add(output)
        _require(isinstance(item["required"], bool), f"{label}.required must be boolean")
        reference = item["reference"]
        _require(isinstance(reference, dict), f"{label}.reference must be an object")
        _exact_keys(reference, {"kind", "path", "role", "comparison_dimensions"}, f"{label}.reference")
        reference_path, reference_relative = _resolve_inside(root, reference["path"], f"{label}.reference.path")
        compiled_reference = {
            "kind": reference["kind"],
            "path": reference_relative,
            "sha256": sha256(reference_path),
            "role": reference["role"],
            "comparison_dimensions": reference["comparison_dimensions"],
        }
        compiled_reference = _validate_reference(root, compiled_reference, f"{label}.reference")
        source_url = "not-applicable" if origin["kind"] == "existing-captures" else urljoin(origin["url"].rstrip("/") + "/", route.lstrip("/"))
        target_rows.append(
            {
                "id": target_id,
                "screen_id": screen_id,
                "route": route,
                "source_url": source_url,
                "state": state_label,
                "viewport": viewport,
                "theme": item["theme"],
                "reduced_motion": item["reduced_motion"],
                "output": output,
                "required": item["required"],
                "reference": compiled_reference,
            }
        )

    output, output_relative = _resolve_inside(root, output_path, "render plan output", must_exist=False)
    _require(output_relative == ".design/renders/plan.json", "render plan must use .design/renders/plan.json")
    plan = {
        "schema_version": "1.0",
        "workflow": request["workflow"],
        "state_binding": binding,
        "origin": origin,
        "server": server,
        "authority_artifacts": authority_rows,
        "targets": target_rows,
        "applicable_checks": checks,
        "capture_owner": owner,
        "status": "planned",
        "created_at": at or utc_now(),
    }
    validate_render_plan(root, plan, check_current_state=True)
    _atomic_write_json(output, plan)
    return plan


def validate_render_plan(root: Path, plan: dict[str, Any], *, check_current_state: bool) -> dict[str, Any]:
    _exact_keys(
        plan,
        {
            "schema_version",
            "workflow",
            "state_binding",
            "origin",
            "server",
            "authority_artifacts",
            "targets",
            "applicable_checks",
            "capture_owner",
            "status",
            "created_at",
        },
        "render plan",
    )
    _require(plan["schema_version"] == "1.0" and plan["status"] == "planned", "render plan version or status is invalid")
    _require(plan["workflow"] in {"run", "audit"}, "render plan workflow is invalid")
    allowed_phases = {"rendering"} if plan["workflow"] == "run" else {"qa", "rendering"}
    _validate_state_binding(root, plan["state_binding"], "state_binding", allowed_phases=allowed_phases, check_current=check_current_state)
    current_state = load_state(root)
    origin = _validate_origin(plan["origin"], plan["workflow"])
    _validate_server(plan["server"], origin["kind"])
    authority = plan["authority_artifacts"]
    _require(isinstance(authority, list) and authority, "authority_artifacts must not be empty")
    paths: set[str] = set()
    for index, item in enumerate(authority):
        _require(isinstance(item, dict), f"authority_artifacts[{index}] must be an object")
        _exact_keys(item, {"path", "sha256", "role"}, f"authority_artifacts[{index}]")
        path, relative = _resolve_inside(root, item["path"], f"authority_artifacts[{index}].path")
        _require(relative not in paths, "authority artifact paths must be unique")
        paths.add(relative)
        _require(sha256(path) == _hash(item["sha256"], f"authority_artifacts[{index}].sha256"), f"authority_artifacts[{index}] is stale")
        _text(item["role"], f"authority_artifacts[{index}].role")
    ux_screens: set[str] = set()
    ux_states: dict[str, set[str]] = {}
    approved_quality_targets: dict[str, dict[str, Any]] = {}
    if plan["workflow"] == "run":
        required_authority = {
            ".design/system/reference-lock.json",
            ".design/system/ux-definition.json",
            ".design/implementation/plan.json",
            "DESIGN.md",
        }
        _require(required_authority <= paths, f"run render authority is missing {sorted(required_authority - paths)}")
        gate = current_state["gates"]["repository_changes"]
        _require(isinstance(gate, dict) and gate.get("status") == "approved", "run rendering requires current repository-change approval")
        approval_path, approval_relative = _resolve_inside(root, gate.get("artifact_path"), "repository approval")
        _require(approval_relative == ".design/implementation/plan.md", "repository approval must use the canonical implementation plan")
        _require(sha256(approval_path) == gate.get("artifact_sha256"), "repository approval is stale")
        from design_build import compile_plan_markdown, load_json as load_build_json, validate_plan

        structured_path = root / ".design/implementation/plan.json"
        structured_plan = validate_plan(load_build_json(structured_path))
        approved_quality_targets = {target["id"]: target for target in structured_plan["quality_targets"]}
        _require(approval_path.read_text(encoding="utf-8") == compile_plan_markdown(structured_plan), "structured implementation plan does not compile to the current repository approval")
        _require(sha256(root / ".design/system/reference-lock.json") == structured_plan["reference_lock_sha256"], "reference lock differs from the approved implementation plan")
        _require(sha256(root / ".design/system/ux-definition.json") == structured_plan["ux_definition_sha256"], "UX definition differs from the approved implementation plan")
        _require(sha256(root / "DESIGN.md") == structured_plan["design_md_sha256"], "DESIGN.md differs from the approved implementation plan")
        ux = load_json(root / ".design/system/ux-definition.json")
        ux_screens = {item.get("id") for item in ux.get("screens", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
        ux_states = {
            item["screen_id"]: set(item).difference({"screen_id"})
            for item in ux.get("states", [])
            if isinstance(item, dict) and isinstance(item.get("screen_id"), str)
        }
    checks = _strings(plan["applicable_checks"], "applicable_checks", 1)
    _require(set(checks) <= QUALITY_CATEGORIES and len(checks) == len(set(checks)), "applicable_checks is invalid")
    for required in ("visual", "responsive", "accessibility", "reference"):
        _require(required in checks, f"applicable_checks must include {required}")
    targets = plan["targets"]
    _require(isinstance(targets, list) and targets, "render plan needs targets")
    ids: set[str] = set()
    outputs: set[str] = set()
    for index, target in enumerate(targets):
        label = f"targets[{index}]"
        _require(isinstance(target, dict), f"{label} must be an object")
        _exact_keys(target, {"id", "screen_id", "route", "source_url", "state", "viewport", "theme", "reduced_motion", "output", "required", "reference"}, label)
        target_id = _text(target["id"], f"{label}.id")
        _require(target_id not in ids, "render target IDs must be unique")
        ids.add(target_id)
        screen_id = _text(target["screen_id"], f"{label}.screen_id")
        route = _text(target["route"], f"{label}.route")
        _require(route.startswith("/") or route == "not-applicable", f"{label}.route is invalid")
        source_url = _text(target["source_url"], f"{label}.source_url")
        expected_url = "not-applicable" if origin["kind"] == "existing-captures" else urljoin(origin["url"].rstrip("/") + "/", route.lstrip("/"))
        _require(source_url == expected_url, f"{label}.source_url does not match origin and route")
        state_label = _text(target["state"], f"{label}.state")
        if plan["workflow"] == "run":
            _require(screen_id in ux_screens, f"{label}.screen_id is not in the approved UX definition")
            _require(state_label in ux_states.get(screen_id, set()), f"{label}.state is not approved for screen {screen_id}")
        _validate_viewport(target["viewport"], f"{label}.viewport")
        _require(target["theme"] in {"light", "dark", "system"}, f"{label}.theme is invalid")
        _require(isinstance(target["reduced_motion"], bool) and isinstance(target["required"], bool), f"{label} boolean fields are invalid")
        output = relative_path(target["output"], f"{label}.output")
        _require(output.startswith(".design/renders/captures/") and output.endswith(".png"), f"{label}.output is invalid")
        _require(output not in outputs, "render outputs must be unique")
        outputs.add(output)
        _validate_reference(root, target["reference"], f"{label}.reference")
        if plan["workflow"] == "run":
            _require(target_id in approved_quality_targets, f"{label}.id is not an approved quality target")
            approved = approved_quality_targets[target_id]
            for field in ("screen_id", "route", "state", "viewport", "theme", "reduced_motion", "required"):
                _require(target[field] == approved[field], f"{label}.{field} differs from the approved quality target")
    if plan["workflow"] == "run":
        _require(ids == set(approved_quality_targets), "render plan must cover every approved quality target exactly")
        if current_state["repair_cycle"] > 0:
            repair_relative = f".design/qa/repairs/cycle-{current_state['repair_cycle']}.json"
            repair_path = root / repair_relative
            _require(repair_path.is_file() and current_state["artifacts"].get(repair_relative) == sha256(repair_path), "current repair plan is not bound in state")
            repair_plan = validate_repair_plan(root, load_json(repair_path), state=current_state)
            _require(_renderable_repair_targets(repair_plan) <= ids, "render plan omits a required repair rerender target")
    if "motion" in checks:
        _require(any(target["reduced_motion"] for target in targets), "motion QA requires a reduced-motion target")
    _text(plan["capture_owner"], "capture_owner")
    _timestamp(plan["created_at"], "created_at")
    return plan


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    _require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"Capture has an invalid PNG signature: {path}")
    offset = 8
    width = height = 0
    bit_depth = color_type = 0
    saw_ihdr = False
    saw_idat = False
    saw_plte = False
    saw_iend = False
    idat_parts: list[bytes] = []
    while offset < len(data):
        _require(offset + 12 <= len(data), f"Capture has a truncated PNG chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        _require(chunk_end <= len(data), f"Capture has a truncated PNG chunk: {path}")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = binascii.crc32(kind + payload) & 0xFFFFFFFF
        _require(actual_crc == expected_crc, f"Capture has an invalid PNG chunk checksum: {path}")
        if kind == b"IHDR":
            _require(not saw_ihdr and offset == 8 and length == 13, f"Capture has an invalid PNG header chunk: {path}")
            width, height = struct.unpack(">II", payload[:8])
            bit_depth, color_type, compression, filter_method, interlace = payload[8:13]
            _require(compression == 0 and filter_method == 0 and interlace == 0, f"Capture must use standard non-interlaced PNG encoding: {path}")
            saw_ihdr = True
        elif kind == b"PLTE":
            _require(saw_ihdr and not saw_idat and not saw_iend, f"Capture has an invalid PNG palette order: {path}")
            saw_plte = True
        elif kind == b"IDAT":
            _require(saw_ihdr and not saw_iend, f"Capture has an invalid PNG data order: {path}")
            saw_idat = True
            idat_parts.append(payload)
        elif kind == b"IEND":
            _require(saw_ihdr and saw_idat and length == 0, f"Capture has an invalid PNG end chunk: {path}")
            saw_iend = True
            _require(chunk_end == len(data), f"Capture has trailing data after the PNG end chunk: {path}")
        offset = chunk_end
    _require(saw_ihdr and saw_idat and saw_iend, f"Capture is missing required PNG chunks: {path}")
    _require(width > 0 and height > 0, f"Capture has invalid PNG dimensions: {path}")
    valid_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    _require(color_type in valid_depths and bit_depth in valid_depths[color_type], f"Capture has an unsupported PNG color format: {path}")
    _require(color_type != 3 or saw_plte, f"Indexed PNG capture is missing a palette: {path}")
    decoder = zlib.decompressobj()
    try:
        decoded = decoder.decompress(b"".join(idat_parts)) + decoder.flush()
    except zlib.error as exc:
        raise QualityError(f"Capture PNG image data cannot be decoded: {path}") from exc
    _require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, f"Capture PNG image data is incomplete or has trailing compressed bytes: {path}")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    row_bytes = (width * channels * bit_depth + 7) // 8
    _require(len(decoded) == height * (row_bytes + 1), f"Capture PNG decoded size does not match its dimensions: {path}")
    for row in range(height):
        _require(decoded[row * (row_bytes + 1)] <= 4, f"Capture PNG uses an invalid row filter: {path}")
    return width, height


def verify_render_evidence(root: Path, plan_path: str | Path, evidence_path: str | Path, *, check_current_state: bool = True) -> dict[str, Any]:
    plan_file, plan_relative = _resolve_inside(root, plan_path, "render plan")
    _require(plan_relative == ".design/renders/plan.json", "render plan must use .design/renders/plan.json")
    plan = validate_render_plan(root, load_json(plan_file), check_current_state=check_current_state)
    evidence_file, evidence_relative = _resolve_inside(root, evidence_path, "render evidence")
    _require(evidence_relative == ".design/renders/evidence.json", "render evidence must use .design/renders/evidence.json")
    evidence = load_json(evidence_file)
    _exact_keys(
        evidence,
        {"schema_version", "status", "render_plan", "capture_owner", "server_result", "captures", "limitations", "captured_at"},
        "render evidence",
    )
    _require(evidence["schema_version"] == "1.0", "render evidence schema_version must be 1.0")
    _require(evidence["status"] in {"complete", "blocked"}, "render evidence status is invalid")
    render_plan = evidence["render_plan"]
    _require(isinstance(render_plan, dict), "render_plan must be an object")
    _exact_keys(render_plan, {"path", "sha256"}, "render_plan")
    _require(relative_path(render_plan["path"], "render_plan.path") == plan_relative, "render_plan.path does not match")
    _require(_hash(render_plan["sha256"], "render_plan.sha256") == sha256(plan_file), "render_plan hash is stale")
    _require(_text(evidence["capture_owner"], "capture_owner") == plan["capture_owner"], "capture_owner does not match the plan")
    server_result = evidence["server_result"]
    _require(isinstance(server_result, dict), "server_result must be an object")
    _exact_keys(server_result, {"status", "method", "evidence"}, "server_result")
    _require(server_result["status"] in {"pass", "blocked", "not-applicable"}, "server_result.status is invalid")
    _text(server_result["method"], "server_result.method")
    _text(server_result["evidence"], "server_result.evidence")
    if server_result["status"] == "pass":
        _reject_passing_disclaimer([server_result["method"], server_result["evidence"]], "server_result")
    if plan["origin"]["kind"] == "local":
        _require(server_result["status"] == "pass", "local rendering requires passing server evidence")
    _strings(evidence["limitations"], "limitations")
    _timestamp(evidence["captured_at"], "captured_at")

    captures = evidence["captures"]
    _require(isinstance(captures, list), "captures must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for index, capture in enumerate(captures):
        label = f"captures[{index}]"
        _require(isinstance(capture, dict), f"{label} must be an object")
        _exact_keys(capture, {"target_id", "status", "output", "sha256", "width", "height", "method", "source_url", "evidence", "limitations"}, label)
        target_id = _text(capture["target_id"], f"{label}.target_id")
        _require(target_id not in by_id, "capture target IDs must be unique")
        _require(capture["status"] in {"pass", "blocked", "not-applicable"}, f"{label}.status is invalid")
        _text(capture["method"], f"{label}.method")
        _text(capture["source_url"], f"{label}.source_url")
        _text(capture["evidence"], f"{label}.evidence")
        _strings(capture["limitations"], f"{label}.limitations")
        by_id[target_id] = capture

    targets = {target["id"]: target for target in plan["targets"]}
    _require(set(by_id) == set(targets), "render evidence must cover every planned target exactly once")
    blocking: list[str] = []
    for target_id, target in targets.items():
        capture = by_id[target_id]
        _require(relative_path(capture["output"], f"capture {target_id} output") == target["output"], f"capture {target_id} output does not match plan")
        _require(capture["source_url"] == target["source_url"], f"capture {target_id} source URL does not match plan")
        if capture["status"] == "pass":
            _reject_passing_disclaimer([capture["method"], capture["evidence"], *capture["limitations"]], f"capture {target_id}")
            capture_path, _ = _resolve_inside(root, capture["output"], f"capture {target_id}")
            digest = _hash(capture["sha256"], f"capture {target_id} sha256")
            _require(sha256(capture_path) == digest, f"capture {target_id} hash is stale")
            width, height = png_dimensions(capture_path)
            _require(capture["width"] == width and capture["height"] == height, f"capture {target_id} PNG dimensions do not match evidence")
            viewport = target["viewport"]
            expected_width = round(viewport["width"] * viewport["device_scale_factor"])
            expected_height = round(viewport["height"] * viewport["device_scale_factor"])
            _require((width, height) == (expected_width, expected_height), f"capture {target_id} dimensions do not match planned viewport")
        else:
            _require(capture["sha256"] is None and capture["width"] is None and capture["height"] is None, f"non-passing capture {target_id} cannot claim file evidence")
            _require(bool(capture["limitations"]), f"non-passing capture {target_id} needs a limitation")
            if target["required"]:
                blocking.append(target_id)
            else:
                _require(capture["status"] == "not-applicable", f"optional target {target_id} must use not-applicable when omitted")
    expected_status = "blocked" if blocking else "complete"
    _require(evidence["status"] == expected_status, f"render evidence status must be {expected_status}")
    return {
        "schema_version": "1.0",
        "status": expected_status,
        "render_plan": {"path": plan_relative, "sha256": sha256(plan_file)},
        "render_evidence": {"path": evidence_relative, "sha256": sha256(evidence_file)},
        "required_blockers": blocking,
        "verified_at": utc_now(),
    }


def _validate_evidence_refs(root: Path, value: Any, label: str) -> list[dict[str, str]]:
    _require(isinstance(value, list), f"{label} must be an array")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        _require(isinstance(item, dict), f"{item_label} must be an object")
        _exact_keys(item, {"path", "sha256"}, item_label)
        path, relative = _resolve_inside(root, item["path"], f"{item_label}.path")
        digest = _hash(item["sha256"], f"{item_label}.sha256")
        _require(sha256(path) == digest, f"{item_label} is stale")
        _require(relative not in seen, f"{label} paths must be unique")
        seen.add(relative)
        rows.append({"path": relative, "sha256": digest})
    return rows


def _validate_accessibility_evidence(root: Path, relative: str, target_id: str, label: str) -> str:
    value = load_json(root / relative)
    _exact_keys(value, {"schema_version", "target_id", "performed_by", "checks", "limitations", "created_at"}, label)
    _require(value["schema_version"] == "1.0" and value["target_id"] == target_id, f"{label} is not bound to the QA target")
    _text(value["performed_by"], f"{label}.performed_by")
    _strings(value["limitations"], f"{label}.limitations")
    _timestamp(value["created_at"], f"{label}.created_at")
    required = {"semantics", "accessible-names", "focus", "contrast", "zoom-reflow", "keyboard", "touch-targets", "reduced-motion"}
    checks = value["checks"]
    _require(isinstance(checks, list), f"{label}.checks must be an array")
    seen: set[str] = set()
    statuses: set[str] = set()
    for index, item in enumerate(checks):
        item_label = f"{label}.checks[{index}]"
        _require(isinstance(item, dict), f"{item_label} must be an object")
        _exact_keys(item, {"id", "status", "method", "truth_class", "result", "applicability_reason"}, item_label)
        check_id = _text(item["id"], f"{item_label}.id")
        _require(check_id in required and check_id not in seen, f"{item_label}.id is not a unique required accessibility check")
        seen.add(check_id)
        _require(item["status"] in {"pass", "fail", "blocked", "not-applicable"}, f"{item_label}.status is invalid")
        statuses.add(item["status"])
        _text(item["method"], f"{item_label}.method")
        _require(item["truth_class"] in {"observed", "measured"}, f"{item_label}.truth_class must be observed or measured")
        _text(item["result"], f"{item_label}.result")
        if item["status"] == "not-applicable":
            _text(item["applicability_reason"], f"{item_label}.applicability_reason")
        else:
            _require(item["applicability_reason"] is None, f"{item_label}.applicability_reason is only valid for not-applicable checks")
    _require(seen == required, f"{label}.checks must cover the required accessibility checks exactly")
    if "blocked" in statuses:
        return "blocked"
    if "fail" in statuses:
        return "fail"
    _require("pass" in statuses, f"{label}.checks cannot all be not-applicable")
    _reject_passing_disclaimer(
        [value["performed_by"], *value["limitations"], *[item["method"] for item in checks], *[item["result"] for item in checks]],
        label,
    )
    return "pass"


def _validate_repair_context(root: Path, report: dict[str, Any], state: dict[str, Any]) -> None:
    if report["repair_cycle"] == 0:
        _require(report["prior_qa"] is None and report["repair_plan"] is None and report["repair_evaluation"] is None, "initial QA cannot claim repair context")
        return
    prior_path, _ = _artifact_ref(root, report["prior_qa"], "prior_qa", state=state)
    repair_plan_path, repair_plan_relative = _artifact_ref(root, report["repair_plan"], "repair_plan", state=state)
    evaluation = report["repair_evaluation"]
    _require(isinstance(evaluation, dict), "repair_evaluation is required after a repair")
    _exact_keys(evaluation, {"repair_plan", "prior_qa", "results"}, "repair_evaluation")
    for key in ("repair_plan", "prior_qa"):
        _require(evaluation[key] == report[key], f"repair_evaluation.{key} must match {key}")
    repair_plan = validate_repair_plan(root, load_json(repair_plan_path), state=state)
    prior_report = load_json(prior_path)
    _require(prior_report.get("repair_cycle") == report["repair_cycle"] - 1, "prior_qa must be the immediately preceding quality cycle")
    _require(repair_plan_relative == f".design/qa/repairs/cycle-{report['repair_cycle']}.json", "repair_plan path does not match the current quality cycle")
    _require(repair_plan["cycle_number"] == report["repair_cycle"], "repair_plan cycle does not match QA")
    _require(repair_plan["pass_number"] == report["repair_pass"], "repair_plan pass does not match QA")
    _require(repair_plan["qa_report"] == report["prior_qa"], "repair_plan is not bound to the preceding QA report")
    results = evaluation["results"]
    _require(isinstance(results, list), "repair_evaluation.results must be an array")
    result_map: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(results):
        label = f"repair_evaluation.results[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"finding_id", "status", "evidence", "notes"}, label)
        finding_id = _text(item["finding_id"], f"{label}.finding_id")
        _require(finding_id not in result_map, "repair evaluation finding IDs must be unique")
        _require(item["status"] in {"resolved", "unresolved", "regressed"}, f"{label}.status is invalid")
        _validate_evidence_refs(root, item["evidence"], f"{label}.evidence")
        _text(item["notes"], f"{label}.notes")
        result_map[finding_id] = item
    planned = {item["finding_id"] for item in repair_plan["target_findings"]}
    _require(set(result_map) == planned, "repair evaluation must cover every targeted finding exactly once")
    current_open = {item["id"] for item in report["findings"] if item["status"] == "open"}
    for finding_id, result in result_map.items():
        if result["status"] in {"unresolved", "regressed"}:
            _require(finding_id in current_open, f"unresolved finding {finding_id} must remain open")
        else:
            _require(finding_id not in current_open, f"resolved finding {finding_id} cannot remain open")


def validate_qa_report(root: Path, report_path: str | Path, *, check_current_state: bool = True) -> dict[str, Any]:
    report_file, report_relative = _resolve_inside(root, report_path, "QA report")
    _require(report_relative.startswith(".design/qa/reports/") and report_relative.endswith(".json"), "QA report must live under .design/qa/reports/")
    report = load_json(report_file)
    _exact_keys(
        report,
        {
            "schema_version",
            "workflow",
            "repair_cycle",
            "repair_pass",
            "state_binding",
            "render_evidence",
            "prior_qa",
            "repair_plan",
            "repair_evaluation",
            "checks",
            "findings",
            "summary",
            "qa_owner",
            "created_at",
        },
        "QA report",
    )
    _require(report["schema_version"] == "1.0" and report["workflow"] in {"run", "audit"}, "QA report version or workflow is invalid")
    _require(isinstance(report["repair_cycle"], int) and not isinstance(report["repair_cycle"], bool) and report["repair_cycle"] >= 0, "repair_cycle must be non-negative")
    _require(report_relative == f".design/qa/reports/cycle-{report['repair_cycle']}.json", "QA report path must match repair_cycle")
    _require(isinstance(report["repair_pass"], int) and not isinstance(report["repair_pass"], bool) and 0 <= report["repair_pass"] <= 3, "repair_pass must be 0 to 3")
    state = _validate_state_binding(root, report["state_binding"], "state_binding", allowed_phases={"qa"}, check_current=check_current_state)
    _require(state["workflow"] == report["workflow"], "QA workflow does not match state")
    _require(state["repair_cycle"] == report["repair_cycle"], "QA repair_cycle does not match state")
    _require(state["repair_pass"] == report["repair_pass"], "QA repair_pass does not match state")
    render_file, render_relative = _artifact_ref(root, report["render_evidence"], "render_evidence", state=state)
    evidence = load_json(render_file)
    _require(evidence.get("status") == "complete", "QA requires complete render evidence")
    plan_ref = evidence.get("render_plan")
    _require(isinstance(plan_ref, dict), "render evidence has no render plan")
    plan_path, _ = _artifact_ref(root, plan_ref, "render plan", state=state)
    plan = validate_render_plan(root, load_json(plan_path), check_current_state=False)
    _require(report["workflow"] == plan["workflow"], "QA workflow does not match render plan")
    _text(report["qa_owner"], "qa_owner")
    _timestamp(report["created_at"], "created_at")

    targets_by_id = {target["id"]: target for target in plan["targets"]}
    target_ids = set(targets_by_id)
    checks = report["checks"]
    _require(isinstance(checks, list), "checks must be an array")
    check_map: dict[str, dict[str, Any]] = {}
    pair_map: dict[tuple[str, str], str] = {}
    for index, item in enumerate(checks):
        label = f"checks[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"id", "target_id", "category", "status", "method", "truth_class", "confidence", "reference_role", "comparison_dimensions", "evidence", "notes"}, label)
        check_id = _text(item["id"], f"{label}.id")
        _require(check_id not in check_map, "QA check IDs must be unique")
        category = item["category"]
        _require(category in plan["applicable_checks"], f"{label}.category is not applicable")
        target_id = _text(item["target_id"], f"{label}.target_id")
        expected_target = "project" if category == "code" else target_id
        if category == "code":
            _require(target_id == "project", "code QA must use target_id project")
        else:
            _require(target_id in target_ids, f"{label}.target_id is unknown")
        pair = (expected_target, category)
        _require(pair not in pair_map, f"duplicate QA check for {pair}")
        pair_map[pair] = check_id
        _require(item["status"] in EVIDENCE_STATUSES, f"{label}.status is invalid")
        _text(item["method"], f"{label}.method")
        _require(item["truth_class"] in TRUTH_CLASSES, f"{label}.truth_class is invalid")
        _require(item["confidence"] in CONFIDENCE_LEVELS, f"{label}.confidence is invalid")
        evidence_refs = _validate_evidence_refs(root, item["evidence"], f"{label}.evidence")
        comparison_dimensions = _strings(item["comparison_dimensions"], f"{label}.comparison_dimensions")
        if category == "reference":
            target_reference = targets_by_id[target_id]["reference"]
            _require(item["reference_role"] == target_reference["role"], f"{label}.reference_role does not preserve the planned reference role")
            _require(comparison_dimensions == target_reference["comparison_dimensions"], f"{label}.comparison_dimensions do not match the bounded reference job")
            evidence_paths = {row["path"] for row in evidence_refs}
            _require(target_reference["path"] in evidence_paths, f"{label}.evidence must include the bound reference artifact")
            _require(targets_by_id[target_id]["output"] in evidence_paths, f"{label}.evidence must include the current capture")
        elif category == "accessibility":
            _require(item["truth_class"] in {"observed", "measured"}, f"{label} must record observed or measured accessibility evidence")
            accessibility_paths = [
                row["path"]
                for row in evidence_refs
                if row["path"].startswith(".design/qa/evidence/accessibility-") and row["path"].endswith(".json")
            ]
            _require(len(accessibility_paths) == 1, f"{label}.evidence must include one project-local accessibility check artifact")
            accessibility_status = _validate_accessibility_evidence(root, accessibility_paths[0], target_id, f"{label}.accessibility_evidence")
            expected_accessibility_status = "fail" if item["status"] == "pass-with-deviation" else item["status"]
            _require(accessibility_status == expected_accessibility_status, f"{label}.status does not match its accessibility evidence")
            _require(item["reference_role"] is None and not comparison_dimensions, f"{label} cannot claim a reference role")
        else:
            _require(item["reference_role"] is None and not comparison_dimensions, f"{label} cannot claim a reference role outside reference comparison")
        _text(item["notes"], f"{label}.notes")
        if item["status"] in {"pass", "pass-with-deviation"}:
            _reject_passing_disclaimer([item["method"], item["notes"]], label)
        if item["status"] != "blocked":
            _require(evidence_refs, f"{label} requires current evidence")
        check_map[check_id] = item

    required_pairs: set[tuple[str, str]] = set()
    for category in plan["applicable_checks"]:
        if category == "code":
            required_pairs.add(("project", category))
        else:
            required_pairs.update((target_id, category) for target_id in target_ids)
    _require(set(pair_map) == required_pairs, "QA checks must cover every applicable category and target exactly once")

    findings = report["findings"]
    _require(isinstance(findings, list), "findings must be an array")
    finding_map: dict[str, dict[str, Any]] = {}
    by_check: dict[str, list[dict[str, Any]]] = {check_id: [] for check_id in check_map}
    for index, item in enumerate(findings):
        label = f"findings[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(
            item,
            {"id", "source_check_id", "target_id", "category", "finding_type", "severity", "status", "summary", "observed", "expected", "truth_class", "confidence", "evidence", "repair_scope"},
            label,
        )
        finding_id = _text(item["id"], f"{label}.id")
        _require(finding_id not in finding_map, "finding IDs must be unique")
        check_id = _text(item["source_check_id"], f"{label}.source_check_id")
        _require(check_id in check_map, f"{label}.source_check_id is unknown")
        check = check_map[check_id]
        _require(item["target_id"] == check["target_id"] and item["category"] == check["category"], f"{label} does not match its source check")
        _require(item["finding_type"] in FINDING_TYPES, f"{label}.finding_type is invalid")
        _require(item["severity"] in SEVERITIES, f"{label}.severity is invalid")
        _require(item["status"] in {"open", "accepted-deviation"}, f"{label}.status is invalid")
        if item["status"] == "accepted-deviation":
            _require(item["severity"] == "P3", "only P3 findings may be accepted as deviations")
        for key in ("summary", "observed", "expected"):
            _text(item[key], f"{label}.{key}")
        _require(item["truth_class"] in TRUTH_CLASSES and item["confidence"] in CONFIDENCE_LEVELS, f"{label} evidence classification is invalid")
        _require(_validate_evidence_refs(root, item["evidence"], f"{label}.evidence"), f"{label} requires evidence")
        repair_scope = _strings(item["repair_scope"], f"{label}.repair_scope", 1 if item["status"] == "open" else 0)
        for scope_index, path_value in enumerate(repair_scope):
            relative_path(path_value, f"{label}.repair_scope[{scope_index}]")
        finding_map[finding_id] = item
        by_check[check_id].append(item)

    for check_id, check in check_map.items():
        current = by_check[check_id]
        open_items = [item for item in current if item["status"] == "open"]
        accepted = [item for item in current if item["status"] == "accepted-deviation"]
        if check["status"] == "fail":
            _require(open_items, f"failing check {check_id} requires an open finding")
        elif check["status"] == "pass-with-deviation":
            _require(accepted and not open_items, f"pass-with-deviation check {check_id} requires accepted P3 findings only")
        elif check["status"] == "pass":
            _require(not current, f"passing check {check_id} cannot have a current finding")
        else:
            _require(not current, f"blocked check {check_id} cannot claim findings")

    open_findings = [item for item in findings if item["status"] == "open"]
    blocked_checks = [item for item in checks if item["status"] == "blocked"]
    if blocked_checks or any(item["severity"] == "P0" for item in open_findings):
        expected_status = "blocked"
    elif open_findings:
        expected_status = "repair-required"
    else:
        expected_status = "pass"
    counts = {
        severity: sum(1 for item in open_findings if item["severity"] == severity)
        for severity in ("P0", "P1", "P2", "P3")
    }
    counts["accepted_deviations"] = sum(1 for item in findings if item["status"] == "accepted-deviation")
    counts["blocked_checks"] = len(blocked_checks)
    summary = report["summary"]
    _require(isinstance(summary, dict), "summary must be an object")
    _exact_keys(summary, {"status", "counts", "blockers", "limitations"}, "summary")
    _require(summary["status"] == expected_status, f"QA summary status must be {expected_status}")
    _require(summary["counts"] == counts, "QA summary counts do not match findings")
    blockers = _strings(summary["blockers"], "summary.blockers")
    _strings(summary["limitations"], "summary.limitations")
    if expected_status == "blocked":
        _require(blockers, "blocked QA requires blocker descriptions")
    else:
        _require(not blockers, "non-blocked QA cannot list blockers")

    _validate_repair_context(root, report, state)
    return {
        "schema_version": "1.0",
        "status": expected_status,
        "qa_report": {"path": report_relative, "sha256": sha256(report_file)},
        "render_evidence": {"path": render_relative, "sha256": sha256(render_file)},
        "open_findings": sorted(item["id"] for item in open_findings),
        "accepted_deviations": sorted(item["id"] for item in findings if item["status"] == "accepted-deviation"),
        "verified_at": utc_now(),
    }


def create_repair_plan(
    root: Path,
    qa_path: str | Path,
    finding_ids: list[str],
    worker_id: str,
    allowed_files: list[str],
    actions: list[str],
    checks: list[str],
    state: dict[str, Any],
    *,
    at: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Create the active repair plan after the controller enters repairing."""
    _require(state["phase"] == "repairing" and state["status"] == "active", "repair plan requires active repairing state")
    _require(state["repair_cycle"] >= 1 and 1 <= state["repair_pass"] <= 3, "repair cycle state is invalid")
    report_file, report_relative = _resolve_inside(root, qa_path, "QA report")
    report = load_json(report_file)
    _require(report.get("summary", {}).get("status") in {"repair-required", "blocked"}, "repair plan requires unresolved QA")
    findings = {
        item["id"]: item
        for item in report.get("findings", [])
        if isinstance(item, dict) and item.get("status") == "open"
    }
    _require(finding_ids and len(finding_ids) == len(set(finding_ids)), "repair finding IDs must be non-empty and unique")
    _require(set(finding_ids) <= set(findings), "repair plan targets an unknown or non-open finding")
    target_ids = {findings[finding_id]["target_id"] for finding_id in finding_ids}
    attempts = state.get("repair_attempts", {})
    _require(set(target_ids) <= set(attempts), "repair attempts do not cover every affected target")
    target_attempts = {target_id: attempts[target_id] for target_id in sorted(target_ids)}
    for target_id, count in target_attempts.items():
        _require(1 <= count <= 3, f"repair attempt for {target_id} is outside 1 to 3")

    worker = _text(worker_id, "worker_id")
    allowed = _strings(allowed_files, "allowed_files", 1)
    for index, item in enumerate(allowed):
        relative_path(item, f"allowed_files[{index}]")
    action_rows = _strings(actions, "actions", 1)
    check_rows = _strings(checks, "checks", 1)
    _require(len(action_rows) == len(set(action_rows)), "repair actions must be unique")
    _require(len(check_rows) == len(set(check_rows)), "repair checks must be unique")

    gate = state["gates"]["repository_changes"]
    _require(gate is not None and gate["status"] == "approved", "repair requires current repository-change approval")
    approval_path, approval_relative = _resolve_inside(root, gate["artifact_path"], "repository approval")
    _require(sha256(approval_path) == gate["artifact_sha256"], "repository approval is stale")
    reference_path, reference_relative = _resolve_inside(root, ".design/system/reference-lock.json", "reference lock")

    from design_build import _path_allowed, compile_plan_markdown, load_json as load_build_json, repository_snapshot, validate_plan

    structured_path, structured_relative = _resolve_inside(root, ".design/implementation/plan.json", "structured implementation plan")
    structured_plan = validate_plan(load_build_json(structured_path))
    _require(approval_path.read_text(encoding="utf-8") == compile_plan_markdown(structured_plan), "structured implementation plan does not compile to the current repository approval")
    approved_files = [path for wave in structured_plan["waves"] for path in wave["allowed_files"]]
    outside_approved = [path for path in allowed if not _path_allowed(path, approved_files)]
    _require(not outside_approved, f"repair allowed_files exceed the approved implementation plan: {outside_approved}")
    finding_scope = sorted({path for finding_id in finding_ids for path in findings[finding_id]["repair_scope"]})
    outside_findings = [path for path in allowed if not _path_allowed(path, finding_scope)]
    _require(not outside_findings, f"repair allowed_files are unrelated to the targeted finding scope: {outside_findings}")

    plan = {
        "schema_version": "1.0",
        "cycle_number": state["repair_cycle"],
        "pass_number": state["repair_pass"],
        "worker_id": worker,
        "qa_report": {"path": report_relative, "sha256": sha256(report_file)},
        "repository_approval": {"path": approval_relative, "sha256": sha256(approval_path)},
        "structured_plan": {"path": structured_relative, "sha256": sha256(structured_path)},
        "reference_lock": {"path": reference_relative, "sha256": sha256(reference_path)},
        "target_findings": [
            {
                "finding_id": finding_id,
                "target_id": findings[finding_id]["target_id"],
                "category": findings[finding_id]["category"],
                "severity": findings[finding_id]["severity"],
                "expected": findings[finding_id]["expected"],
                "repair_scope": findings[finding_id]["repair_scope"],
            }
            for finding_id in finding_ids
        ],
        "target_attempts": target_attempts,
        "allowed_files": allowed,
        "actions": action_rows,
        "checks": check_rows,
        "rerender_targets": sorted(target_ids),
        "repository_baseline": repository_snapshot(root),
        "state_revision": state["revision"],
        "status": "active",
        "started_at": at or utc_now(),
    }
    output = root / f".design/qa/repairs/cycle-{state['repair_cycle']}.json"
    _require(not output.exists(), f"repair cycle {state['repair_cycle']} already has a plan")
    validate_repair_plan(root, plan)
    _atomic_write_json(output, plan)
    return output, plan


def validate_repair_plan(root: Path, plan: dict[str, Any], *, state: dict[str, Any] | None = None) -> dict[str, Any]:
    _exact_keys(
        plan,
        {
            "schema_version",
            "cycle_number",
            "pass_number",
            "worker_id",
            "qa_report",
            "repository_approval",
            "structured_plan",
            "reference_lock",
            "target_findings",
            "target_attempts",
            "allowed_files",
            "actions",
            "checks",
            "rerender_targets",
            "repository_baseline",
            "state_revision",
            "status",
            "started_at",
        },
        "repair plan",
    )
    _require(plan["schema_version"] == "1.0" and plan["status"] == "active", "repair plan version or status is invalid")
    _require(isinstance(plan["cycle_number"], int) and not isinstance(plan["cycle_number"], bool) and plan["cycle_number"] >= 1, "cycle_number must be positive")
    _require(isinstance(plan["pass_number"], int) and not isinstance(plan["pass_number"], bool) and 1 <= plan["pass_number"] <= 3, "pass_number must be 1 to 3")
    _text(plan["worker_id"], "worker_id")
    _artifact_ref(root, plan["qa_report"], "qa_report", state=state)
    approval_path, _ = _artifact_ref(root, plan["repository_approval"], "repository_approval")
    structured_path, structured_relative = _artifact_ref(root, plan["structured_plan"], "structured_plan")
    _require(structured_relative == ".design/implementation/plan.json", "structured_plan must use the canonical path")
    _artifact_ref(root, plan["reference_lock"], "reference_lock")
    targets = plan["target_findings"]
    _require(isinstance(targets, list) and targets, "target_findings must not be empty")
    ids: set[str] = set()
    target_ids: set[str] = set()
    for index, item in enumerate(targets):
        label = f"target_findings[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"finding_id", "target_id", "category", "severity", "expected", "repair_scope"}, label)
        finding_id = _text(item["finding_id"], f"{label}.finding_id")
        _require(finding_id not in ids, "target finding IDs must be unique")
        ids.add(finding_id)
        target_ids.add(_text(item["target_id"], f"{label}.target_id"))
        _require(item["category"] in QUALITY_CATEGORIES and item["severity"] in SEVERITIES, f"{label} classification is invalid")
        _text(item["expected"], f"{label}.expected")
        scope = _strings(item["repair_scope"], f"{label}.repair_scope", 1)
        for scope_index, path_value in enumerate(scope):
            relative_path(path_value, f"{label}.repair_scope[{scope_index}]")
    attempts = plan["target_attempts"]
    _require(isinstance(attempts, dict) and set(attempts) == target_ids, "target_attempts must cover each affected target")
    for target_id, count in attempts.items():
        _require(isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= 3, f"target_attempts[{target_id}] must be 1 to 3")
    allowed = _strings(plan["allowed_files"], "allowed_files", 1)
    for index, path in enumerate(allowed):
        relative_path(path, f"allowed_files[{index}]")
    from design_build import _path_allowed, compile_plan_markdown, load_json as load_build_json, validate_plan

    structured_plan = validate_plan(load_build_json(structured_path))
    _require(approval_path.read_text(encoding="utf-8") == compile_plan_markdown(structured_plan), "repair plan is not bound to the approved compiled implementation plan")
    approved_files = [path for wave in structured_plan["waves"] for path in wave["allowed_files"]]
    outside_approved = [path for path in allowed if not _path_allowed(path, approved_files)]
    _require(not outside_approved, f"repair allowed_files exceed the approved implementation plan: {outside_approved}")
    finding_scope = sorted({path for item in targets for path in item["repair_scope"]})
    outside_findings = [path for path in allowed if not _path_allowed(path, finding_scope)]
    _require(not outside_findings, f"repair allowed_files are unrelated to the targeted finding scope: {outside_findings}")
    _strings(plan["actions"], "actions", 1)
    _strings(plan["checks"], "checks", 1)
    rerender = _strings(plan["rerender_targets"], "rerender_targets", 1)
    _require(set(rerender) == target_ids, "rerender_targets must exactly cover affected targets")
    baseline = plan["repository_baseline"]
    _require(isinstance(baseline, dict), "repository_baseline must be an object")
    _exact_keys(baseline, {"head", "dirty_files", "recorded_at"}, "repository_baseline")
    _text(baseline["head"], "repository_baseline.head")
    _require(isinstance(baseline["dirty_files"], list), "repository_baseline.dirty_files must be an array")
    _timestamp(baseline["recorded_at"], "repository_baseline.recorded_at")
    _require(isinstance(plan["state_revision"], int) and plan["state_revision"] >= 0, "state_revision is invalid")
    _timestamp(plan["started_at"], "started_at")
    if state is not None:
        _require(state["phase"] in {"repairing", "rendering", "qa"}, "repair plan state phase is invalid")
        _require(state["revision"] >= plan["state_revision"], "repair plan is from a future state")
        for target_id, count in attempts.items():
            _require(state.get("repair_attempts", {}).get(target_id) == count, f"repair attempt for {target_id} is stale")
    return plan


def validate_repair_handoff(root: Path, plan_path: str | Path, handoff_path: str | Path, *, state: dict[str, Any]) -> dict[str, Any]:
    from design_build import _path_allowed, changed_since

    plan_file, plan_relative = _resolve_inside(root, plan_path, "repair plan")
    plan = validate_repair_plan(root, load_json(plan_file), state=state)
    _require(plan_relative == f".design/qa/repairs/cycle-{plan['cycle_number']}.json", "repair plan path does not match cycle_number")
    handoff_file, handoff_relative = _resolve_inside(root, handoff_path, "repair handoff")
    expected_handoff = f".design/qa/repairs/cycle-{plan['cycle_number']}-handoff.json"
    _require(handoff_relative == expected_handoff, f"repair handoff must use {expected_handoff}")
    handoff = load_json(handoff_file)
    _exact_keys(
        handoff,
        {"schema_version", "cycle_number", "pass_number", "status", "repair_plan_sha256", "changed_files", "completed_actions", "completed_checks", "target_results", "ended_at"},
        "repair handoff",
    )
    _require(handoff["schema_version"] == "1.0" and handoff["status"] == "applied", "repair handoff version or status is invalid")
    _require(handoff["cycle_number"] == plan["cycle_number"], "repair handoff cycle does not match plan")
    _require(handoff["pass_number"] == plan["pass_number"], "repair handoff pass does not match plan")
    _require(_hash(handoff["repair_plan_sha256"], "repair_plan_sha256") == sha256(plan_file), "repair plan hash is stale")
    current_changed = set(changed_since(root, plan["repository_baseline"]))
    control = {".design/state.json", plan_relative, handoff_relative, f".design/qa/repairs/cycle-{plan['cycle_number']}-verification.json"}
    product_changed = sorted(current_changed - control)
    outside = [path for path in product_changed if not _path_allowed(path, plan["allowed_files"])]
    _require(not outside, f"repair changed files outside approved scope: {outside}")
    rows = handoff["changed_files"]
    _require(isinstance(rows, list), "changed_files must be an array")
    claimed: set[str] = set()
    for index, item in enumerate(rows):
        label = f"changed_files[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"path", "change", "sha256", "evidence"}, label)
        path = relative_path(item["path"], f"{label}.path")
        _require(path not in claimed, "changed_files paths must be unique")
        claimed.add(path)
        _require(path in product_changed, f"{label}.path is not changed from the repair baseline")
        _require(item["change"] == "changed", f"{label}.change must be changed; repair deletion requires a separately approved implementation plan")
        _text(item["evidence"], f"{label}.evidence")
        file_path = root / path
        _require(file_path.is_file(), f"changed file is missing: {path}")
        _require(_hash(item["sha256"], f"{label}.sha256") == sha256(file_path), f"changed file hash is stale: {path}")
    _require(claimed == set(product_changed), "repair handoff must claim every changed product file exactly")
    _require(_strings(handoff["completed_actions"], "completed_actions", 1) == plan["actions"], "completed_actions must match the repair plan")
    checks = handoff["completed_checks"]
    _require(isinstance(checks, list) and len(checks) == len(plan["checks"]), "completed_checks must cover every planned check")
    seen_checks: set[str] = set()
    for index, item in enumerate(checks):
        label = f"completed_checks[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"check", "status", "evidence"}, label)
        check = _text(item["check"], f"{label}.check")
        _require(check in plan["checks"] and check not in seen_checks, f"{label}.check is not uniquely planned")
        seen_checks.add(check)
        _require(item["status"] == "pass", f"repair check failed: {check}")
        _text(item["evidence"], f"{label}.evidence")
    results = handoff["target_results"]
    _require(isinstance(results, list), "target_results must be an array")
    result_ids: set[str] = set()
    for index, item in enumerate(results):
        label = f"target_results[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"finding_id", "status", "evidence"}, label)
        finding_id = _text(item["finding_id"], f"{label}.finding_id")
        _require(finding_id not in result_ids, "target_results finding IDs must be unique")
        result_ids.add(finding_id)
        _require(item["status"] == "implemented-awaiting-rerender", f"{label}.status must defer resolution to rerendered QA")
        _text(item["evidence"], f"{label}.evidence")
    _require(result_ids == {item["finding_id"] for item in plan["target_findings"]}, "target_results must cover every repair finding")
    _timestamp(handoff["ended_at"], "ended_at")
    return {
        "schema_version": "1.0",
        "status": "applied",
        "repair_plan": {"path": plan_relative, "sha256": sha256(plan_file)},
        "repair_handoff": {"path": handoff_relative, "sha256": sha256(handoff_file)},
        "changed_files": product_changed,
        "rerender_targets": plan["rerender_targets"],
        "verified_at": utc_now(),
    }


def _validate_deviations(root: Path, path_value: str | Path, qa_ref: dict[str, str]) -> tuple[dict[str, Any], str, str]:
    path, relative = _resolve_inside(root, path_value, "deviations report")
    _require(relative == ".design/qa/deviations.json", "deviations report must use .design/qa/deviations.json")
    value = load_json(path)
    _exact_keys(value, {"schema_version", "qa_report", "deviations", "owner", "created_at"}, "deviations report")
    _require(value["schema_version"] == "1.0" and value["qa_report"] == qa_ref, "deviations report is not bound to QA")
    _text(value["owner"], "deviations owner")
    _timestamp(value["created_at"], "deviations created_at")
    deviations = value["deviations"]
    _require(isinstance(deviations, list), "deviations must be an array")
    ids: set[str] = set()
    for index, item in enumerate(deviations):
        label = f"deviations[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"finding_id", "target_id", "category", "severity", "disposition", "rationale", "evidence"}, label)
        finding_id = _text(item["finding_id"], f"{label}.finding_id")
        _require(finding_id not in ids, "deviation finding IDs must be unique")
        ids.add(finding_id)
        _text(item["target_id"], f"{label}.target_id")
        _require(item["category"] in QUALITY_CATEGORIES and item["severity"] == "P3", f"{label} must be a P3 quality deviation")
        _require(item["disposition"] == "accepted", f"{label}.disposition must be accepted")
        _text(item["rationale"], f"{label}.rationale")
        _require(_validate_evidence_refs(root, item["evidence"], f"{label}.evidence"), f"{label} requires evidence")
    return value, relative, sha256(path)


def _validate_scorecard(root: Path, path_value: str | Path, qa_ref: dict[str, str], applicable: list[str]) -> tuple[dict[str, Any], str, str]:
    path, relative = _resolve_inside(root, path_value, "scorecard")
    _require(relative == ".design/qa/scorecard.json", "scorecard must use .design/qa/scorecard.json")
    value = load_json(path)
    _exact_keys(value, {"schema_version", "qa_report", "overall", "dimensions", "blockers", "limitations", "owner", "created_at"}, "scorecard")
    _require(value["schema_version"] == "1.0" and value["qa_report"] == qa_ref, "scorecard is not bound to QA")
    _require(value["overall"] == "pass", "final scorecard must pass")
    _require(not _strings(value["blockers"], "scorecard.blockers"), "passing scorecard cannot contain blockers")
    _strings(value["limitations"], "scorecard.limitations")
    _text(value["owner"], "scorecard owner")
    _timestamp(value["created_at"], "scorecard created_at")
    dimensions = value["dimensions"]
    _require(isinstance(dimensions, list), "scorecard dimensions must be an array")
    seen: set[str] = set()
    for index, item in enumerate(dimensions):
        label = f"dimensions[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"category", "status", "evidence_checks", "notes"}, label)
        category = item["category"]
        _require(category in applicable and category not in seen, f"{label}.category is not uniquely applicable")
        seen.add(category)
        _require(item["status"] in {"pass", "pass-with-deviation"}, f"{label}.status is not complete")
        _strings(item["evidence_checks"], f"{label}.evidence_checks", 1)
        _text(item["notes"], f"{label}.notes")
    _require(seen == set(applicable), "scorecard must cover every applicable QA category")
    return value, relative, sha256(path)


def verify_completion(root: Path, qa_path: str | Path, deviations_path: str | Path, scorecard_path: str | Path) -> dict[str, Any]:
    qa_result = validate_qa_report(root, qa_path, check_current_state=True)
    _require(qa_result["status"] == "pass", "quality completion requires passing QA")
    qa_file, qa_relative = _resolve_inside(root, qa_path, "QA report")
    qa_ref = {"path": qa_relative, "sha256": sha256(qa_file)}
    report = load_json(qa_file)
    render_file, _ = _artifact_ref(root, report["render_evidence"], "render evidence", state=load_state(root))
    render = load_json(render_file)
    plan_file, _ = _artifact_ref(root, render["render_plan"], "render plan", state=load_state(root))
    plan = load_json(plan_file)
    deviations, deviations_relative, deviations_digest = _validate_deviations(root, deviations_path, qa_ref)
    accepted = {item["id"]: item for item in report["findings"] if item["status"] == "accepted-deviation"}
    deviation_map = {item["finding_id"]: item for item in deviations["deviations"]}
    _require(set(deviation_map) == set(accepted), "deviations report must cover every accepted finding exactly")
    for finding_id, item in accepted.items():
        deviation = deviation_map[finding_id]
        _require(deviation["target_id"] == item["target_id"] and deviation["category"] == item["category"] and deviation["severity"] == item["severity"], f"deviation {finding_id} does not match QA")
    scorecard, score_relative, score_digest = _validate_scorecard(root, scorecard_path, qa_ref, plan["applicable_checks"])
    checks_by_id = {item["id"]: item for item in report["checks"]}
    for dimension in scorecard["dimensions"]:
        evidence_checks = dimension["evidence_checks"]
        _require(set(evidence_checks) <= set(checks_by_id), f"scorecard category {dimension['category']} cites an unknown check")
        _require(
            all(checks_by_id[check_id]["category"] == dimension["category"] for check_id in evidence_checks),
            f"scorecard category {dimension['category']} cites a check from another category",
        )
    return {
        "schema_version": "1.0",
        "status": "complete",
        "qa_report": qa_ref,
        "deviations": {"path": deviations_relative, "sha256": deviations_digest},
        "scorecard": {"path": score_relative, "sha256": score_digest},
        "accepted_deviations": sorted(accepted),
        "verified_at": utc_now(),
    }


def validate_learning_proposal(root: Path, proposal_path: str | Path) -> dict[str, Any]:
    path, relative = _resolve_inside(root, proposal_path, "learning proposal")
    _require(relative.startswith(".design/learning/proposals/") and relative.endswith(".json"), "learning proposal must remain under .design/learning/proposals/")
    value = load_json(path)
    _exact_keys(
        value,
        {
            "schema_version",
            "proposal_id",
            "status",
            "source_projects",
            "observations",
            "evidence",
            "proposed_rule",
            "exceptions",
            "risks",
            "conflicting_rules",
            "destination",
            "evaluation",
            "privacy_review",
            "approval",
            "created_at",
        },
        "learning proposal",
    )
    _require(value["schema_version"] == "1.0" and value["status"] == "proposal-only", "learning must remain proposal-only")
    proposal_id = _text(value["proposal_id"], "proposal_id")
    _require(relative == f".design/learning/proposals/{proposal_id}.json", "learning proposal path must match proposal_id")
    projects = value["source_projects"]
    _require(isinstance(projects, list) and len(projects) >= 2, "a general learning proposal requires at least two projects")
    project_ids: set[str] = set()
    for index, item in enumerate(projects):
        label = f"source_projects[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"opaque_id", "visibility", "evidence_ref"}, label)
        opaque = _text(item["opaque_id"], f"{label}.opaque_id")
        _require(opaque not in project_ids and "/" not in opaque and "\\" not in opaque, f"{label}.opaque_id must be unique and non-path")
        project_ids.add(opaque)
        _require(item["visibility"] in {"private", "internal", "public"}, f"{label}.visibility is invalid")
        _text(item["evidence_ref"], f"{label}.evidence_ref")
    observations = value["observations"]
    _require(isinstance(observations, list) and len(observations) >= 2, "observations must contain at least two items")
    observed_projects: set[str] = set()
    for index, item in enumerate(observations):
        label = f"observations[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"source_project_id", "statement"}, label)
        source_id = _text(item["source_project_id"], f"{label}.source_project_id")
        _require(source_id in project_ids, f"{label}.source_project_id is unknown")
        observed_projects.add(source_id)
        _text(item["statement"], f"{label}.statement")
    _require(observed_projects == project_ids, "observations must cover every source project")
    evidence = value["evidence"]
    _require(isinstance(evidence, list) and len(evidence) >= 2, "evidence must contain at least two items")
    evidence_ids: set[str] = set()
    evidence_projects: set[str] = set()
    evidence_paths: set[str] = set()
    evidence_digests: set[str] = set()
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"id", "source_project_id", "artifact", "summary"}, label)
        evidence_id = _text(item["id"], f"{label}.id")
        _require(evidence_id not in evidence_ids, "evidence IDs must be unique")
        evidence_ids.add(evidence_id)
        source_id = _text(item["source_project_id"], f"{label}.source_project_id")
        _require(source_id in project_ids and source_id not in evidence_projects, f"{label}.source_project_id must uniquely cover a source project")
        evidence_projects.add(source_id)
        artifact_path, artifact_relative = _artifact_ref(root, item["artifact"], f"{label}.artifact")
        _require(artifact_relative.startswith(".design/learning/evidence/"), f"{label}.artifact must stay under .design/learning/evidence/")
        _require(artifact_relative not in evidence_paths, "learning evidence artifacts must be distinct")
        artifact_digest = item["artifact"]["sha256"]
        _require(artifact_digest not in evidence_digests, "learning evidence artifacts must have distinct content hashes")
        evidence_paths.add(artifact_relative)
        evidence_digests.add(artifact_digest)
        _text(item["summary"], f"{label}.summary")
        try:
            artifact_value: Any = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            artifact_value = artifact_path.read_text(encoding="utf-8")
        _require(artifact_value not in ({}, [], ""), f"{label}.artifact must contain redacted evidence")
        _scan_learning_value(artifact_value, f"{label}.artifact")
    _require(evidence_projects == project_ids, "evidence must cover every source project exactly once")
    project_evidence = {item["opaque_id"]: item["evidence_ref"] for item in projects}
    evidence_by_project = {item["source_project_id"]: item["id"] for item in evidence}
    _require(project_evidence == evidence_by_project, "source project evidence_ref values must bind the project evidence IDs")
    _text(value["proposed_rule"], "proposed_rule", 12)
    _strings(value["exceptions"], "exceptions", 1)
    _strings(value["risks"], "risks", 1)
    _strings(value["conflicting_rules"], "conflicting_rules")
    destination = value["destination"]
    _require(isinstance(destination, dict), "destination must be an object")
    _exact_keys(destination, {"kind", "candidate", "write_performed"}, "destination")
    _require(destination["kind"] in {"skill", "reference", "corpus-rule", "template", "none"}, "destination.kind is invalid")
    _text(destination["candidate"], "destination.candidate")
    _require(destination["write_performed"] is False, "learning proposal cannot write to its destination")
    _strings(value["evaluation"], "evaluation", 1)
    privacy = value["privacy_review"]
    _require(isinstance(privacy, dict), "privacy_review must be an object")
    _exact_keys(privacy, {"status", "reviewer", "redactions", "review_artifact"}, "privacy_review")
    _require(privacy["status"] == "pass", "privacy_review.status must be pass before validation")
    _text(privacy["reviewer"], "privacy_review.reviewer")
    _strings(privacy["redactions"], "privacy_review.redactions")
    review_path, review_relative = _artifact_ref(root, privacy["review_artifact"], "privacy_review.review_artifact")
    _require(review_relative.startswith(".design/learning/reviews/"), "privacy review artifact must stay under .design/learning/reviews/")
    review_value = load_json(review_path)
    _exact_keys(review_value, {"schema_version", "proposal_id", "reviewer", "reviewer_kind", "status", "reviewed_artifacts", "checks", "limitations", "created_at"}, "privacy review artifact")
    _require(review_value["schema_version"] == "1.0" and review_value["proposal_id"] == proposal_id, "privacy review artifact is not bound to the proposal")
    _require(review_value["reviewer"] == privacy["reviewer"] and review_value["status"] == "pass", "privacy review artifact does not record the declared passing reviewer")
    _require(review_value["reviewer_kind"] == "human", "privacy review artifact requires a declared human reviewer")
    reviewed_artifacts = _strings(review_value["reviewed_artifacts"], "privacy review artifact.reviewed_artifacts", 3)
    _require(set(reviewed_artifacts) == {relative, *evidence_paths}, "privacy review artifact must cover the proposal and every evidence artifact")
    privacy_checks = review_value["checks"]
    _require(isinstance(privacy_checks, list), "privacy review artifact.checks must be an array")
    required_privacy_checks = {"private-details", "absolute-paths", "secrets", "benchmark-data"}
    seen_privacy_checks: set[str] = set()
    for index, item in enumerate(privacy_checks):
        label = f"privacy review artifact.checks[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        _exact_keys(item, {"id", "status", "method", "notes"}, label)
        check_id = _text(item["id"], f"{label}.id")
        _require(check_id in required_privacy_checks and check_id not in seen_privacy_checks, f"{label}.id is not a unique required privacy check")
        seen_privacy_checks.add(check_id)
        _require(item["status"] == "pass", f"{label}.status must be pass")
        _text(item["method"], f"{label}.method")
        _text(item["notes"], f"{label}.notes")
    _require(seen_privacy_checks == required_privacy_checks, "privacy review artifact must cover every required privacy check")
    _strings(review_value["limitations"], "privacy review artifact.limitations")
    _timestamp(review_value["created_at"], "privacy review artifact.created_at")
    review_text = json.dumps(review_value, ensure_ascii=False).casefold()
    _require("synthetic" not in review_text and "not a human" not in review_text, "privacy review artifact explicitly disclaims a human review")
    _scan_learning_value(review_value, "privacy_review.review_artifact")
    approval = value["approval"]
    _require(isinstance(approval, dict), "approval must be an object")
    _exact_keys(approval, {"status", "decision_text", "decided_at"}, "approval")
    _require(approval["status"] == "pending" and approval["decision_text"] is None and approval["decided_at"] is None, "new learning proposals cannot be preapproved or activated")
    _timestamp(value["created_at"], "created_at")
    _scan_learning_value(value, "learning proposal")
    return {
        "schema_version": "1.0",
        "status": "valid-proposal",
        "proposal": {"path": relative, "sha256": sha256(path)},
        "source_project_count": len(project_ids),
        "bound_evidence_count": len(evidence_ids),
        "privacy_status": privacy["status"],
        "privacy_review": {"path": review_relative, "sha256": sha256(review_path)},
        "approval_status": approval["status"],
        "verified_at": utc_now(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-render", help="Compile a state-bound local render plan")
    prepare.add_argument("--project-root", default=".")
    prepare.add_argument("--request", required=True)
    prepare.add_argument("--output", default=".design/renders/plan.json")
    prepare.add_argument("--at", default=None)

    renders = sub.add_parser("verify-renders", help="Validate current viewport capture records")
    renders.add_argument("--project-root", default=".")
    renders.add_argument("--plan", default=".design/renders/plan.json")
    renders.add_argument("--evidence", default=".design/renders/evidence.json")

    qa = sub.add_parser("validate-qa", help="Validate a current QA report")
    qa.add_argument("--project-root", default=".")
    qa.add_argument("--report", required=True)

    repair = sub.add_parser("verify-repair", help="Validate a bounded repair handoff")
    repair.add_argument("--project-root", default=".")
    repair.add_argument("--plan", required=True)
    repair.add_argument("--handoff", required=True)

    complete = sub.add_parser("verify-completion", help="Validate QA bindings and completion constraints")
    complete.add_argument("--project-root", default=".")
    complete.add_argument("--qa-report", required=True)
    complete.add_argument("--deviations", default=".design/qa/deviations.json")
    complete.add_argument("--scorecard", default=".design/qa/scorecard.json")

    learning = sub.add_parser("validate-learning", help="Validate a proposal-only reusable learning artifact")
    learning.add_argument("--project-root", default=".")
    learning.add_argument("--proposal", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "prepare-render":
            result = create_render_plan(root, args.request, args.output, at=args.at)
        elif args.command == "verify-renders":
            result = verify_render_evidence(root, args.plan, args.evidence)
        elif args.command == "validate-qa":
            result = validate_qa_report(root, args.report)
        elif args.command == "verify-repair":
            result = validate_repair_handoff(root, args.plan, args.handoff, state=load_state(root))
        elif args.command == "verify-completion":
            result = verify_completion(root, args.qa_report, args.deviations, args.scorecard)
        elif args.command == "validate-learning":
            result = validate_learning_proposal(root, args.proposal)
        else:
            raise QualityError(f"Unknown command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (QualityError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
