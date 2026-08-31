#!/usr/bin/env python3
"""Regression tests for the Wave 1 package contract."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads((ROOT / "bundle-spec.json").read_text(encoding="utf-8"))
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_distributions.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_verifier_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_distributions.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["version"], self.spec["version"])
        self.assertTrue(report["shared_files_identical"])
        self.assertTrue(report["state_tool_bundled"])
        self.assertTrue(report["system_tool_bundled"])
        self.assertTrue(report["adapter_tool_bundled"])
        self.assertTrue(report["build_tool_bundled"])
        self.assertFalse(report["mcp_bundled"])
        self.assertFalse(report["full_corpus_bundled"])

    def test_host_manifests_are_isolated(self) -> None:
        openai_manifest = ROOT / "dist/design-openai/.codex-plugin/plugin.json"
        claude_manifest = ROOT / "dist/design-claude/.claude-plugin/plugin.json"
        self.assertTrue(openai_manifest.is_file())
        self.assertFalse((ROOT / "dist/design-openai/.claude-plugin").exists())
        self.assertTrue(claude_manifest.is_file())
        self.assertFalse((ROOT / "dist/design-claude/.codex-plugin").exists())
        self.assertEqual(json.loads(openai_manifest.read_text())["version"], self.spec["version"])
        self.assertEqual(json.loads(claude_manifest.read_text())["version"], self.spec["version"])

    def test_shared_manifest_matches(self) -> None:
        openai = json.loads((ROOT / "dist/design-openai/SHARED_MANIFEST.json").read_text())
        claude = json.loads((ROOT / "dist/design-claude/SHARED_MANIFEST.json").read_text())
        self.assertEqual(openai, claude)
        self.assertGreater(len(openai), 0)
        for required in self.spec["required_shared_files"]:
            self.assertIn(required, openai)

    def test_runtime_entrypoints_exist_in_both_hosts(self) -> None:
        for distribution in ("design-openai", "design-claude"):
            root = ROOT / "dist" / distribution
            self.assertTrue((root / "scripts/design_state.py").is_file())
            self.assertTrue((root / "scripts/design_intake.py").is_file())
            self.assertTrue((root / "scripts/design_system.py").is_file())
            self.assertTrue((root / "scripts/design_adapters.py").is_file())
            self.assertTrue((root / "scripts/design_build.py").is_file())
            self.assertTrue((root / "skills/run/SKILL.md").is_file())
            self.assertTrue((root / "skills/audit/SKILL.md").is_file())
            self.assertTrue((root / "skills/resume/SKILL.md").is_file())
            self.assertTrue((root / "skills/environment/SKILL.md").is_file())
            self.assertTrue((root / "skills/grill/SKILL.md").is_file())
            for skill in ("lock", "ux", "design-md", "tokens", "plan"):
                self.assertTrue((root / f"skills/{skill}/SKILL.md").is_file())
                self.assertTrue((root / f"skills/{skill}/scripts/design_system.py").is_file())
            for skill in ("imagery", "figma", "mobile"):
                self.assertTrue((root / f"skills/{skill}/SKILL.md").is_file())
                self.assertTrue((root / f"skills/{skill}/scripts/design_adapters.py").is_file())
            self.assertTrue((root / "skills/build-wave/SKILL.md").is_file())
            self.assertTrue((root / "skills/build-wave/scripts/design_build.py").is_file())

    def test_generated_python_cache_is_not_bundled(self) -> None:
        cache_root = ROOT / "core/scripts/__pycache__"
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / "migration-probe.pyc").write_bytes(b"not-runtime-source")
        try:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_distributions.py")],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            for distribution in ("design-openai", "design-claude"):
                root = ROOT / "dist" / distribution
                self.assertFalse(any(path.name == "__pycache__" for path in root.rglob("*")))
                self.assertFalse(any(root.rglob("*.pyc")))
                self.assertFalse(any(root.rglob("*.pyo")))
        finally:
            shutil.rmtree(cache_root)


if __name__ == "__main__":
    unittest.main()
