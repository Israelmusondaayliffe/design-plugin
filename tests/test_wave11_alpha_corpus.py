#!/usr/bin/env python3
"""Wave 11 acceptance tests for the reviewed 60-case alpha corpus."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
CASES = CORPUS / "cases"
VALIDATOR_PATH = CORPUS / "scripts/validate_corpus.py"
BUILD_PATH = CORPUS / "scripts/build_catalog.py"
SOURCE_AUDIT_PATH = CORPUS / "scripts/audit_sources.py"
ORIGINALITY_AUDIT_PATH = CORPUS / "scripts/audit_originality.py"
ALPHA_LANES = {
    "brand-editorial-portfolio-marketing": 15,
    "saas-dashboard-admin-productivity": 15,
    "mobile": 10,
    "commerce-media-content-heavy": 8,
    "onboarding-forms-settings-flows": 7,
    "design-systems-data-experimental": 5,
}
spec = importlib.util.spec_from_file_location("wave11_validate_corpus", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(validator)
source_spec = importlib.util.spec_from_file_location("wave11_audit_sources", SOURCE_AUDIT_PATH)
source_audit = importlib.util.module_from_spec(source_spec)
assert source_spec.loader
source_spec.loader.exec_module(source_audit)
originality_spec = importlib.util.spec_from_file_location("wave11_audit_originality", ORIGINALITY_AUDIT_PATH)
originality_audit = importlib.util.module_from_spec(originality_spec)
assert originality_spec.loader
originality_spec.loader.exec_module(originality_audit)
build_spec = importlib.util.spec_from_file_location("wave11_build_catalog", BUILD_PATH)
catalog_builder = importlib.util.module_from_spec(build_spec)
assert build_spec.loader
build_spec.loader.exec_module(catalog_builder)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Wave11AlphaCorpusTests(unittest.TestCase):
    def test_accepted_validator_requires_sixty_independently_reviewed_cases(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["case_count"], 60)
        self.assertEqual(report["lane_counts"], ALPHA_LANES)
        self.assertEqual(report["review_mode"], "accepted-only")

    def test_exact_single_count_lane_allocation(self) -> None:
        metadata = [read_json(path / "metadata.json") for path in CASES.iterdir() if path.is_dir()]
        self.assertEqual(len(metadata), 60)
        self.assertEqual(Counter(item["corpus_lane"] for item in metadata), Counter(ALPHA_LANES))
        self.assertEqual(len({item["slug"] for item in metadata}), 60)

    def test_source_health_and_diversity_receipt(self) -> None:
        report = read_json(ROOT / "review/wave-11-source-health.json")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["case_count"], 60)
        self.assertEqual(report["failing_url_count"], 0)
        self.assertEqual(report["unique_url_count"], report["passing_url_count"])
        self.assertEqual(report["hash_kind"], "canonical-source-identity-v1")
        self.assertEqual(report["stored_hash_mismatch_count"], 0)
        self.assertEqual(report["canonical_effective_collision_count"], 0)
        self.assertEqual(report["locator_mismatch_count"], 0)
        binding, case_bindings = source_audit.corpus_binding({
            path.name: {"case_dir": path} for path in CASES.iterdir() if path.is_dir()
        })
        self.assertEqual(report["corpus_binding_sha256"], binding)
        self.assertEqual(report["case_bindings"], case_bindings)
        urls = []
        domains = set()
        for case_dir in (path for path in CASES.iterdir() if path.is_dir()):
            metadata = read_json(case_dir / "metadata.json")
            source = read_json(case_dir / "source.json")
            urls.append(metadata["source_url"])
            domains.add(urlparse(metadata["source_url"]).hostname)
            self.assertNotEqual(source["content_sha256"], "0" * 64)
            self.assertTrue(200 <= source["http_status"] <= 399)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertGreaterEqual(len(domains), 50)

    def test_source_audit_stabilizes_experiment_headings_and_detects_redirect_aliases(self) -> None:
        first = b"<html><head><title>Stable owner page</title></head><body><h1>Core</h1></body></html>"
        second = b"<html><head><title>Stable owner page</title></head><body><h1>Core</h1><h2>Experimental CTA</h2></body></html>"
        url = "https://owner.example/design"
        self.assertEqual(
            source_audit.canonical_source_identity(first, url),
            source_audit.canonical_source_identity(second, url),
        )
        collisions = source_audit.effective_url_collisions({
            "https://owner.example/a": {"effective_url": "https://owner.example/design"},
            "https://owner.example/b": {"effective_url": "https://owner.example/design"},
        })
        self.assertEqual(len(collisions), 1)
        self.assertEqual(len(collisions[0]["requested_urls"]), 2)

    def test_source_identity_does_not_change_when_one_request_uses_two_redirect_targets(self) -> None:
        payload = b"<html><head><title>Observable Plot</title></head><body><h1>Plot</h1></body></html>"
        requested = "https://observablehq.com/plot/"
        first_effective = "https://observablehq.com/plot/"
        second_effective = "https://observablehq.github.io/plot/"
        self.assertNotEqual(first_effective, second_effective)
        first = source_audit.canonical_source_identity(payload, requested)
        second = source_audit.canonical_source_identity(payload, requested)
        self.assertEqual(first, second)

    def test_source_locator_requires_exact_url_or_fetched_text(self) -> None:
        url = "https://owner.example/design"
        self.assertTrue(source_audit.locator_matches(f"URL: {url}", url, "unrelated visible text"))
        self.assertTrue(source_audit.locator_matches("Component guidance", url, "overview component guidance examples"))
        self.assertFalse(source_audit.locator_matches("Invented section", url, "overview component guidance examples"))

    def test_originality_audit_passes_without_exempting_narrative(self) -> None:
        report = read_json(ROOT / "review/wave-11-originality-audit.json")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["case_count"], 60)
        self.assertEqual(report["rules"]["banned_phrase_count"], 0)
        self.assertEqual(report["rules"]["mechanical_prose_finding_count"], 0)
        self.assertEqual(report["rules"]["degenerate_normalization_count"], 0)
        self.assertEqual(report["rules"]["repeated_eight_word_phrase_count"], 0)
        self.assertEqual(report["rules"]["repeated_narrative_sentence_count"], 0)
        self.assertEqual(report["rules"]["entity_normalized_template_count"], 0)
        self.assertEqual(report["rules"]["dominant_structure_profile_count"], 0)
        self.assertEqual(report["rules"]["uniform_optional_heading_count"], 0)
        binding, case_bindings = originality_audit.corpus_binding(sorted(path for path in CASES.iterdir() if path.is_dir()))
        self.assertEqual(report["corpus_binding_sha256"], binding)
        self.assertEqual(report["case_bindings"], case_bindings)

    def test_review_ledgers_bind_exact_artifacts_to_an_independent_reviewer(self) -> None:
        for case_dir in (path for path in CASES.iterdir() if path.is_dir()):
            review = read_json(case_dir / "review.json")
            self.assertEqual(review["result"], "pass", case_dir.name)
            self.assertTrue(review["independent"], case_dir.name)
            self.assertNotEqual(review["author"], review["reviewer"], case_dir.name)
            self.assertEqual(set(review["artifact_sha256"]), validator.HASHED_FILES, case_dir.name)
            for name, recorded in review["artifact_sha256"].items():
                self.assertEqual(recorded, hashlib.sha256((case_dir / name).read_bytes()).hexdigest(), f"{case_dir.name}/{name}")

    def test_local_and_public_catalog_visibility_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-wave11-catalog-") as temp_dir:
            temp = Path(temp_dir)
            local_corpus = temp / "local-corpus"
            local_site = temp / "local-site"
            public_corpus = temp / "public-corpus"
            public_site = temp / "public-site"
            subprocess.run(
                [sys.executable, str(BUILD_PATH), "--visibility", "local", "--allow-pending-review", "--corpus-out", str(local_corpus), "--site-out", str(local_site)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(BUILD_PATH), "--visibility", "public", "--allow-pending-review", "--corpus-out", str(public_corpus), "--site-out", str(public_site)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(read_json(local_site / "catalog/index.json")["case_count"], 60)
            public_count = sum(
                read_json(path / "metadata.json")["publication_status"] == "public"
                for path in CASES.iterdir() if path.is_dir()
            )
            self.assertEqual(read_json(public_site / "catalog/index.json")["case_count"], public_count)
            self.assertEqual(len(list((public_site / "cases").glob("*"))), public_count)
            self.assertFalse(catalog_builder.include_case("review", "public"))
            self.assertTrue(catalog_builder.include_case("public", "public"))
            self.assertTrue(catalog_builder.include_case("review", "local"))

    def test_catalog_generation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-wave11-determinism-") as temp_dir:
            temp = Path(temp_dir)
            hashes = []
            for suffix in ("a", "b"):
                corpus_out = temp / f"corpus-{suffix}"
                site_out = temp / f"site-{suffix}"
                subprocess.run(
                    [sys.executable, str(BUILD_PATH), "--allow-pending-review", "--corpus-out", str(corpus_out), "--site-out", str(site_out)],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                hashes.append((tree_hash(corpus_out), tree_hash(site_out)))
            self.assertEqual(hashes[0], hashes[1])

    def test_validator_rejects_bad_enum_placeholder_hash_and_asset_uri(self) -> None:
        taxonomy = read_json(CORPUS / "taxonomy/taxonomy.json")
        with tempfile.TemporaryDirectory(prefix="design-wave11-negative-") as temp_dir:
            case_dir = Path(temp_dir) / "vercel-geist"
            shutil.copytree(CASES / "vercel-geist", case_dir)

            metadata = read_json(case_dir / "metadata.json")
            metadata["density"] = "invented-density"
            (case_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_metadata(case_dir, taxonomy)

            shutil.copy2(CASES / "vercel-geist/metadata.json", case_dir / "metadata.json")
            metadata = read_json(case_dir / "metadata.json")
            source = read_json(case_dir / "source.json")
            source["content_sha256"] = "0" * 64
            (case_dir / "source.json").write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_source(case_dir, metadata)

            preview = read_json(case_dir / "preview-spec.json")
            preview["pattern"] = "A data:image/png;base64 payload embedded in an otherwise descriptive preview pattern."
            (case_dir / "preview-spec.json").write_text(json.dumps(preview), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_preview(case_dir)

    def test_validator_rejects_generic_locators_class_overstatement_and_unsupported_lane_fit(self) -> None:
        taxonomy = read_json(CORPUS / "taxonomy/taxonomy.json")
        with tempfile.TemporaryDirectory(prefix="design-wave11-evidence-negative-") as temp_dir:
            case_dir = Path(temp_dir) / "observable-plot"
            shutil.copytree(CASES / "observable-plot", case_dir)
            metadata = read_json(case_dir / "metadata.json")

            evidence = read_json(case_dir / "evidence.json")
            evidence["items"][1]["locator"] = "Public overview"
            (case_dir / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_evidence(case_dir, metadata)

            shutil.copy2(CASES / "observable-plot/evidence.json", case_dir / "evidence.json")
            records = validator.validate_evidence(case_dir, metadata)
            tokens = read_json(case_dir / "tokens.json")
            tokens["tokens"][0]["evidence_class"] = "observed"
            (case_dir / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_tokens(case_dir, records)

            coverage = read_json(case_dir / "coverage.json")
            coverage["lane_fit"] = "This generic statement removes the required primary suitable use and case relationship."
            (case_dir / "coverage.json").write_text(json.dumps(coverage), encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_coverage(case_dir, metadata)

    def test_review_hashes_reject_post_review_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-wave11-review-negative-") as temp_dir:
            case_dir = Path(temp_dir) / "vercel-geist"
            shutil.copytree(CASES / "vercel-geist", case_dir)
            metadata = read_json(case_dir / "metadata.json")
            design = case_dir / "DESIGN.md"
            design.write_text(design.read_text(encoding="utf-8") + "\nmutation\n", encoding="utf-8")
            with self.assertRaises(validator.CorpusError):
                validator.validate_review(case_dir, metadata, False)


if __name__ == "__main__":
    unittest.main()
