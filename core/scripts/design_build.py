#!/usr/bin/env python3
"""Prepare, scope-check, and verify bounded Design implementation waves.

The runtime uses only the Python standard library. It reads local repository
evidence, writes only explicit local output paths, and performs no network,
installation, deployment, publication, image, or external-system actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_system import compile_plan_markdown


class ValidationError(RuntimeError):
    """Raised when a build-wave artifact or repository state is unsafe."""


HASH_CHARS = set("0123456789abcdef")
MANIFEST_KEYS = {
    "schema_version",
    "wave_id",
    "wave_number",
    "worker_id",
    "plan_json_sha256",
    "approved_plan_artifact",
    "approved_plan_sha256",
    "goal",
    "declared_inputs",
    "artifact_inputs",
    "approved_requirements",
    "design_sections",
    "dependencies",
    "allowed_files",
    "work_items",
    "render_targets",
    "tests",
    "completion_criteria",
    "rollback",
    "planned_risks",
    "control_files",
    "repository_baseline",
    "previous_handoff",
    "status",
    "started_at",
}
HANDOFF_KEYS = {
    "schema_version",
    "wave_id",
    "wave_number",
    "status",
    "manifest_sha256",
    "changed_files",
    "completed_checks",
    "render_results",
    "completion_criteria",
    "known_deviations",
    "new_risks",
    "review_results",
    "next_inputs",
    "rollback_notes",
    "ended_at",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{label} must be non-empty")
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


def _git_oid(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and len(value) in {40, 64} and set(value) <= HASH_CHARS,
        f"{label} must be a lowercase Git SHA-1 or SHA-256 object ID",
    )
    return value


def _timestamp(value: Any, label: str) -> str:
    _text(value, label)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label} must be ISO-8601") from exc
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative_path(value: Any, label: str) -> str:
    text = _text(value, label).replace("\\", "/")
    pure = PurePosixPath(text)
    _require(not pure.is_absolute() and ".." not in pure.parts, f"{label} must stay inside the project")
    _require(not (pure.parts and ":" in pure.parts[0]), f"{label} must not be drive-qualified")
    return pure.as_posix()


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc
    _require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def _resolve_inside(root: Path, value: str | Path, label: str, *, must_exist: bool = True) -> tuple[Path, str]:
    raw = Path(value).expanduser()
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValidationError(f"{label} must stay inside the project root") from exc
    relative_path(relative, label)
    if must_exist:
        _require(path.is_file(), f"{label} does not exist: {relative}")
    return path, relative


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".design-wave-", suffix=".tmp", dir=path.parent)
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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    _require(plan.get("schema_version") == "1.0", "implementation plan schema_version must be 1.0")
    for key in ("approved_direction_sha256", "reference_lock_sha256", "ux_definition_sha256", "design_md_sha256"):
        _hash(plan.get(key), key)
    _require(plan.get("repository_change_gate") == "awaiting_approval", "plan source must retain awaiting_approval")
    relative_path(plan.get("approval_artifact"), "approval_artifact")
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
    _require(isinstance(waves, list) and 1 <= len(waves) <= 7, "plan must contain 1 to 7 waves")
    known: set[str] = set()
    for index, wave in enumerate(waves):
        _require(isinstance(wave, dict), f"waves[{index}] must be an object")
        wave_id = _text(wave.get("id"), f"waves[{index}].id")
        _require(wave_id not in known, "wave ids must be unique")
        dependencies = _strings(wave.get("dependencies"), f"waves[{index}].dependencies")
        _require(set(dependencies) <= known, f"waves[{index}] has a missing or later dependency")
        known.add(wave_id)
        _text(wave.get("goal"), f"waves[{index}].goal", 8)
        for key in (
            "inputs",
            "approved_requirements",
            "design_sections",
            "allowed_files",
            "work_items",
            "render_targets",
            "tests",
            "completion_criteria",
            "rollback",
            "risks",
        ):
            _strings(wave.get(key), f"waves[{index}].{key}", 1)
        for path_index, item in enumerate(wave["allowed_files"]):
            relative_path(item, f"waves[{index}].allowed_files[{path_index}]")
        _require(wave.get("status") == "planned", "implementation waves must begin planned")
    return plan


def _run_git(root: Path, *arguments: str, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode and not allow_failure:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise ValidationError(f"Repository evidence failed: {message}")
    return completed


def _file_hash(root: Path, relative: str) -> str | None:
    path = root / relative
    return sha256(path) if path.is_file() else None


def status_snapshot(root: Path) -> list[dict[str, Any]]:
    completed = _run_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    raw = completed.stdout.split("\0")
    records: dict[str, dict[str, Any]] = {}
    index = 0
    while index < len(raw):
        entry = raw[index]
        index += 1
        if not entry:
            continue
        _require(len(entry) >= 4, "git status returned an invalid record")
        status = entry[:2]
        path = entry[3:]
        if status[0] in {"R", "C"} and index < len(raw):
            source = raw[index]
            index += 1
            if source:
                source = relative_path(source, "renamed source")
                records[source] = {"path": source, "status": "renamed-source", "sha256": _file_hash(root, source)}
        path = relative_path(path, "repository status path")
        records[path] = {"path": path, "status": status, "sha256": _file_hash(root, path)}
    return [records[path] for path in sorted(records)]


def repository_snapshot(root: Path) -> dict[str, Any]:
    inside = _run_git(root, "rev-parse", "--is-inside-work-tree").stdout.strip()
    _require(inside == "true", "project root must be inside a Git worktree")
    head = _run_git(root, "rev-parse", "HEAD").stdout.strip()
    _git_oid(head, "repository HEAD")
    return {"head": head, "dirty_files": status_snapshot(root), "recorded_at": utc_now()}


def _snapshot_map(records: list[dict[str, Any]]) -> dict[str, tuple[Any, Any]]:
    return {item["path"]: (item.get("status"), item.get("sha256")) for item in records}


def changed_since(root: Path, baseline: dict[str, Any]) -> list[str]:
    head = _git_oid(baseline.get("head"), "repository_baseline.head")
    ancestor = _run_git(root, "merge-base", "--is-ancestor", head, "HEAD", allow_failure=True)
    _require(ancestor.returncode == 0, "repository history diverged from the wave baseline")
    committed = _run_git(root, "diff", "--name-only", "-z", head, "HEAD").stdout.split("\0")
    changed = {relative_path(path, "committed changed path") for path in committed if path}
    baseline_map = _snapshot_map(baseline.get("dirty_files", []))
    current_map = _snapshot_map(status_snapshot(root))
    for path in set(baseline_map) | set(current_map):
        if baseline_map.get(path) != current_map.get(path):
            changed.add(path)
    return sorted(changed)


def _path_allowed(path: str, allowed: list[str]) -> bool:
    return any(path == rule.rstrip("/") or path.startswith(rule.rstrip("/") + "/") for rule in allowed)


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    _require(set(manifest) == MANIFEST_KEYS, "wave manifest has missing or unexpected keys")
    _require(manifest["schema_version"] == "1.0", "wave manifest schema_version must be 1.0")
    _text(manifest["wave_id"], "wave_id")
    _require(isinstance(manifest["wave_number"], int) and not isinstance(manifest["wave_number"], bool) and manifest["wave_number"] >= 1, "wave_number must be an integer >= 1")
    _text(manifest["worker_id"], "worker_id")
    _hash(manifest["plan_json_sha256"], "plan_json_sha256")
    relative_path(manifest["approved_plan_artifact"], "approved_plan_artifact")
    _hash(manifest["approved_plan_sha256"], "approved_plan_sha256")
    _text(manifest["goal"], "goal", 8)
    for key in (
        "declared_inputs",
        "approved_requirements",
        "design_sections",
        "allowed_files",
        "work_items",
        "render_targets",
        "tests",
        "completion_criteria",
        "rollback",
        "planned_risks",
    ):
        _strings(manifest[key], key, 1)
    _strings(manifest["dependencies"], "dependencies")
    for index, path in enumerate(manifest["allowed_files"]):
        relative_path(path, f"allowed_files[{index}]")
    artifact_inputs = manifest["artifact_inputs"]
    _require(isinstance(artifact_inputs, list) and len(artifact_inputs) >= 5, "artifact_inputs must bind at least five artifacts")
    seen_paths: set[str] = set()
    for index, item in enumerate(artifact_inputs):
        _require(isinstance(item, dict) and set(item) == {"path", "sha256", "purpose"}, f"artifact_inputs[{index}] is invalid")
        path = relative_path(item["path"], f"artifact_inputs[{index}].path")
        _require(path not in seen_paths, "artifact input paths must be unique")
        seen_paths.add(path)
        _hash(item["sha256"], f"artifact_inputs[{index}].sha256")
        _text(item["purpose"], f"artifact_inputs[{index}].purpose")
    purposes = {item["purpose"] for item in artifact_inputs}
    required_purposes = {
        "approved shared understanding",
        "approved reference lock",
        "approved design system",
        "structured implementation plan",
        "approved compiled implementation plan",
    }
    _require(required_purposes <= purposes, "artifact_inputs is missing a required approved input role")
    _require(len(purposes) == len(artifact_inputs), "artifact input purposes must be unique")
    control_files = manifest["control_files"]
    _require(isinstance(control_files, list) and len(control_files) == 4, "control_files must list four engine-owned artifacts")
    control_paths = [relative_path(item, f"control_files[{index}]") for index, item in enumerate(control_files)]
    expected_prefix = f".design/implementation/waves/{manifest['wave_id']}/"
    expected_names = {"manifest.json", "handoff.json", "handoff.md", "verification.json"}
    _require(
        all(path.startswith(expected_prefix) for path in control_paths)
        and {Path(path).name for path in control_paths} == expected_names,
        "control_files must be the canonical engine artifacts for this wave",
    )
    _require(not set(control_paths) & set(manifest["allowed_files"]), "control files are not product file scope")
    baseline = manifest["repository_baseline"]
    _require(isinstance(baseline, dict) and set(baseline) == {"head", "dirty_files", "recorded_at"}, "repository_baseline is invalid")
    _git_oid(baseline["head"], "repository_baseline.head")
    _timestamp(baseline["recorded_at"], "repository_baseline.recorded_at")
    _require(isinstance(baseline["dirty_files"], list), "repository_baseline.dirty_files must be a list")
    dirty_paths: set[str] = set()
    for index, item in enumerate(baseline["dirty_files"]):
        _require(isinstance(item, dict) and set(item) == {"path", "status", "sha256"}, f"dirty_files[{index}] is invalid")
        path = relative_path(item["path"], f"dirty_files[{index}].path")
        _require(path not in dirty_paths, "baseline dirty paths must be unique")
        dirty_paths.add(path)
        _text(item["status"], f"dirty_files[{index}].status")
        if item["sha256"] is not None:
            _hash(item["sha256"], f"dirty_files[{index}].sha256")
    previous = manifest["previous_handoff"]
    if previous is not None:
        _require(isinstance(previous, dict) and set(previous) == {"path", "sha256"}, "previous_handoff is invalid")
        relative_path(previous["path"], "previous_handoff.path")
        _hash(previous["sha256"], "previous_handoff.sha256")
    _require(manifest["status"] == "active", "new wave manifest status must be active")
    _timestamp(manifest["started_at"], "started_at")
    return manifest


def _validate_active_state(root: Path, plan: dict[str, Any]) -> tuple[dict[str, Any], Path, str]:
    from design_state_validation import load_state as load_design_state

    state = load_design_state(root)
    _require(state.get("phase") == "building" and state.get("status") == "active", "Design state must be active in building phase")
    wave_number = state.get("active_wave")
    _require(isinstance(wave_number, int) and not isinstance(wave_number, bool), "Design state requires active_wave")
    gate = state.get("gates", {}).get("repository_changes")
    _require(isinstance(gate, dict) and gate.get("status") == "approved", "repository-change approval must be active")
    for gate_name, record in state.get("gates", {}).items():
        if isinstance(record, dict) and record.get("status") in {"approved", "skipped"}:
            artifact, _ = _resolve_inside(root, record.get("artifact_path"), f"{gate_name} approval artifact")
            _require(sha256(artifact) == record.get("artifact_sha256"), f"{gate_name} approval is stale")
    approved_path, approved_relative = _resolve_inside(root, gate.get("artifact_path"), "approved plan artifact")
    _require(approved_relative == plan.get("approval_artifact"), "plan approval_artifact does not match the repository gate")
    _require(sha256(approved_path) == gate.get("artifact_sha256"), "approved implementation plan is stale")
    approved_text = approved_path.read_text(encoding="utf-8")
    _require(
        approved_text == compile_plan_markdown(plan),
        "structured implementation plan does not compile to the approved plan artifact",
    )
    return state, approved_path, approved_relative


def _artifact_input(root: Path, path: str, purpose: str, expected_hash: str | None = None) -> dict[str, str]:
    resolved, relative = _resolve_inside(root, path, purpose)
    digest = sha256(resolved)
    if expected_hash is not None:
        _require(digest == expected_hash, f"{purpose} hash does not match the approved plan")
    return {"path": relative, "sha256": digest, "purpose": purpose}


def _validate_completed_dependency(
    root: Path,
    state: dict[str, Any],
    wave_id: str,
) -> tuple[Path, dict[str, Any]]:
    directory = root / ".design/implementation/waves" / wave_id
    manifest_path = directory / "manifest.json"
    handoff_path = directory / "handoff.json"
    handoff_markdown_path = directory / "handoff.md"
    receipt_path = directory / "verification.json"
    manifest = validate_manifest(load_json(manifest_path))
    handoff = validate_handoff(load_json(handoff_path), manifest)
    _require(handoff["status"] == "complete", f"dependency {wave_id} is incomplete")
    _validate_changed_file_hashes(root, handoff, f"dependency {wave_id}")
    _require(handoff["manifest_sha256"] == sha256(manifest_path), f"dependency {wave_id} handoff is stale")
    receipt = load_json(receipt_path)
    _require(
        receipt.get("status") == "pass"
        and receipt.get("wave_id") == wave_id
        and receipt.get("manifest_sha256") == sha256(manifest_path)
        and receipt.get("handoff_sha256") == sha256(handoff_path)
        and receipt.get("handoff_markdown_sha256") == sha256(handoff_markdown_path),
        f"dependency {wave_id} verification receipt is invalid",
    )
    for path in (manifest_path, handoff_path, handoff_markdown_path, receipt_path):
        relative = path.relative_to(root).as_posix()
        _require(
            state["artifacts"].get(relative) == sha256(path),
            f"dependency {wave_id} lacks a state-bound verified {path.name}",
        )
    return handoff_path, handoff


def prepare_wave(
    project_root: str | Path,
    plan_path: str | Path,
    output: str | Path,
    worker_id: str,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    _require(root.is_dir(), "project root does not exist")
    plan_file, plan_relative = _resolve_inside(root, plan_path, "implementation plan JSON")
    plan = validate_plan(load_json(plan_file))
    state, approved_plan, approved_relative = _validate_active_state(root, plan)
    number = state["active_wave"]
    _require(number <= len(plan["waves"]), "active_wave exceeds the approved implementation plan")
    wave = plan["waves"][number - 1]

    previous_record: dict[str, str] | None = None
    for dependency in wave["dependencies"]:
        _validate_completed_dependency(root, state, dependency)
    if number > 1:
        previous_id = plan["waves"][number - 2]["id"]
        previous_path, previous_handoff = _validate_completed_dependency(root, state, previous_id)
        _require(previous_handoff["status"] == "complete", "previous wave handoff is incomplete")
        previous_record = {
            "path": previous_path.relative_to(root).as_posix(),
            "sha256": sha256(previous_path),
        }

    understanding_gate = state["gates"]["understanding"]
    artifact_inputs = [
        _artifact_input(root, understanding_gate["artifact_path"], "approved shared understanding", understanding_gate["artifact_sha256"]),
        _artifact_input(root, ".design/system/reference-lock.json", "approved reference lock", plan["reference_lock_sha256"]),
        _artifact_input(root, ".design/system/ux-definition.json", "approved UX definition", plan["ux_definition_sha256"]),
        _artifact_input(root, "DESIGN.md", "approved design system", plan["design_md_sha256"]),
        _artifact_input(root, plan_relative, "structured implementation plan"),
        _artifact_input(root, approved_relative, "approved compiled implementation plan", state["gates"]["repository_changes"]["artifact_sha256"]),
    ]
    if previous_record is not None:
        artifact_inputs.append({**previous_record, "purpose": "previous wave handoff"})

    expected_output = f".design/implementation/waves/{wave['id']}/manifest.json"
    output_path, output_relative = _resolve_inside(root, output, "wave manifest output", must_exist=False)
    _require(output_relative == expected_output, f"wave manifest output must be {expected_output}")
    control_files = [
        expected_output,
        f".design/implementation/waves/{wave['id']}/handoff.json",
        f".design/implementation/waves/{wave['id']}/handoff.md",
        f".design/implementation/waves/{wave['id']}/verification.json",
    ]
    manifest = {
        "schema_version": "1.0",
        "wave_id": wave["id"],
        "wave_number": number,
        "worker_id": _text(worker_id, "worker_id"),
        "plan_json_sha256": sha256(plan_file),
        "approved_plan_artifact": approved_plan.relative_to(root).as_posix(),
        "approved_plan_sha256": sha256(approved_plan),
        "goal": wave["goal"],
        "declared_inputs": wave["inputs"],
        "artifact_inputs": artifact_inputs,
        "approved_requirements": wave["approved_requirements"],
        "design_sections": wave["design_sections"],
        "dependencies": wave["dependencies"],
        "allowed_files": wave["allowed_files"],
        "work_items": wave["work_items"],
        "render_targets": wave["render_targets"],
        "tests": wave["tests"],
        "completion_criteria": wave["completion_criteria"],
        "rollback": wave["rollback"],
        "planned_risks": wave["risks"],
        "control_files": control_files,
        "repository_baseline": repository_snapshot(root),
        "previous_handoff": previous_record,
        "status": "active",
        "started_at": utc_now(),
    }
    validate_manifest(manifest)
    _require(not output_path.exists(), "wave manifest already exists; resume from it instead of replacing it")
    _atomic_write_json(output_path, manifest)
    try:
        from design_state_commands import command_start_wave

        command_start_wave(
            argparse.Namespace(
                project_root=str(root),
                manifest=output_relative,
                reason="Prepared from the exact approved plan and repository baseline.",
                at=manifest["started_at"],
            )
        )
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise
    return manifest


def check_scope(project_root: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    validate_manifest(manifest)
    changed = [
        path
        for path in changed_since(root, manifest["repository_baseline"])
        if path not in set(manifest["control_files"]) | {".design/state.json"}
    ]
    outside = [path for path in changed if not _path_allowed(path, manifest["allowed_files"])]
    return {
        "status": "pass" if not outside else "blocked",
        "changed_files": changed,
        "outside_allowed_scope": outside,
        "allowed_files": manifest["allowed_files"],
    }


def validate_handoff(handoff: dict[str, Any], manifest: dict[str, Any] | None) -> dict[str, Any]:
    _require(set(handoff) == HANDOFF_KEYS, "wave handoff has missing or unexpected keys")
    _require(handoff["schema_version"] == "1.0", "wave handoff schema_version must be 1.0")
    _text(handoff["wave_id"], "wave_id")
    _require(isinstance(handoff["wave_number"], int) and not isinstance(handoff["wave_number"], bool) and handoff["wave_number"] >= 1, "wave_number must be an integer >= 1")
    _require(handoff["status"] in {"complete", "blocked"}, "handoff status must be complete or blocked")
    _hash(handoff["manifest_sha256"], "manifest_sha256")
    changed = handoff["changed_files"]
    _require(isinstance(changed, list), "changed_files must be a list")
    changed_paths: set[str] = set()
    for index, item in enumerate(changed):
        _require(isinstance(item, dict) and set(item) == {"path", "change", "sha256", "evidence"}, f"changed_files[{index}] is invalid")
        path = relative_path(item["path"], f"changed_files[{index}].path")
        _require(path not in changed_paths, "changed file paths must be unique")
        changed_paths.add(path)
        _require(item["change"] in {"changed", "deleted"}, f"changed_files[{index}].change is invalid")
        if item["change"] == "deleted":
            _require(item["sha256"] is None, f"changed_files[{index}].sha256 must be null for deletion")
        else:
            _hash(item["sha256"], f"changed_files[{index}].sha256")
        _text(item["evidence"], f"changed_files[{index}].evidence")
    checks = handoff["completed_checks"]
    _require(isinstance(checks, list) and len(checks) >= 1, "completed_checks must not be empty")
    check_names: set[str] = set()
    for index, item in enumerate(checks):
        _require(isinstance(item, dict) and set(item) == {"name", "command", "status", "evidence"}, f"completed_checks[{index}] is invalid")
        check_name = _text(item["name"], f"completed_checks[{index}].name")
        _require(check_name not in check_names, "completed check names must be unique")
        check_names.add(check_name)
        _text(item["command"], f"completed_checks[{index}].command")
        _require(item["status"] in {"pass", "fail", "blocked"}, f"completed_checks[{index}].status is invalid")
        _text(item["evidence"], f"completed_checks[{index}].evidence")
    renders = handoff["render_results"]
    _require(isinstance(renders, list) and len(renders) >= 1, "render_results must not be empty")
    render_targets: set[str] = set()
    for index, item in enumerate(renders):
        _require(isinstance(item, dict) and set(item) == {"target", "status", "evidence"}, f"render_results[{index}] is invalid")
        render_target = _text(item["target"], f"render_results[{index}].target")
        _require(render_target not in render_targets, "render targets must be unique")
        render_targets.add(render_target)
        _require(item["status"] in {"pass", "fail", "blocked", "not-applicable"}, f"render_results[{index}].status is invalid")
        _text(item["evidence"], f"render_results[{index}].evidence")
    criteria = handoff["completion_criteria"]
    _require(isinstance(criteria, list) and len(criteria) >= 1, "completion_criteria must not be empty")
    criteria_names: set[str] = set()
    for index, item in enumerate(criteria):
        _require(isinstance(item, dict) and set(item) == {"criterion", "status", "evidence"}, f"completion_criteria[{index}] is invalid")
        criterion = _text(item["criterion"], f"completion_criteria[{index}].criterion")
        _require(criterion not in criteria_names, "completion criteria must be unique")
        criteria_names.add(criterion)
        _require(item["status"] in {"pass", "fail", "blocked"}, f"completion_criteria[{index}].status is invalid")
        _text(item["evidence"], f"completion_criteria[{index}].evidence")
    for key in ("known_deviations", "new_risks"):
        _strings(handoff[key], key)
    reviews = handoff["review_results"]
    _require(isinstance(reviews, list) and len(reviews) >= 1, "review_results must include an independent verifier")
    reviewer_ids: set[str] = set()
    for index, item in enumerate(reviews):
        _require(
            isinstance(item, dict) and set(item) == {"reviewer_id", "role", "status", "evidence"},
            f"review_results[{index}] is invalid",
        )
        reviewer = _text(item["reviewer_id"], f"review_results[{index}].reviewer_id")
        _require(reviewer not in reviewer_ids, "reviewer ids must be unique")
        reviewer_ids.add(reviewer)
        _require(item["role"] in {"independent-verifier", "unslop-reviewer", "specialist"}, f"review_results[{index}].role is invalid")
        _require(item["status"] in {"pass", "fail", "blocked"}, f"review_results[{index}].status is invalid")
        _text(item["evidence"], f"review_results[{index}].evidence")
    for key in ("next_inputs", "rollback_notes"):
        _strings(handoff[key], key, 1)
    _timestamp(handoff["ended_at"], "ended_at")

    if manifest is not None:
        validate_manifest(manifest)
        _require(handoff["wave_id"] == manifest["wave_id"], "handoff wave_id does not match manifest")
        _require(handoff["wave_number"] == manifest["wave_number"], "handoff wave_number does not match manifest")
        expected_renders = set(manifest["render_targets"])
        actual_renders = {item["target"] for item in renders}
        _require(actual_renders == expected_renders, "handoff must report every planned render target exactly once")
        expected_criteria = set(manifest["completion_criteria"])
        actual_criteria = {item["criterion"] for item in criteria}
        _require(actual_criteria == expected_criteria, "handoff must report every completion criterion exactly once")
        _require(check_names == set(manifest["tests"]), "handoff must report every planned test exactly once")
        independent = [item for item in reviews if item["role"] == "independent-verifier"]
        _require(independent, "handoff requires an independent verifier review")
        unslop = [item for item in reviews if item["role"] == "unslop-reviewer"]
        _require(unslop, "handoff requires an Unslop review")
        _require(
            all(
                item["reviewer_id"] != manifest["worker_id"]
                for item in independent + unslop
            ),
            "the implementation worker cannot verify or Unslop-review the same wave",
        )
    if handoff["status"] == "complete":
        _require(all(item["status"] == "pass" for item in checks), "complete handoff requires every check to pass")
        _require(all(item["status"] in {"pass", "not-applicable"} for item in renders), "complete handoff has a failed render target")
        _require(all(item["status"] == "pass" for item in criteria), "complete handoff requires every criterion to pass")
        _require(all(item["status"] == "pass" for item in reviews), "complete handoff requires every recorded review to pass")
    return handoff


def _validate_changed_file_hashes(root: Path, handoff: dict[str, Any], label: str) -> None:
    for item in handoff["changed_files"]:
        path = root / item["path"]
        if item["change"] == "deleted":
            _require(not path.exists(), f"{label} deleted file exists again: {item['path']}")
            continue
        _require(path.is_file(), f"{label} changed file is missing: {item['path']}")
        _require(
            sha256(path) == item["sha256"],
            f"{label} changed file hash is stale: {item['path']}",
        )


def compile_handoff(handoff: dict[str, Any], manifest: dict[str, Any]) -> str:
    validate_handoff(handoff, manifest)
    lines = [
        f"# {handoff['wave_id']} handoff",
        "",
        f"Status: {handoff['status']}",
        f"Wave number: {handoff['wave_number']}",
        "",
        "## Changed files",
        "",
    ]
    lines.extend(
        f"- `{item['path']}`: {item['change']}; SHA-256 `{item['sha256'] or 'deleted'}`. {item['evidence']}"
        for item in handoff["changed_files"]
    )
    if not handoff["changed_files"]:
        lines.append("- None.")
    sections = (
        ("Completed checks", "completed_checks", lambda item: f"{item['name']}: {item['status']}. {item['evidence']}"),
        ("Render targets", "render_results", lambda item: f"{item['target']}: {item['status']}. {item['evidence']}"),
        ("Completion criteria", "completion_criteria", lambda item: f"{item['criterion']}: {item['status']}. {item['evidence']}"),
        ("Review results", "review_results", lambda item: f"{item['role']} by {item['reviewer_id']}: {item['status']}. {item['evidence']}"),
    )
    for heading, key, format_item in sections:
        lines.extend(["", f"## {heading}", ""])
        lines.extend(f"- {format_item(item)}" for item in handoff[key])
    for heading, key in (
        ("Known deviations", "known_deviations"),
        ("New risks", "new_risks"),
        ("Next inputs", "next_inputs"),
        ("Rollback notes", "rollback_notes"),
    ):
        lines.extend(["", f"## {heading}", ""])
        lines.extend(f"- {item}" for item in handoff[key])
        if not handoff[key]:
            lines.append("- None.")
    lines.extend(["", f"Ended at: {handoff['ended_at']}", ""])
    return "\n".join(lines)


def _validate_manifest_against_plan(
    manifest: dict[str, Any],
    plan: dict[str, Any],
    state: dict[str, Any],
    root: Path,
    plan_relative: str,
) -> None:
    number = manifest["wave_number"]
    _require(1 <= number <= len(plan["waves"]), "manifest wave_number is outside the approved plan")
    wave = plan["waves"][number - 1]
    mappings = {
        "wave_id": "id",
        "goal": "goal",
        "declared_inputs": "inputs",
        "approved_requirements": "approved_requirements",
        "design_sections": "design_sections",
        "dependencies": "dependencies",
        "allowed_files": "allowed_files",
        "work_items": "work_items",
        "render_targets": "render_targets",
        "tests": "tests",
        "completion_criteria": "completion_criteria",
        "rollback": "rollback",
        "planned_risks": "risks",
    }
    for manifest_key, plan_key in mappings.items():
        _require(
            manifest[manifest_key] == wave[plan_key],
            f"manifest {manifest_key} differs from the approved plan wave",
        )
    _require(manifest["plan_json_sha256"] == sha256(root / plan_relative), "manifest plan hash is stale")
    _require(manifest["approved_plan_artifact"] == plan["approval_artifact"], "manifest approved plan path differs")
    gate = state["gates"]["repository_changes"]
    _require(manifest["approved_plan_sha256"] == gate["artifact_sha256"], "manifest approved plan hash differs")

    inputs = {item["purpose"]: item for item in manifest["artifact_inputs"]}
    expected_paths = {
        "approved shared understanding": state["gates"]["understanding"]["artifact_path"],
        "approved reference lock": ".design/system/reference-lock.json",
        "approved design system": "DESIGN.md",
        "structured implementation plan": plan_relative,
        "approved compiled implementation plan": plan["approval_artifact"],
    }
    for purpose, expected_path in expected_paths.items():
        _require(inputs[purpose]["path"] == expected_path, f"manifest {purpose} path differs from the approved chain")
    _require(inputs["approved reference lock"]["sha256"] == plan["reference_lock_sha256"], "manifest reference lock hash differs")
    _require(inputs["approved design system"]["sha256"] == plan["design_md_sha256"], "manifest DESIGN.md hash differs")

    expected_control = [
        f".design/implementation/waves/{wave['id']}/manifest.json",
        f".design/implementation/waves/{wave['id']}/handoff.json",
        f".design/implementation/waves/{wave['id']}/handoff.md",
        f".design/implementation/waves/{wave['id']}/verification.json",
    ]
    _require(manifest["control_files"] == expected_control, "manifest control files differ from the engine contract")


def verify_wave8(project_root: str | Path, manifest_path: str | Path, handoff_path: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    manifest_file, manifest_relative = _resolve_inside(root, manifest_path, "wave manifest")
    manifest = validate_manifest(load_json(manifest_file))
    expected_manifest = f".design/implementation/waves/{manifest['wave_id']}/manifest.json"
    expected_handoff = f".design/implementation/waves/{manifest['wave_id']}/handoff.json"
    _require(manifest_relative == expected_manifest, f"manifest must be {expected_manifest}")
    state_artifact_path = root / ".design/state.json"
    _require(state_artifact_path.is_file(), "Design state is missing")
    state_artifact = load_json(state_artifact_path)
    _require(
        state_artifact.get("artifacts", {}).get(manifest_relative) == sha256(manifest_file),
        "wave manifest is not immutably bound in Design state",
    )
    handoff_file, handoff_relative = _resolve_inside(root, handoff_path, "wave handoff")
    _require(handoff_relative == expected_handoff, f"handoff must be {expected_handoff}")
    handoff = validate_handoff(load_json(handoff_file), manifest)
    _require(handoff["manifest_sha256"] == sha256(manifest_file), "handoff is bound to a different manifest")
    handoff_md = root / f".design/implementation/waves/{manifest['wave_id']}/handoff.md"
    _require(handoff_md.is_file(), "compiled wave handoff Markdown is missing")
    _require(
        handoff_md.read_text(encoding="utf-8") == compile_handoff(handoff, manifest),
        "compiled wave handoff Markdown is stale",
    )

    for item in manifest["artifact_inputs"]:
        artifact, _ = _resolve_inside(root, item["path"], item["purpose"])
        _require(sha256(artifact) == item["sha256"], f"stale wave input: {item['path']}")
    if manifest["previous_handoff"] is not None:
        previous, _ = _resolve_inside(root, manifest["previous_handoff"]["path"], "previous wave handoff")
        _require(sha256(previous) == manifest["previous_handoff"]["sha256"], "previous wave handoff changed")

    input_map = {item["purpose"]: item for item in manifest["artifact_inputs"]}
    _require("structured implementation plan" in input_map, "manifest lacks structured implementation plan input")
    plan_path = input_map["structured implementation plan"]["path"]
    plan = validate_plan(load_json(root / plan_path))
    state, approved_plan, approved_relative = _validate_active_state(root, plan)
    _require(state["active_wave"] == manifest["wave_number"], "state active_wave does not match the manifest")
    _require(
        state["artifacts"].get(manifest_relative) == sha256(manifest_file),
        "wave manifest is not immutably bound in Design state",
    )
    _validate_manifest_against_plan(manifest, plan, state, root, plan_path)
    _require(sha256(root / plan_path) == manifest["plan_json_sha256"], "structured implementation plan changed")
    _require(approved_relative == manifest["approved_plan_artifact"], "approved plan path changed")
    _require(sha256(approved_plan) == manifest["approved_plan_sha256"], "approved plan changed")

    scope = check_scope(root, manifest)
    _require(scope["status"] == "pass", f"changed files escaped wave scope: {scope['outside_allowed_scope']}")
    declared = {item["path"] for item in handoff["changed_files"]}
    _require(declared == set(scope["changed_files"]), "handoff changed_files does not match repository evidence")
    _validate_changed_file_hashes(root, handoff, f"wave {manifest['wave_id']}")
    _require(handoff["status"] == "complete", "only a complete handoff can close a build wave")
    return {
        "status": "pass",
        "manifest": manifest_relative,
        "manifest_sha256": sha256(manifest_file),
        "handoff": handoff_relative,
        "handoff_sha256": sha256(handoff_file),
        "handoff_markdown": handoff_md.relative_to(root).as_posix(),
        "handoff_markdown_sha256": sha256(handoff_md),
        "wave_id": manifest["wave_id"],
        "wave_number": manifest["wave_number"],
        "changed_files": scope["changed_files"],
        "ready_for_state_completion": True,
        "next_state_command": "design_state.py complete-wave",
    }


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("prepare-wave")
    command.add_argument("--project-root", default=".")
    command.add_argument("--plan", default=".design/implementation/plan.json")
    command.add_argument("--output", required=True)
    command.add_argument("--worker-id", required=True)

    command = commands.add_parser("validate-manifest")
    command.add_argument("path")

    command = commands.add_parser("check-scope")
    command.add_argument("--project-root", default=".")
    command.add_argument("--manifest", required=True)

    command = commands.add_parser("validate-handoff")
    command.add_argument("--manifest", required=True)
    command.add_argument("--handoff", required=True)

    command = commands.add_parser("compile-handoff")
    command.add_argument("--manifest", required=True)
    command.add_argument("--handoff", required=True)
    command.add_argument("--output", required=True)

    command = commands.add_parser("verify-wave8")
    command.add_argument("--project-root", default=".")
    command.add_argument("--manifest", required=True)
    command.add_argument("--handoff", required=True)
    command.add_argument("--receipt")

    args = parser.parse_args()
    try:
        if args.command == "prepare-wave":
            _dump(prepare_wave(args.project_root, args.plan, args.output, args.worker_id))
        elif args.command == "validate-manifest":
            _dump({"status": "pass", "artifact": args.path, "wave": validate_manifest(load_json(args.path))["wave_id"]})
        elif args.command == "check-scope":
            report = check_scope(args.project_root, validate_manifest(load_json(args.manifest)))
            _dump(report)
            if report["status"] != "pass":
                return 2
        elif args.command == "validate-handoff":
            manifest = validate_manifest(load_json(args.manifest))
            validate_handoff(load_json(args.handoff), manifest)
            _dump({"status": "pass", "artifact": args.handoff})
        elif args.command == "compile-handoff":
            manifest = validate_manifest(load_json(args.manifest))
            text = compile_handoff(load_json(args.handoff), manifest)
            _write_text(Path(args.output), text)
            _dump({"status": "pass", "output": args.output, "sha256": sha256(args.output)})
        else:
            report = verify_wave8(args.project_root, args.manifest, args.handoff)
            if args.receipt:
                root = Path(args.project_root).expanduser().resolve()
                receipt, relative = _resolve_inside(root, args.receipt, "verification receipt", must_exist=False)
                expected = f".design/implementation/waves/{report['wave_id']}/verification.json"
                _require(relative == expected, f"verification receipt must be {expected}")
                _atomic_write_json(receipt, report)
            _dump(report)
        return 0
    except (ValidationError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
