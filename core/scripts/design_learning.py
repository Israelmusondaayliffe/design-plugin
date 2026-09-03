#!/usr/bin/env python3
"""Store bounded Design feedback privately and export neutral learning signals.

The standard-library tool writes outside repositories by default. It never scans
passively, changes another plugin, or sends data to an external service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LearningError(RuntimeError):
    pass


CATEGORIES = {
    "feedback",
    "friction",
    "repair",
    "missed-tool",
    "cost-decision",
    "user-method",
}
SENSITIVE_RE = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]
PATH_RE = re.compile(r"(?:/[A-Za-z0-9._ -]+){2,}")
FORBIDDEN_COMPONENTS = {".git", "dist", "site", "sites", "evidence", "review", "plugins"}
SOURCE_MARKERS = re.compile(r"(?:^|[-_])(?:plugin-?source|source-plugin)(?:$|[-_])", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact(text: str) -> str:
    result = text.strip()
    for pattern in SENSITIVE_RE:
        result = pattern.sub("[REDACTED]", result)
    result = PATH_RE.sub("[REDACTED_PATH]", result)
    return result[:1200]


def opaque_project_id(project_key: str) -> str:
    value = project_key.strip()
    if not value:
        raise LearningError("project key must not be empty")
    return "project-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _default_root() -> Path:
    configured = os.environ.get("DESIGN_LEARNING_ROOT")
    if configured:
        return Path(configured).expanduser()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "design-plugin" / "learning"
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
    return base / "design-plugin" / "learning"


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _inside_git_worktree(path: Path) -> bool:
    cursor = path if path.exists() and path.is_dir() else path.parent
    for candidate in (cursor, *cursor.parents):
        if (candidate / ".git").exists():
            return True
    return False


def validate_state_root(value: str | Path | None = None) -> Path:
    raw_candidate = Path(value).expanduser() if value else _default_root()
    if _has_symlink_component(raw_candidate.absolute()):
        raise LearningError("learning root cannot contain symbolic links")
    candidate = raw_candidate.resolve(strict=False)
    lowered = {part.casefold() for part in candidate.parts}
    own_plugin_root = Path(__file__).resolve().parents[2]
    known_plugin_roots = (
        own_plugin_root,
        Path.home() / ".codex" / "plugins",
        Path.home() / ".claude" / "plugins",
        Path.home() / "plugins",
    )
    inside_known_plugin_root = any(
        candidate == root.resolve(strict=False) or root.resolve(strict=False) in candidate.parents
        for root in known_plugin_roots
    )
    source_named = any(SOURCE_MARKERS.search(part) for part in candidate.parts)
    if lowered & FORBIDDEN_COMPONENTS or inside_known_plugin_root or source_named:
        raise LearningError("learning root cannot be inside plugin, distribution, Site, review, or evidence paths")
    if _inside_git_worktree(candidate):
        raise LearningError("learning root cannot be inside a Git worktree")
    return candidate


def _event_files(root: Path) -> list[Path]:
    events = root / "events"
    if not events.exists():
        return []
    return sorted(path for path in events.rglob("*.json") if path.is_file() and not path.is_symlink())


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearningError(f"cannot read valid event {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LearningError(f"event is not an object: {path}")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def capture_event(args: argparse.Namespace) -> dict[str, Any]:
    root = validate_state_root(args.state_root)
    if args.category not in CATEGORIES:
        raise LearningError(f"unknown category: {args.category}")
    if args.exact_quote and not args.retain_exact_quote:
        raise LearningError("exact quotes require --retain-exact-quote after an explicit retention request such as 'file this'")
    project_id = opaque_project_id(args.project_key)
    created_at = utc_now()
    neutral = "\n".join(
        redact(value) for value in (args.summary, args.impact or "", args.method or "") if value
    )
    fingerprint = hashlib.sha256(f"{args.category}\0{neutral.casefold()}".encode("utf-8")).hexdigest()
    event_id = f"event-{uuid.uuid4().hex}"
    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "project_id": project_id,
        "category": args.category,
        "summary": redact(args.summary),
        "impact": redact(args.impact) if args.impact else None,
        "method": redact(args.method) if args.method else None,
        "exact_quote": redact(args.exact_quote) if args.exact_quote else None,
        "exact_quote_retained": bool(args.exact_quote),
        "fingerprint": fingerprint,
        "created_at": created_at,
    }
    destination = root / "events" / project_id / f"{event_id}.json"
    _atomic_json(destination, event)
    return {"event": event, "path": str(destination), "state_root": str(root)}


def list_events(args: argparse.Namespace) -> dict[str, Any]:
    root = validate_state_root(args.state_root)
    project_id = opaque_project_id(args.project_key) if args.project_key else None
    events = []
    for path in _event_files(root):
        event = _load(path)
        if project_id and event.get("project_id") != project_id:
            continue
        if args.category and event.get("category") != args.category:
            continue
        events.append(event)
    events.sort(key=lambda item: (item.get("created_at", ""), item.get("event_id", "")))
    return {"state_root": str(root), "count": len(events), "events": events}


def export_events(args: argparse.Namespace) -> dict[str, Any]:
    listed = list_events(args)
    records = []
    seen: set[str] = set()
    for event in listed["events"]:
        fingerprint = event["fingerprint"]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        records.append({
            "schema_version": "1.0",
            "source_type": "design-neutral-export",
            "fingerprint": fingerprint,
            "project_id": event["project_id"],
            "signal_class": event["category"],
            "summary": event["summary"],
            "impact": event.get("impact"),
            "method": event.get("method"),
            "created_at": event["created_at"],
        })
    return {"schema_version": "1.0", "exported_at": utc_now(), "count": len(records), "records": records}


def _purge(args: argparse.Namespace, project_id: str | None, before: datetime | None) -> dict[str, Any]:
    root = validate_state_root(args.state_root)
    removed = []
    for path in _event_files(root):
        event = _load(path)
        if project_id and event.get("project_id") != project_id:
            continue
        if before:
            timestamp = datetime.fromisoformat(str(event.get("created_at", "")).replace("Z", "+00:00"))
            if timestamp >= before:
                continue
        path.unlink()
        removed.append(event.get("event_id"))
    return {"state_root": str(root), "removed_count": len(removed), "removed_event_ids": removed}


def purge_before(args: argparse.Namespace) -> dict[str, Any]:
    try:
        before = datetime.fromisoformat(args.before.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LearningError("--before must be an ISO-8601 timestamp") from exc
    if before.tzinfo is None:
        raise LearningError("--before must include a timezone")
    return _purge(args, None, before.astimezone(timezone.utc))


def purge_project(args: argparse.Namespace) -> dict[str, Any]:
    return _purge(args, opaque_project_id(args.project_key), None)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--project-key", required=True)
    capture.add_argument("--category", choices=sorted(CATEGORIES), required=True)
    capture.add_argument("--summary", required=True)
    capture.add_argument("--impact")
    capture.add_argument("--method")
    capture.add_argument("--exact-quote")
    capture.add_argument("--retain-exact-quote", action="store_true")
    capture.add_argument("--state-root")
    capture.set_defaults(func=capture_event)
    for name, func in (("list", list_events), ("export", export_events)):
        command = sub.add_parser(name)
        command.add_argument("--project-key")
        command.add_argument("--category", choices=sorted(CATEGORIES))
        command.add_argument("--state-root")
        command.set_defaults(func=func)
    before = sub.add_parser("purge-before-date")
    before.add_argument("--before", required=True)
    before.add_argument("--state-root")
    before.set_defaults(func=purge_before)
    project = sub.add_parser("purge-project")
    project.add_argument("--project-key", required=True)
    project.add_argument("--state-root")
    project.set_defaults(func=purge_project)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        payload = args.func(args)
    except (LearningError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **payload}, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
