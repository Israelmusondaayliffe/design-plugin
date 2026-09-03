#!/usr/bin/env python3
"""Durable workflow state controller for the Design plugin.

The tool uses only the Python standard library. It installs nothing, accesses no
network, and never overwrites invalid state. All writes are atomic.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
STATE_RELATIVE_PATH = Path(".design/state.json")
DIRECTION_SET_RELATIVE_PATH = ".design/directions/direction-set.json"
GATE_NAMES = ("understanding", "direction", "repository_changes")
GATE_ARTIFACT_PATHS = {
    "understanding": ".design/shared-understanding.md",
    "direction": ".design/directions/decision.md",
    "repository_changes": ".design/implementation/plan.md",
}
GATE_APPROVAL_DECISIONS = {
    "understanding": {
        "approved",
        "this understanding is approved",
    },
    "direction": {
        "direction approved",
        "this direction is approved",
    },
    "repository_changes": {
        "repository changes approved",
        "these repository changes are approved",
    },
}
AWAITING_APPROVAL_PHASES = {
    "understanding_awaiting_approval",
    "directions_awaiting_approval",
    "implementation_plan_awaiting_approval",
}
PHASES = {
    "intake",
    "interviewing",
    *AWAITING_APPROVAL_PHASES,
    "researching",
    "system_definition",
    "building",
    "rendering",
    "qa",
    "repairing",
    "complete",
    "blocked",
}
STATUSES = {"active", "awaiting_approval", "paused", "blocked", "complete"}
TOP_LEVEL_KEYS = {
    "schema_version",
    "plugin",
    "revision",
    "workflow_cycle",
    "workflow",
    "route",
    "phase",
    "status",
    "phase_before_block",
    "gates",
    "artifacts",
    "active_wave",
    "repair_cycle",
    "repair_pass",
    "repair_attempts",
    "blockers",
    "history",
    "created_at",
    "updated_at",
}
LEGACY_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS - {"workflow_cycle"}
PRE_BUILD_PHASES = {
    "intake",
    "interviewing",
    "understanding_awaiting_approval",
    "researching",
    "directions_awaiting_approval",
    "system_definition",
    "implementation_plan_awaiting_approval",
}


class StateError(RuntimeError):
    """Raised when state is missing, invalid, stale, or cannot transition."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: str | None) -> str:
    timestamp = value or utc_now()
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise StateError(f"Invalid ISO-8601 timestamp: {timestamp}") from exc
    return timestamp


def default_status_for_phase(phase: str) -> str:
    if phase in AWAITING_APPROVAL_PHASES:
        return "awaiting_approval"
    if phase == "blocked":
        return "blocked"
    if phase == "complete":
        return "complete"
    return "active"


def project_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.exists():
        raise StateError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise StateError(f"Project root is not a directory: {root}")
    return root


def state_path(root: Path) -> Path:
    return root / STATE_RELATIVE_PATH


def resource_path(relative: str) -> Path:
    candidates = [PACKAGE_ROOT / relative, PACKAGE_ROOT / "core" / relative]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise StateError(f"Design package resource is missing: {relative}")


def load_transition_table() -> dict[str, Any]:
    path = resource_path("references/state-machine.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateError(f"Transition table is invalid JSON: {exc}") from exc
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_relative_record_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{label} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise StateError(f"{label} must stay inside the project root")
    if pure.parts and ":" in pure.parts[0]:
        raise StateError(f"{label} must not contain a drive-qualified path")
    return pure.as_posix()


def resolve_artifact(root: Path, artifact: str) -> tuple[Path, str]:
    raw = Path(artifact).expanduser()
    resolved = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise StateError("Approval artifacts must live inside the project root") from exc
    if not resolved.is_file():
        raise StateError(f"Approval artifact does not exist: {relative}")
    validate_relative_record_path(relative, "approval artifact path")
    return resolved, relative
