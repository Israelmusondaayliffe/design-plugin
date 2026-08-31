#!/usr/bin/env python3
"""Verify installable Design marketplace fixtures and release archives."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MCP_PATTERN = re.compile(r"\bmcp\b|model[_ -]?context[_ -]?protocol", re.IGNORECASE)
MCP_RUNTIME_PATTERN = re.compile(
    r"(?:\bfrom\s+mcp\b|\bimport\s+mcp\b|mcp[_-]?(?:client|server)|mcpServers|model[_ -]?context[_ -]?protocol)",
    re.IGNORECASE,
)
RUNTIME_SUFFIXES = {".py", ".sh", ".js", ".ts", ".cjs", ".mjs"}


class VerificationError(RuntimeError):
    """Raised when an installable artifact violates the host package contract."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"Missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise VerificationError(f"Missing directory: {root.relative_to(ROOT)}")
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise VerificationError(f"Symlink is not permitted: {path.relative_to(ROOT)}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256(path)
    return result


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise VerificationError(f"Skill has no frontmatter: {path.relative_to(ROOT)}")
    try:
        block = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise VerificationError(f"Skill frontmatter is not closed: {path.relative_to(ROOT)}") from exc
    values: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def nested_mcp_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if MCP_PATTERN.search(str(key)):
                found.append(name)
            found.extend(nested_mcp_keys(child, name))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(nested_mcp_keys(child, f"{prefix}[{index}]"))
    return found


def verify_manifest(host: str, marketplace: Path, config: dict[str, Any]) -> None:
    host_config = config["hosts"][host]
    manifest = load_json(marketplace / host_config["marketplace_manifest"])
    if manifest.get("name") != host_config["marketplace_name"]:
        raise VerificationError(f"{host} marketplace has the wrong name")
    plugins = manifest.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1 or plugins[0].get("name") != config["plugin"]:
        raise VerificationError(f"{host} marketplace must contain exactly the Design plugin")
    if host == "openai":
        expected = {"source": "local", "path": "./plugins/design"}
        if plugins[0].get("source") != expected:
            raise VerificationError("OpenAI marketplace source must be the local generated package")
        if plugins[0].get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
            raise VerificationError("OpenAI marketplace policy is incorrect")
    elif plugins[0].get("source") != "./plugins/design" or plugins[0].get("version") != config["version"]:
        raise VerificationError("Claude marketplace source or version is incorrect")
    if host == "claude" and not manifest.get("description"):
        raise VerificationError("Claude marketplace must include a description")


def verify_skills(plugin: Path, config: dict[str, Any]) -> dict[str, list[str]]:
    visible: list[str] = []
    internal: list[str] = []
    for skill_file in sorted((plugin / "skills").glob("*/SKILL.md")):
        metadata = parse_frontmatter(skill_file)
        name = metadata.get("name", skill_file.parent.name)
        if metadata.get("user-invocable", "true").lower() == "false":
            internal.append(name)
        else:
            visible.append(name)
    if visible != sorted(config["visible_workflows"]):
        raise VerificationError(f"Visible skill set is incorrect: {visible}")
    if internal != sorted(config["internal_skills"]):
        raise VerificationError(f"Internal skill set is incorrect: {internal}")
    return {"visible": visible, "internal": internal}


def verify_no_mcp(plugin: Path) -> dict[str, list[str]]:
    paths: list[str] = []
    runtime_references: list[str] = []
    manifest_keys: list[str] = []
    for path in sorted(plugin.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(plugin).as_posix()
        if MCP_PATTERN.search(relative):
            paths.append(relative)
        if path.is_file() and path.suffix in RUNTIME_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            if MCP_RUNTIME_PATTERN.search(text):
                runtime_references.append(relative)
        if path.is_file() and path.suffix == ".json" and (
            relative.endswith("plugin.json") or relative.endswith("marketplace.json")
        ):
            manifest_keys.extend(f"{relative}:{key}" for key in nested_mcp_keys(load_json(path)))
    if paths or runtime_references or manifest_keys:
        raise VerificationError(
            f"MCP dependency detected: paths={paths}, runtime={runtime_references}, manifest_keys={manifest_keys}"
        )
    return {"paths": paths, "runtime_references": runtime_references, "manifest_keys": manifest_keys}


def verify_lifecycle_copy(source: Path) -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="design-wave10-package-") as raw:
        root = Path(raw)
        installed = root / "installed" / "design"
        shutil.copytree(source, installed)
        install_ok = file_hashes(installed) == file_hashes(source)
        marker = installed / "BUILD_RECEIPT.json"
        marker_data = load_json(marker)
        marker_data["version"] = "0.0.0-old-fixture"
        marker.write_text(json.dumps(marker_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.rmtree(installed)
        shutil.copytree(source, installed)
        update_ok = file_hashes(installed) == file_hashes(source)
        shutil.rmtree(installed)
        remove_ok = not installed.exists()
    if not all((install_ok, update_ok, remove_ok)):
        raise VerificationError("Filesystem lifecycle simulation failed")
    return {"install": install_ok, "update": update_ok, "remove": remove_ok}


def verify_archives(config: dict[str, Any]) -> list[dict[str, Any]]:
    receipt_path = ROOT / config["release_root"] / "RELEASE_RECEIPT.json"
    receipt = load_json(receipt_path)
    if receipt.get("plugin") != config["plugin"] or receipt.get("version") != config["version"]:
        raise VerificationError("Release receipt plugin or version is stale")
    results = []
    for item in receipt.get("archives", []):
        archive_path = ROOT / item["path"]
        if sha256(archive_path) != item.get("sha256") or archive_path.stat().st_size != item.get("size_bytes"):
            raise VerificationError(f"Release archive receipt mismatch: {item.get('path')}")
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) != item.get("file_count"):
                raise VerificationError(f"Release archive file count mismatch: {item.get('path')}")
            for member in members:
                parts = Path(member.filename).parts
                if member.filename.startswith("/") or ".." in parts:
                    raise VerificationError(f"Unsafe release archive member: {member.filename}")
        results.append({"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]})
    if len(results) != 2:
        raise VerificationError("Release receipt must contain exactly two archives")
    return results


def main() -> int:
    try:
        config = load_json(ROOT / "host-packaging.json")
        spec = load_json(ROOT / "bundle-spec.json")
        if config.get("version") != spec.get("version"):
            raise VerificationError("Host packaging and bundle versions differ")
        activation = load_json(ROOT / config["activation_policy"])
        positive_ids = sorted(case.get("id") for case in activation.get("positive_cases", []))
        negative_ids = sorted(case.get("id") for case in activation.get("negative_cases", []))
        if positive_ids != sorted(
            ["audit", "chatgpt-site", "claude-artifact", "dashboard", "design-system", "mobile", "redesign", "resume", "website"]
        ):
            raise VerificationError("Activation policy positive cases are incomplete")
        if negative_ids != sorted(
            ["backend", "database", "deployment-only", "document-summary", "general-programming", "unrelated-image"]
        ):
            raise VerificationError("Activation policy negative cases are incomplete")

        hosts: dict[str, Any] = {}
        for host in ("openai", "claude"):
            host_config = config["hosts"][host]
            marketplace = ROOT / host_config["marketplace_root"]
            plugin = marketplace / "plugins" / config["plugin"]
            source = ROOT / host_config["distribution"]
            verify_manifest(host, marketplace, config)
            if file_hashes(plugin) != file_hashes(source):
                raise VerificationError(f"{host} marketplace plugin differs from its distribution")
            skills = verify_skills(plugin, config)
            mcp = verify_no_mcp(plugin)
            lifecycle = verify_lifecycle_copy(plugin)
            files = [path for path in plugin.rglob("*") if path.is_file()]
            size_bytes = sum(path.stat().st_size for path in files)
            if size_bytes > spec["max_uncompressed_bytes"]:
                raise VerificationError(f"{host} package exceeds the one MiB ceiling")
            largest = sorted(
                ((path.stat().st_size, path.relative_to(plugin).as_posix()) for path in files),
                reverse=True,
            )[:5]
            hosts[host] = {
                "size_bytes": size_bytes,
                "file_count": len(files),
                "largest_files": [{"path": path, "size_bytes": size} for size, path in largest],
                "skills": skills,
                "mcp_scan": mcp,
                "filesystem_lifecycle": lifecycle,
            }
        if (ROOT / config["hosts"]["claude"]["marketplace_root"] / "plugins/design/skills/run/agents/openai.yaml").exists():
            raise VerificationError("Claude installable package contains OpenAI-only skill metadata")
        if not (ROOT / config["hosts"]["openai"]["marketplace_root"] / "plugins/design/skills/run/agents/openai.yaml").is_file():
            raise VerificationError("OpenAI installable package is missing its host-only skill metadata")

        report = {
            "status": "pass",
            "plugin": config["plugin"],
            "version": config["version"],
            "activation_cases": {
                "positive": len(activation["positive_cases"]),
                "negative": len(activation["negative_cases"]),
            },
            "archives": verify_archives(config),
            "hosts": hosts,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except VerificationError as exc:
        print(f"INSTALLABLE VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
