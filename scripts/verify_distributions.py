#!/usr/bin/env python3
"""Verify Design plugin distributions and shared-core parity.

Standard-library only. The script does not modify source files, install software,
or access the network.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATED_CACHE_PARTS = {"__pycache__"}
GENERATED_CACHE_SUFFIXES = {".pyc", ".pyo"}


class VerificationError(RuntimeError):
    """Raised when a distribution violates the package contract."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"Missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def path_is_forbidden(relative: str, forbidden: list[str]) -> bool:
    normalized = relative.replace("\\", "/").strip("/")
    parts = normalized.split("/") if normalized else []
    for rule in forbidden:
        candidate = rule.replace("\\", "/").strip("/")
        if not candidate:
            continue
        if "/" in candidate:
            if normalized == candidate or normalized.startswith(candidate + "/"):
                return True
            if f"/{candidate}/" in f"/{normalized}/":
                return True
        elif candidate in parts:
            return True
    return False


def file_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def collect_actual_shared_manifest(
    distribution: Path,
    shared_roots: list[str],
    common_files: list[str],
    exclusions: list[str],
) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative in common_files:
        path = distribution / relative
        if not path.is_file():
            raise VerificationError(f"Missing common file: {relative}")
        manifest[relative] = sha256(path)
    for root_name in shared_roots:
        root = distribution / root_name
        if not root.is_dir():
            raise VerificationError(f"Missing shared directory: {root_name}")
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(distribution).as_posix()
            if path.is_file() and relative not in exclusions:
                manifest[relative] = sha256(path)
    return dict(sorted(manifest.items()))


def verify_host(host: str, spec: dict[str, Any]) -> dict[str, Any]:
    host_spec = spec["hosts"][host]
    distribution = ROOT / host_spec["distribution"]
    if not distribution.is_dir():
        raise VerificationError(
            f"Distribution does not exist: {distribution.relative_to(ROOT)}. Run build_distributions.py first."
        )

    required = [
        host_spec["required_manifest"],
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "SHARED_MANIFEST.json",
        "BUILD_RECEIPT.json",
    ]
    required.extend(spec["shared_directories"])
    required.extend(spec["required_shared_files"])
    for relative in required:
        path = distribution / relative
        if not path.exists():
            raise VerificationError(f"{host} distribution is missing {relative}")

    manifest = load_json(distribution / host_spec["required_manifest"])
    if manifest.get("name") != spec["plugin"]:
        raise VerificationError(f"{host} manifest has the wrong plugin name")
    if manifest.get("version") != spec["version"]:
        raise VerificationError(f"{host} manifest version does not match bundle spec")
    if manifest.get("skills") != "./skills/":
        raise VerificationError(f"{host} manifest must load skills from ./skills/")

    receipt = load_json(distribution / "BUILD_RECEIPT.json")
    expected_receipt = {
        "plugin": spec["plugin"],
        "host": host,
        "version": spec["version"],
        "shared_manifest": "SHARED_MANIFEST.json",
    }
    if receipt != expected_receipt:
        raise VerificationError(f"{host} BUILD_RECEIPT.json is not deterministic or is stale")

    declared_hashes = load_json(distribution / "SHARED_MANIFEST.json")
    if not isinstance(declared_hashes, dict) or not declared_hashes:
        raise VerificationError(f"{host} shared manifest must be a non-empty object")
    actual_hashes = collect_actual_shared_manifest(
        distribution,
        spec["shared_directories"],
        spec["common_files"],
        spec.get("host_specific_shared_path_exclusions", []),
    )
    if declared_hashes != actual_hashes:
        missing = sorted(set(actual_hashes).difference(declared_hashes))
        extra = sorted(set(declared_hashes).difference(actual_hashes))
        changed = sorted(
            path
            for path in set(actual_hashes).intersection(declared_hashes)
            if actual_hashes[path] != declared_hashes[path]
        )
        raise VerificationError(
            f"{host} shared manifest is incomplete or stale; missing={missing}, extra={extra}, changed={changed}"
        )

    for path in sorted(distribution.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise VerificationError(f"{host} distribution contains a symlink: {path}")
        relative = path.relative_to(distribution).as_posix()
        if any(part in GENERATED_CACHE_PARTS for part in path.relative_to(distribution).parts):
            raise VerificationError(f"{host} distribution contains generated cache: {relative}")
        if path.is_file() and path.suffix in GENERATED_CACHE_SUFFIXES:
            raise VerificationError(f"{host} distribution contains generated bytecode: {relative}")
        if path_is_forbidden(relative, spec["forbidden_paths"]):
            raise VerificationError(f"{host} distribution contains forbidden path: {relative}")

    size_bytes = file_size(distribution)
    if size_bytes > spec["max_uncompressed_bytes"]:
        raise VerificationError(
            f"{host} distribution is {size_bytes} bytes, above {spec['max_uncompressed_bytes']}"
        )

    return {
        "host": host,
        "size_bytes": size_bytes,
        "shared_files": len(declared_hashes),
        "shared_manifest": declared_hashes,
    }


def verify_host_specific_boundaries(spec: dict[str, Any]) -> None:
    openai = ROOT / spec["hosts"]["openai"]["distribution"]
    claude = ROOT / spec["hosts"]["claude"]["distribution"]
    if not (openai / ".codex-plugin/plugin.json").is_file():
        raise VerificationError("OpenAI distribution is missing its Codex manifest")
    if (openai / ".claude-plugin").exists():
        raise VerificationError("OpenAI distribution contains Claude-only files")
    if not (claude / ".claude-plugin/plugin.json").is_file():
        raise VerificationError("Claude distribution is missing its Claude manifest")
    if (claude / ".codex-plugin").exists():
        raise VerificationError("Claude distribution contains OpenAI-only files")
    openai_metadata = "skills/run/agents/openai.yaml"
    exclusions = spec.get("host_specific_shared_path_exclusions", [])
    if exclusions != [openai_metadata]:
        raise VerificationError("The OpenAI skill metadata exclusion must be exact and singular")
    if not (openai / openai_metadata).is_file():
        raise VerificationError("OpenAI distribution is missing OpenAI-only skill metadata")
    if (claude / openai_metadata).exists():
        raise VerificationError("Claude distribution contains OpenAI-only skill metadata")


def main() -> int:
    try:
        spec = load_json(ROOT / "bundle-spec.json")
        results = {host: verify_host(host, spec) for host in sorted(spec["hosts"])}
        if results["openai"]["shared_manifest"] != results["claude"]["shared_manifest"]:
            raise VerificationError("Shared core differs between host distributions")
        verify_host_specific_boundaries(spec)

        report = {
            "status": "pass",
            "plugin": spec["plugin"],
            "version": spec["version"],
            "shared_files_identical": True,
            "state_tool_bundled": True,
            "system_tool_bundled": True,
            "adapter_tool_bundled": True,
            "build_tool_bundled": True,
            "quality_tool_bundled": True,
            "mcp_bundled": False,
            "full_corpus_bundled": False,
            "hosts": {
                host: {
                    "size_bytes": data["size_bytes"],
                    "shared_files": data["shared_files"],
                }
                for host, data in results.items()
            },
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except VerificationError as exc:
        print(f"VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
