#!/usr/bin/env python3
"""Regression tests for the harness-independent R04 probe contract."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/run_r04_activation_probes.py"
SPEC = importlib.util.spec_from_file_location("run_r04_activation_probes", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot import the R04 activation probe")
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class R04ActivationProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_distributions.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_matrix_contains_every_required_case(self) -> None:
        cases = PROBE.build_cases()
        counts: dict[str, int] = {}
        for case in cases:
            counts[case.category] = counts.get(case.category, 0) + 1
        self.assertEqual(
            counts,
            {
                "explicit": 3,
                "automatic-positive": 9,
                "automatic-negative": 6,
                "precedence": 2,
            },
        )
        self.assertEqual(len(cases), 20)

    def test_explicit_syntax_is_host_specific(self) -> None:
        run_case = next(case for case in PROBE.build_cases() if case.case_id == "explicit-run")
        self.assertEqual(PROBE.host_prompt("codex", run_case), "$design:run")
        self.assertEqual(PROBE.host_prompt("claude", run_case), "/design:run")

    def test_claude_selection_uses_native_skill_events(self) -> None:
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Skill",
                            "input": {"skill": "design:audit"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-1", "content": "ok"}
                    ]
                },
            },
        ]
        selected, observations = PROBE.claude_selection(events)
        self.assertEqual(selected, ["audit"])
        self.assertEqual(observations[0]["source"], "correlated-skill-tool")

    def test_claude_selection_ignores_model_prose(self) -> None:
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "I selected design:run."},
                    ]
                },
            }
        ]
        self.assertEqual(PROBE.claude_selection(events), ([], []))

    def test_codex_selection_requires_native_event_or_exact_skill_load(self) -> None:
        prose = [{"type": "agent_message", "text": "I selected design:resume."}]
        self.assertEqual(PROBE.codex_selection(prose), ([], []))
        package_root = ROOT / "dist/design-openai"
        skill_path = package_root / "skills/resume/SKILL.md"
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": f"sed -n 1,240p {skill_path}",
                    "aggregated_output": skill_path.read_text(encoding="utf-8"),
                    "exit_code": 0,
                },
            }
        ]
        selected, observations = PROBE.codex_selection(events, package_root)
        self.assertEqual(selected, ["resume"])
        self.assertEqual(
            observations[0]["source"], "successful-content-verified-skill-file-load"
        )

    def test_active_codex_home_is_always_rejected(self) -> None:
        result = PROBE.codex_preflight("codex", PROBE.ACTIVE_CODEX_HOME)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("active ~/.codex", result["reason"])

    def test_codex_execution_ignores_user_config(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('"--ignore-user-config"', source)
        self.assertIn("CODEX_QUALIFICATION_HOME_ALLOWLIST", source)

    def test_case_receipt_binds_model_and_cli_version(self) -> None:
        case = PROBE.ProbeCase("test", "explicit", "run", "run")
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        events = [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-haiku",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Skill",
                            "input": {"skill": "design:run"},
                        }
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-1", "content": "ok"}
                    ]
                },
            },
            {"type": "result", "subtype": "success", "is_error": False},
        ]
        result = PROBE.summarize_case(
            host="claude",
            case=case,
            prompt="/design:run",
            completed=completed,
            events=events,
            ignored_lines=0,
            requested_model="haiku",
            cli_version="2.1.206 (Claude Code)",
        )
        self.assertEqual(result["model_binding_status"], "pass")
        self.assertEqual(result["requested_model"], "haiku")
        self.assertEqual(result["cli_version"], "2.1.206 (Claude Code)")

    def test_adversarial_parser_fixtures_cannot_pass(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        positive = PROBE.ProbeCase("attack", "automatic-positive", "run", "prompt")
        negative = PROBE.ProbeCase("attack", "automatic-negative", "none", "prompt")

        fixtures = [
            (
                "codex",
                positive,
                [
                    {"type": "system.init", "skill_metadata": {"name": "design:run"}},
                    {"type": "turn.completed", "model": "gpt-5.4-mini"},
                ],
                0,
            ),
            (
                "codex",
                PROBE.ProbeCase("attack", "automatic-positive", "audit", "prompt"),
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "sed /tmp/unrelated/skills/audit/SKILL.md",
                            "exit_code": 1,
                        },
                    },
                    {"type": "turn.completed", "model": "gpt-5.4-mini"},
                ],
                0,
            ),
            (
                "codex",
                PROBE.ProbeCase("attack", "automatic-positive", "resume", "prompt"),
                [
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "skill_invocation",
                            "name": "design:resume",
                            "status": "completed",
                        },
                    },
                    {"type": "turn.failed", "model": "gpt-5.4-mini"},
                ],
                0,
            ),
            (
                "codex",
                negative,
                [{"type": "turn.failed", "model": "gpt-5.4-mini"}],
                1,
            ),
            (
                "claude",
                negative,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "model": "claude-haiku",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "tool-2",
                                    "name": "Skill",
                                    "input": {"skill": "design:research"},
                                }
                            ],
                        },
                    },
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {"type": "tool_result", "tool_use_id": "tool-2", "content": "ok"}
                            ]
                        },
                    },
                    {"type": "result", "subtype": "success", "is_error": False},
                ],
                0,
            ),
            (
                "claude",
                positive,
                [
                    {"type": "system", "commands": [{"commandName": "design:run"}]},
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "model": "claude-haiku",
                    },
                ],
                0,
            ),
        ]
        for host, case, events, ignored in fixtures:
            with self.subTest(host=host, events=events):
                result = PROBE.summarize_case(
                    host=host,
                    case=case,
                    prompt=case.base_prompt,
                    completed=completed,
                    events=events,
                    ignored_lines=ignored,
                    requested_model="haiku" if host == "claude" else "gpt-5.4-mini",
                    cli_version="test-cli",
                    package_root=Path("/tmp/installed-design"),
                )
                self.assertNotEqual(result["status"], "pass")

    def test_missing_observed_model_cannot_pass(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        case = PROBE.ProbeCase("negative", "automatic-negative", "none", "prompt")
        result = PROBE.summarize_case(
            host="codex",
            case=case,
            prompt="prompt",
            completed=completed,
            events=[{"type": "turn.completed"}],
            ignored_lines=0,
            requested_model="gpt-5.4-mini",
            cli_version="codex test",
        )
        self.assertEqual(result["model_binding_status"], "fail")
        self.assertNotEqual(result["status"], "pass")

    def test_catalog_model_field_is_not_native_model_evidence(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        case = PROBE.ProbeCase("negative", "automatic-negative", "none", "prompt")
        result = PROBE.summarize_case(
            host="codex",
            case=case,
            prompt="prompt",
            completed=completed,
            events=[
                {"type": "system.init", "catalog": {"model": "gpt-5.4-mini"}},
                {"type": "turn.completed"},
            ],
            ignored_lines=0,
            requested_model="gpt-5.4-mini",
            cli_version="codex test",
        )
        self.assertEqual(result["observed_models"], [])
        self.assertNotEqual(result["status"], "pass")

    def test_codex_echoed_path_and_hidden_second_visible_route_cannot_pass(self) -> None:
        package_root = ROOT / "dist/design-openai"
        run_path = package_root / "skills/run/SKILL.md"
        audit_path = package_root / "skills/audit/SKILL.md"
        echo_only = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": f"echo {run_path}",
                    "aggregated_output": str(run_path),
                    "exit_code": 0,
                },
            }
        ]
        self.assertEqual(PROBE.codex_selection(echo_only, package_root), ([], []))

        two_routes = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": f"cat {run_path} {audit_path}",
                    "aggregated_output": (
                        run_path.read_text(encoding="utf-8")
                        + audit_path.read_text(encoding="utf-8")
                    ),
                    "exit_code": 0,
                },
            }
        ]
        selected, _ = PROBE.codex_selection(two_routes, package_root)
        self.assertEqual(sorted(selected), ["audit", "run"])

    def test_positive_visible_selection_allows_internal_design_calls(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        case = PROBE.ProbeCase("positive", "automatic-positive", "run", "prompt")
        events = [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-haiku",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "visible",
                            "name": "Skill",
                            "input": {"skill": "design:run"},
                        },
                        {
                            "type": "tool_use",
                            "id": "internal",
                            "name": "Skill",
                            "input": {"skill": "design:environment"},
                        },
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "visible", "content": "ok"},
                        {"type": "tool_result", "tool_use_id": "internal", "content": "ok"},
                    ]
                },
            },
            {"type": "result", "subtype": "success", "is_error": False},
        ]
        result = PROBE.summarize_case(
            host="claude",
            case=case,
            prompt="prompt",
            completed=completed,
            events=events,
            ignored_lines=0,
            requested_model="haiku",
            cli_version="claude test",
        )
        self.assertEqual(result["observed_visible_workflows"], ["run"])
        self.assertEqual(result["status"], "pass")

    def test_active_codex_descendants_are_rejected(self) -> None:
        result = PROBE.codex_preflight("codex", PROBE.ACTIVE_CODEX_HOME / "child")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("descendants", result["reason"])

    def test_claude_provider_environment_is_sanitized(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "PATH": os.environ.get("PATH", ""),
                "ANTHROPIC_API_KEY": "not-a-real-key",
                "ANTHROPIC_BASE_URL": "https://example.invalid",
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "AWS_REGION": "test-region",
            },
            clear=True,
        ):
            env = PROBE.claude_api_key_env(Path("/tmp/claude-r04"))
        self.assertEqual(env["ANTHROPIC_API_KEY"], "not-a-real-key")
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("CLAUDE_CODE_USE_BEDROCK", env)
        self.assertNotIn("AWS_REGION", env)

    def test_claude_preflight_does_not_fall_back_to_subscription_auth(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            result = PROBE.claude_preflight("claude")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("ANTHROPIC_API_KEY is absent", result["reason"])

    def test_probe_distinguishes_evidence_isolation_from_user_installation(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("compatibility is outside this runner's evidence boundary", source)
        self.assertIn("active_user_installation", source)
        self.assertNotIn("copyIfExists", source)
        self.assertNotIn('copyfile(Path.home() / ".codex/auth.json"', source)

    def test_qualification_restrictions_are_not_bundled_into_the_plugin(self) -> None:
        forbidden = (
            "ANTHROPIC_API_KEY is absent",
            "The active ~/.codex home is forbidden",
            "run_r04_activation_probes.py",
        )
        for host in ("design-openai", "design-claude"):
            distribution = ROOT / "dist" / host
            paths = [path for path in distribution.rglob("*") if path.is_file()]
            self.assertFalse(any(path.name == "run_r04_activation_probes.py" for path in paths))
            runtime_paths = [
                path
                for root_name in ("skills", "scripts")
                for path in (distribution / root_name).rglob("*")
                if path.is_file()
            ]
            searchable = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore") for path in runtime_paths
            )
            for phrase in forbidden:
                self.assertNotIn(phrase, searchable)

    def test_install_docs_separate_preflight_from_paid_execution(self) -> None:
        text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("Preflight only", text)
        self.assertIn("--execute", text)
        self.assertIn("--confirm-external-usage", text)
        self.assertIn("--claude-max-total-cost-usd 4.00", text)


if __name__ == "__main__":
    unittest.main()
