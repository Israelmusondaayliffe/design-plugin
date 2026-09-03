import argparse
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "core" / "scripts" / "design_learning.py"
SPEC = importlib.util.spec_from_file_location("design_learning", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DesignLearningTests(unittest.TestCase):
    def _args(self, root: Path, **values):
        defaults = {
            "state_root": str(root.resolve()), "project_key": "private/path/project", "category": "friction",
            "summary": "owner@example.com wasted a retry token=secret-value", "impact": "extra cost",
            "method": "inspect available tools first", "exact_quote": None, "retain_exact_quote": False,
        }
        defaults.update(values)
        return argparse.Namespace(**defaults)

    def test_capture_is_redacted_opaque_and_export_is_neutral(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "learning"
            result = MODULE.capture_event(self._args(root))
            event = result["event"]
            self.assertNotIn("owner@example.com", json.dumps(event))
            self.assertNotIn("private/path/project", json.dumps(event))
            exported = MODULE.export_events(argparse.Namespace(
                state_root=str(root), project_key=None, category=None
            ))
            self.assertEqual(1, exported["count"])
            self.assertNotIn("exact_quote", exported["records"][0])
            self.assertEqual("design-neutral-export", exported["records"][0]["source_type"])

    def test_exact_quote_requires_explicit_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(MODULE.LearningError):
                MODULE.capture_event(self._args(Path(temp).resolve() / "learning", exact_quote="keep this"))

    def test_git_and_symlink_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            repository = base / "repository"
            (repository / ".git").mkdir(parents=True)
            with self.assertRaises(MODULE.LearningError):
                MODULE.validate_state_root(repository / "private")
            actual = base / "actual"
            actual.mkdir()
            link = base / "link"
            link.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(MODULE.LearningError):
                MODULE.validate_state_root(link / "private")
            nested_parent = base / "nested"
            nested_parent.mkdir()
            nested_link = nested_parent / "link"
            nested_link.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(MODULE.LearningError):
                MODULE.validate_state_root(nested_link / "private")
            dangling = base / "dangling"
            dangling.symlink_to(base / "missing", target_is_directory=True)
            with self.assertRaises(MODULE.LearningError):
                MODULE.validate_state_root(dangling / "private")

    def test_purge_controls_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "learning"
            MODULE.capture_event(self._args(root))
            result = MODULE.purge_project(argparse.Namespace(state_root=str(root), project_key="private/path/project"))
            self.assertEqual(1, result["removed_count"])
            self.assertEqual([], MODULE._event_files(root))

    def test_default_root_uses_private_user_state(self):
        with mock.patch.dict(os.environ, {"DESIGN_LEARNING_ROOT": ""}, clear=False):
            root = MODULE._default_root()
        self.assertNotIn(".design", root.parts)
        self.assertNotIn("dist", {part.casefold() for part in root.parts})

    def test_plugin_distribution_site_and_evidence_roots_are_rejected(self):
        candidates = (
            SCRIPT.parents[2] / "private-learning",
            SCRIPT.parents[2] / "dist" / "design-openai" / "learning",
            Path("/private/var/tmp/design-test/site/learning"),
            Path("/private/var/tmp/design-test/evidence/learning"),
            Path("/private/var/tmp/design-plugin-source/learning"),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(MODULE.LearningError):
                    MODULE.validate_state_root(candidate)


if __name__ == "__main__":
    unittest.main()
