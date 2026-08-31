"""Gate refresh and transition preconditions for Design workflow state."""

from __future__ import annotations

from typing import Any

from design_state_validation import *


def status_for_phase(phase: str) -> str:
    return default_status_for_phase(phase)


def refresh_staleness(root: Path, state: dict[str, Any], at: str) -> list[str]:
    stale: list[str] = []

    def mark_stale(name: str, reason: str) -> None:
        gate = state["gates"][name]
        if gate is None or gate["status"] not in {"approved", "skipped"}:
            return
        gate["status"] = "stale"
        gate["stale_reason"] = reason
        gate["stale_at"] = at
        stale.append(name)
        append_history(state, "gate_stale", at, gate=name, reason=reason)

    for name in GATE_NAMES:
        gate = state["gates"][name]
        if gate is None or gate["status"] not in {"approved", "skipped"}:
            continue
        artifact = (root / gate["artifact_path"]).resolve()
        try:
            artifact.relative_to(root)
        except ValueError:
            reason = "approved artifact no longer resolves inside project root"
        else:
            if not artifact.is_file():
                reason = "approved artifact is missing"
            else:
                actual = sha256(artifact)
                if actual == gate["artifact_sha256"]:
                    continue
                reason = f"approved artifact hash changed to {actual}"
        mark_stale(name, reason)

    direction_gate = state["gates"]["direction"]
    if direction_gate is not None and direction_gate["status"] in {"approved", "skipped"}:
        direction_set = (root / DIRECTION_SET_RELATIVE_PATH).resolve()
        expected = state["artifacts"].get(DIRECTION_SET_RELATIVE_PATH)
        if expected is None:
            reason = "approved direction has no bound direction-set hash"
        elif not direction_set.is_file():
            reason = "approved direction set is missing"
        else:
            actual = sha256(direction_set)
            reason = "" if actual == expected else f"approved direction-set hash changed to {actual}"
        if reason:
            mark_stale("direction", reason)

    # Approval dependencies are directional. A changed understanding invalidates
    # every downstream approval; a changed direction invalidates the build plan.
    if "understanding" in stale:
        mark_stale("direction", "upstream understanding approval became stale")
        mark_stale("repository_changes", "upstream understanding approval became stale")
    if "direction" in stale:
        mark_stale("repository_changes", "upstream direction approval became stale")
    return stale


def stale_gate_names(state: dict[str, Any]) -> list[str]:
    return [
        name
        for name in GATE_NAMES
        if state["gates"][name] is not None and state["gates"][name]["status"] == "stale"
    ]


def gate_requirement(table: dict[str, Any], workflow: str, target: str) -> dict[str, Any] | None:
    workflow_requirement = (
        table.get("workflow_gate_requirements", {}).get(workflow, {}).get(target)
    )
    if workflow_requirement is not None:
        return workflow_requirement
    requirement = table["gate_requirements"].get(target)
    if target == "system_definition" and workflow != "run":
        return None
    return requirement


def ensure_gate(state: dict[str, Any], requirement: dict[str, Any] | None) -> None:
    if requirement is None:
        return
    name = requirement["gate"]
    gate = state["gates"][name]
    if gate is None:
        raise StateError(f"Transition requires the {name} gate, but no decision is recorded")
    if gate["status"] not in set(requirement["allowed_statuses"]):
        raise StateError(
            f"Transition requires {name} status in {requirement['allowed_statuses']}; current status is {gate['status']}"
        )
