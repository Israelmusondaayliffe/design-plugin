#!/usr/bin/env python3
"""Build deterministic OpenAI and Claude Design plugin distributions.

Standard-library only. The script does not install software or access the network.
Generated output under dist/ is disposable and must never be edited by hand.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "bundle-spec.json"
GENERATED_CACHE_PARTS = {"__pycache__"}
GENERATED_CACHE_SUFFIXES = {".pyc", ".pyo"}


class BuildError(RuntimeError):
    """Raised when the source package violates the bundle contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"Required file is missing: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise BuildError(f"Symlinks are not permitted: {source.relative_to(ROOT)}")
    if not source.is_file():
        raise BuildError(f"Expected a file: {source.relative_to(ROOT)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise BuildError(f"Expected a directory: {source.relative_to(ROOT)}")
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise BuildError(f"Symlinks are not permitted: {path.relative_to(ROOT)}")
        relative = path.relative_to(source)
        if any(part in GENERATED_CACHE_PARTS for part in relative.parts):
            continue
        if path.is_file() and path.suffix in GENERATED_CACHE_SUFFIXES:
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            copy_file(path, target)


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


def collect_shared_manifest(
    distribution: Path,
    shared_roots: list[str],
    common_files: list[str],
    exclusions: list[str],
) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for common in common_files:
        path = distribution / common
        if not path.is_file():
            raise BuildError(f"Missing common file in distribution: {common}")
        manifest[common] = sha256(path)
    for root_name in shared_roots:
        root = distribution / root_name
        if not root.is_dir():
            raise BuildError(f"Missing shared directory in distribution: {root_name}")
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(distribution).as_posix()
            if path.is_file() and relative not in exclusions:
                manifest[relative] = sha256(path)
    return dict(sorted(manifest.items()))


def validate_distribution_paths(distribution: Path, forbidden: list[str]) -> None:
    for path in sorted(distribution.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise BuildError(f"Generated distribution contains a symlink: {path}")
        relative = path.relative_to(distribution).as_posix()
        if path_is_forbidden(relative, forbidden):
            raise BuildError(f"Forbidden path entered distribution: {relative}")


def validate_required_shared_files(distribution: Path, required: list[str]) -> None:
    for relative in required:
        path = distribution / relative
        if not path.is_file():
            raise BuildError(f"Required shared runtime file is missing: {relative}")


def distribution_size(distribution: Path) -> int:
    return sum(path.stat().st_size for path in distribution.rglob("*") if path.is_file())


def build_host(host: str, spec: dict[str, Any]) -> dict[str, Any]:
    host_spec = spec["hosts"][host]
    distribution = ROOT / host_spec["distribution"]
    overlay = ROOT / host_spec["overlay"]
    shared_root = ROOT / spec["canonical_shared_root"]

    if distribution.exists():
        shutil.rmtree(distribution)
    distribution.mkdir(parents=True, exist_ok=True)

    for directory in spec["shared_directories"]:
        copy_tree(shared_root / directory, distribution / directory)
    for common_file in spec["common_files"]:
        copy_file(ROOT / common_file, distribution / common_file)
    copy_tree(overlay, distribution)

    required_manifest = distribution / host_spec["required_manifest"]
    manifest_data = load_json(required_manifest)
    if manifest_data.get("name") != spec["plugin"]:
        raise BuildError(
            f"{host} manifest name must be {spec['plugin']!r}; got {manifest_data.get('name')!r}"
        )
    if manifest_data.get("version") != spec["version"]:
        raise BuildError(
            f"{host} manifest version must match bundle spec {spec['version']!r}"
        )

    validate_required_shared_files(distribution, spec["required_shared_files"])
    validate_distribution_paths(distribution, spec["forbidden_paths"])
    shared_manifest = collect_shared_manifest(
        distribution,
        spec["shared_directories"],
        spec["common_files"],
        spec.get("host_specific_shared_path_exclusions", []),
    )
    write_json(distribution / "SHARED_MANIFEST.json", shared_manifest)

    receipt = {
        "plugin": spec["plugin"],
        "host": host,
        "version": spec["version"],
        "shared_manifest": "SHARED_MANIFEST.json",
    }
    write_json(distribution / "BUILD_RECEIPT.json", receipt)

    size_bytes = distribution_size(distribution)
    if size_bytes > spec["max_uncompressed_bytes"]:
        raise BuildError(
            f"{host} distribution is {size_bytes} bytes, above {spec['max_uncompressed_bytes']}"
        )

    return {
        "host": host,
        "path": distribution.relative_to(ROOT).as_posix(),
        "shared_files": len(shared_manifest),
        "size_bytes": size_bytes,
    }


def main() -> int:
    try:
        spec = load_json(SPEC_PATH)
        required_keys = {
            "plugin",
            "version",
            "canonical_shared_root",
            "hosts",
            "shared_directories",
            "required_shared_files",
            "common_files",
            "max_uncompressed_bytes",
            "forbidden_paths",
        }
        missing = sorted(required_keys.difference(spec))
        if missing:
            raise BuildError(f"bundle-spec.json is missing keys: {', '.join(missing)}")
        if sorted(spec["hosts"]) != ["claude", "openai"]:
            raise BuildError("Exactly the openai and claude hosts must be defined")

        receipts = [build_host(host, spec) for host in sorted(spec["hosts"])]
        print(json.dumps({"status": "built", "distributions": receipts}, indent=2))
        return 0
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
