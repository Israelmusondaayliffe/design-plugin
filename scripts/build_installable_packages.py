#!/usr/bin/env python3
"""Build deterministic local marketplace fixtures and release archives.

Standard-library only. The script writes only below dist/ and never changes a
host configuration, plugin cache, or marketplace registration.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "host-packaging.json"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class PackagingError(RuntimeError):
    """Raised when an installable package cannot be built safely."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PackagingError(f"Missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise PackagingError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackagingError(f"Expected a JSON object: {path.relative_to(ROOT)}")
    return data


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


def safe_copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise PackagingError(
            f"Missing distribution: {source.relative_to(ROOT)}. Run build_distributions.py first."
        )
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise PackagingError(f"Symlink is not permitted: {path.relative_to(ROOT)}")
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def archive_tree(source: Path, destination: Path, archive_root: str) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    files = [
        path
        for path in sorted(source.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    ]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(f"{archive_root}/{relative}", FIXED_ZIP_TIME)
            info.create_system = 3
            mode = 0o755 if path.suffix == ".py" else 0o644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    return {
        "path": destination.relative_to(ROOT).as_posix(),
        "sha256": sha256(destination),
        "size_bytes": destination.stat().st_size,
        "file_count": len(files),
    }


def build_openai(config: dict[str, Any]) -> dict[str, Any]:
    host = config["hosts"]["openai"]
    marketplace = ROOT / host["marketplace_root"]
    plugin = marketplace / "plugins" / config["plugin"]
    if marketplace.exists():
        shutil.rmtree(marketplace)
    safe_copy_tree(ROOT / host["distribution"], plugin)
    manifest = {
        "name": host["marketplace_name"],
        "interface": {"displayName": "Design local qualification"},
        "plugins": [
            {
                "name": config["plugin"],
                "source": {"source": "local", "path": f"./plugins/{config['plugin']}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Design",
            }
        ],
    }
    write_json(marketplace / host["marketplace_manifest"], manifest)
    return {"host": "openai", "root": host["marketplace_root"]}


def build_claude(config: dict[str, Any]) -> dict[str, Any]:
    host = config["hosts"]["claude"]
    marketplace = ROOT / host["marketplace_root"]
    plugin = marketplace / "plugins" / config["plugin"]
    if marketplace.exists():
        shutil.rmtree(marketplace)
    safe_copy_tree(ROOT / host["distribution"], plugin)
    manifest = {
        "name": host["marketplace_name"],
        "owner": {"name": "Israel Ayliffe"},
        "description": "Local marketplace package for the Design plugin.",
        "plugins": [
            {
                "name": config["plugin"],
                "source": f"./plugins/{config['plugin']}",
                "description": "Research-grounded design operating system.",
                "version": config["version"],
            }
        ],
    }
    write_json(marketplace / host["marketplace_manifest"], manifest)
    return {"host": "claude", "root": host["marketplace_root"]}


def main() -> int:
    try:
        config = load_json(CONFIG_PATH)
        spec = load_json(ROOT / "bundle-spec.json")
        if config.get("plugin") != spec.get("plugin") or config.get("version") != spec.get("version"):
            raise PackagingError("host-packaging.json and bundle-spec.json must name the same plugin and version")
        if sorted(config.get("hosts", {})) != ["claude", "openai"]:
            raise PackagingError("Exactly the openai and claude hosts must be configured")

        marketplaces = [build_openai(config), build_claude(config)]
        release_root = ROOT / config["release_root"]
        if release_root.exists():
            shutil.rmtree(release_root)
        release_root.mkdir(parents=True)
        archives = []
        for host in ("openai", "claude"):
            source = ROOT / config["hosts"][host]["distribution"]
            filename = f"design-{host}-{config['version']}.zip"
            archives.append(archive_tree(source, release_root / filename, f"design-{host}"))
        receipt = {
            "schema_version": "1.0",
            "plugin": config["plugin"],
            "version": config["version"],
            "archives": archives,
        }
        write_json(release_root / "RELEASE_RECEIPT.json", receipt)
        print(json.dumps({"status": "built", "marketplaces": marketplaces, **receipt}, indent=2))
        return 0
    except PackagingError as exc:
        print(f"PACKAGING FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
