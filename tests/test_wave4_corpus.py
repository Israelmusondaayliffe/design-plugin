#!/usr/bin/env python3
"""Wave 4 regression tests for corpus integrity, retrieval, and Site foundation."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
CASES = CORPUS / "cases"
SITE = ROOT / "site"
MANIFEST = ROOT / "core/catalog-manifest/catalog.json"
EXPECTED = {
    "adobe-spectrum-2",
    "apple-hig",
    "atlassian-design-system",
    "github-primer",
    "govuk-design-system",
    "ibm-carbon",
    "material-3",
    "microsoft-fluent-2",
    "porsche-design-system",
    "salesforce-slds-2",
    "shopify-polaris",
    "uswds",
}
REQUIRED_CASE_FILES = {
    "DESIGN.md",
    "metadata.json",
    "evidence.json",
    "tokens.json",
    "source-notes.md",
    "review.json",
    "preview-spec.json",
}


class Wave4CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (CORPUS / "generated", SITE / "generated-data"):
            if path.exists():
                shutil.rmtree(path)
        cls.validation = subprocess.run(
            [sys.executable, str(CORPUS / "scripts/validate_corpus.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cls.validation_report = json.loads(cls.validation.stdout)
        cls.build = subprocess.run(
            [sys.executable, str(CORPUS / "scripts/build_catalog.py")],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cls.build_report = json.loads(cls.build.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        for path in (CORPUS / "generated", SITE / "generated-data"):
            if path.exists():
                shutil.rmtree(path)

    def test_exact_engineering_seed_exists(self) -> None:
        actual = {path.name for path in CASES.iterdir() if path.is_dir()}
        self.assertEqual(actual, EXPECTED)
        self.assertEqual(self.validation_report["case_count"], 12)
        self.assertEqual(set(self.validation_report["slugs"]), EXPECTED)

    def test_each_case_has_complete_original_record_shape(self) -> None:
        for slug in EXPECTED:
            case = CASES / slug
            files = {path.name for path in case.iterdir() if path.is_file()}
            self.assertTrue(REQUIRED_CASE_FILES.issubset(files), slug)
            design = (case / "DESIGN.md").read_text(encoding="utf-8")
            self.assertIn("## Visual thesis", design)
            self.assertIn("## Signature relationships", design)
            self.assertIn("## Adaptation rules", design)
            self.assertIn("## Failure modes", design)
            self.assertGreater(len(design), 1200)

    def test_refero_is_not_a_corpus_source(self) -> None:
        prohibited = ("refero.design", "styles.refero.design", "api.refero.design")
        for slug in EXPECTED:
            metadata = json.loads((CASES / slug / "metadata.json").read_text())
            evidence = json.loads((CASES / slug / "evidence.json").read_text())
            urls = [metadata["source_url"], *[item["source_url"] for item in evidence["items"]]]
            for url in urls:
                host = (urlparse(url).hostname or "").lower()
                self.assertFalse(any(host == item or host.endswith("." + item) for item in prohibited), (slug, url))

    def test_seed_cases_do_not_bundle_source_binaries(self) -> None:
        forbidden = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".woff", ".woff2", ".ttf", ".otf"}
        for path in CASES.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), forbidden, str(path))

    def test_compact_manifest_matches_seed_and_stays_small(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["case_count"], 12)
        self.assertEqual(set(manifest["seed_cases"]), EXPECTED)
        self.assertFalse(manifest["remote_corpus_bundled"])
        self.assertLess(MANIFEST.stat().st_size, 100_000)
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn("## Visual thesis", text)
        self.assertEqual(
            manifest["progressive_disclosure"],
            ["manifest", "category-index", "ranked-summaries", "finalist-design-md", "validation-evidence"],
        )

    def test_offline_fallback_continues_with_lower_confidence(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        fallback = manifest["offline_fallback"]
        self.assertTrue(fallback["continue"])
        self.assertTrue(fallback["use_bundled_craft_guidance"])
        self.assertTrue(fallback["use_user_references"])
        self.assertTrue(fallback["state_remote_unavailability"])
        self.assertTrue(fallback["lower_confidence"])

    def test_catalog_generation_builds_progressive_routes(self) -> None:
        self.assertEqual(self.build_report["case_count"], 12)
        for root in (CORPUS / "generated", SITE / "generated-data"):
            index = json.loads((root / "catalog/index.json").read_text())
            self.assertEqual(index["case_count"], 12)
            self.assertEqual({case["slug"] for case in index["cases"]}, EXPECTED)
            for slug in EXPECTED:
                base = root / "cases" / slug
                self.assertTrue((base / "summary.json").is_file())
                self.assertTrue((base / "DESIGN.md").is_file())
                self.assertTrue((base / "evidence.json").is_file())
                self.assertTrue((base / "tokens.json").is_file())
            self.assertTrue((root / "catalog/categories/platforms/web.json").is_file())
            self.assertTrue((root / "catalog/categories/archetypes/developer-dense.json").is_file())

    def test_site_foundation_supports_search_filter_and_compare(self) -> None:
        html = (SITE / "index.html").read_text(encoding="utf-8")
        app = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="search"', html)
        self.assertIn('id="archetype"', html)
        self.assertIn('id="platform"', html)
        self.assertIn('id="comparison"', html)
        self.assertIn("selected.size<5", app)
        self.assertIn("generated-data/catalog/index.json", app)
        self.assertIn("fall back to its local manifest", app)

    def test_full_corpus_and_site_are_outside_distributed_package(self) -> None:
        spec = json.loads((ROOT / "bundle-spec.json").read_text())
        self.assertIn("corpus/cases", spec["forbidden_paths"])
        self.assertIn("site", spec["forbidden_paths"])
        self.assertIn("catalog-manifest/catalog.json", spec["required_shared_files"])
        self.assertIn("references/corpus-retrieval.md", spec["required_shared_files"])
        self.assertNotIn("corpus", spec["shared_directories"])
        self.assertNotIn("site", spec["shared_directories"])

    def test_source_policy_requires_original_analysis_and_publication_review(self) -> None:
        policy = (CORPUS / "source-policy/SOURCE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("original analysis", policy.lower())
        self.assertIn("do not bulk-copy refero", policy.lower())
        self.assertIn("publication states", policy.lower())
        for slug in EXPECTED:
            metadata = json.loads((CASES / slug / "metadata.json").read_text())
            review = json.loads((CASES / slug / "review.json").read_text())
            self.assertEqual(metadata["publication_status"], "review")
            self.assertEqual(review["status"], "review")
            self.assertTrue(review["originality_checked"])
            self.assertTrue(review["rights_checked"])
            self.assertTrue(review["assets_checked"])


if __name__ == "__main__":
    unittest.main()
