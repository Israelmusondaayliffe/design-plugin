#!/usr/bin/env python3
"""Exercise real Codex and Claude plugin lifecycles in temporary config roots.

This script never writes to the active Codex or Claude configuration. Each host
receives a fresh temporary config root, a private marketplace copy, and no copied
credentials. The temporary roots are deleted after removal checks finish.
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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class HostCheckError(RuntimeError):
    """Raised when an isolated host lifecycle fails."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HostCheckError(f"Cannot load JSON at {path}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.is_dir():
        raise HostCheckError(f"Expected directory does not exist: {root}")
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise HostCheckError(f"Symlink found in isolated package: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256(path)
    return result


def active_state_snapshot() -> dict[str, str]:
    """Hash active registries without recording their contents or paths."""

    home = Path.home()
    candidates = [
        home / ".codex/config.toml",
        home / ".agents/plugins/marketplace.json",
        home / ".claude/settings.json",
        home / ".claude.json",
        home / ".claude/plugins/installed_plugins.json",
        home / ".claude/plugins/known_marketplaces.json",
    ]
    return {
        f"registry_{index}": sha256(path) if path.is_file() else "missing"
        for index, path in enumerate(candidates)
    }


def run(command: list[str], env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        rendered = " ".join(command)
        detail = (completed.stderr or completed.stdout).strip()
        raise HostCheckError(f"Command failed ({rendered}): {detail}")
    return completed.stdout


def parse_json_output(output: str, label: str) -> Any:
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise HostCheckError(f"{label} did not return JSON") from exc


def replace_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def rewrite_version(marketplace: Path, host: str, version: str) -> None:
    manifest_relative = ".codex-plugin/plugin.json" if host == "openai" else ".claude-plugin/plugin.json"
    plugin = marketplace / "plugins/design"
    manifest_path = plugin / manifest_relative
    manifest = load_json(manifest_path)
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt_path = plugin / "BUILD_RECEIPT.json"
    receipt = load_json(receipt_path)
    receipt["version"] = version
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if host == "claude":
        marketplace_path = marketplace / ".claude-plugin/marketplace.json"
        marketplace_data = load_json(marketplace_path)
        marketplace_data["plugins"][0]["version"] = version
        marketplace_path.write_text(
            json.dumps(marketplace_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def installed_skill_sets(plugin: Path) -> dict[str, list[str]]:
    visible: list[str] = []
    internal: list[str] = []
    for skill_file in sorted((plugin / "skills").glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        name_match = re.search(r"(?m)^name:\s*([^\n]+)$", text)
        name = name_match.group(1).strip() if name_match else skill_file.parent.name
        if re.search(r"(?m)^user-invocable:\s*false\s*$", text):
            internal.append(name)
        else:
            visible.append(name)
    return {"visible": sorted(visible), "internal": sorted(internal)}


def prompt_text(prompt_input: Any) -> str:
    parts: list[str] = []
    if not isinstance(prompt_input, list):
        return ""
    for message in prompt_input:
        for item in message.get("content", []) if isinstance(message, dict) else []:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return "\n".join(parts)


def run_codex(
    codex: str,
    config: dict[str, Any],
    source: Path,
    temp_root: Path,
) -> dict[str, Any]:
    config_root = temp_root / "codex-config"
    marketplace = temp_root / "codex-marketplace"
    config_root.mkdir(parents=True)
    shutil.copytree(source, marketplace)
    rewrite_version(marketplace, "openai", config["previous_test_version"])
    env = os.environ.copy()
    env["CODEX_HOME"] = str(config_root)
    plugin_id = f"{config['plugin']}@{config['hosts']['openai']['marketplace_name']}"

    run([codex, "plugin", "marketplace", "add", str(marketplace), "--json"], env)
    old_install = parse_json_output(run([codex, "plugin", "add", plugin_id, "--json"], env), "Codex install")
    if old_install.get("version") != config["previous_test_version"]:
        raise HostCheckError("Codex did not install the old qualification version")
    old_list = parse_json_output(run([codex, "plugin", "list", "--json"], env), "Codex list")
    if len(old_list.get("installed", [])) != 1:
        raise HostCheckError("Codex old-version discovery failed")

    replace_tree(ROOT / config["hosts"]["openai"]["distribution"], marketplace / "plugins/design")
    current_install = parse_json_output(run([codex, "plugin", "add", plugin_id, "--json"], env), "Codex update")
    if current_install.get("version") != config["version"]:
        raise HostCheckError("Codex did not install the current qualification version")
    current_list = parse_json_output(run([codex, "plugin", "list", "--json"], env), "Codex current list")
    installed = current_list.get("installed", [])
    if len(installed) != 1 or installed[0].get("version") != config["version"] or not installed[0].get("enabled"):
        raise HostCheckError("Codex current-version discovery failed")

    cache_path = Path(current_install["installedPath"])
    if file_hashes(cache_path) != file_hashes(marketplace / "plugins/design"):
        raise HostCheckError("Codex installed cache differs from the current marketplace package")
    skills = installed_skill_sets(cache_path)
    if skills["visible"] != sorted(config["visible_workflows"]) or skills["internal"] != sorted(config["internal_skills"]):
        raise HostCheckError("Codex installed skill visibility metadata is incorrect")

    positive_prompt = "Design and build a website for this product."
    negative_prompt = "Fix this backend API timeout."
    positive = parse_json_output(run([codex, "debug", "prompt-input", positive_prompt], env), "Codex positive prompt input")
    negative = parse_json_output(run([codex, "debug", "prompt-input", negative_prompt], env), "Codex negative prompt input")
    positive_text = prompt_text(positive)
    negative_text = prompt_text(negative)
    names = config["visible_workflows"] + config["internal_skills"]
    if not all(f"design:{name}" in positive_text for name in names):
        raise HostCheckError("Codex fresh prompt input is missing model-routable Design skills")
    if positive_prompt not in positive_text or negative_prompt not in negative_text:
        raise HostCheckError("Codex fresh prompt input did not preserve activation probes")
    if "Use automatically for unmistakable end-to-end design work" not in positive_text:
        raise HostCheckError("Codex fresh prompt input is missing the automatic activation contract")

    run([codex, "plugin", "remove", plugin_id, "--json"], env)
    run([codex, "plugin", "marketplace", "remove", config["hosts"]["openai"]["marketplace_name"], "--json"], env)
    removed = parse_json_output(run([codex, "plugin", "list", "--json"], env), "Codex removed list")
    if removed.get("installed") or removed.get("available"):
        raise HostCheckError("Codex removal left a plugin or marketplace listing")
    cache_files = list((config_root / "plugins/cache" / config["hosts"]["openai"]["marketplace_name"]).rglob("*"))
    if any(path.is_file() for path in cache_files):
        raise HostCheckError("Codex removal left cached plugin files")

    return {
        "status": "pass",
        "cli_version": run([codex, "--version"], env).strip(),
        "installed_versions": [config["previous_test_version"], config["version"]],
        "fresh_process_discovery": True,
        "cache_source_parity": True,
        "visible_workflows": skills["visible"],
        "model_routable_internal_skills": len(skills["internal"]),
        "automatic_activation_contract_loaded": True,
        "positive_and_negative_prompts_in_fresh_inputs": True,
        "removal_cleared_registration_and_cache_files": True,
    }


def run_claude(
    claude: str,
    config: dict[str, Any],
    source: Path,
    temp_root: Path,
) -> dict[str, Any]:
    config_root = temp_root / "claude-config"
    marketplace = temp_root / "claude-marketplace"
    config_root.mkdir(parents=True)
    shutil.copytree(source, marketplace)
    rewrite_version(marketplace, "claude", config["previous_test_version"])
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config_root)
    plugin_id = f"{config['plugin']}@{config['hosts']['claude']['marketplace_name']}"

    run([claude, "plugin", "marketplace", "add", str(marketplace), "--scope", "user"], env)
    run([claude, "plugin", "install", plugin_id, "--scope", "user"], env)
    old_list = parse_json_output(run([claude, "plugin", "list", "--json"], env), "Claude install list")
    if len(old_list) != 1 or old_list[0].get("version") != config["previous_test_version"]:
        raise HostCheckError("Claude did not install the old qualification version")

    replace_tree(ROOT / config["hosts"]["claude"]["distribution"], marketplace / "plugins/design")
    marketplace_manifest = load_json(ROOT / config["hosts"]["claude"]["marketplace_root"] / ".claude-plugin/marketplace.json")
    (marketplace / ".claude-plugin/marketplace.json").write_text(
        json.dumps(marketplace_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run([claude, "plugin", "marketplace", "update", config["hosts"]["claude"]["marketplace_name"]], env)
    run([claude, "plugin", "update", plugin_id, "--scope", "user"], env)
    current_list = parse_json_output(run([claude, "plugin", "list", "--json"], env), "Claude current list")
    if len(current_list) != 1 or current_list[0].get("version") != config["version"] or not current_list[0].get("enabled"):
        raise HostCheckError("Claude current-version discovery failed")
    details = run([claude, "plugin", "details", plugin_id], env)
    expected_names = sorted(config["visible_workflows"] + config["internal_skills"])
    if config["version"] not in details or "MCP servers (0)" not in details:
        raise HostCheckError("Claude fresh details output lacks the current version or reported MCP server count")
    if not all(re.search(rf"\b{re.escape(name)}\b", details) for name in expected_names):
        raise HostCheckError("Claude component discovery is missing Design skills")

    cache_path = Path(current_list[0]["installPath"])
    if file_hashes(cache_path) != file_hashes(marketplace / "plugins/design"):
        raise HostCheckError("Claude installed cache differs from the current marketplace package")
    skills = installed_skill_sets(cache_path)
    if skills["visible"] != sorted(config["visible_workflows"]) or skills["internal"] != sorted(config["internal_skills"]):
        raise HostCheckError("Claude installed skill visibility metadata is incorrect")

    run([claude, "plugin", "uninstall", plugin_id, "--scope", "user", "--yes"], env)
    run(
        [
            claude,
            "plugin",
            "marketplace",
            "remove",
            config["hosts"]["claude"]["marketplace_name"],
            "--scope",
            "user",
        ],
        env,
    )
    removed = parse_json_output(run([claude, "plugin", "list", "--json"], env), "Claude removed list")
    if removed:
        raise HostCheckError("Claude removal left an installed plugin listing")
    known = load_json(config_root / "plugins/known_marketplaces.json")
    if config["hosts"]["claude"]["marketplace_name"] in known:
        raise HostCheckError("Claude removal left a marketplace registration")

    return {
        "status": "pass",
        "cli_version": run([claude, "--version"], env).strip(),
        "installed_versions": [config["previous_test_version"], config["version"]],
        "fresh_process_discovery": True,
        "cache_source_parity": True,
        "component_inventory_count": len(expected_names),
        "visible_workflows": skills["visible"],
        "installed_internal_skills": len(skills["internal"]),
        "mcp_servers": 0,
        "removal_cleared_registration": True,
        "host_cache_disposal": "temporary config root deleted after the check",
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
    parser.add_argument("--output", help="Optional JSON evidence path, relative to the repository root")
    args = parser.parse_args()
    try:
        config = load_json(ROOT / "host-packaging.json")
        codex = shutil.which("codex")
        claude = shutil.which("claude")
        if not codex or not claude:
            raise HostCheckError("Both codex and claude CLIs are required for local host qualification")
        before = active_state_snapshot()
        temp_path = ""
        with tempfile.TemporaryDirectory(prefix="design-wave10-hosts-") as raw:
            temp_path = raw
            temp_root = Path(raw)
            codex_result = run_codex(
                codex,
                config,
                ROOT / config["hosts"]["openai"]["marketplace_root"],
                temp_root,
            )
            claude_result = run_claude(
                claude,
                config,
                ROOT / config["hosts"]["claude"]["marketplace_root"],
                temp_root,
            )
        if Path(temp_path).exists():
            raise HostCheckError("Temporary host root was not deleted")
        after = active_state_snapshot()
        if before != after:
            raise HostCheckError("An active user plugin registry changed during isolated qualification")
        activation = load_json(ROOT / config["activation_policy"])
        report = {
            "schema_version": "1.0",
            "status": "pass",
            "plugin": config["plugin"],
            "version": config["version"],
            "scope": "isolated temporary host configurations only",
            "credentials_copied": False,
            "active_user_registries_unchanged": True,
            "temporary_host_roots_deleted": True,
            "activation_policy": {
                "positive_cases": len(activation["positive_cases"]),
                "negative_cases": len(activation["negative_cases"]),
                "routing_precedence": activation["precedence"],
                "codex_proof": "Fresh Codex prompt-input processes loaded the routing descriptions and positive and negative probe prompts.",
                "claude_proof": "A fresh Claude process reported the installed component inventory. Claude prompt selection was not exercised.",
                "external_model_inference_called": False,
            },
            "hosts": {"openai": codex_result, "claude": claude_result},
        }
        write_report(report, args.output)
        return 0
    except HostCheckError as exc:
        print(f"ISOLATED HOST CHECK FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
