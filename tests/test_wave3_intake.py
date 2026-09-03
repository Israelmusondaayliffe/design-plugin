import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "core" / "scripts" / "design_intake.py"
spec = importlib.util.spec_from_file_location("design_intake", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


class Wave3IntakeTests(unittest.TestCase):
    def project(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "README.md").write_text("hello", encoding="utf-8")
        return td, root

    def valid_session(self):
        return {
            "schema_version": "1.0",
            "status": "active",
            "rounds": [{
                "round": 1,
                "questions": [
                    {"id": "R1Q1", "text": "a?", "impact": "normal"},
                    {"id": "R1Q2", "text": "b?", "impact": "normal"},
                    {"id": "R1Q3", "text": "c?", "impact": "normal"},
                ],
            }],
            "assumptions": [],
            "approval": None,
            "skip": None,
        }

    def test_inspection_is_read_only_probe(self):
        td, root = self.project()
        try:
            report = mod.inspect_environment(root)
            self.assertTrue(report["read_only_probe"])
            self.assertFalse(report["network_accessed"])
            self.assertFalse(report["software_installed"])
            self.assertIn("README.md", report["project"]["files_present"])
            capabilities = report["host_connections"]["capability_classes"]
            self.assertEqual(
                {"browser", "computer_use", "image_generation", "image_editing", "figma", "connectors", "local_tools"},
                set(capabilities),
            )
            self.assertTrue(all(item["status"] == "unverified" for item in capabilities.values()))
        finally:
            td.cleanup()

    def test_scaffold_writes_only_design_directory(self):
        td, root = self.project()
        try:
            before = {p.relative_to(root).as_posix() for p in root.rglob("*")}
            mod.scaffold(root)
            after = {p.relative_to(root).as_posix() for p in root.rglob("*")}
            added = after - before
            self.assertTrue(added)
            self.assertTrue(all(p == ".design" or p.startswith(".design/") for p in added))
        finally:
            td.cleanup()

    def test_scaffold_preserves_existing_interview_files(self):
        td, root = self.project()
        try:
            mod.scaffold(root)
            questions = root / ".design/interview/questions.md"
            questions.write_text("KEEP", encoding="utf-8")
            mod.scaffold(root)
            self.assertEqual(questions.read_text(encoding="utf-8"), "KEEP")
        finally:
            td.cleanup()

    def test_six_round_ceiling(self):
        session = self.valid_session()
        session["rounds"] = [
            {"round": i, "questions": [{"id": f"R{i}Q1", "text": "?", "impact": "high"}]}
            for i in range(1, 8)
        ]
        self.assertTrue(any("six rounds" in error for error in mod.validate_session(session)))

    def test_ordinary_round_must_have_three_to_six_questions(self):
        session = self.valid_session()
        session["rounds"][0]["questions"] = session["rounds"][0]["questions"][:2]
        self.assertTrue(any("3-6" in error for error in mod.validate_session(session)))

    def test_high_impact_question_must_be_alone(self):
        session = self.valid_session()
        session["rounds"][0]["questions"][0]["impact"] = "high"
        self.assertTrue(any("one at a time" in error for error in mod.validate_session(session)))

    def test_single_high_impact_round_is_valid(self):
        session = self.valid_session()
        session["rounds"][0]["questions"] = [{"id": "R1Q1", "text": "?", "impact": "high"}]
        self.assertEqual(mod.validate_session(session), [])

    def test_rounds_must_be_sequential(self):
        session = self.valid_session()
        session["rounds"][0]["round"] = 2
        self.assertTrue(any("sequential" in error for error in mod.validate_session(session)))

    def test_assumption_classification_is_bounded(self):
        session = self.valid_session()
        session["assumptions"] = [{"item": "x", "classification": "guess"}]
        self.assertTrue(any("classification" in error for error in mod.validate_session(session)))

    def test_approval_phrases_are_explicit(self):
        session = self.valid_session()
        session["status"] = "approved"
        session["approval"] = {"phrase": "Approved"}
        self.assertEqual(mod.validate_session(session), [])
        self.assertTrue(mod.approval_phrase_valid("This understanding is approved"))
        self.assertFalse(mod.approval_phrase_valid("looks good"))

    def test_skip_requires_acknowledged_warning(self):
        session = self.valid_session()
        session["status"] = "skipped"
        session["skip"] = {"warning_acknowledged": False}
        self.assertTrue(any("acknowledged" in error for error in mod.validate_session(session)))
        session["skip"]["warning_acknowledged"] = True
        self.assertEqual(mod.validate_session(session), [])

    def test_validate_project_after_scaffold(self):
        td, root = self.project()
        try:
            mod.scaffold(root)
            result = mod.validate_project(root)
            self.assertTrue(result["valid"], result["errors"])
        finally:
            td.cleanup()

    def test_wave3_skills_and_templates_exist(self):
        required = [
            "core/skills/grill/SKILL.md",
            "core/skills/environment/SKILL.md",
            "core/templates/shared-understanding.template.md",
            "core/templates/prerequisite-proposal.template.md",
            "core/schemas/interview-session.schema.json",
            "core/schemas/environment-report.schema.json",
        ]
        for relative in required:
            self.assertTrue((PLUGIN_ROOT / relative).is_file(), relative)

    def test_install_boundary_is_explicit_in_environment_skill(self):
        text = (PLUGIN_ROOT / "core/skills/environment/SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("never install", text)
        self.assertIn("separate explicit approval", text)
        for label in ("approximate disk use", "how to remove it", "exact command"):
            self.assertIn(label, text)

    def test_grill_skill_contains_protocol_limits(self):
        text = (PLUGIN_ROOT / "core/skills/grill/SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("six rounds", text)
        self.assertIn("3–6 questions", text)
        self.assertIn("high-impact question by itself", text)
        self.assertIn("approved", text)
        self.assertIn("skipped", text)

    def test_codex_and_claude_host_capability_fixtures_are_complete(self):
        fixtures = PLUGIN_ROOT / "tests" / "fixtures"
        for name, host in (("host-capabilities-codex.json","codex"),("host-capabilities-claude.json","claude-code")):
            report=json.loads((fixtures/name).read_text(encoding="utf-8"))
            self.assertEqual(host,report["host"])
            self.assertEqual([],mod.validate_host_capabilities(report))

    def test_no_image_tool_fixture_uses_local_fallback(self):
        path=PLUGIN_ROOT/"tests"/"fixtures"/"host-capabilities-no-image.json"
        report=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([],mod.validate_host_capabilities(report))
        self.assertEqual("local-imagery-scaffold-only",mod.image_tool_route(report))


if __name__ == "__main__":
    unittest.main()
