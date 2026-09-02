#!/usr/bin/env python3
"""Wave 11 Benchmark 2 tests for the public Evidence Exchange package contract."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
CASES = CORPUS / "cases"
BUILDER_PATH = CORPUS / "scripts/build_public_packages.py"
CATALOG_PATH = CORPUS / "scripts/build_catalog.py"
SEED_MANIFEST = ROOT / "core/catalog-manifest/catalog.json"
EXPECTED_ROUTES = {
    "index": "catalog/index.json",
    "category": "catalog/categories/{facet}/{value}.json",
    "case_summary": "cases/{slug}/summary.json",
    "case_analysis": "cases/{slug}/DESIGN.md",
    "case_evidence": "cases/{slug}/evidence.json",
    "case_source": "cases/{slug}/source.json",
    "case_download_manifest": "cases/{slug}/downloads/manifest.json",
    "case_download_readable": "cases/{slug}/downloads/case.md",
    "case_download_structured": "cases/{slug}/downloads/case.json",
}
LANES = {
    "brand-editorial-portfolio-marketing",
    "saas-dashboard-admin-productivity",
    "mobile",
    "commerce-media-content-heavy",
    "onboarding-forms-settings-flows",
    "design-systems-data-experimental",
}
spec = importlib.util.spec_from_file_location("wave11_public_packages", BUILDER_PATH)
public_packages = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(public_packages)
catalog_spec = importlib.util.spec_from_file_location("wave11_catalog_builder", CATALOG_PATH)
catalog_builder = importlib.util.module_from_spec(catalog_spec)
assert catalog_spec.loader
catalog_spec.loader.exec_module(catalog_builder)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\x00")
        digest.update(path.read_bytes())
    return digest.hexdigest()


class EvidenceExchangePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="design-evidence-exchange-")
        cls.temp_root = Path(cls.temp.name)
        cls.corpus_out = cls.temp_root / "corpus"
        cls.site_out = cls.temp_root / "site"
        cls.seed_before = file_sha256(SEED_MANIFEST)
        completed = subprocess.run(
            [
                sys.executable,
                str(CATALOG_PATH),
                "--visibility",
                "public",
                "--corpus-out",
                str(cls.corpus_out),
                "--site-out",
                str(cls.site_out),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        cls.report = json.loads(completed.stdout)
        cls.index = read_json(cls.site_out / "catalog/index.json")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_exactly_sixty_public_three_file_packages_match_the_closed_schema(self) -> None:
        self.assertEqual(self.report["case_count"], 60)
        package_dirs = sorted(self.site_out.glob("cases/*/downloads"))
        self.assertEqual(len(package_dirs), 60)
        schema = public_packages.load_json_strict(CORPUS / "schemas/public-case-package.schema.json")
        for package_dir in package_dirs:
            self.assertEqual({path.name for path in package_dir.iterdir()}, {"case.md", "case.json", "manifest.json"})
            model = public_packages.load_json_strict(package_dir / "case.json")
            public_packages._validate_schema(model, schema, package_dir.parent.name)
            self.assertEqual(model["publication_status"], "public")

    def test_non_public_and_invalid_cases_never_replace_or_create_a_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-public-filter-") as raw:
            temp = Path(raw)
            cases_root = temp / "cases"
            output_root = temp / "out"
            for status in ("review", "private", "blocked"):
                slug = f"{status}-case"
                case_dir = cases_root / slug
                shutil.copytree(CASES / "ibm-carbon", case_dir)
                metadata = read_json(case_dir / "metadata.json")
                metadata["slug"] = slug
                metadata["publication_status"] = status
                write_json(case_dir / "metadata.json", metadata)
                source = read_json(case_dir / "source.json")
                source["source_scope_id"] = slug
                write_json(case_dir / "source.json", source)
            report = public_packages.build_public_packages(cases_root, output_root)
            self.assertEqual(report["case_count"], 0)
            self.assertFalse((output_root / "cases").exists())

            invalid_case = cases_root / "invalid-case"
            shutil.copytree(CASES / "ibm-carbon", invalid_case)
            metadata = read_json(invalid_case / "metadata.json")
            metadata["slug"] = "invalid-case"
            metadata["unexpected_private_field"] = "must fail closed"
            write_json(invalid_case / "metadata.json", metadata)
            source = read_json(invalid_case / "source.json")
            source["source_scope_id"] = "invalid-case"
            write_json(invalid_case / "source.json", source)
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_public_packages(cases_root, output_root, slugs=["invalid-case"])
            self.assertFalse((output_root / "cases/invalid-case/downloads").exists())

            missing_case = cases_root / "missing-case"
            shutil.copytree(CASES / "ibm-carbon", missing_case)
            metadata = read_json(missing_case / "metadata.json")
            metadata["slug"] = "missing-case"
            write_json(missing_case / "metadata.json", metadata)
            source = read_json(missing_case / "source.json")
            source["source_scope_id"] = "missing-case"
            write_json(missing_case / "source.json", source)
            (missing_case / "coverage.json").unlink()
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_public_packages(cases_root, output_root, slugs=["missing-case"])
            self.assertFalse((output_root / "cases/missing-case/downloads").exists())

    def test_public_to_review_rebuild_removes_stale_public_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-public-transition-") as raw:
            temp = Path(raw)
            cases_root = temp / "cases"
            output_root = temp / "out"
            case_dir = cases_root / "transition-case"
            shutil.copytree(CASES / "ibm-carbon", case_dir)
            metadata = read_json(case_dir / "metadata.json")
            metadata["slug"] = "transition-case"
            write_json(case_dir / "metadata.json", metadata)
            source = read_json(case_dir / "source.json")
            source["source_scope_id"] = "transition-case"
            write_json(case_dir / "source.json", source)
            self.assertEqual(public_packages.build_public_packages(cases_root, output_root)["case_count"], 1)
            self.assertTrue((output_root / "cases/transition-case/downloads/manifest.json").is_file())

            metadata["publication_status"] = "review"
            write_json(case_dir / "metadata.json", metadata)
            self.assertEqual(public_packages.build_public_packages(cases_root, output_root)["case_count"], 0)
            self.assertFalse((output_root / "cases/transition-case/downloads/manifest.json").exists())

    def test_route_contract_only_adds_public_download_routes_and_seed_manifest_is_unchanged(self) -> None:
        self.assertEqual(self.index["route_contract"], EXPECTED_ROUTES)
        self.assertEqual(file_sha256(SEED_MANIFEST), self.seed_before)
        seed = read_json(SEED_MANIFEST)
        self.assertEqual(seed["case_count"], 12)

    def test_evidence_and_provenance_are_exact_allowlisted_projections(self) -> None:
        for case_dir in sorted(path for path in CASES.iterdir() if path.is_dir()):
            canonical_evidence = read_json(case_dir / "evidence.json")["items"]
            canonical_source = read_json(case_dir / "source.json")
            canonical_metadata = read_json(case_dir / "metadata.json")
            model = read_json(self.site_out / "cases" / case_dir.name / "downloads/case.json")
            self.assertEqual(len(model["evidence"]), len(canonical_evidence), case_dir.name)
            for projected, canonical in zip(model["evidence"], canonical_evidence):
                self.assertEqual(projected["id"], canonical["id"])
                self.assertEqual(projected["claim"], canonical["claim"])
                self.assertEqual(projected["truth_class"], canonical["class"])
                self.assertEqual(projected["source_url"], canonical["source_url"])
                self.assertEqual(projected["retrieved_at"], canonical_source["retrieved_at"])
                self.assertEqual(projected["captured_at"], canonical["captured_at"])
                self.assertEqual(projected["confidence"], canonical["confidence"])
                self.assertEqual(projected["qualification"], canonical["notes"])
                expected_locator = canonical["locator"] if canonical["locator"].startswith("URL: https://") else None
                self.assertEqual(projected["locator"], expected_locator)
            self.assertEqual(model["provenance"]["owner_url"], canonical_source["owner_url"])
            self.assertEqual(model["provenance"]["retrieved_at"], canonical_source["retrieved_at"])
            self.assertEqual(model["provenance"]["rights_basis"], canonical_metadata["rights_basis"])
            self.assertEqual(model["provenance"]["permitted_use_basis"], canonical_source["permitted_use_basis"])
            self.assertEqual(model["provenance"]["terms_or_license_url"], canonical_source["terms_or_license_url"])
            self.assertEqual(
                [item["statement"] for item in model["limitations"]],
                [public_packages._public_limitation(item) for item in canonical_source["limitations"]],
            )
            self.assertEqual(model["context"]["study_context"]["audience"]["truth_class"], "unknown")
            self.assertIn("No audience is recorded", model["context"]["study_context"]["audience"]["statement"])

    def test_public_models_contain_no_private_review_or_operational_fields(self) -> None:
        forbidden = {key.casefold() for key in public_packages.FORBIDDEN_KEYS}
        for path in self.site_out.glob("cases/*/downloads/case.json"):
            model = read_json(path)
            public_packages.scan_public_value(model)
            stack = [model]
            keys = set()
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    keys.update(key.casefold() for key in value)
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
            self.assertFalse(keys & forbidden, path)

    def test_operational_values_fail_closed_in_allowed_text_fields_and_generated_bytes(self) -> None:
        prohibited_values = (
            "response hash",
            "responseHash",
            "content_sha256",
            "contentSHA256",
            "HTTP status",
            "HTTPStatus",
            "redirect history",
            "redirectHistory",
            "archive URL",
            "archiveURL",
            "effective URL",
            "effectiveURL",
        )
        for prohibited_value in prohibited_values:
            with self.subTest(value=prohibited_value, surface="generated-bytes"):
                with self.assertRaises(public_packages.PublicPackageError):
                    public_packages.scan_generated_bytes(
                        {"case.md": f"Recorded {prohibited_value}.\n".encode("utf-8")}
                    )
            for surface in ("metadata", "evidence"):
                with self.subTest(value=prohibited_value, surface=surface):
                    with tempfile.TemporaryDirectory(prefix="design-package-operational-value-") as raw:
                        case_dir = Path(raw) / "ibm-carbon"
                        shutil.copytree(CASES / "ibm-carbon", case_dir)
                        if surface == "metadata":
                            metadata = read_json(case_dir / "metadata.json")
                            metadata["summary"] += f" Recorded {prohibited_value}."
                            write_json(case_dir / "metadata.json", metadata)
                        else:
                            evidence = read_json(case_dir / "evidence.json")
                            evidence["items"][0]["claim"] += f" Recorded {prohibited_value}."
                            write_json(case_dir / "evidence.json", evidence)
                        with self.assertRaises(public_packages.PublicPackageError):
                            public_packages.build_public_model(case_dir)

    def test_markdown_and_json_share_one_complete_semantic_model(self) -> None:
        for slug in ("ibm-carbon", "github-primer", "wise-design"):
            model = public_packages.build_public_model(CASES / slug)
            markdown, trace = public_packages.render_markdown(model)
            public_packages.assert_semantic_parity(model, trace)
            package = self.site_out / "cases" / slug / "downloads"
            manifest = read_json(package / "manifest.json")
            self.assertEqual(read_json(package / "case.json"), model)
            self.assertEqual((package / "case.md").read_text(encoding="utf-8"), markdown)
            self.assertEqual(manifest["model_sha256"], public_packages.model_sha256(model))
            self.assertEqual(
                {(item["path"], item["value_sha256"]) for item in trace},
                {(item["path"], item["value_sha256"]) for item in public_packages.semantic_leaf_bindings(model)},
            )

    def test_semantic_parity_rejects_missing_changed_extra_or_wrong_values(self) -> None:
        model = public_packages.build_public_model(CASES / "ibm-carbon")
        _, trace = public_packages.render_markdown(model)
        with self.assertRaises(public_packages.PublicPackageError):
            public_packages.assert_semantic_parity(model, trace[:-1])
        changed = [dict(item) for item in trace]
        changed[-1]["path"] = "$.unknowns[0].invented"
        with self.assertRaises(public_packages.PublicPackageError):
            public_packages.assert_semantic_parity(model, changed)
        with self.assertRaises(public_packages.PublicPackageError):
            public_packages.assert_semantic_parity(model, trace + [{"path": "$.extra", "value_sha256": "0" * 64}])

        changed_model = json.loads(json.dumps(model))
        changed_model["evidence"][0]["claim"] = "A replacement claim with enough length to remain structurally valid but different meaning."
        with self.assertRaises(public_packages.PublicPackageError):
            public_packages.assert_semantic_parity(changed_model, trace)
        renderer = public_packages.MarkdownRenderer(model)
        with self.assertRaises(public_packages.PublicPackageError):
            renderer.value("$.name", "Wrong name")

    def test_manifest_hash_size_filename_and_model_bindings_are_exact(self) -> None:
        for package in self.site_out.glob("cases/*/downloads"):
            manifest = read_json(package / "manifest.json")
            self.assertEqual([item["format"] for item in manifest["files"]], ["readable", "structured"])
            for item in manifest["files"]:
                path = package / item["route"]
                self.assertEqual(item["byte_size"], len(path.read_bytes()))
                self.assertEqual(item["sha256"], file_sha256(path))
                self.assertEqual(item["model_sha256"], manifest["model_sha256"])
                self.assertTrue(item["download_filename"].startswith(manifest["slug"] + "-design-reference."))
            self.assertNotIn("generated_at", manifest)
            self.assertNotIn("output_root", manifest)

    def test_package_verifier_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-tamper-") as raw:
            destination = Path(raw) / "downloads"
            model = public_packages.build_public_model(CASES / "ibm-carbon")
            public_packages.build_case_package(CASES / "ibm-carbon", destination, output_root=Path(raw))
            with (destination / "case.md").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.verify_package_tree(destination, model, output_root=Path(raw))

    def test_two_clean_catalog_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-determinism-") as raw:
            temp = Path(raw)
            results = []
            for suffix in ("a", "b"):
                corpus_out = temp / f"corpus-{suffix}"
                site_out = temp / f"site-{suffix}"
                subprocess.run(
                    [sys.executable, str(CATALOG_PATH), "--visibility", "public", "--corpus-out", str(corpus_out), "--site-out", str(site_out)],
                    cwd=ROOT,
                    check=True,
                    text=True,
                    capture_output=True,
                )
                results.append((tree_digest(corpus_out), tree_digest(site_out)))
            self.assertEqual(results[0], results[1])

    def test_failed_rebuild_preserves_the_last_good_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-rollback-") as raw:
            temp = Path(raw)
            case_dir = temp / "ibm-carbon"
            destination = temp / "downloads"
            shutil.copytree(CASES / "ibm-carbon", case_dir)
            public_packages.build_case_package(case_dir, destination, output_root=temp)
            before = tree_digest(destination)
            metadata = read_json(case_dir / "metadata.json")
            metadata["unexpected"] = "must not replace the last good package"
            write_json(case_dir / "metadata.json", metadata)
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_case_package(case_dir, destination, output_root=temp)
            self.assertEqual(tree_digest(destination), before)

    def test_integrated_mid_build_failure_preserves_both_complete_catalog_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-catalog-rollback-") as raw:
            temp = Path(raw)
            corpus_out = temp / "corpus"
            site_out = temp / "site"
            catalog_builder.build(visibility="public", corpus_out=corpus_out, site_out=site_out)
            before = (tree_digest(corpus_out), tree_digest(site_out))
            original = catalog_builder.public_packages.build_case_package
            calls = {"count": 0}

            def fail_on_second_package(*args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise public_packages.PublicPackageError("injected package-stage failure")
                return original(*args, **kwargs)

            catalog_builder.public_packages.build_case_package = fail_on_second_package
            try:
                with self.assertRaises(public_packages.PublicPackageError):
                    catalog_builder.build(visibility="public", corpus_out=corpus_out, site_out=site_out)
            finally:
                catalog_builder.public_packages.build_case_package = original
            self.assertEqual((tree_digest(corpus_out), tree_digest(site_out)), before)
            self.assertEqual(len(list(site_out.glob("cases/*/downloads/manifest.json"))), 60)

    def test_unsafe_slugs_and_symlink_destinations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-paths-") as raw:
            temp = Path(raw)
            unsafe = temp / "bad%2fslug"
            shutil.copytree(CASES / "ibm-carbon", unsafe)
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_public_model(unsafe)

            destination = temp / "downloads"
            target = temp / "target"
            target.mkdir()
            os.symlink(target, destination)
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_case_package(CASES / "ibm-carbon", destination, output_root=temp)

            output_root = temp / "output"
            output_root.mkdir()
            escape_target = temp / "escape-target"
            escape_target.mkdir()
            os.symlink(escape_target, output_root / "cases")
            nested_destination = output_root / "cases/ibm-carbon/downloads"
            with self.assertRaises(public_packages.PublicPackageError):
                public_packages.build_case_package(CASES / "ibm-carbon", nested_destination, output_root=output_root)
            self.assertFalse((escape_target / "ibm-carbon/downloads").exists())

    def test_unicode_and_line_endings_normalize_deterministically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-unicode-") as raw:
            temp = Path(raw)
            case_dir = temp / "ibm-carbon"
            shutil.copytree(CASES / "ibm-carbon", case_dir)
            metadata = read_json(case_dir / "metadata.json")
            metadata["name"] = "Cafe\u0301 Carbon"
            metadata["summary"] = metadata["summary"].replace(" system ", "\r\nsystem ", 1)
            write_json(case_dir / "metadata.json", metadata)
            model = public_packages.build_public_model(case_dir)
            self.assertEqual(model["name"], "Caf\u00e9 Carbon")
            self.assertEqual(unicodedata.normalize("NFC", model["name"]), model["name"])
            files = public_packages.package_bytes(model)
            self.assertTrue(all(b"\r" not in data for data in files.values()))
            self.assertEqual(files, public_packages.package_bytes(model))

    def test_strict_loader_rejects_duplicate_nonfinite_bidi_and_surrogate_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-json-") as raw:
            path = Path(raw) / "value.json"
            for payload in (
                b'{"x":1,"x":2}',
                b'{"x":NaN}',
                b'{"x":Infinity}',
                b'{"x":"\\u202eunsafe"}',
                b'{"x":"\\ud800"}',
            ):
                path.write_bytes(payload)
                with self.assertRaises(public_packages.PublicPackageError):
                    public_packages.load_json_strict(path)

    def test_hostile_prose_cannot_inject_markdown_or_html(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-package-markdown-") as raw:
            case_dir = Path(raw) / "ibm-carbon"
            shutil.copytree(CASES / "ibm-carbon", case_dir)
            metadata = read_json(case_dir / "metadata.json")
            metadata["name"] = "# <script>alert(1)</script> [click](https://evil.example) ![image](https://evil.example/x)"
            metadata["summary"] = "First line\n## injected heading\n| injected | table | " + metadata["summary"]
            write_json(case_dir / "metadata.json", metadata)
            model = public_packages.build_public_model(case_dir)
            markdown, _ = public_packages.render_markdown(model)
            self.assertNotIn("<script>", markdown)
            self.assertNotIn("[click](https://evil.example)", markdown)
            self.assertNotIn("![image]", markdown)
            self.assertNotIn("\n## injected heading", markdown)
            self.assertNotIn("\n| injected | table |", markdown)

    def test_generated_tree_has_no_symlinks_binary_data_uri_or_refero_content(self) -> None:
        for path in self.site_out.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            if path.is_file():
                data = path.read_bytes()
                self.assertNotIn(b"\x00", data, path)
                text = data.decode("utf-8").lower()
                self.assertNotIn("data:", text, path)
                self.assertNotIn("refero.design", text, path)
                if "/downloads/" in path.as_posix():
                    self.assertNotIn("response hash", text, path)

    def test_readable_packages_preserve_urls_and_remove_misleading_repetition(self) -> None:
        for slug in ("salesforce-slds-2", "sap-fiori"):
            canonical = read_json(CASES / slug / "evidence.json")
            markdown = (self.site_out / "cases" / slug / "downloads/case.md").read_text(encoding="utf-8")
            for item in canonical["items"]:
                self.assertIn(item["source_url"], markdown)
                escaped = item["source_url"].replace("_", "\\_").replace("&", "&amp;")
                if escaped != item["source_url"]:
                    self.assertNotIn(escaped, markdown)

        model = read_json(self.site_out / "cases/ibm-carbon/downloads/case.json")
        markdown = (self.site_out / "cases/ibm-carbon/downloads/case.md").read_text(encoding="utf-8")
        self.assertEqual(markdown.count(model["context"]["study_context"]["summary"]), 1)
        self.assertIn("**Color and surfaces:**", markdown)
        self.assertIn("**Components and interaction:**", markdown)
        self.assertIn("**Audience truth class:** unknown", markdown)
        self.assertIn("**Truth classes:** inferred, recommended", markdown)
        self.assertNotIn("approved public projection", markdown.lower())
        self.assertNotIn("cleared for public distribution", markdown.lower())

    def test_one_package_from_each_lane_is_human_and_machine_readable(self) -> None:
        representative = {"design-systems-data-experimental": "ibm-carbon"}
        for case_dir in sorted(path for path in CASES.iterdir() if path.is_dir()):
            metadata = read_json(case_dir / "metadata.json")
            representative.setdefault(metadata["corpus_lane"], case_dir.name)
        self.assertEqual(set(representative), LANES)
        for lane, slug in representative.items():
            package = self.site_out / "cases" / slug / "downloads"
            markdown = (package / "case.md").read_text(encoding="utf-8")
            model = read_json(package / "case.json")
            self.assertEqual(model["context"]["study_context"]["corpus_lane"], lane)
            for heading in (
                "## Context",
                "## Adaptation intent",
                "## Recommended uses and limits",
                "## Evidence records",
                "## Source limitations",
                "## Unresolved unknowns",
            ):
                self.assertIn(heading, markdown, slug)


if __name__ == "__main__":
    unittest.main()
