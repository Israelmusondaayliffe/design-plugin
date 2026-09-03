"""State-changing commands for the Design workflow controller."""

from __future__ import annotations

import argparse
import json
import shutil
from typing import Any

from design_state_gates import *


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    path = state_path(root)
    if path.exists():
        raise StateError(f"State already exists: {path}. Use Design Resume or preserve and remove it explicitly.")
    at = normalize_timestamp(args.at)
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "plugin": "design",
        "revision": 0,
        "workflow_cycle": 1,
        "workflow": args.workflow,
        "route": args.route,
        "phase": "intake",
        "status": "active",
        "phase_before_block": None,
        "gates": {name: None for name in GATE_NAMES},
        "artifacts": {},
        "active_wave": None,
        "repair_cycle": 0,
        "repair_pass": 0,
        "repair_attempts": {},
        "blockers": [],
        "history": [
            {
                "event": "initialized",
                "at": at,
                "workflow": args.workflow,
                "route": args.route,
            }
        ],
        "created_at": at,
        "updated_at": at,
    }
    validate_state(state)
    atomic_write_json(path, state)
    return state


def command_revise(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    if state["phase"] != "complete" or state["status"] != "complete":
        raise StateError("A revision can begin only from a completed Design state")
    at = normalize_timestamp(args.at)
    cycle = state.get("workflow_cycle", 1)
    archive = root / ".design" / "archive" / f"cycle-{cycle}"
    if archive.exists():
        raise StateError(f"Revision archive already exists: {archive.relative_to(root)}")
    archive.mkdir(parents=True)
    archived_state = archive / "state.json"
    shutil.copyfile(state_path(root), archived_state)
    manifest = {
        "schema_version": "1.0",
        "workflow_cycle": cycle,
        "archived_at": at,
        "reason": args.reason,
        "state_path": archived_state.relative_to(root).as_posix(),
        "state_sha256": sha256(archived_state),
        "artifacts": dict(sorted(state["artifacts"].items())),
    }
    atomic_write_json(archive / "manifest.json", manifest)

    state["workflow_cycle"] = cycle + 1
    state["phase"] = "intake"
    state["status"] = "active"
    state["phase_before_block"] = None
    state["gates"] = {name: None for name in GATE_NAMES}
    state["artifacts"] = {}
    state["active_wave"] = None
    state["repair_cycle"] = 0
    state["repair_pass"] = 0
    state["repair_attempts"] = {}
    state["blockers"] = []
    append_history(
        state,
        "revision_started",
        at,
        prior_workflow_cycle=cycle,
        workflow_cycle=cycle + 1,
        archive_manifest=(archive / "manifest.json").relative_to(root).as_posix(),
        reason=args.reason,
    )
    save_state(root, state, at)
    return state


def command_transition(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)
    stale = stale_gate_names(state)
    if stale:
        raise StateError(f"Stale approval gates detected: {', '.join(stale)}. Reapproval is required.")
    if state["status"] == "paused":
        raise StateError("Workflow is paused. Resume it before transitioning.")
    if state["phase"] == "blocked":
        raise StateError("Workflow is blocked. Resolve the blocker before transitioning.")
    if state["phase"] == "complete":
        raise StateError("Completed workflow has no further transitions")

    if (state["phase"], args.to) in {
        ("rendering", "qa"),
        ("qa", "repairing"),
        ("repairing", "rendering"),
        ("qa", "complete"),
    }:
        raise StateError(
            f"Evidence-bound transition required for {state['phase']} -> {args.to}; "
            "use accept-renders, begin-repair, complete-repair, or complete-quality"
        )

    table = load_transition_table()
    allowed = table["transitions"][state["workflow"]].get(state["phase"], [])
    if args.to not in allowed:
        raise StateError(
            f"Illegal transition for {state['workflow']}: {state['phase']} -> {args.to}; allowed={allowed}"
        )
    ensure_gate(state, gate_requirement(table, state["workflow"], args.to))

    if args.to == "building" and state["active_wave"] is None:
        state["active_wave"] = 1

    previous = state["phase"]
    state["phase"] = args.to
    state["status"] = status_for_phase(args.to)
    append_history(state, "transition", at, from_phase=previous, to_phase=args.to, reason=args.reason)
    save_state(root, state, at)
    return state


def require_gate_dependencies(state: dict[str, Any], gate_name: str) -> None:
    if gate_name in {"direction", "repository_changes"} and not gate_is_active(state, "understanding"):
        raise StateError(f"Cannot approve {gate_name} while understanding is missing or stale")
    if (
        gate_name == "repository_changes"
        and state["workflow"] == "run"
        and not gate_is_active(state, "direction")
    ):
        raise StateError("Cannot approve repository changes while direction is missing or stale")


def command_record_gate(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)

    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)

    table = load_transition_table()
    expected_phase = table["gate_recording_phases"][args.gate]
    existing = state["gates"][args.gate]
    reapproving_stale = existing is not None and existing["status"] == "stale"
    if state["phase"] != expected_phase and not reapproving_stale:
        raise StateError(
            f"Gate {args.gate} may be recorded only in phase {expected_phase}, unless reapproving a stale gate"
        )
    if state["status"] == "paused" and not reapproving_stale:
        raise StateError("Workflow is paused")
    if state["phase"] in {"blocked", "complete"}:
        raise StateError(f"Cannot record an approval gate while phase is {state['phase']}")

    require_gate_dependencies(state, args.gate)

    if args.status == "skipped":
        if args.gate != "understanding":
            raise StateError("Only the understanding gate may be skipped")
        if not args.warning_acknowledged:
            raise StateError("Skipping shared understanding requires the risk warning acknowledgement")
    artifact, relative = resolve_artifact(root, args.artifact)
    validate_gate_authority_contract(
        args.gate,
        args.status,
        relative,
        args.decision_text,
        bool(args.warning_acknowledged),
    )
    digest = sha256(artifact)
    direction_set_digest: str | None = None
    if args.gate == "direction":
        direction_set, direction_set_relative = resolve_artifact(
            root, DIRECTION_SET_RELATIVE_PATH
        )
        if direction_set_relative != DIRECTION_SET_RELATIVE_PATH:
            raise StateError(
                f"Direction approval must bind canonical artifact {DIRECTION_SET_RELATIVE_PATH}"
            )
        direction_set_digest = sha256(direction_set)
    record = {
        "gate": args.gate,
        "status": args.status,
        "artifact_path": relative,
        "artifact_sha256": digest,
        "decided_at": at,
        "decision_text": args.decision_text.strip(),
        "warning_acknowledged": bool(args.warning_acknowledged),
        "scope": args.scope or "",
        "assumptions_accepted": list(args.assumption or []),
        "stale_reason": None,
        "stale_at": None,
    }
    validate_gate(args.gate, record)
    state["gates"][args.gate] = record
    state["artifacts"][relative] = digest
    if direction_set_digest is not None:
        state["artifacts"][DIRECTION_SET_RELATIVE_PATH] = direction_set_digest
    append_history(
        state,
        "gate_recorded",
        at,
        gate=args.gate,
        status=args.status,
        artifact_path=relative,
        artifact_sha256=digest,
        bound_direction_set_path=(
            DIRECTION_SET_RELATIVE_PATH if direction_set_digest is not None else None
        ),
        bound_direction_set_sha256=direction_set_digest,
    )
    save_state(root, state, at)
    return state


def command_pause(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    if state["status"] in {"paused", "blocked", "complete"}:
        raise StateError(f"Cannot pause workflow with status {state['status']}")
    state["status"] = "paused"
    append_history(state, "paused", at, phase=state["phase"], reason=args.reason)
    save_state(root, state, at)
    return state


def command_resume(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)
    stale = stale_gate_names(state)
    if stale:
        raise StateError(f"Cannot resume with stale approval gates: {', '.join(stale)}")
    if state["status"] != "paused":
        raise StateError(f"Resume requires paused status; current status is {state['status']}")
    state["status"] = status_for_phase(state["phase"])
    append_history(state, "resumed", at, phase=state["phase"], reason=args.reason)
    save_state(root, state, at)
    return state


def command_block(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    if state["status"] == "paused":
        raise StateError("Resume the paused workflow before recording a blocker")
    if state["phase"] in {"blocked", "complete"}:
        raise StateError(f"Cannot block workflow from phase {state['phase']}")
    previous = state["phase"]
    blocker = {
        "reason": args.reason,
        "created_at": at,
        "phase": previous,
        "resolved_at": None,
        "resolution": None,
    }
    state["blockers"].append(blocker)
    state["phase_before_block"] = previous
    state["phase"] = "blocked"
    state["status"] = "blocked"
    append_history(state, "blocked", at, from_phase=previous, reason=args.reason)
    save_state(root, state, at)
    return state


def command_unblock(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    if state["phase"] != "blocked" or state["status"] != "blocked":
        raise StateError("Workflow is not blocked")
    restore = state["phase_before_block"]
    if restore is None or restore not in PHASES - {"blocked"}:
        raise StateError("Blocked state has no valid recovery phase")
    unresolved = next(
        (item for item in reversed(state["blockers"]) if item.get("resolved_at") is None),
        None,
    )
    if unresolved is None:
        raise StateError("Blocked state has no unresolved blocker record")
    unresolved["resolved_at"] = at
    unresolved["resolution"] = args.reason
    state["phase"] = restore
    state["status"] = status_for_phase(restore)
    state["phase_before_block"] = None
    refresh_staleness(root, state, at)
    append_history(state, "unblocked", at, to_phase=restore, reason=args.reason)
    save_state(root, state, at)
    return state


def legal_targets(state: dict[str, Any], table: dict[str, Any]) -> list[str]:
    if state["status"] != default_status_for_phase(state["phase"]):
        return []
    if stale_gate_names(state) or state["phase"] in {"blocked", "complete"}:
        return []
    legal: list[str] = []
    for target in table["transitions"][state["workflow"]].get(state["phase"], []):
        try:
            ensure_gate(state, gate_requirement(table, state["workflow"], target))
        except StateError:
            continue
        legal.append(target)
    return legal


def command_verify(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)
    stale = stale_gate_names(state)
    table = load_transition_table()
    structural = table["transitions"][state["workflow"]].get(state["phase"], [])
    if state["phase"] == "blocked":
        next_action = ["unblock"]
    elif stale:
        next_action = [f"reapprove:{name}" for name in stale]
    elif state["status"] == "paused":
        next_action = ["resume"]
    else:
        next_action = legal_targets(state, table)
    report = {
        "valid": True,
        "state_path": state_path(root).as_posix(),
        "workflow": state["workflow"],
        "route": state["route"],
        "phase": state["phase"],
        "status": state["status"],
        "revision": state["revision"],
        "stale_gates": stale,
        "next_structural": structural,
        "next_legal": next_action,
    }
    return report, 2 if stale else 0


def command_show(args: argparse.Namespace) -> dict[str, Any]:
    return load_state(project_root(args.project_root))


def command_start_wave(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    state = load_state(root)
    at = normalize_timestamp(args.at)
    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)
    stale = stale_gate_names(state)
    if stale:
        raise StateError(f"Cannot start a wave with stale approval gates: {', '.join(stale)}")
    if state["phase"] != "building" or state["status"] != "active":
        raise StateError("Wave start requires active building state")
    active_wave = state["active_wave"]
    if active_wave is None:
        raise StateError("Building state has no active wave")
    manifest, manifest_relative = resolve_artifact(root, args.manifest)
    try:
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateError(f"Wave manifest is invalid JSON: {exc}") from exc
    if not isinstance(manifest_data, dict):
        raise StateError("Wave manifest root must be an object")
    try:
        from design_build import (
            _validate_active_state,
            _validate_manifest_against_plan,
            changed_since,
            load_json as load_build_json,
            validate_manifest,
            validate_plan,
        )

        validate_manifest(manifest_data)
        input_map = {item["purpose"]: item for item in manifest_data["artifact_inputs"]}
        plan_relative = input_map["structured implementation plan"]["path"]
        plan = validate_plan(load_build_json(root / plan_relative))
        verified_state, _, _ = _validate_active_state(root, plan)
        _validate_manifest_against_plan(manifest_data, plan, verified_state, root, plan_relative)
        control = set(manifest_data["control_files"]) | {".design/state.json"}
        unexpected = [
            path
            for path in changed_since(root, manifest_data["repository_baseline"])
            if path not in control
        ]
        if unexpected:
            raise StateError(f"Product files changed before manifest binding: {unexpected}")
    except (ImportError, KeyError, OSError, RuntimeError) as exc:
        raise StateError(f"Wave manifest validation failed: {exc}") from exc
    if manifest_data.get("wave_number") != active_wave or manifest_data.get("status") != "active":
        raise StateError("Wave manifest does not match active_wave")
    expected = f".design/implementation/waves/{manifest_data.get('wave_id')}/manifest.json"
    if manifest_relative != expected:
        raise StateError(f"Wave manifest must use canonical path {expected}")
    if manifest_relative in state["artifacts"]:
        raise StateError("Wave manifest is already bound in state")

    digest = sha256(manifest)
    state["artifacts"][manifest_relative] = digest
    append_history(
        state,
        "wave_started",
        at,
        wave=active_wave,
        manifest_path=manifest_relative,
        manifest_sha256=digest,
        reason=args.reason,
    )
    save_state(root, state, at)
    return state


def command_complete_wave(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    at = normalize_timestamp(args.at)
    try:
        from design_build import _atomic_write_json
        from design_build import load_json as load_build_json
        from design_build import validate_plan, verify_wave8

        report = verify_wave8(root, args.manifest, args.handoff)
        manifest_path, manifest_relative = resolve_artifact(root, args.manifest)
        manifest_data = load_build_json(manifest_path)
        input_map = {item["purpose"]: item for item in manifest_data["artifact_inputs"]}
        plan_path = root / input_map["structured implementation plan"]["path"]
        plan = validate_plan(load_build_json(plan_path))
        receipt_path = root / f".design/implementation/waves/{report['wave_id']}/verification.json"
        _atomic_write_json(receipt_path, report)
    except (ImportError, KeyError, OSError, RuntimeError) as exc:
        raise StateError(f"Wave verification failed: {exc}") from exc

    state = load_state(root)
    active_wave = state["active_wave"]
    if state["phase"] != "building" or state["status"] != "active" or active_wave is None:
        raise StateError("Wave completion requires active building state")
    if report["wave_number"] != active_wave:
        raise StateError("Verified wave does not match active_wave")
    handoff, handoff_relative = resolve_artifact(root, args.handoff)
    handoff_digest = sha256(handoff)
    state["artifacts"][handoff_relative] = handoff_digest
    handoff_markdown, handoff_markdown_relative = resolve_artifact(root, report["handoff_markdown"])
    handoff_markdown_digest = sha256(handoff_markdown)
    state["artifacts"][handoff_markdown_relative] = handoff_markdown_digest
    receipt_relative = receipt_path.relative_to(root).as_posix()
    state["artifacts"][receipt_relative] = sha256(receipt_path)
    append_history(
        state,
        "wave_completed",
        at,
        wave=active_wave,
        manifest_path=manifest_relative,
        manifest_sha256=sha256(manifest_path),
        handoff_path=handoff_relative,
        handoff_sha256=handoff_digest,
        handoff_markdown_path=handoff_markdown_relative,
        handoff_markdown_sha256=handoff_markdown_digest,
        verification_path=receipt_relative,
        verification_sha256=sha256(receipt_path),
        reason=args.reason,
    )
    total_waves = len(plan["waves"])
    if active_wave < total_waves:
        state["active_wave"] = active_wave + 1
    else:
        state["active_wave"] = None
        state["phase"] = "rendering"
        state["status"] = status_for_phase("rendering")
        append_history(
            state,
            "transition",
            at,
            from_phase="building",
            to_phase="rendering",
            reason="All approved implementation waves have complete handoffs.",
        )
    save_state(root, state, at)
    return state


def _require_active_quality_state(root: Path, state: dict[str, Any], at: str, phases: set[str]) -> None:
    newly_stale = refresh_staleness(root, state, at)
    if newly_stale:
        save_state(root, state, at)
        raise StateError(f"Stale approval gates detected: {', '.join(newly_stale)}. Reapproval is required.")
    if state["status"] != "active" or state["phase"] not in phases:
        raise StateError(f"Quality command requires active state in {sorted(phases)}")


def command_accept_renders(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    at = normalize_timestamp(args.at)
    state = load_state(root)
    allowed = {"rendering"} if state["workflow"] == "run" else {"rendering", "qa"}
    _require_active_quality_state(root, state, at, allowed)
    try:
        from design_quality import _atomic_write_json, verify_render_evidence

        report = verify_render_evidence(root, args.plan, args.evidence, check_current_state=True)
    except (ImportError, OSError, RuntimeError) as exc:
        raise StateError(f"Render verification failed: {exc}") from exc
    if report["status"] != "complete":
        raise StateError(f"Required render evidence is blocked: {report['required_blockers']}")
    receipt = root / ".design/renders/verification.json"
    report["accepted_at"] = at
    _atomic_write_json(receipt, report)
    for item in (report["render_plan"], report["render_evidence"]):
        state["artifacts"][item["path"]] = item["sha256"]
    receipt_relative = receipt.relative_to(root).as_posix()
    state["artifacts"][receipt_relative] = sha256(receipt)
    previous = state["phase"]
    if previous == "rendering":
        state["phase"] = "qa"
        state["status"] = status_for_phase("qa")
    append_history(
        state,
        "renders_accepted",
        at,
        from_phase=previous,
        to_phase=state["phase"],
        render_plan=report["render_plan"],
        render_evidence=report["render_evidence"],
        verification_path=receipt_relative,
        verification_sha256=sha256(receipt),
        reason=args.reason,
    )
    save_state(root, state, at)
    return state


def command_begin_repair(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    at = normalize_timestamp(args.at)
    state = load_state(root)
    _require_active_quality_state(root, state, at, {"qa"})
    ensure_gate(state, {"gate": "repository_changes", "allowed_statuses": ["approved"]})
    try:
        from design_quality import create_repair_plan, validate_qa_report

        qa_result = validate_qa_report(root, args.qa_report, check_current_state=True)
        qa_path, qa_relative = resolve_artifact(root, args.qa_report)
        qa_data = json.loads(qa_path.read_text(encoding="utf-8"))
    except (ImportError, json.JSONDecodeError, OSError, RuntimeError) as exc:
        raise StateError(f"QA verification failed: {exc}") from exc
    if qa_result["status"] not in {"repair-required", "blocked"}:
        raise StateError("A repair cycle requires unresolved QA findings")
    requested = list(args.finding)
    if not requested or len(requested) != len(set(requested)):
        raise StateError("Repair finding IDs must be non-empty and unique")
    open_findings = {
        item["id"]: item
        for item in qa_data["findings"]
        if item["status"] == "open"
    }
    if not set(requested) <= set(open_findings):
        raise StateError("Repair request contains an unknown or non-open finding")
    target_ids = sorted({open_findings[finding_id]["target_id"] for finding_id in requested})
    attempts = dict(state["repair_attempts"])
    for target_id in target_ids:
        current = attempts.get(target_id, 0)
        if current >= 3:
            raise StateError(
                f"Repair limit reached for {target_id}. Record a blocker instead of starting attempt 4."
            )
        attempts[target_id] = current + 1

    projected = json.loads(json.dumps(state))
    projected["repair_cycle"] += 1
    projected["repair_attempts"] = attempts
    projected["repair_pass"] = max(attempts[target_id] for target_id in target_ids)
    projected["phase"] = "repairing"
    projected["status"] = status_for_phase("repairing")
    projected["revision"] += 1
    projected["updated_at"] = at
    try:
        plan_path, _ = create_repair_plan(
            root,
            qa_path,
            requested,
            args.worker_id,
            list(args.allowed_file),
            list(args.action),
            list(args.check),
            projected,
            at=at,
        )
    except (ImportError, OSError, RuntimeError) as exc:
        raise StateError(f"Repair plan preparation failed: {exc}") from exc

    state["repair_cycle"] = projected["repair_cycle"]
    state["repair_attempts"] = attempts
    state["repair_pass"] = projected["repair_pass"]
    state["phase"] = "repairing"
    state["status"] = status_for_phase("repairing")
    state["artifacts"][qa_relative] = sha256(qa_path)
    plan_relative = plan_path.relative_to(root).as_posix()
    state["artifacts"][plan_relative] = sha256(plan_path)
    append_history(
        state,
        "repair_started",
        at,
        repair_cycle=state["repair_cycle"],
        repair_pass=state["repair_pass"],
        target_ids=target_ids,
        finding_ids=requested,
        qa_report_path=qa_relative,
        qa_report_sha256=sha256(qa_path),
        repair_plan_path=plan_relative,
        repair_plan_sha256=sha256(plan_path),
        reason=args.reason,
    )
    save_state(root, state, at)
    return state


def command_complete_repair(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    at = normalize_timestamp(args.at)
    state = load_state(root)
    _require_active_quality_state(root, state, at, {"repairing"})
    try:
        from design_quality import _atomic_write_json, load_json as load_quality_json, validate_repair_handoff

        plan_path, plan_relative = resolve_artifact(root, args.plan)
        if state["artifacts"].get(plan_relative) != sha256(plan_path):
            raise StateError("Repair plan is not bound in state")
        plan = load_quality_json(plan_path)
        report = validate_repair_handoff(root, plan_path, args.handoff, state=state)
        handoff_path, handoff_relative = resolve_artifact(root, args.handoff)
        receipt = root / f".design/qa/repairs/cycle-{plan['cycle_number']}-verification.json"
        report["accepted_at"] = at
        _atomic_write_json(receipt, report)
    except StateError:
        raise
    except (ImportError, OSError, RuntimeError) as exc:
        raise StateError(f"Repair verification failed: {exc}") from exc
    state["artifacts"][handoff_relative] = sha256(handoff_path)
    receipt_relative = receipt.relative_to(root).as_posix()
    state["artifacts"][receipt_relative] = sha256(receipt)
    state["phase"] = "rendering"
    state["status"] = status_for_phase("rendering")
    append_history(
        state,
        "repair_completed",
        at,
        repair_cycle=plan["cycle_number"],
        repair_pass=plan["pass_number"],
        repair_plan_path=plan_relative,
        repair_handoff_path=handoff_relative,
        repair_handoff_sha256=sha256(handoff_path),
        verification_path=receipt_relative,
        verification_sha256=sha256(receipt),
        rerender_targets=report["rerender_targets"],
        reason=args.reason,
    )
    save_state(root, state, at)
    return state


def command_complete_quality(args: argparse.Namespace) -> dict[str, Any]:
    root = project_root(args.project_root)
    at = normalize_timestamp(args.at)
    state = load_state(root)
    _require_active_quality_state(root, state, at, {"qa"})
    try:
        from design_quality import _atomic_write_json, verify_completion

        report = verify_completion(root, args.qa_report, args.deviations, args.scorecard)
    except (ImportError, OSError, RuntimeError) as exc:
        raise StateError(f"Quality completion failed: {exc}") from exc
    receipt = root / ".design/qa/verification.json"
    report["accepted_at"] = at
    _atomic_write_json(receipt, report)
    for key in ("qa_report", "deviations", "scorecard"):
        item = report[key]
        state["artifacts"][item["path"]] = item["sha256"]
    receipt_relative = receipt.relative_to(root).as_posix()
    state["artifacts"][receipt_relative] = sha256(receipt)
    state["phase"] = "complete"
    state["status"] = status_for_phase("complete")
    append_history(
        state,
        "quality_completed",
        at,
        qa_report=report["qa_report"],
        deviations=report["deviations"],
        scorecard=report["scorecard"],
        accepted_deviations=report["accepted_deviations"],
        verification_path=receipt_relative,
        verification_sha256=sha256(receipt),
        reason=args.reason,
    )
    save_state(root, state, at)
    return state
