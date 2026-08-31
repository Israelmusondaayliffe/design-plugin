"""Validation and durable storage for Design workflow state."""

from __future__ import annotations

from typing import Any

from design_state_base import *


def require_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{label} must be a non-empty ISO-8601 timestamp")
    return normalize_timestamp(value)


def normalize_gate_decision(value: str) -> str:
    return value.strip().rstrip(".").casefold()


def validate_gate_authority_contract(
    name: str,
    status: str,
    artifact_path: str,
    decision_text: str,
    warning_acknowledged: bool,
) -> None:
    expected_path = GATE_ARTIFACT_PATHS[name]
    if artifact_path != expected_path:
        raise StateError(
            f"Gate {name!r} must bind its canonical artifact {expected_path}; got {artifact_path}"
        )

    approval_required = status == "approved" or (
        name != "understanding" and status in {"stale", "revoked"}
    )
    if approval_required:
        normalized = normalize_gate_decision(decision_text)
        allowed = GATE_APPROVAL_DECISIONS[name]
        if normalized not in allowed:
            if name == "understanding":
                raise StateError(
                    "Shared understanding approval must be 'Approved' or 'This understanding is approved'"
                )
            required = " or ".join(repr(value) for value in sorted(allowed))
            raise StateError(
                f"Gate {name!r} approval decision must be {required}"
            )
    elif name == "understanding" and status in {"stale", "revoked"}:
        normalized = normalize_gate_decision(decision_text)
        if not warning_acknowledged and normalized not in GATE_APPROVAL_DECISIONS[name]:
            raise StateError(
                "An inactive understanding gate must preserve an explicit approval decision or an acknowledged skip"
            )


def validate_gate(name: str, gate: Any) -> None:
    if gate is None:
        return
    if not isinstance(gate, dict):
        raise StateError(f"Gate {name!r} must be an object or null")
    required = {
        "gate",
        "status",
        "artifact_path",
        "artifact_sha256",
        "decided_at",
        "decision_text",
        "warning_acknowledged",
        "scope",
        "assumptions_accepted",
        "stale_reason",
        "stale_at",
    }
    if set(gate) != required:
        missing = sorted(required.difference(gate))
        extra = sorted(set(gate).difference(required))
        raise StateError(f"Gate {name!r} keys invalid; missing={missing}, extra={extra}")
    if gate["gate"] != name:
        raise StateError(f"Gate record {name!r} names {gate['gate']!r}")
    if gate["status"] not in {"approved", "skipped", "stale", "revoked"}:
        raise StateError(f"Gate {name!r} has invalid status")
    validate_relative_record_path(gate["artifact_path"], f"Gate {name!r} artifact_path")
    digest = gate["artifact_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise StateError(f"Gate {name!r} artifact_sha256 is invalid")
    require_timestamp(gate["decided_at"], f"Gate {name!r} decided_at")
    if not isinstance(gate["decision_text"], str) or not gate["decision_text"].strip():
        raise StateError(f"Gate {name!r} decision_text must be non-empty")
    if not isinstance(gate["warning_acknowledged"], bool):
        raise StateError(f"Gate {name!r} warning_acknowledged must be boolean")
    if not isinstance(gate["scope"], str):
        raise StateError(f"Gate {name!r} scope must be a string")
    if not isinstance(gate["assumptions_accepted"], list) or not all(
        isinstance(item, str) for item in gate["assumptions_accepted"]
    ):
        raise StateError(f"Gate {name!r} assumptions_accepted must be a string array")
    if gate["stale_reason"] is not None and not isinstance(gate["stale_reason"], str):
        raise StateError(f"Gate {name!r} stale_reason must be string or null")
    if gate["stale_at"] is not None:
        require_timestamp(gate["stale_at"], f"Gate {name!r} stale_at")

    validate_gate_authority_contract(
        name,
        gate["status"],
        gate["artifact_path"],
        gate["decision_text"],
        gate["warning_acknowledged"],
    )

    if gate["status"] == "skipped" and name != "understanding":
        raise StateError("Only the understanding gate may be skipped")
    if gate["status"] == "skipped" and not gate["warning_acknowledged"]:
        raise StateError("A skipped understanding gate must acknowledge the risk warning")
    if gate["status"] in {"approved", "skipped"}:
        if gate["stale_reason"] is not None or gate["stale_at"] is not None:
            raise StateError(f"Active gate {name!r} must not retain stale metadata")
    if gate["status"] in {"stale", "revoked"}:
        if not isinstance(gate["stale_reason"], str) or not gate["stale_reason"].strip():
            raise StateError(f"Inactive gate {name!r} requires a reason")
        if gate["stale_at"] is None:
            raise StateError(f"Inactive gate {name!r} requires a timestamp")


def validate_blocker(blocker: Any, index: int) -> bool:
    if not isinstance(blocker, dict):
        raise StateError(f"blockers[{index}] must be an object")
    required = {"reason", "created_at", "phase", "resolved_at", "resolution"}
    if set(blocker) != required:
        raise StateError(f"blockers[{index}] has invalid keys")
    if not isinstance(blocker["reason"], str) or not blocker["reason"].strip():
        raise StateError(f"blockers[{index}] reason must be non-empty")
    require_timestamp(blocker["created_at"], f"blockers[{index}] created_at")
    if blocker["phase"] not in PHASES - {"blocked"}:
        raise StateError(f"blockers[{index}] phase is invalid")
    resolved = blocker["resolved_at"] is not None
    if resolved:
        require_timestamp(blocker["resolved_at"], f"blockers[{index}] resolved_at")
        if not isinstance(blocker["resolution"], str) or not blocker["resolution"].strip():
            raise StateError(f"blockers[{index}] resolved blocker needs a resolution")
    elif blocker["resolution"] is not None:
        raise StateError(f"blockers[{index}] unresolved blocker cannot have a resolution")
    return not resolved


def validate_history_event(event: Any, index: int) -> None:
    if not isinstance(event, dict):
        raise StateError(f"history[{index}] must be an object")
    if not isinstance(event.get("event"), str) or not event["event"].strip():
        raise StateError(f"history[{index}] requires an event name")
    require_timestamp(event.get("at"), f"history[{index}] at")


def gate_is_active(state: dict[str, Any], name: str) -> bool:
    gate = state["gates"][name]
    return gate is not None and gate["status"] in {"approved", "skipped"}


def validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise StateError("State root must be a JSON object")
    if set(state) != TOP_LEVEL_KEYS:
        missing = sorted(TOP_LEVEL_KEYS.difference(state))
        extra = sorted(set(state).difference(TOP_LEVEL_KEYS))
        raise StateError(f"State keys invalid; missing={missing}, extra={extra}")
    if state["schema_version"] != "1.0" or state["plugin"] != "design":
        raise StateError("Unsupported state schema or plugin identity")
    if not isinstance(state["revision"], int) or isinstance(state["revision"], bool) or state["revision"] < 0:
        raise StateError("revision must be a non-negative integer")
    if state["workflow"] not in {"run", "audit"}:
        raise StateError("workflow must be run or audit")
    if state["route"] not in {"standard", "lightweight_repair"}:
        raise StateError("route must be standard or lightweight_repair")
    if state["phase"] not in PHASES:
        raise StateError(f"Unknown phase: {state['phase']!r}")
    if state["status"] not in STATUSES:
        raise StateError(f"Unknown status: {state['status']!r}")

    expected_status = default_status_for_phase(state["phase"])
    allowed_statuses = {expected_status}
    if state["phase"] not in {"blocked", "complete"}:
        allowed_statuses.add("paused")
    if state["status"] not in allowed_statuses:
        raise StateError(
            f"Phase {state['phase']!r} cannot have status {state['status']!r}; allowed={sorted(allowed_statuses)}"
        )

    if state["phase"] == "blocked":
        if state["phase_before_block"] not in PHASES - {"blocked"}:
            raise StateError("Blocked state requires a valid phase_before_block")
    elif state["phase_before_block"] is not None:
        raise StateError("phase_before_block must be null outside blocked state")

    if not isinstance(state["gates"], dict) or set(state["gates"]) != set(GATE_NAMES):
        raise StateError("gates must contain exactly understanding, direction, repository_changes")
    for name in GATE_NAMES:
        validate_gate(name, state["gates"][name])

    if gate_is_active(state, "direction") and not gate_is_active(state, "understanding"):
        raise StateError("An active direction gate requires an active understanding gate")
    if gate_is_active(state, "repository_changes"):
        if not gate_is_active(state, "understanding"):
            raise StateError("Repository approval requires an active understanding gate")
        if state["workflow"] == "run" and not gate_is_active(state, "direction"):
            raise StateError("Run workflow repository approval requires an active direction gate")

    if not isinstance(state["artifacts"], dict):
        raise StateError("artifacts must be an object")
    for path, digest in state["artifacts"].items():
        validate_relative_record_path(path, "artifact key")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise StateError(f"artifact digest invalid for {path!r}")

    if state["gates"]["direction"] is not None:
        if DIRECTION_SET_RELATIVE_PATH not in state["artifacts"]:
            raise StateError(
                f"Direction approval must bind {DIRECTION_SET_RELATIVE_PATH} in state artifacts"
            )

    if state["active_wave"] is not None and (
        not isinstance(state["active_wave"], int)
        or isinstance(state["active_wave"], bool)
        or state["active_wave"] < 1
    ):
        raise StateError("active_wave must be null or an integer >= 1")
    effective_phase = state["phase_before_block"] if state["phase"] == "blocked" else state["phase"]
    if effective_phase in PRE_BUILD_PHASES and state["active_wave"] is not None:
        raise StateError("active_wave must be null before implementation begins")
    if effective_phase == "building" and state["active_wave"] is None:
        raise StateError("building phase requires an active_wave")

    if (
        not isinstance(state["repair_pass"], int)
        or isinstance(state["repair_pass"], bool)
        or not 0 <= state["repair_pass"] <= 3
    ):
        raise StateError("repair_pass must be between 0 and 3")
    if (
        not isinstance(state["repair_cycle"], int)
        or isinstance(state["repair_cycle"], bool)
        or state["repair_cycle"] < 0
    ):
        raise StateError("repair_cycle must be a non-negative integer")
    if not isinstance(state["repair_attempts"], dict):
        raise StateError("repair_attempts must be an object")
    for target, count in state["repair_attempts"].items():
        if not isinstance(target, str) or not target.strip():
            raise StateError("repair_attempts keys must be non-empty target IDs")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 3:
            raise StateError(f"repair_attempts[{target!r}] must be between 1 and 3")
    if state["repair_cycle"] == 0 and (state["repair_pass"] != 0 or state["repair_attempts"]):
        raise StateError("repair state cannot exist before the first repair cycle")

    if not isinstance(state["blockers"], list):
        raise StateError("blockers must be an array")
    unresolved_count = sum(
        1 for index, blocker in enumerate(state["blockers"]) if validate_blocker(blocker, index)
    )
    if state["phase"] == "blocked" and unresolved_count != 1:
        raise StateError("Blocked state requires exactly one unresolved blocker")
    if state["phase"] != "blocked" and unresolved_count != 0:
        raise StateError("Unresolved blockers require blocked state")

    if not isinstance(state["history"], list) or not state["history"]:
        raise StateError("history must be a non-empty array")
    for index, event in enumerate(state["history"]):
        validate_history_event(event, index)

    created_at = require_timestamp(state["created_at"], "created_at")
    updated_at = require_timestamp(state["updated_at"], "updated_at")
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    if updated < created:
        raise StateError("updated_at cannot be earlier than created_at")
    return state


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StateError(f"State file does not exist: {path}") from exc
    try:
        state = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StateError(f"State file is corrupted JSON: {exc}") from exc
    return validate_state(state)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    descriptor, temp_name = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def append_history(state: dict[str, Any], event: str, at: str, **details: Any) -> None:
    state["history"].append({"event": event, "at": at, **details})


def save_state(root: Path, state: dict[str, Any], at: str) -> None:
    state["revision"] += 1
    state["updated_at"] = at
    validate_state(state)
    atomic_write_json(state_path(root), state)
