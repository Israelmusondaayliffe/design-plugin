#!/usr/bin/env python3
"""Wave 11 tests for the public catalog build and local reference Site."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CORPUS = ROOT / "corpus"


class Wave11SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = subprocess.run(
            [sys.executable, str(CORPUS / "scripts/build_catalog.py"), "--visibility", "public"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cls.report = json.loads(cls.build.stdout)
        cls.index = json.loads((SITE / "generated-data/catalog/index.json").read_text(encoding="utf-8"))
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.app = (SITE / "app.js").read_text(encoding="utf-8")
        cls.css = (SITE / "styles.css").read_text(encoding="utf-8")
        cls.readme = (SITE / "README.md").read_text(encoding="utf-8")

    def test_public_catalog_contains_all_reviewed_cases(self) -> None:
        self.assertEqual(self.report["visibility"], "public")
        self.assertEqual(self.report["case_count"], 60)
        self.assertEqual(self.index["visibility"], "public")
        self.assertEqual(self.index["case_count"], 60)
        self.assertTrue(all(case["publication_status"] == "public" for case in self.index["cases"]))

    def test_site_exposes_search_lane_and_deep_filters(self) -> None:
        for element_id in (
            "search",
            "lane-filters",
            "platform",
            "product-type",
            "archetype",
            "media",
            "density",
            "evidence",
            "results",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("URLSearchParams", self.app)

    def test_site_supports_progressive_case_detail_and_comparison(self) -> None:
        for element_id in ("case-dialog", "compare-dialog", "comparison"):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("generated-data/catalog/index.json", self.app)
        self.assertIn("generated-data/cases/${encodeURIComponent(slug)}", self.app)
        self.assertIn("source?.retrieved_at", self.app)
        self.assertIn("Source retrieved", self.app)
        self.assertIn("state.selected.size<5", self.app)
        self.assertIn("showModal", self.app)
        self.assertIn("Rebuild the public catalog data", self.app)

    def test_accessibility_and_responsive_contracts_are_present(self) -> None:
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('role="tablist"', self.html)
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        self.assertIn("@media (max-width: 760px)", self.css)
        self.assertIn(":focus-visible", self.css)

    def test_site_has_no_remote_visual_dependencies(self) -> None:
        combined = f"{self.html}\n{self.css}\n{self.app}".lower()
        self.assertNotIn("@import", combined)
        self.assertNotIn("<img", combined)
        self.assertNotIn("cdn.", combined)
        self.assertNotIn("fonts.googleapis", combined)

    def test_readme_preserves_local_only_publication_boundary(self) -> None:
        self.assertIn("python3 corpus/scripts/build_catalog.py --visibility public", self.readme)
        self.assertIn("python3 -m http.server 4173 --directory site", self.readme)
        self.assertIn("No Site deployment", self.readme)
        self.assertIn("separate approval gate", self.readme)


if __name__ == "__main__":
    unittest.main()
