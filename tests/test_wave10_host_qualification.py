#!/usr/bin/env python3
"""Regression tests for Wave 10 host packaging and qualification."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    }


class Wave10HostQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads((ROOT / "bundle-spec.json").read_text(encoding="utf-8"))
        cls.config = json.loads((ROOT / "host-packaging.json").read_text(encoding="utf-8"))
        for script in ("build_distributions.py", "build_installable_packages.py"):
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script)],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

    def test_versions_are_synchronized(self) -> None:
        versions = {
            self.spec["version"],
            self.config["version"],
            json.loads((ROOT / "hosts/openai/.codex-plugin/plugin.json").read_text())["version"],
            json.loads((ROOT / "hosts/claude/.claude-plugin/plugin.json").read_text())["version"],
        }
        self.assertEqual(versions, {"0.1.0-dev.10"})

    def test_installable_verifier_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_installable_packages.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["activation_cases"], {"positive": 9, "negative": 6})
        for host in ("openai", "claude"):
            self.assertLess(report["hosts"][host]["size_bytes"], 1024 * 1024)
            self.assertEqual(report["hosts"][host]["mcp_scan"]["paths"], [])
            self.assertEqual(report["hosts"][host]["mcp_scan"]["runtime_references"], [])
            self.assertTrue(all(report["hosts"][host]["filesystem_lifecycle"].values()))

    def test_installable_marketplaces_are_exact_distribution_copies(self) -> None:
        for host in ("openai", "claude"):
            distribution = ROOT / self.config["hosts"][host]["distribution"]
            plugin = ROOT / self.config["hosts"][host]["marketplace_root"] / "plugins/design"
            self.assertEqual(file_hashes(distribution), file_hashes(plugin))

    def test_claude_marketplace_has_required_description(self) -> None:
        marketplace = ROOT / self.config["hosts"]["claude"]["marketplace_root"]
        manifest = json.loads((marketplace / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(manifest["description"], "Local marketplace package for the Design plugin.")

    def test_openai_metadata_is_host_only(self) -> None:
        relative = Path("skills/run/agents/openai.yaml")
        self.assertFalse((ROOT / "core" / relative).exists())
        self.assertTrue((ROOT / "hosts/openai" / relative).is_file())
        self.assertTrue((ROOT / "dist/design-openai" / relative).is_file())
        self.assertFalse((ROOT / "dist/design-claude" / relative).exists())
        shared_openai = json.loads((ROOT / "dist/design-openai/SHARED_MANIFEST.json").read_text())
        shared_claude = json.loads((ROOT / "dist/design-claude/SHARED_MANIFEST.json").read_text())
        self.assertEqual(shared_openai, shared_claude)
        self.assertNotIn(relative.as_posix(), shared_openai)

    def test_visibility_contract_is_exact(self) -> None:
        self.assertEqual(sorted(self.config["visible_workflows"]), ["audit", "resume", "run"])
        self.assertEqual(len(self.config["internal_skills"]), 19)
        for host in ("design-openai", "design-claude"):
            root = ROOT / "dist" / host / "skills"
            visible = []
            internal = []
            for skill_file in sorted(root.glob("*/SKILL.md")):
                text = skill_file.read_text(encoding="utf-8")
                target = internal if "user-invocable: false" in text.split("---", 2)[1] else visible
                target.append(skill_file.parent.name)
            self.assertEqual(sorted(visible), ["audit", "resume", "run"])
            self.assertEqual(sorted(internal), sorted(self.config["internal_skills"]))

    def test_activation_policy_has_positive_negative_and_precedence_cases(self) -> None:
        activation = json.loads((ROOT / self.config["activation_policy"]).read_text())
        self.assertEqual(activation["precedence"], ["resume", "audit", "run"])
        self.assertEqual(len(activation["positive_cases"]), 9)
        self.assertEqual(len(activation["negative_cases"]), 6)
        self.assertEqual({case["expected"] for case in activation["positive_cases"]}, {"run", "audit", "resume"})
        self.assertEqual({case["expected"] for case in activation["negative_cases"]}, {"none"})

    def test_archives_are_deterministic(self) -> None:
        receipt_path = ROOT / self.config["release_root"] / "RELEASE_RECEIPT.json"
        before = {
            item["path"]: item["sha256"]
            for item in json.loads(receipt_path.read_text())["archives"]
        }
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_installable_packages.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        after = {
            item["path"]: item["sha256"]
            for item in json.loads(receipt_path.read_text())["archives"]
        }
        self.assertEqual(before, after)

    def test_guidance_contains_exact_install_update_and_remove_commands(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        for fragment in (
            'codex plugin marketplace add "$PWD/dist/installable/openai"',
            "codex plugin add design@design-local-openai --json",
            'claude plugin marketplace add "$PWD/dist/installable/claude" --scope user',
            "claude plugin install design@design-local-claude --scope user",
        ):
            self.assertIn(fragment, readme)
        for fragment in (
            "codex plugin remove design@design-local-openai --json",
            "claude plugin update design@design-local-claude --scope user",
            "claude plugin uninstall design@design-local-claude --scope user --yes",
            "claude plugin marketplace remove design-local-claude --scope user",
            "explicitly approves installation",
        ):
            self.assertIn(fragment, guide)

    def test_host_parity_document_contains_required_sections(self) -> None:
        parity = (ROOT / self.config["host_parity_reference"]).read_text(encoding="utf-8")
        for phrase in (
            "Equivalent shared behavior",
            "Accepted host differences",
            "Neither package includes an MCP server",
            "OpenAI",
            "Claude Code",
        ):
            self.assertIn(phrase, parity)

    def test_isolated_harness_declares_temporary_config_roots(self) -> None:
        script = (ROOT / "scripts/run_isolated_host_checks.py").read_text(encoding="utf-8")
        self.assertIn('env["CODEX_HOME"]', script)
        self.assertIn('env["CLAUDE_CONFIG_DIR"]', script)
        self.assertIn("TemporaryDirectory", script)
        self.assertIn("credentials_copied", script)
        self.assertNotIn("copy2(Path.home()", script)


if __name__ == "__main__":
    unittest.main()
