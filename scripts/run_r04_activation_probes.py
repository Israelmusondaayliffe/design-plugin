#!/usr/bin/env python3
"""Run fail-closed R04 routing probes without using the active harness.

This maintainer-only evidence runner is not part of either plugin runtime. Its
restrictions keep qualification independent of one developer's global
instructions, plugins, memories, and routing rules. Normal multi-plugin
compatibility is outside this runner's evidence boundary.

Claude probes require ``ANTHROPIC_API_KEY`` because ``--bare`` deliberately
ignores subscription and keychain authentication. Codex probes require a
separate, preauthenticated ``CODEX_HOME`` supplied with ``--codex-home``.
The active ``~/.codex`` home is always rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CODEX_HOME = (Path.home() / ".codex").resolve()
VISIBLE_WORKFLOWS = ("run", "audit", "resume")
CODEX_QUALIFICATION_HOME_ALLOWLIST = {
    ".codex-global-state.json",
    "auth.json",
    "config.toml",
    "installation_id",
    "models_cache.json",
    "version.json",
}
CLAUDE_PROVIDER_ENV_PREFIXES = (
    "ANTHROPIC_",
    "AWS_",
    "AMAZON_",
    "AZURE_",
    "CLAUDE_",
    "GOOGLE_",
    "VERTEX_",
)


class ProbeError(RuntimeError):
    """Raised when a probe cannot run inside the required boundary."""


@dataclass(frozen=True)
class ProbeCase:
    case_id: str
    category: str
    expected: str
    base_prompt: str


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ProbeError(f"Cannot load JSON at {path}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def tree_sha256(root: Path) -> str:
    if not root.is_dir():
        raise ProbeError(f"Required package directory is missing: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ProbeError(f"Package contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            contents = path.read_bytes()
            digest.update(len(contents).to_bytes(8, "big"))
            digest.update(contents)
    return digest.hexdigest()


def command_version(command: str) -> str:
    completed = run_command([command, "--version"], cwd=ROOT, env=os.environ.copy())
    version = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0 or not version:
        raise ProbeError(f"Could not bind the {Path(command).name} CLI version")
    return version


def candidate_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    return {
        "commit": commit,
        "tree": tree,
        "clean": not status.strip(),
        "status_sha256": sha256_bytes(status.encode("utf-8")),
    }


def active_registry_snapshot() -> dict[str, str]:
    candidates = [
        Path.home() / ".codex/config.toml",
        Path.home() / ".agents/plugins/marketplace.json",
        Path.home() / ".claude/settings.json",
        Path.home() / ".claude.json",
        Path.home() / ".claude/plugins/installed_plugins.json",
        Path.home() / ".claude/plugins/known_marketplaces.json",
    ]
    return {
        f"registry_{index}": sha256_file(path) if path.is_file() else "missing"
        for index, path in enumerate(candidates)
    }


def claude_api_key_env(config_root: Path) -> dict[str, str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProbeError("ANTHROPIC_API_KEY is required for bare Claude qualification")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(CLAUDE_PROVIDER_ENV_PREFIXES)
    }
    env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CONFIG_DIR"] = str(config_root)
    return env


def build_cases() -> list[ProbeCase]:
    policy = load_json(ROOT / "core/references/activation-policy.json")
    cases = [
        ProbeCase(
            case_id=f"explicit-{workflow}",
            category="explicit",
            expected=workflow,
            base_prompt=workflow,
        )
        for workflow in VISIBLE_WORKFLOWS
    ]
    cases.extend(
        ProbeCase(
            case_id=f"automatic-positive-{case['id']}",
            category="automatic-positive",
            expected=case["expected"],
            base_prompt=case["prompt"],
        )
        for case in policy["positive_cases"]
    )
    cases.extend(
        ProbeCase(
            case_id=f"automatic-negative-{case['id']}",
            category="automatic-negative",
            expected=case["expected"],
            base_prompt=case["prompt"],
        )
        for case in policy["negative_cases"]
    )
    cases.extend(
        [
            ProbeCase(
                case_id="precedence-resume-over-audit-run",
                category="precedence",
                expected="resume",
                base_prompt=(
                    "Resume the unfinished approved Design workflow from its saved state, "
                    "then audit and redesign the existing interface."
                ),
            ),
            ProbeCase(
                case_id="precedence-audit-over-run",
                category="precedence",
                expected="audit",
                base_prompt=(
                    "Audit and redesign this existing interface, but do not resume a prior "
                    "Design workflow."
                ),
            ),
        ]
    )
    if len(cases) != 20:
        raise ProbeError(f"Expected 20 R04 cases, found {len(cases)}")
    return cases


def host_prompt(host: str, case: ProbeCase) -> str:
    if case.category != "explicit":
        return case.base_prompt
    prefix = "$design:" if host == "codex" else "/design:"
    return f"{prefix}{case.expected}"


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"Command timed out after {timeout} seconds: {command[0]}") from exc


def parse_jsonl(text: str) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    ignored = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            ignored += 1
            continue
        if isinstance(value, dict):
            events.append(value)
    return events, ignored


def event_type(event: dict[str, Any]) -> str:
    if isinstance(event.get("type"), str):
        return event["type"]
    return "unknown"


def walk_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from walk_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_objects(nested)


def route_from_skill_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("design:"):
        return None
    route = value.removeprefix("design:")
    return route if route else None


def claude_selection(
    events: list[dict[str, Any]], package_root: Path | None = None
) -> tuple[list[str], list[dict[str, Any]]]:
    selected: list[str] = []
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    tool_uses: dict[str, tuple[str, int]] = {}
    successful_results: set[str] = set()
    for event_index, event in enumerate(events):
        if event_type(event) == "assistant":
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            for item in content if isinstance(content, list) else []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "tool_use" or item.get("name") != "Skill":
                    continue
                tool_id = item.get("id")
                skill = item.get("input", {}).get("skill") if isinstance(item.get("input"), dict) else None
                route = route_from_skill_name(skill)
                if isinstance(tool_id, str) and route:
                    tool_uses[tool_id] = (route, event_index)
        if event_type(event) == "user":
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            for item in content if isinstance(content, list) else []:
                if not isinstance(item, dict) or item.get("type") != "tool_result":
                    continue
                tool_id = item.get("tool_use_id")
                if isinstance(tool_id, str) and item.get("is_error") is not True:
                    successful_results.add(tool_id)

        if event.get("isSynthetic") is True and event_type(event) in {"user", "system"}:
            texts = [
                item.get("text", "")
                for item in walk_objects(event)
                if isinstance(item.get("text"), str)
            ]
            rendered = "\n".join(texts)
            for route in VISIBLE_WORKFLOWS:
                expected = package_root / "skills" / route if package_root else None
                path_match = expected is None or str(expected.resolve()) in rendered
                command_match = bool(
                    re.search(rf"(?:^|[\s>/])/?design:{re.escape(route)}(?:[\s<]|$)", rendered)
                )
                if path_match and command_match:
                    key = (route, "synthetic-skill-load")
                    if key not in seen:
                        seen.add(key)
                        selected.append(route)
                        observations.append(
                            {
                                "workflow": route,
                                "source": "synthetic-skill-load",
                                "event_index": event_index,
                            }
                        )

    for tool_id, (route, event_index) in tool_uses.items():
        if tool_id not in successful_results:
            continue
        key = (route, "correlated-skill-tool")
        if key not in seen:
            seen.add(key)
            selected.append(route)
            observations.append(
                {
                    "workflow": route,
                    "source": "correlated-skill-tool",
                    "event_index": event_index,
                    "tool_use_id_sha256": sha256_bytes(tool_id.encode("utf-8")),
                }
            )
    return selected, observations


def codex_selection(
    events: list[dict[str, Any]], package_root: Path | None = None
) -> tuple[list[str], list[dict[str, Any]]]:
    selected: list[str] = []
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    path_pattern = re.compile(
        r"(?P<path>/[^\s'\"]+(?:/|\\)skills(?:/|\\)(?P<route>[A-Za-z0-9_-]+)(?:/|\\)SKILL\.md)"
    )
    for event_index, event in enumerate(events):
        if event_type(event) != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_kind = item.get("type")
        route: str | None = None
        source: str | None = None
        proof: dict[str, Any] = {"event_index": event_index}
        if item_kind in {"skill", "skill_invocation"} and item.get("status", "completed") == "completed":
            for name_key in ("qualified_name", "skill_name", "name"):
                route = route_from_skill_name(item.get(name_key))
                if route:
                    source = "native-skill-event"
                    break
        if item_kind == "command_execution" and item.get("exit_code") == 0:
            command = item.get("command")
            output = item.get("aggregated_output")
            if not isinstance(output, str):
                output = item.get("output")
            if isinstance(command, str) and isinstance(output, str):
                for match in path_pattern.finditer(command):
                    candidate_path = Path(match.group("path")).resolve()
                    candidate_route = match.group("route")
                    expected_path = (
                        (package_root / "skills" / candidate_route / "SKILL.md").resolve()
                        if package_root
                        else candidate_path
                    )
                    try:
                        expected_content = expected_path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError):
                        expected_content = ""
                    if candidate_path == expected_path and expected_content and expected_content in output:
                        route = candidate_route
                        source = "successful-content-verified-skill-file-load"
                        key = (route, source)
                        if key not in seen:
                            seen.add(key)
                            selected.append(route)
                            observations.append(
                                {
                                    "workflow": route,
                                    "source": source,
                                    **proof,
                                    "command_sha256": sha256_bytes(command.encode("utf-8")),
                                    "loaded_content_sha256": sha256_bytes(
                                        expected_content.encode("utf-8")
                                    ),
                                }
                            )
        if route and source and source == "native-skill-event":
            key = (route, source)
            if key not in seen:
                seen.add(key)
                selected.append(route)
                observations.append({"workflow": route, "source": source, **proof})
    return selected, observations


def result_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event_type(event) in {"result", "turn.completed", "turn.failed", "turn.cancelled"}:
            return event
    return None


def successful_terminal(host: str, terminal: dict[str, Any] | None) -> bool:
    if terminal is None:
        return False
    if host == "codex":
        return event_type(terminal) == "turn.completed"
    return (
        event_type(terminal) == "result"
        and terminal.get("subtype") == "success"
        and terminal.get("is_error") is not True
    )


def native_models(host: str, events: list[dict[str, Any]]) -> list[str]:
    if host != "claude":
        return []
    return sorted(
        {
            message["model"]
            for event in events
            if event_type(event) == "assistant"
            for message in [event.get("message")]
            if isinstance(message, dict) and isinstance(message.get("model"), str)
        }
    )


def summarize_case(
    *,
    host: str,
    case: ProbeCase,
    prompt: str,
    completed: subprocess.CompletedProcess[str],
    events: list[dict[str, Any]],
    ignored_lines: int,
    requested_model: str,
    cli_version: str,
    package_root: Path | None = None,
) -> dict[str, Any]:
    selected, observations = (
        claude_selection(events, package_root)
        if host == "claude"
        else codex_selection(events, package_root)
    )
    unique_routes = sorted(set(selected))
    visible_routes = sorted(route for route in unique_routes if route in VISIBLE_WORKFLOWS)
    selection_pass = (
        not unique_routes if case.expected == "none" else visible_routes == [case.expected]
    )
    terminal = result_event(events)
    execution_pass = (
        completed.returncode == 0
        and ignored_lines == 0
        and bool(events)
        and successful_terminal(host, terminal)
    )
    models = native_models(host, events)
    requested_token = requested_model.lower()
    compatible_models = [
        model
        for model in models
        if requested_token == model.lower()
        or requested_token in model.lower()
        or model.lower() in requested_token
    ]
    model_binding_pass = bool(requested_model) and bool(models) and compatible_models == models
    status = (
        "pass"
        if selection_pass and execution_pass and model_binding_pass and cli_version
        else "partial"
        if selection_pass
        else "fail"
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "expected_workflow": case.expected,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "fresh_process": True,
        "exit_code": completed.returncode,
        "event_count": len(events),
        "ignored_output_lines": ignored_lines,
        "cli_version": cli_version,
        "requested_model": requested_model,
        "event_type_counts": dict(sorted(Counter(event_type(event) for event in events).items())),
        "observed_models": models,
        "model_binding_source": (
            "assistant.message.model" if host == "claude" else "no-accepted-codex-jsonl-field"
        ),
        "model_binding_status": "pass" if model_binding_pass else "fail",
        "observed_workflows": unique_routes,
        "observed_visible_workflows": visible_routes,
        "selection_observations": observations,
        "sanitized_native_proof_retained": bool(observations) or case.expected == "none",
        "selection_status": "pass" if selection_pass else "fail",
        "execution_status": "pass" if execution_pass else "fail",
        "status": status,
        "trace_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "terminal_type": event_type(terminal) if terminal else "missing",
        "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
    }


def claude_preflight(claude: str) -> dict[str, Any]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {
            "status": "blocked",
            "reason": (
                "ANTHROPIC_API_KEY is absent. Bare Claude qualification cannot use "
                "subscription, OAuth, keychain, user settings, or harness state."
            ),
        }
    with tempfile.TemporaryDirectory(prefix="design-r04-claude-preflight-") as raw:
        config_root = Path(raw) / "config"
        work_root = Path(raw) / "work"
        config_root.mkdir()
        work_root.mkdir()
        env = claude_api_key_env(config_root)
        completed = run_command(
            [claude, "--bare", "auth", "status", "--json"], cwd=work_root, env=env
        )
        try:
            status = json.loads(completed.stdout)
        except json.JSONDecodeError:
            status = {}
        auth_method = status.get("authMethod")
        api_provider = status.get("apiProvider")
        if (
            completed.returncode != 0
            or not status.get("loggedIn")
            or auth_method not in {"api_key", "apiKey"}
            or api_provider != "firstParty"
        ):
            return {
                "status": "blocked",
                "reason": (
                    "Bare Claude did not report first-party API-key authentication after "
                    "third-party provider variables were removed."
                ),
            }
    return {
        "status": "pass",
        "authentication": "bare first-party API key",
        "provider_environment_sanitized": True,
        "credential_copy_operation_by_runner": False,
    }


def run_claude_cases(
    claude: str,
    cases: list[ProbeCase],
    *,
    model: str,
    max_case_cost_usd: float,
    max_total_cost_usd: float,
) -> dict[str, Any]:
    preflight = claude_preflight(claude)
    if preflight["status"] != "pass":
        return {"status": "blocked", "preflight": preflight, "cases": []}
    package = ROOT / "dist/design-claude"
    package_digest = tree_sha256(package)
    cli_version = command_version(claude)
    planned_max_cost_usd = max_case_cost_usd * len(cases)
    if planned_max_cost_usd > max_total_cost_usd + 1e-9:
        raise ProbeError(
            "The Claude per-case ceilings exceed --claude-max-total-cost-usd "
            f"({planned_max_cost_usd:.2f} > {max_total_cost_usd:.2f})"
        )
    results: list[dict[str, Any]] = []
    for case in cases:
        prompt = host_prompt("claude", case)
        with tempfile.TemporaryDirectory(prefix=f"design-r04-claude-{case.case_id}-") as raw:
            temp_root = Path(raw)
            config_root = temp_root / "config"
            work_root = temp_root / "work"
            config_root.mkdir()
            work_root.mkdir()
            env = claude_api_key_env(config_root)
            command = [
                claude,
                "--bare",
                "--plugin-dir",
                str(package),
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--no-chrome",
                "--no-session-persistence",
                "--permission-mode",
                "dontAsk",
                "--tools",
                "Skill",
                "--allowedTools",
                "Skill",
                "--effort",
                "low",
                "--model",
                model,
                "--max-budget-usd",
                str(max_case_cost_usd),
                "--output-format",
                "stream-json",
                "--verbose",
                "-p",
                prompt,
            ]
            completed = run_command(command, cwd=work_root, env=env)
            events, ignored = parse_jsonl(completed.stdout)
            results.append(
                summarize_case(
                    host="claude",
                    case=case,
                    prompt=prompt,
                    completed=completed,
                    events=events,
                    ignored_lines=ignored,
                    requested_model=model,
                    cli_version=cli_version,
                    package_root=package,
                )
            )
    all_pass = len(results) == 20 and all(result["status"] == "pass" for result in results)
    return {
        "status": "pass" if all_pass else "partial",
        "preflight": preflight,
        "cli_version": cli_version,
        "requested_model": model,
        "package_tree_sha256": package_digest,
        "claude_max_case_cost_usd": max_case_cost_usd,
        "claude_planned_max_cost_usd": planned_max_cost_usd,
        "claude_authorized_total_ceiling_usd": max_total_cost_usd,
        "session_only_plugin_load": True,
        "active_user_installation": False,
        "cases": results,
    }


def codex_preflight(codex: str, codex_home: Path | None) -> dict[str, Any]:
    if codex_home is None:
        return {
            "status": "blocked",
            "reason": (
                "No separate preauthenticated CODEX_HOME was supplied. A temporary home is "
                "logged out, and the active home is forbidden for qualification."
            ),
        }
    expanded = codex_home.expanduser()
    if expanded.is_symlink():
        return {"status": "blocked", "reason": "The supplied CODEX_HOME is a symlink."}
    resolved = expanded.resolve()
    if resolved == ACTIVE_CODEX_HOME or ACTIVE_CODEX_HOME in resolved.parents:
        return {
            "status": "blocked",
            "reason": "The active ~/.codex home and its descendants are forbidden for R04 qualification.",
        }
    if not resolved.is_dir():
        return {"status": "blocked", "reason": f"CODEX_HOME does not exist: {resolved}"}
    unsafe_links = sorted(path.relative_to(resolved).as_posix() for path in resolved.rglob("*") if path.is_symlink())
    unexpected = sorted(
        path.name
        for path in resolved.iterdir()
        if path.name not in CODEX_QUALIFICATION_HOME_ALLOWLIST
    )
    if unexpected or unsafe_links:
        return {
            "status": "blocked",
            "reason": (
                "The separate CODEX_HOME contains non-auth qualification state: "
                + ", ".join(unexpected + unsafe_links)
            ),
        }
    env = os.environ.copy()
    env["CODEX_HOME"] = str(resolved)
    completed = run_command([codex, "login", "status"], cwd=ROOT, env=env)
    if completed.returncode != 0 or "Logged in" not in completed.stdout:
        return {
            "status": "blocked",
            "reason": "The separate CODEX_HOME is not authenticated.",
        }
    listing = run_command([codex, "plugin", "list", "--json"], cwd=ROOT, env=env)
    try:
        plugins = json.loads(listing.stdout)
    except json.JSONDecodeError:
        plugins = {}
    if listing.returncode != 0 or plugins.get("installed") or plugins.get("available"):
        return {
            "status": "blocked",
            "reason": "The separate CODEX_HOME is not an empty qualification profile.",
        }
    return {
        "status": "pass",
        "authentication": "preauthenticated separate CODEX_HOME",
        "credential_copy_operation_by_runner": False,
        "credential_provenance": "operator-prepared; external attestation required",
        "codex_home_is_active": False,
        "clean_profile_allowlist": sorted(CODEX_QUALIFICATION_HOME_ALLOWLIST),
        "user_config_ignored_at_execution": True,
    }


def run_codex_cases(
    codex: str,
    cases: list[ProbeCase],
    *,
    codex_home: Path | None,
    model: str,
) -> dict[str, Any]:
    preflight = codex_preflight(codex, codex_home)
    if preflight["status"] != "pass" or codex_home is None:
        return {"status": "blocked", "preflight": preflight, "cases": []}
    package = ROOT / "dist/design-openai"
    package_digest = tree_sha256(package)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home.expanduser().resolve())
    marketplace = ROOT / "dist/installable/openai"
    installable_package = marketplace / "plugins/design"
    installable_package_digest = tree_sha256(installable_package)
    if installable_package_digest != package_digest:
        raise ProbeError("Codex distribution and installable marketplace package differ")
    plugin_id = "design@design-local-openai"
    cli_version = command_version(codex)
    results: list[dict[str, Any]] = []
    installed_package_digest = "unavailable"
    install_attempted = False
    marketplace_add_attempted = False
    cleanup: dict[str, Any] = {}
    try:
        marketplace_add_attempted = True
        added = run_command(
            [codex, "plugin", "marketplace", "add", str(marketplace), "--json"],
            cwd=ROOT,
            env=env,
        )
        if added.returncode != 0:
            raise ProbeError("Codex could not add the isolated Design marketplace")
        install_attempted = True
        install = run_command(
            [codex, "plugin", "add", plugin_id, "--json"], cwd=ROOT, env=env
        )
        if install.returncode != 0:
            raise ProbeError("Codex could not install Design into the separate qualification home")
        try:
            install_record = json.loads(install.stdout)
            installed_path = Path(install_record["installedPath"]).resolve()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ProbeError("Codex install did not return a bound installed cache path") from exc
        qualification_home = codex_home.expanduser().resolve()
        if not installed_path.is_relative_to(qualification_home):
            raise ProbeError("Codex installed outside the separate qualification home")
        installed_package_digest = tree_sha256(installed_path)
        if installed_package_digest != installable_package_digest:
            raise ProbeError("Codex installed cache differs from the installable package")
        installed_listing = run_command([codex, "plugin", "list", "--json"], cwd=ROOT, env=env)
        try:
            installed_plugins = json.loads(installed_listing.stdout).get("installed", [])
        except (json.JSONDecodeError, AttributeError):
            installed_plugins = []
        if (
            installed_listing.returncode != 0
            or len(installed_plugins) != 1
            or installed_plugins[0].get("pluginId") != plugin_id
            or installed_plugins[0].get("enabled") is not True
        ):
            raise ProbeError("Codex qualification home did not expose only enabled Design")
        for case in cases:
            prompt = host_prompt("codex", case)
            with tempfile.TemporaryDirectory(prefix=f"design-r04-codex-{case.case_id}-") as raw:
                work_root = Path(raw)
                command = [
                    codex,
                    "exec",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--json",
                    "-c",
                    'approval_policy="never"',
                    "-c",
                    'plugins={"design@design-local-openai"={enabled=true}}',
                    "-m",
                    model,
                    "-C",
                    str(work_root),
                    prompt,
                ]
                completed = run_command(command, cwd=work_root, env=env)
                events, ignored = parse_jsonl(completed.stdout)
                results.append(
                    summarize_case(
                        host="codex",
                        case=case,
                        prompt=prompt,
                        completed=completed,
                        events=events,
                        ignored_lines=ignored,
                        requested_model=model,
                        cli_version=cli_version,
                        package_root=installed_path,
                    )
                )
    finally:
        remove_plugin = (
            run_command([codex, "plugin", "remove", plugin_id, "--json"], cwd=ROOT, env=env)
            if install_attempted
            else None
        )
        remove_marketplace = (
            run_command(
                [codex, "plugin", "marketplace", "remove", "design-local-openai", "--json"],
                cwd=ROOT,
                env=env,
            )
            if marketplace_add_attempted
            else None
        )
        final_plugins = run_command([codex, "plugin", "list", "--json"], cwd=ROOT, env=env)
        final_marketplaces = run_command(
            [codex, "plugin", "marketplace", "list", "--json"], cwd=ROOT, env=env
        )
        try:
            plugin_state = json.loads(final_plugins.stdout)
            marketplace_state = json.loads(final_marketplaces.stdout)
        except json.JSONDecodeError as exc:
            raise ProbeError("Codex cleanup post-state was not valid JSON") from exc
        design_marketplaces = [
            item
            for item in marketplace_state.get("marketplaces", [])
            if item.get("name") == "design-local-openai"
        ]
        cache_root = codex_home.expanduser().resolve() / "plugins/cache/design-local-openai"
        cached_files = [path for path in cache_root.rglob("*") if path.is_file()]
        cleanup = {
            "plugin_remove_exit_code": remove_plugin.returncode if remove_plugin else "not-attempted",
            "marketplace_remove_exit_code": (
                remove_marketplace.returncode if remove_marketplace else "not-attempted"
            ),
            "post_plugin_state_empty": not plugin_state.get("installed")
            and not plugin_state.get("available"),
            "post_design_marketplace_absent": not design_marketplaces,
            "post_design_cache_files_absent": not cached_files,
        }
        cleanup_pass = (
            (remove_plugin is None or remove_plugin.returncode == 0)
            and (remove_marketplace is None or remove_marketplace.returncode == 0)
            and final_plugins.returncode == 0
            and final_marketplaces.returncode == 0
            and all(
                cleanup[key]
                for key in (
                    "post_plugin_state_empty",
                    "post_design_marketplace_absent",
                    "post_design_cache_files_absent",
                )
            )
        )
        cleanup["status"] = "pass" if cleanup_pass else "fail"
        if not cleanup_pass:
            raise ProbeError("Codex cleanup did not return the qualification home to empty state")
    all_pass = len(results) == 20 and all(result["status"] == "pass" for result in results)
    return {
        "status": "pass" if all_pass else "partial",
        "preflight": preflight,
        "cli_version": cli_version,
        "requested_model": model,
        "distribution_tree_sha256": package_digest,
        "installable_source_tree_sha256": installable_package_digest,
        "installed_cache_tree_sha256": installed_package_digest,
        "installed_cache_matches_source": True,
        "cleanup": cleanup,
        "dedicated_plugin_store": True,
        "active_user_installation": False,
        "cases": results,
    }


def write_report(report: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        destination = Path(output)
        if not destination.is_absolute():
            destination = ROOT / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("all", "codex", "claude"), default="all")
    parser.add_argument("--case", action="append", dest="case_ids", help="Run one exact case ID")
    parser.add_argument("--execute", action="store_true", help="Run model inference after preflight")
    parser.add_argument("--codex-home", type=Path, help="Separate preauthenticated qualification home")
    parser.add_argument("--codex-model", default="gpt-5.4-mini")
    parser.add_argument("--claude-model", default="haiku")
    parser.add_argument("--claude-max-case-cost-usd", type=float, default=0.20)
    parser.add_argument("--claude-max-total-cost-usd", type=float, default=4.00)
    parser.add_argument(
        "--confirm-external-usage",
        action="store_true",
        help="Confirm authority for 20 Codex and 20 billed Claude model calls",
    )
    parser.add_argument("--output", help="Optional JSON receipt path")
    args = parser.parse_args()

    all_cases = build_cases()
    selected_ids = set(args.case_ids or [])
    unknown = selected_ids.difference(case.case_id for case in all_cases)
    if unknown:
        parser.error(f"Unknown case IDs: {', '.join(sorted(unknown))}")
    cases = [case for case in all_cases if not selected_ids or case.case_id in selected_ids]
    if args.claude_max_case_cost_usd <= 0:
        parser.error("--claude-max-case-cost-usd must be positive")
    if args.claude_max_total_cost_usd <= 0:
        parser.error("--claude-max-total-cost-usd must be positive")
    if args.execute and not args.confirm_external_usage:
        parser.error("--execute requires --confirm-external-usage")

    candidate = candidate_state()
    if args.execute and not candidate["clean"]:
        raise ProbeError("--execute requires a clean, frozen Git candidate")

    codex = shutil.which("codex")
    claude = shutil.which("claude")
    if args.host in {"all", "codex"} and not codex:
        raise ProbeError("codex CLI is required")
    if args.host in {"all", "claude"} and not claude:
        raise ProbeError("claude CLI is required")

    before = active_registry_snapshot()
    host_results: dict[str, Any] = {}
    if args.host in {"all", "codex"}:
        if args.execute:
            host_results["codex"] = run_codex_cases(
                codex or "codex", cases, codex_home=args.codex_home, model=args.codex_model
            )
        else:
            preflight = codex_preflight(codex or "codex", args.codex_home)
            host_results["codex"] = {
                "status": preflight["status"],
                "preflight": preflight,
                "cases": [],
            }
    if args.host in {"all", "claude"}:
        if args.execute:
            host_results["claude"] = run_claude_cases(
                claude or "claude",
                cases,
                model=args.claude_model,
                max_case_cost_usd=args.claude_max_case_cost_usd,
                max_total_cost_usd=args.claude_max_total_cost_usd,
            )
        else:
            preflight = claude_preflight(claude or "claude")
            host_results["claude"] = {
                "status": preflight["status"],
                "preflight": preflight,
                "cases": [],
            }
    after = active_registry_snapshot()
    registries_unchanged = before == after
    if not registries_unchanged:
        raise ProbeError("An active user registry changed during R04 qualification")

    full_matrix = not selected_ids
    all_pass = (
        args.execute
        and full_matrix
        and set(host_results) == {"codex", "claude"}
        and all(result["status"] == "pass" for result in host_results.values())
    )
    status = "pass" if all_pass else "partial" if args.execute else "blocked"
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "requirement": "R04",
        "scope": "harness-independent runtime selection qualification",
        "candidate": candidate,
        "activation_policy_sha256": sha256_file(ROOT / "core/references/activation-policy.json"),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "regression_test_sha256": sha256_file(ROOT / "tests/test_wave10_r04_activation.py"),
        "case_count": len(cases),
        "full_matrix": full_matrix,
        "external_model_inference_called": args.execute
        and any(result.get("cases") for result in host_results.values()),
        "credential_handling": {
            "copy_operation_present_in_runner": False,
            "codex_auth_provenance": "operator-prepared; external attestation required",
            "claude_auth_source": "sanitized ANTHROPIC_API_KEY environment entry",
        },
        "active_user_registries_unchanged": registries_unchanged,
        "active_user_installation": False,
        "qualification_only_restriction": (
            "Isolation protects the evidence and is absent from both distributed runtime "
            "directories. Normal multi-plugin compatibility is not tested by this runner."
        ),
        "hosts": host_results,
        "requirements": {
            "R04": "pass" if all_pass else "partial",
            "R22": "partial",
            "final_plugin_acceptance": "prohibited",
        },
    }
    write_report(report, args.output)
    return 0 if all_pass else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        print(f"R04 PROBE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
