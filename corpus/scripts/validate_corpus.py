#!/usr/bin/env python3
"""Validate the Wave 11 Design Knowledge Corpus with the standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

CORPUS_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from json_schema_subset import SchemaViolation, validate_schema

CASES_ROOT = CORPUS_ROOT / "cases"
TAXONOMY = CORPUS_ROOT / "taxonomy/taxonomy.json"
SCHEMAS_ROOT = CORPUS_ROOT / "schemas"
SCHEMA_FILES = {
    "metadata": "case.schema.json",
    "evidence": "evidence.schema.json",
    "tokens": "tokens.schema.json",
    "coverage": "coverage.schema.json",
    "preview": "preview.schema.json",
    "source": "source.schema.json",
    "review": "review.schema.json",
}
_SCHEMA_CACHE: dict[str, dict] = {}
REQUIRED_FILES = {
    "DESIGN.md", "metadata.json", "evidence.json", "tokens.json", "coverage.json",
    "preview-spec.json", "source.json", "source-notes.md", "review.json",
}
HASHED_FILES = REQUIRED_FILES - {"review.json"}
TRUTH = {"observed", "measured", "inferred", "estimated", "recommended", "unknown"}
BANNED_LOCATORS = {
    "Public overview",
    "Foundations, patterns, or visible system relationships",
    "Platform and workflow examples",
    "Cross-source design synthesis",
}
TOKEN_SOURCE_CLASSES = {
    "observed": {"observed", "measured"},
    "measured": {"measured"},
    "inferred": {"observed", "measured", "inferred"},
    "estimated": {"observed", "measured", "inferred", "estimated"},
    "recommended": {"observed", "measured", "inferred", "estimated", "recommended"},
    "unknown": TRUTH,
}
CONFIDENCE = {"low", "medium", "high"}
PUBLICATION = {"private", "review", "public", "blocked"}
SOURCE_KINDS = {"public-design-system", "public-website", "open-source", "user-owned", "client-authorized", "original"}
RIGHTS_BASES = {"original-analysis-public-source", "open-source", "user-authorized", "client-authorized", "original"}
ALPHA_LANES = {
    "brand-editorial-portfolio-marketing": 15,
    "saas-dashboard-admin-productivity": 15,
    "mobile": 10,
    "commerce-media-content-heavy": 8,
    "onboarding-forms-settings-flows": 7,
    "design-systems-data-experimental": 5,
}
BANNED_SOURCE_DOMAINS = {"refero.design", "styles.refero.design", "api.refero.design"}
BANNED_CASE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".pdf", ".woff", ".woff2",
    ".ttf", ".otf", ".mp4", ".webm", ".mov", ".zip", ".tar", ".gz", ".7z",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
RADIUS_RE = re.compile(r"^[0-9]+px$")


class CorpusError(RuntimeError):
    """Raised when a canonical corpus record violates the alpha contract."""


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CorpusError(f"missing {path.relative_to(CORPUS_ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON {path.relative_to(CORPUS_ROOT)}: {exc}") from exc


def require_keys(data: dict, required: set[str], label: str, *, exact: bool = False) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise CorpusError(f"{label}: missing fields {missing}")
    if exact:
        extra = sorted(set(data) - required)
        if extra:
            raise CorpusError(f"{label}: unexpected fields {extra}")


def require_schema(data, schema_name: str, label: str) -> None:
    if schema_name not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[schema_name] = read_json(SCHEMAS_ROOT / SCHEMA_FILES[schema_name])
    try:
        validate_schema(data, _SCHEMA_CACHE[schema_name], label)
    except SchemaViolation as exc:
        raise CorpusError(str(exc)) from exc


def require_text(value, label: str, minimum: int = 1) -> None:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise CorpusError(f"{label} must contain at least {minimum} characters")


def require_string_list(value, label: str, minimum: int = 1, *, unique: bool = False) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        raise CorpusError(f"{label} must contain at least {minimum} items")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise CorpusError(f"{label} contains an empty or non-string item")
    if unique and len(value) != len(set(value)):
        raise CorpusError(f"{label} contains duplicate items")


def require_date(value, label: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CorpusError(f"{label} must be an ISO date") from exc
    if parsed > date.today():
        raise CorpusError(f"{label} cannot be in the future")


def require_https(value: str, label: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise CorpusError(f"{label} must be an https URL")
    host = (parsed.hostname or "").lower()
    if host in BANNED_SOURCE_DOMAINS or any(host.endswith("." + domain) for domain in BANNED_SOURCE_DOMAINS):
        raise CorpusError(f"{label} uses a prohibited corpus source domain: {host}")


def require_taxonomy(values, facet: str, taxonomy: dict, slug: str) -> None:
    bad = sorted(set(values) - set(taxonomy["facets"][facet]))
    if bad:
        raise CorpusError(f"{slug}: invalid {facet}: {bad}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_metadata(case_dir: Path, taxonomy: dict) -> dict:
    slug = case_dir.name
    required = {
        "schema_version", "slug", "name", "source_name", "source_url", "source_kind", "studied_at",
        "corpus_lane", "platforms", "product_types", "industries", "archetypes", "typography_character",
        "media_strategy", "layout_behavior", "journey", "brand_maturity", "accessibility_maturity",
        "density", "color_modes", "interaction_complexity", "evidence_quality", "publication_status",
        "rights_basis", "summary", "signature_traits", "best_for", "avoid_for",
    }
    meta = read_json(case_dir / "metadata.json")
    require_schema(meta, "metadata", f"{slug} metadata")
    require_keys(meta, required, f"{slug} metadata", exact=True)
    if meta["schema_version"] != "1.0" or meta["slug"] != slug or not SLUG_RE.fullmatch(slug):
        raise CorpusError(f"{slug}: metadata schema or slug mismatch")
    for key in ("name", "source_name"):
        require_text(meta[key], f"{slug} metadata {key}")
    require_https(meta["source_url"], f"{slug} source_url")
    require_date(meta["studied_at"], f"{slug} studied_at")
    if meta["source_kind"] not in SOURCE_KINDS:
        raise CorpusError(f"{slug}: invalid source_kind")
    if meta["rights_basis"] not in RIGHTS_BASES:
        raise CorpusError(f"{slug}: invalid rights_basis")
    if meta["publication_status"] not in PUBLICATION:
        raise CorpusError(f"{slug}: invalid publication_status")
    for facet in ("platforms", "product_types", "industries", "archetypes", "journey", "color_modes"):
        require_string_list(meta[facet], f"{slug} metadata {facet}", unique=True)
        require_taxonomy(meta[facet], facet, taxonomy, slug)
    for facet in (
        "corpus_lane", "typography_character", "media_strategy", "layout_behavior", "brand_maturity",
        "accessibility_maturity", "density", "interaction_complexity", "evidence_quality",
    ):
        require_taxonomy([meta[facet]], facet, taxonomy, slug)
    require_text(meta["summary"], f"{slug} summary", 40)
    require_string_list(meta["signature_traits"], f"{slug} signature_traits", 3, unique=True)
    require_string_list(meta["best_for"], f"{slug} best_for", 2, unique=True)
    require_string_list(meta["avoid_for"], f"{slug} avoid_for", 1, unique=True)
    return meta


def validate_evidence(case_dir: Path, meta: dict) -> dict[str, dict]:
    slug = case_dir.name
    evidence = read_json(case_dir / "evidence.json")
    require_schema(evidence, "evidence", f"{slug} evidence")
    require_keys(evidence, {"schema_version", "items"}, f"{slug} evidence", exact=True)
    items = evidence["items"]
    if evidence["schema_version"] != "1.0" or not isinstance(items, list) or len(items) < 4:
        raise CorpusError(f"{slug}: evidence requires schema 1.0 and at least 4 items")
    ids: set[str] = set()
    records: dict[str, dict] = {}
    required = {"id", "claim", "class", "confidence", "source_url", "locator", "captured_at", "notes"}
    for item in items:
        require_keys(item, required, f"{slug} evidence item", exact=True)
        evidence_id = item["id"]
        if not isinstance(evidence_id, str) or not re.fullmatch(r"E[0-9]{2,}", evidence_id):
            raise CorpusError(f"{slug}: invalid evidence id {evidence_id!r}")
        if evidence_id in ids:
            raise CorpusError(f"{slug}: duplicate evidence id {evidence_id}")
        ids.add(evidence_id)
        records[evidence_id] = item
        require_text(item["claim"], f"{slug} evidence {evidence_id} claim", 30)
        require_text(item["locator"], f"{slug} evidence {evidence_id} locator", 3)
        if item["locator"] in BANNED_LOCATORS:
            raise CorpusError(f"{slug}: evidence {evidence_id} uses a generic locator")
        require_text(item["notes"], f"{slug} evidence {evidence_id} notes", 3)
        require_date(item["captured_at"], f"{slug} evidence {evidence_id} captured_at")
        if item["class"] not in TRUTH:
            raise CorpusError(f"{slug}: invalid evidence class")
        if item["class"] in {"observed", "measured"} and any(
            phrase in item["notes"].lower()
            for phrase in ("original corpus interpretation", "source-bounded analyst interpretation", "not an owner claim")
        ):
            raise CorpusError(f"{slug}: direct evidence {evidence_id} is mislabeled as interpretation")
        if item["confidence"] not in CONFIDENCE:
            raise CorpusError(f"{slug}: invalid evidence confidence")
        require_https(item["source_url"], f"{slug} evidence {evidence_id} source_url")
    distinct_urls = {item["source_url"] for item in items}
    if any("cross-source" in f"{item['claim']} {item['locator']}".lower() for item in items) and len(distinct_urls) < 2:
        raise CorpusError(f"{slug}: cross-source evidence requires at least two source URLs")
    return records


def validate_tokens(case_dir: Path, evidence_records: dict[str, dict]) -> None:
    slug = case_dir.name
    tokens = read_json(case_dir / "tokens.json")
    require_schema(tokens, "tokens", f"{slug} tokens")
    require_keys(tokens, {"schema_version", "tokens"}, f"{slug} tokens", exact=True)
    if tokens["schema_version"] != "1.0" or not isinstance(tokens["tokens"], list) or len(tokens["tokens"]) < 4:
        raise CorpusError(f"{slug}: tokens require schema 1.0 and at least 4 normalized roles")
    required = {"name", "category", "role", "value", "exact", "evidence_class", "source_evidence_ids", "notes"}
    names = set()
    for token in tokens["tokens"]:
        require_keys(token, required, f"{slug} token", exact=True)
        require_text(token["name"], f"{slug} token name", 3)
        require_text(token["category"], f"{slug} token category", 3)
        require_text(token["role"], f"{slug} token role", 20)
        require_text(token["notes"], f"{slug} token notes", 3)
        if token["name"] in names:
            raise CorpusError(f"{slug}: duplicate token name {token['name']}")
        names.add(token["name"])
        if token["evidence_class"] not in TRUTH:
            raise CorpusError(f"{slug}: invalid token evidence class")
        if not isinstance(token["exact"], bool):
            raise CorpusError(f"{slug}: token exact flag must be boolean")
        if token["exact"]:
            if token["value"] is None or token["evidence_class"] not in {"observed", "measured"}:
                raise CorpusError(f"{slug}: exact token values require a value and observed or measured evidence")
        elif token["value"] is not None:
            raise CorpusError(f"{slug}: non-exact normalized token roles cannot carry source values")
        require_string_list(token["source_evidence_ids"], f"{slug} token evidence ids", unique=True)
        unknown = sorted(set(token["source_evidence_ids"]) - set(evidence_records))
        if unknown:
            raise CorpusError(f"{slug}: token references unknown evidence {unknown}")
        disallowed = sorted(
            evidence_id for evidence_id in token["source_evidence_ids"]
            if evidence_records[evidence_id]["class"] not in TOKEN_SOURCE_CLASSES[token["evidence_class"]]
        )
        if disallowed:
            raise CorpusError(
                f"{slug}: token {token['name']} overstates linked evidence classes for {disallowed}"
            )


def validate_coverage(case_dir: Path, meta: dict) -> None:
    slug = case_dir.name
    required = {
        "schema_version", "source", "study_date", "platform", "category", "lane_fit", "industry", "archetype",
        "visual_thesis", "brand_posture", "layout", "grid", "container", "responsive_behavior", "typography",
        "color", "spacing", "surfaces", "components", "states", "navigation", "forms", "flows", "motion",
        "interaction", "imagery", "accessibility", "signature_moves", "failure_modes", "suitable_uses",
        "unsuitable_uses", "confidence", "unknowns",
    }
    coverage = read_json(case_dir / "coverage.json")
    require_schema(coverage, "coverage", f"{slug} coverage")
    require_keys(coverage, required, f"{slug} coverage", exact=True)
    if coverage["schema_version"] != "1.0":
        raise CorpusError(f"{slug}: coverage schema mismatch")
    if coverage["source"] != meta["source_url"] or coverage["study_date"] != meta["studied_at"]:
        raise CorpusError(f"{slug}: coverage source or study date differs from metadata")
    if coverage["category"] != meta["corpus_lane"]:
        raise CorpusError(f"{slug}: coverage category differs from metadata")
    if meta["best_for"][0].lower() not in coverage["lane_fit"].lower():
        raise CorpusError(f"{slug}: lane_fit must name the primary suitable use")
    if not any(trait.lower() in coverage["lane_fit"].lower() for trait in meta["signature_traits"]):
        raise CorpusError(f"{slug}: lane_fit must name a case-specific signature relationship")
    if coverage["confidence"] not in CONFIDENCE:
        raise CorpusError(f"{slug}: invalid coverage confidence")
    list_minimums = {"signature_moves": 3, "failure_modes": 3, "suitable_uses": 2, "unsuitable_uses": 1, "unknowns": 1}
    for key, minimum in list_minimums.items():
        require_string_list(coverage[key], f"{slug} coverage {key}", minimum, unique=True)
    for key in required - {"schema_version", "confidence", *list_minimums}:
        require_text(coverage[key], f"{slug} coverage {key}", 3)


def validate_preview(case_dir: Path) -> None:
    slug = case_dir.name
    required = {"schema_version", "primary", "secondary", "radius", "pattern", "layout", "motion", "lineage"}
    preview = read_json(case_dir / "preview-spec.json")
    require_schema(preview, "preview", f"{slug} preview")
    require_keys(preview, required, f"{slug} preview", exact=True)
    if preview["schema_version"] != "1.0":
        raise CorpusError(f"{slug}: preview schema mismatch")
    if not HEX_RE.fullmatch(preview["primary"]) or not HEX_RE.fullmatch(preview["secondary"]):
        raise CorpusError(f"{slug}: preview colors must be six-digit hex values")
    if not RADIUS_RE.fullmatch(preview["radius"]):
        raise CorpusError(f"{slug}: preview radius must be an integer px value")
    for key, minimum in (("pattern", 20), ("layout", 10), ("motion", 10)):
        require_text(preview[key], f"{slug} preview {key}", minimum)
        if "url(" in preview[key].lower() or "data:" in preview[key].lower():
            raise CorpusError(f"{slug}: preview {key} embeds an asset reference")
    lineage = {"origin": "original-abstract-spec", "source_assets_used": False, "generated_asset": False}
    if preview["lineage"] != lineage:
        raise CorpusError(f"{slug}: preview lineage must prove an original asset-free spec")


def validate_source(case_dir: Path, meta: dict) -> dict:
    slug = case_dir.name
    required = {
        "schema_version", "source_scope_id", "owner_url", "effective_url", "retrieved_at", "http_status",
        "content_sha256", "inspected_locators", "source_version", "terms_or_license_url",
        "permitted_use_basis", "archive_url", "limitations", "third_party_assets_stored",
    }
    source = read_json(case_dir / "source.json")
    require_schema(source, "source", f"{slug} source")
    require_keys(source, required, f"{slug} source", exact=True)
    if source["schema_version"] != "1.0" or source["source_scope_id"] != slug:
        raise CorpusError(f"{slug}: source schema or scope mismatch")
    if source["owner_url"] != meta["source_url"]:
        raise CorpusError(f"{slug}: source owner_url differs from metadata")
    require_https(source["owner_url"], f"{slug} owner_url")
    require_https(source["effective_url"], f"{slug} effective_url")
    require_date(source["retrieved_at"], f"{slug} source retrieved_at")
    if not isinstance(source["http_status"], int) or not 200 <= source["http_status"] <= 399:
        raise CorpusError(f"{slug}: source http_status is not successful")
    if not isinstance(source["content_sha256"], str) or not SHA_RE.fullmatch(source["content_sha256"]):
        raise CorpusError(f"{slug}: source content_sha256 is invalid")
    if source["content_sha256"] == "0" * 64:
        raise CorpusError(f"{slug}: source content_sha256 is still a placeholder")
    require_string_list(source["inspected_locators"], f"{slug} inspected_locators", unique=True)
    require_text(source["source_version"], f"{slug} source_version", 3)
    for key in ("terms_or_license_url", "archive_url"):
        if source[key] is not None:
            require_https(source[key], f"{slug} source {key}")
    if source["permitted_use_basis"] != "original-analysis-from-ordinary-public-access":
        raise CorpusError(f"{slug}: invalid source permitted_use_basis")
    if source["third_party_assets_stored"] is not False:
        raise CorpusError(f"{slug}: third-party assets may not be stored")
    require_string_list(source["limitations"], f"{slug} source limitations", 1, unique=True)
    if any("must be refreshed" in item.lower() or "placeholder" in item.lower() for item in source["limitations"]):
        raise CorpusError(f"{slug}: source limitations still contain an audit placeholder")
    return source


def validate_prose(case_dir: Path) -> None:
    slug = case_dir.name
    design = (case_dir / "DESIGN.md").read_text(encoding="utf-8")
    for heading in ("# ", "## Visual thesis", "## Signature relationships", "## Adaptation rules", "## Failure modes"):
        if heading not in design:
            raise CorpusError(f"{slug}: DESIGN.md missing {heading}")
    if len(design) < 1200:
        raise CorpusError(f"{slug}: DESIGN.md is too shallow for alpha review")
    if "\u2014" in design:
        raise CorpusError(f"{slug}: DESIGN.md contains an em dash")
    notes = (case_dir / "source-notes.md").read_text(encoding="utf-8")
    if len(notes) < 180:
        raise CorpusError(f"{slug}: source notes are too short for alpha review")


def validate_review(case_dir: Path, meta: dict, allow_pending_review: bool) -> None:
    slug = case_dir.name
    required = {
        "schema_version", "status", "result", "author", "reviewer", "independent", "method",
        "artifact_sha256", "originality_checked", "evidence_checked", "rights_checked", "assets_checked",
        "reviewed_at", "notes",
    }
    review = read_json(case_dir / "review.json")
    require_schema(review, "review", f"{slug} review")
    require_keys(review, required, f"{slug} review", exact=True)
    if review["schema_version"] != "1.0" or review["status"] != meta["publication_status"]:
        raise CorpusError(f"{slug}: review schema or publication state mismatch")
    if review["result"] not in {"pending", "pass", "fail"}:
        raise CorpusError(f"{slug}: invalid review result")
    for key in ("author", "reviewer", "method"):
        require_text(review[key], f"{slug} review {key}", 3)
    require_date(review["reviewed_at"], f"{slug} review reviewed_at")
    if not isinstance(review["artifact_sha256"], dict):
        raise CorpusError(f"{slug}: review artifact_sha256 must be an object")
    if review["result"] == "pending" and allow_pending_review:
        if review["independent"] is not False or review["artifact_sha256"]:
            raise CorpusError(f"{slug}: pending review cannot claim independence or artifact hashes")
        return
    if review["result"] != "pass":
        raise CorpusError(f"{slug}: independent review has not passed")
    if review["independent"] is not True or review["author"] == review["reviewer"]:
        raise CorpusError(f"{slug}: passing review must be independent from the author")
    for key in ("originality_checked", "evidence_checked", "rights_checked", "assets_checked"):
        if review[key] is not True:
            raise CorpusError(f"{slug}: review {key} must be true")
    if set(review["artifact_sha256"]) != HASHED_FILES:
        raise CorpusError(f"{slug}: review hashes must cover exactly {sorted(HASHED_FILES)}")
    for name in HASHED_FILES:
        expected = review["artifact_sha256"][name]
        if not isinstance(expected, str) or not SHA_RE.fullmatch(expected) or expected != sha256(case_dir / name):
            raise CorpusError(f"{slug}: review hash mismatch for {name}")


def validate_case(case_dir: Path, taxonomy: dict, allow_pending_review: bool) -> tuple[dict, dict]:
    slug = case_dir.name
    if case_dir.is_symlink():
        raise CorpusError(f"{slug}: case directories may not be symlinks")
    found = {path.name for path in case_dir.iterdir() if path.is_file()}
    missing = sorted(REQUIRED_FILES - found)
    if missing:
        raise CorpusError(f"{slug}: missing files {missing}")
    for path in case_dir.rglob("*"):
        if path.is_symlink():
            raise CorpusError(f"{slug}: symlinks are not allowed in canonical case records: {path.name}")
        if path.is_file() and path.suffix.lower() in BANNED_CASE_EXTENSIONS:
            raise CorpusError(f"{slug}: binary or distributable source asset is not allowed: {path.name}")
    meta = validate_metadata(case_dir, taxonomy)
    evidence_records = validate_evidence(case_dir, meta)
    validate_tokens(case_dir, evidence_records)
    validate_coverage(case_dir, meta)
    validate_preview(case_dir)
    source = validate_source(case_dir, meta)
    for evidence_id, item in evidence_records.items():
        if (
            item["class"] in {"observed", "measured"}
            and item["source_url"] == meta["source_url"]
            and item["locator"] not in source["inspected_locators"]
        ):
            raise CorpusError(f"{slug}: direct evidence {evidence_id} locator is absent from source.json")
    validate_prose(case_dir)
    validate_review(case_dir, meta, allow_pending_review)
    return meta, source


def validate(*, allow_pending_review: bool = False) -> dict:
    taxonomy = read_json(TAXONOMY)
    if taxonomy.get("schema_version") != "1.0" or not isinstance(taxonomy.get("facets"), dict):
        raise CorpusError("taxonomy schema is invalid")
    if not CASES_ROOT.is_dir():
        raise CorpusError("cases directory is missing")
    cases: list[dict] = []
    sources: list[dict] = []
    for case_dir in sorted((path for path in CASES_ROOT.iterdir() if path.is_dir()), key=lambda path: path.name):
        meta, source = validate_case(case_dir, taxonomy, allow_pending_review)
        cases.append(meta)
        sources.append(source)
    if len(cases) != 60:
        raise CorpusError(f"Wave 11 alpha requires exactly 60 cases, found {len(cases)}")
    lane_counts = Counter(case["corpus_lane"] for case in cases)
    if {lane: lane_counts[lane] for lane in ALPHA_LANES} != ALPHA_LANES:
        raise CorpusError(f"alpha lane counts differ from plan: {dict(lane_counts)}")
    source_urls = [case["source_url"] for case in cases]
    source_scopes = [source["source_scope_id"] for source in sources]
    if len(source_urls) != len(set(source_urls)):
        raise CorpusError("alpha cases must have unique canonical source URLs")
    if len(source_scopes) != len(set(source_scopes)):
        raise CorpusError("alpha cases must have unique source_scope_id values")
    return {
        "status": "pass",
        "review_mode": "allow-pending" if allow_pending_review else "accepted-only",
        "case_count": len(cases),
        "lane_counts": {lane: lane_counts[lane] for lane in ALPHA_LANES},
        "slugs": [case["slug"] for case in cases],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-pending-review", action="store_true",
        help="Validate candidate structure while allowing an explicitly pending independent review.",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(validate(allow_pending_review=args.allow_pending_review), indent=2, sort_keys=True))
        return 0
    except CorpusError as exc:
        print(f"CORPUS INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
