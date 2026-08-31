#!/usr/bin/env python3
"""Portability test for the skill-local Design state controller launcher."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "core/skills/state-controller/scripts/design_state.py"


class SkillLauncherTests(unittest.TestCase):
    def test_launcher_resolves_canonical_runtime_from_skill_root(self) -> None:
        self.assertTrue((LAUNCHER.parents[1] / "SKILL.md").is_file())
        self.assertTrue((ROOT / "core/scripts/design_state_cli.py").is_file())
        self.assertTrue((ROOT / "core/references/state-machine.json").is_file())

        spec = importlib.util.spec_from_file_location("design_state_skill_launcher", LAUNCHER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.PLUGIN_ROOT, ROOT / "core")
        self.assertEqual(module.RUNTIME_DIR, ROOT / "core/scripts")
        self.assertTrue(callable(module.main))
        self.assertTrue(callable(module.command_init))


if __name__ == "__main__":
    unittest.main()
