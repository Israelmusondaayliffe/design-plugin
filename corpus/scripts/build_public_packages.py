#!/usr/bin/env python3
"""Build deterministic, privacy-filtered public packages for corpus cases."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse


CORPUS_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
SCHEMAS_ROOT = CORPUS_ROOT / "schemas"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from json_schema_subset import SchemaViolation, validate_schema


PUBLIC_SCHEMA_PATH = SCHEMAS_ROOT / "public-case-package.schema.json"
SOURCE_SCHEMAS = {
    "metadata": SCHEMAS_ROOT / "case.schema.json",
    "evidence": SCHEMAS_ROOT / "evidence.schema.json",
    "coverage": SCHEMAS_ROOT / "coverage.schema.json",
    "source": SCHEMAS_ROOT / "source.schema.json",
}
SOURCE_FILES = {
    "metadata": "metadata.json",
    "evidence": "evidence.json",
    "coverage": "coverage.json",
    "source": "source.json",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
URL_LOCATOR_RE = re.compile(r"^URL: (https://\S+)$")
FORBIDDEN_KEYS = {
    "author",
    "reviewer",
    "review",
    "review_notes",
    "review_method",
    "artifact_sha256",
    "source_notes",
    "archive_url",
    "effective_url",
    "http_status",
    "content_sha256",
    "source_version",
    "inspected_locators",
    "redirect_history",
    "internal_path",
    "local_path",
}
PROHIBITED_OPERATIONAL_VALUE_PATTERNS = (
    re.compile(r"\bresponse[\W_]*hash\b", re.IGNORECASE),
    re.compile(r"\bcontent[\W_]*sha[\W_]*256\b", re.IGNORECASE),
    re.compile(r"\bhttp[\W_]*status\b", re.IGNORECASE),
    re.compile(r"\bredirect[\W_]*histor(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\b(?:archive|archived|effective)[\W_]*url\b", re.IGNORECASE),
)
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"file://", re.IGNORECASE),
    re.compile(r"(?:^|[/\\])\.codex(?:[/\\]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[/\\])\.claude(?:[/\\]|$)", re.IGNORECASE),
    re.compile(r"CODEX_HOME", re.IGNORECASE),
    re.compile(r"Codex-Workspace", re.IGNORECASE),
    re.compile(r"refero\.design", re.IGNORECASE),
    re.compile(r"\bdata:[^\s]+", re.IGNORECASE),
) + PROHIBITED_OPERATIONAL_VALUE_PATTERNS
BIDI_FORMAT_CONTROLS = {
    "\u061c",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
    "\ufeff",
}
ANALYSIS_FIELDS = (
    "brand_posture",
    "layout",
    "grid",
    "container",
    "responsive_behavior",
    "typography",
    "color",
    "spacing",
    "surfaces",
    "components",
    "states",
    "navigation",
    "forms",
    "flows",
    "motion",
    "interaction",
    "imagery",
    "accessibility",
)
BOUNDARY_TEXT = {
    "observed": "Directly supported by the cited public source at the recorded locator.",
    "inferred": "Corpus analysis of source patterns, not the source owner's stated intent.",
    "recommended": "Adaptation guidance, not a source claim or an outcome guarantee.",
    "unknown": "Not established by the inspected public material and still unresolved.",
    "evidence_scope": "Evidence IDs are scoped to this case.",
    "date_boundary": "The source retrieval date records source retrieval; the evidence capture date records evidence capture.",
    "public_projection": (
        "This package contains only the public projection of a canonical case whose publication status is public. "
        "That status does not certify adaptation, accessibility, or fitness for a particular use."
    ),
}
PUBLIC_LIMITATION_MAP = {
    "The live public source may change after the recorded response hash.":
        "The live public source may change after the recorded retrieval date.",
    "The response hash proves retrieval of the owner source; evidence classification and review determine what the source supports.":
        "Retrieval of the owner source does not prove every design claim. Evidence classifications and qualifications define the support for each public claim.",
}


class PublicPackageError(RuntimeError):
    """Raised when a public package cannot be produced safely."""


class NonPublicCaseError(PublicPackageError):
    """Raised when a canonical case is not eligible for public projection."""


def _reject_constant(value: str):
    raise PublicPackageError(f"non-finite JSON value is not allowed: {value}")


def _reject_float(value: str):
    raise PublicPackageError(f"floating-point JSON value is not allowed: {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicPackageError(f"duplicate JSON key is not allowed: {key!r}")
        result[key] = value
    return result


def _normalize_string(value: str, label: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = unicodedata.normalize("NFC", value)
    for character in value:
        codepoint = ord(character)
        if character in BIDI_FORMAT_CONTROLS:
            raise PublicPackageError(f"{label}: bidirectional format controls are not allowed")
        if 0xD800 <= codepoint <= 0xDFFF:
            raise PublicPackageError(f"{label}: unpaired Unicode surrogates are not allowed")
        if codepoint == 0 or (codepoint < 32 and character not in {"\n", "\t"}):
            raise PublicPackageError(f"{label}: disallowed control character U+{codepoint:04X}")
    return value


def _normalize_tree(value, label: str = "$"):
    if isinstance(value, str):
        return _normalize_string(value, label)
    if isinstance(value, list):
        return [_normalize_tree(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise PublicPackageError(f"{label}: JSON object keys must be strings")
            normalized_key = _normalize_string(key, f"{label} key")
            if normalized_key in normalized:
                raise PublicPackageError(f"{label}: keys collide after Unicode normalization")
            normalized[normalized_key] = _normalize_tree(item, f"{label}.{normalized_key}")
        return normalized
    return value


def load_json_strict(path: Path):
    try:
        text = path.read_bytes().decode("utf-8")
    except FileNotFoundError as exc:
        raise PublicPackageError(f"missing canonical input: {path}") from exc
    except UnicodeDecodeError as exc:
        raise PublicPackageError(f"canonical input is not UTF-8: {path}") from exc
    try:
        loaded = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except json.JSONDecodeError as exc:
        raise PublicPackageError(f"invalid JSON {path}: {exc}") from exc
    return _normalize_tree(loaded)


def _canonical_json_bytes(value, *, pretty: bool) -> bytes:
    options = {
        "ensure_ascii": False,
        "sort_keys": True,
        "allow_nan": False,
    }
    if pretty:
        text = json.dumps(value, indent=2, **options) + "\n"
    else:
        text = json.dumps(value, separators=(",", ":"), **options)
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def model_sha256(model: dict) -> str:
    return sha256_bytes(_canonical_json_bytes(model, pretty=False))


def _validate_schema(value, schema: dict, label: str) -> None:
    try:
        validate_schema(value, schema, label)
    except SchemaViolation as exc:
        raise PublicPackageError(str(exc)) from exc


def _require_exact_source_shape(record: dict, schema: dict, label: str) -> None:
    if not isinstance(record, dict):
        raise PublicPackageError(f"{label}: expected an object")
    expected = set(schema.get("properties", {}))
    actual = set(record)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise PublicPackageError(f"{label}: source shape mismatch; missing={missing}, unexpected={extra}")
    _validate_schema(record, schema, label)


def _validate_slug(slug: str) -> None:
    if unicodedata.normalize("NFC", slug) != slug:
        raise PublicPackageError("case slug changes under NFC normalization")
    if unquote(slug) != slug or "%" in slug:
        raise PublicPackageError("percent-encoded case slugs are not allowed")
    if not SLUG_RE.fullmatch(slug) or "/" in slug or "\\" in slug or slug in {".", ".."}:
        raise PublicPackageError(f"unsafe case slug: {slug!r}")


def _validate_https_url(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise PublicPackageError(f"{label}: expected a URL string")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise PublicPackageError(f"{label}: expected a public https URL")
    if any(character.isspace() or character in "<>[]{}\\`" for character in value):
        raise PublicPackageError(f"{label}: URL contains unsafe characters")
    host = (parsed.hostname or "").lower()
    if host == "refero.design" or host.endswith(".refero.design"):
        raise PublicPackageError(f"{label}: Refero sources are not permitted")


def _public_locator(locator: str):
    match = URL_LOCATOR_RE.fullmatch(locator)
    if not match:
        return None
    _validate_https_url(match.group(1), "evidence locator")
    return locator


def _public_limitation(statement: str) -> str:
    projected = PUBLIC_LIMITATION_MAP.get(statement, statement)
    for pattern in PROHIBITED_OPERATIONAL_VALUE_PATTERNS:
        if pattern.search(projected):
            raise PublicPackageError(
                "source limitation contains operational wording without a public projection: "
                f"{pattern.pattern!r}"
            )
    return projected


def load_canonical_case(case_dir: Path) -> dict:
    if case_dir.is_symlink() or not case_dir.is_dir():
        raise PublicPackageError(f"canonical case must be a real directory: {case_dir}")
    slug = case_dir.name
    _validate_slug(slug)
    design_path = case_dir / "DESIGN.md"
    if design_path.is_symlink() or not design_path.is_file():
        raise PublicPackageError(f"{slug}: canonical DESIGN.md is missing or is a symlink")

    schemas = {name: load_json_strict(path) for name, path in SOURCE_SCHEMAS.items()}
    for filename in SOURCE_FILES.values():
        source_path = case_dir / filename
        if source_path.is_symlink():
            raise PublicPackageError(f"{slug}: canonical input cannot be a symlink: {filename}")
    records = {name: load_json_strict(case_dir / filename) for name, filename in SOURCE_FILES.items()}
    for name in SOURCE_FILES:
        _require_exact_source_shape(records[name], schemas[name], f"{slug} {name}")

    metadata = records["metadata"]
    evidence = records["evidence"]
    coverage = records["coverage"]
    source = records["source"]
    if metadata["slug"] != slug or source["source_scope_id"] != slug:
        raise PublicPackageError(f"{slug}: canonical scope identifiers do not match the directory slug")
    if metadata["publication_status"] != "public":
        raise NonPublicCaseError(f"{slug}: only publication_status=public can produce a public package")
    if coverage["source"] != metadata["source_url"] or source["owner_url"] != metadata["source_url"]:
        raise PublicPackageError(f"{slug}: canonical source URLs disagree")
    if coverage["study_date"] != metadata["studied_at"]:
        raise PublicPackageError(f"{slug}: canonical study dates disagree")
    if coverage["category"] != metadata["corpus_lane"]:
        raise PublicPackageError(f"{slug}: coverage category differs from the corpus lane")
    if source["third_party_assets_stored"] is not False:
        raise PublicPackageError(f"{slug}: public packages cannot include stored third-party assets")

    for label, url in (
        ("metadata source_url", metadata["source_url"]),
        ("source owner_url", source["owner_url"]),
    ):
        _validate_https_url(url, f"{slug} {label}")
    if source["terms_or_license_url"] is not None:
        _validate_https_url(source["terms_or_license_url"], f"{slug} terms_or_license_url")
    for item in evidence["items"]:
        _validate_https_url(item["source_url"], f"{slug} evidence {item['id']} source_url")
    return records


def build_public_model(case_dir: Path) -> dict:
    records = load_canonical_case(case_dir)
    metadata = records["metadata"]
    evidence = records["evidence"]
    coverage = records["coverage"]
    source = records["source"]
    model = {
        "schema_version": "1.0",
        "package_type": "design-reference-public-case",
        "slug": metadata["slug"],
        "name": metadata["name"],
        "publication_status": "public",
        "context": {
            "source_identity": {
                "truth_class": "observed",
                "source_name": metadata["source_name"],
                "source_kind": metadata["source_kind"],
                "source_url": metadata["source_url"],
                "studied_at": metadata["studied_at"],
            },
            "study_context": {
                "truth_class": "inferred",
                "summary": metadata["summary"],
                "audience": {
                    "truth_class": "unknown",
                    "statement": "No audience is recorded in the canonical public fields for this case.",
                },
                "corpus_lane": metadata["corpus_lane"],
                "platforms": list(metadata["platforms"]),
                "product_types": list(metadata["product_types"]),
                "industries": list(metadata["industries"]),
                "archetypes": list(metadata["archetypes"]),
                "density": metadata["density"],
                "media_strategy": metadata["media_strategy"],
            },
        },
        "intent": {
            "truth_class": "inferred",
            "visual_thesis": coverage["visual_thesis"],
            "journeys": list(metadata["journey"]),
            "signature_relationships": list(coverage["signature_moves"]),
        },
        "value": {
            "truth_class": "recommended",
            "best_for": list(metadata["best_for"]),
            "avoid_for": list(metadata["avoid_for"]),
            "failure_modes": list(coverage["failure_modes"]),
        },
        "quality": {
            "truth_class": "inferred",
            "evidence_quality": metadata["evidence_quality"],
            "coverage_confidence": coverage["confidence"],
            "accessibility_maturity": metadata["accessibility_maturity"],
            "accessibility_note": "Accessibility maturity is corpus guidance, not a test result or certification.",
            "evidence_count": len(evidence["items"]),
        },
        "analysis": {
            "truth_classes": ["inferred", "recommended"],
            **{field: coverage[field] for field in ANALYSIS_FIELDS},
        },
        "evidence_boundary": dict(BOUNDARY_TEXT),
        "evidence": [
            {
                "id": item["id"],
                "claim": item["claim"],
                "truth_class": item["class"],
                "source_url": item["source_url"],
                "retrieved_at": source["retrieved_at"],
                "captured_at": item["captured_at"],
                "confidence": item["confidence"],
                "locator": _public_locator(item["locator"]),
                "qualification": item["notes"],
            }
            for item in evidence["items"]
        ],
        "provenance": {
            "truth_class": "observed",
            "owner_url": source["owner_url"],
            "retrieved_at": source["retrieved_at"],
            "rights_basis": metadata["rights_basis"],
            "permitted_use_basis": source["permitted_use_basis"],
            "terms_or_license_url": source["terms_or_license_url"],
            "third_party_assets_stored": False,
        },
        "limitations": [
            {"kind": "source-limitation", "statement": _public_limitation(statement)}
            for statement in source["limitations"]
        ],
        "unknowns": [
            {"truth_class": "unknown", "statement": statement}
            for statement in coverage["unknowns"]
        ],
    }
    public_schema = load_json_strict(PUBLIC_SCHEMA_PATH)
    _validate_schema(model, public_schema, f"{metadata['slug']} public package")
    scan_public_value(model)
    return model


def semantic_leaf_paths(value, path: str = "$") -> list[str]:
    paths = []
    if isinstance(value, dict):
        for key in sorted(value):
            paths.extend(semantic_leaf_paths(value[key], f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(semantic_leaf_paths(item, f"{path}[{index}]"))
    else:
        paths.append(path)
    return paths


def semantic_paths_sha256(model: dict) -> str:
    joined = "\n".join(semantic_leaf_paths(model)) + "\n"
    return sha256_bytes(joined.encode("utf-8"))


def _model_value_at_path(model: dict, path: str):
    if path == "$":
        return model
    if not path.startswith("$"):
        raise PublicPackageError(f"invalid semantic path: {path}")
    current = model
    position = 1
    while position < len(path):
        if path[position] == ".":
            match = re.match(r"\.([A-Za-z_][A-Za-z0-9_]*)", path[position:])
            if not match or not isinstance(current, dict):
                raise PublicPackageError(f"invalid semantic object path: {path}")
            key = match.group(1)
            if key not in current:
                raise PublicPackageError(f"semantic path is absent from the model: {path}")
            current = current[key]
            position += len(match.group(0))
        elif path[position] == "[":
            match = re.match(r"\[([0-9]+)\]", path[position:])
            if not match or not isinstance(current, list):
                raise PublicPackageError(f"invalid semantic list path: {path}")
            index = int(match.group(1))
            if index >= len(current):
                raise PublicPackageError(f"semantic list path is outside the model: {path}")
            current = current[index]
            position += len(match.group(0))
        else:
            raise PublicPackageError(f"invalid semantic path syntax: {path}")
    return current


def _leaf_binding(path: str, value) -> dict:
    return {"path": path, "value_sha256": sha256_bytes(_canonical_json_bytes(value, pretty=False))}


def semantic_leaf_bindings(model: dict) -> list[dict]:
    return [_leaf_binding(path, _model_value_at_path(model, path)) for path in semantic_leaf_paths(model)]


def _markdown_inline(value) -> str:
    if value is None:
        return "Not recorded"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = " ".join(str(value).split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = []
    for character in text:
        if character in "\\`*_{}[]()#+!|~":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def _markdown_url(value) -> str:
    if value is None:
        return "Not recorded"
    if value.startswith("URL: "):
        _validate_https_url(value[5:], "Markdown URL locator")
    else:
        _validate_https_url(value, "Markdown URL")
    return value


class MarkdownRenderer:
    """Render only declared model paths and record every semantic leaf consumed."""

    def __init__(self, model: dict):
        self.model = model
        self.lines = []
        self.trace = []

    def value(self, path: str, value, *, formatter=_markdown_inline) -> str:
        canonical = _model_value_at_path(self.model, path)
        if canonical != value:
            raise PublicPackageError(f"Markdown renderer value differs from the normalized model at {path}")
        self.trace.append(_leaf_binding(path, canonical))
        return formatter(canonical)

    def consume(self, path: str, value) -> None:
        self.value(path, value)

    def field(self, label: str, path: str, value) -> None:
        self.lines.append(f"- **{label}:** {self.value(path, value)}")

    def url_field(self, label: str, path: str, value) -> None:
        self.lines.append(f"- **{label}:** {self.value(path, value, formatter=_markdown_url)}")

    def items(self, path: str, values) -> None:
        for index, value in enumerate(values):
            self.lines.append(f"- {self.value(f'{path}[{index}]', value)}")

    def inline_items_field(self, label: str, path: str, values) -> None:
        rendered = [self.value(f"{path}[{index}]", value) for index, value in enumerate(values)]
        self.lines.append(f"- **{label}:** {', '.join(rendered)}")

    def heading(self, title: str) -> None:
        self.lines.extend(["", f"## {title}", ""])

    def render(self):
        model = self.model
        self.lines.append(f"# {self.value('$.name', model['name'])}")

        self.heading("Record facts")
        self.field("Schema version", "$.schema_version", model["schema_version"])
        self.field("Package type", "$.package_type", model["package_type"])
        self.field("Slug", "$.slug", model["slug"])
        self.field("Publication status", "$.publication_status", model["publication_status"])

        source_identity = model["context"]["source_identity"]
        study_context = model["context"]["study_context"]
        self.heading("Context")
        self.field("Source truth class", "$.context.source_identity.truth_class", source_identity["truth_class"])
        self.field("Source name", "$.context.source_identity.source_name", source_identity["source_name"])
        self.field("Source kind", "$.context.source_identity.source_kind", source_identity["source_kind"])
        self.url_field("Source URL", "$.context.source_identity.source_url", source_identity["source_url"])
        self.field("Studied at", "$.context.source_identity.studied_at", source_identity["studied_at"])
        self.field("Study truth class", "$.context.study_context.truth_class", study_context["truth_class"])
        self.field("Summary", "$.context.study_context.summary", study_context["summary"])
        self.field("Audience truth class", "$.context.study_context.audience.truth_class", study_context["audience"]["truth_class"])
        self.field("Audience", "$.context.study_context.audience.statement", study_context["audience"]["statement"])
        self.field("Corpus lane", "$.context.study_context.corpus_lane", study_context["corpus_lane"])
        self.lines.extend(["", "### Platforms", ""])
        self.items("$.context.study_context.platforms", study_context["platforms"])
        self.lines.extend(["", "### Product types", ""])
        self.items("$.context.study_context.product_types", study_context["product_types"])
        self.lines.extend(["", "### Industries", ""])
        self.items("$.context.study_context.industries", study_context["industries"])
        self.lines.extend(["", "### Archetypes", ""])
        self.items("$.context.study_context.archetypes", study_context["archetypes"])
        self.lines.extend(["", "### Additional context", ""])
        self.field("Density", "$.context.study_context.density", study_context["density"])
        self.field("Media strategy", "$.context.study_context.media_strategy", study_context["media_strategy"])

        intent = model["intent"]
        self.heading("Adaptation intent")
        self.field("Truth class", "$.intent.truth_class", intent["truth_class"])
        self.field("Visual thesis", "$.intent.visual_thesis", intent["visual_thesis"])
        self.lines.extend(["", "### Journeys", ""])
        self.items("$.intent.journeys", intent["journeys"])
        self.lines.extend(["", "### Signature relationships", ""])
        self.items("$.intent.signature_relationships", intent["signature_relationships"])

        self.heading("Reusable relationships")
        analysis = model["analysis"]
        self.inline_items_field("Truth classes", "$.analysis.truth_classes", analysis["truth_classes"])
        grouped = {}
        for field in ANALYSIS_FIELDS:
            grouped.setdefault(analysis[field], []).append(field)
        for statement, fields in grouped.items():
            labels = [field.replace("_", " ") for field in fields]
            label = " and ".join(labels).capitalize()
            for field in fields:
                self.consume(f"$.analysis.{field}", analysis[field])
            if statement == study_context["summary"]:
                self.lines.append(f"- **{label}:** Same statement as the Context summary.")
            else:
                self.lines.append(f"- **{label}:** {_markdown_inline(statement)}")

        value = model["value"]
        self.heading("Recommended uses and limits")
        self.field("Truth class", "$.value.truth_class", value["truth_class"])
        self.lines.extend(["", "### Best for", ""])
        self.items("$.value.best_for", value["best_for"])
        self.lines.extend(["", "### Avoid for", ""])
        self.items("$.value.avoid_for", value["avoid_for"])
        self.lines.extend(["", "### Failure modes", ""])
        self.items("$.value.failure_modes", value["failure_modes"])

        quality = model["quality"]
        self.heading("Evidence quality")
        self.field("Truth class", "$.quality.truth_class", quality["truth_class"])
        self.field("Evidence quality", "$.quality.evidence_quality", quality["evidence_quality"])
        self.field("Coverage confidence", "$.quality.coverage_confidence", quality["coverage_confidence"])
        self.field("Accessibility maturity", "$.quality.accessibility_maturity", quality["accessibility_maturity"])
        self.field("Accessibility note", "$.quality.accessibility_note", quality["accessibility_note"])
        self.field("Evidence count", "$.quality.evidence_count", quality["evidence_count"])

        boundary = model["evidence_boundary"]
        self.lines.extend(["", "### Evidence boundary", ""])
        for field in ("observed", "inferred", "recommended", "unknown", "evidence_scope", "date_boundary", "public_projection"):
            self.field(field.replace("_", " ").capitalize(), f"$.evidence_boundary.{field}", boundary[field])

        self.heading("Evidence records")
        for index, item in enumerate(model["evidence"]):
            prefix = f"$.evidence[{index}]"
            self.lines.extend(["", f"### {self.value(prefix + '.id', item['id'])}", ""])
            self.field("Claim", prefix + ".claim", item["claim"])
            self.field("Truth class", prefix + ".truth_class", item["truth_class"])
            self.url_field("Source URL", prefix + ".source_url", item["source_url"])
            self.field("Source retrieved at", prefix + ".retrieved_at", item["retrieved_at"])
            self.field("Evidence captured at", prefix + ".captured_at", item["captured_at"])
            self.field("Confidence", prefix + ".confidence", item["confidence"])
            if item["locator"] is None:
                self.field("Public locator", prefix + ".locator", item["locator"])
            else:
                self.url_field("Public locator", prefix + ".locator", item["locator"])
            self.field("Qualification", prefix + ".qualification", item["qualification"])

        provenance = model["provenance"]
        self.heading("Source and originality")
        self.field("Truth class", "$.provenance.truth_class", provenance["truth_class"])
        self.url_field("Owner URL", "$.provenance.owner_url", provenance["owner_url"])
        self.field("Retrieved at", "$.provenance.retrieved_at", provenance["retrieved_at"])
        self.field("Rights basis", "$.provenance.rights_basis", provenance["rights_basis"])
        self.field("Permitted use basis", "$.provenance.permitted_use_basis", provenance["permitted_use_basis"])
        if provenance["terms_or_license_url"] is None:
            self.field("Terms or license URL", "$.provenance.terms_or_license_url", provenance["terms_or_license_url"])
        else:
            self.url_field("Terms or license URL", "$.provenance.terms_or_license_url", provenance["terms_or_license_url"])
        self.field(
            "Third-party assets stored in the canonical source record",
            "$.provenance.third_party_assets_stored",
            provenance["third_party_assets_stored"],
        )

        self.heading("Source limitations")
        for index, item in enumerate(model["limitations"]):
            prefix = f"$.limitations[{index}]"
            self.field("Kind", prefix + ".kind", item["kind"])
            self.field("Statement", prefix + ".statement", item["statement"])

        self.heading("Unresolved unknowns")
        for index, item in enumerate(model["unknowns"]):
            prefix = f"$.unknowns[{index}]"
            self.field("Truth class", prefix + ".truth_class", item["truth_class"])
            self.field("Statement", prefix + ".statement", item["statement"])

        text = "\n".join(self.lines).strip() + "\n"
        text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
        return text, list(self.trace)


def assert_semantic_parity(model: dict, renderer_trace: list[dict]) -> None:
    expected = semantic_leaf_bindings(model)
    expected_pairs = {(item["path"], item["value_sha256"]) for item in expected}
    actual_pairs = set()
    for item in renderer_trace:
        if not isinstance(item, dict) or set(item) != {"path", "value_sha256"}:
            raise PublicPackageError("Markdown renderer trace contains an invalid binding")
        actual_pairs.add((item["path"], item["value_sha256"]))
    if len(renderer_trace) != len(actual_pairs):
        raise PublicPackageError("Markdown renderer consumed a semantic binding more than once")
    missing = sorted(expected_pairs - actual_pairs)
    extra = sorted(actual_pairs - expected_pairs)
    if missing or extra:
        raise PublicPackageError(f"Markdown/JSON semantic parity failed; missing={missing}, extra={extra}")


def render_markdown(model: dict) -> tuple[str, list[dict]]:
    renderer = MarkdownRenderer(model)
    text, trace = renderer.render()
    assert_semantic_parity(model, trace)
    return text, trace


def scan_public_value(value, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in FORBIDDEN_KEYS:
                raise PublicPackageError(f"{path}: prohibited public field {key!r}")
            scan_public_value(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_public_value(item, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(value):
                raise PublicPackageError(f"{path}: prohibited public value matched {pattern.pattern!r}")


def scan_generated_bytes(files: dict[str, bytes]) -> None:
    for route, data in files.items():
        if b"\x00" in data:
            raise PublicPackageError(f"{route}: generated file contains a NUL byte")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PublicPackageError(f"{route}: generated file is not UTF-8 text") from exc
        _normalize_string(text, route)
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(text):
                raise PublicPackageError(f"{route}: generated file matched prohibited value {pattern.pattern!r}")


def package_bytes(model: dict) -> dict[str, bytes]:
    markdown, trace = render_markdown(model)
    assert_semantic_parity(model, trace)
    digest = model_sha256(model)
    structured = _canonical_json_bytes(model, pretty=True)
    readable = markdown.encode("utf-8")
    slug = model["slug"]
    files = {
        "case.md": readable,
        "case.json": structured,
    }
    manifest = {
        "schema_version": "1.0",
        "slug": slug,
        "model_sha256": digest,
        "semantic_paths_sha256": semantic_paths_sha256(model),
        "files": [
            {
                "format": "readable",
                "route": "case.md",
                "download_filename": f"{slug}-design-reference.md",
                "media_type": "text/markdown; charset=utf-8",
                "byte_size": len(readable),
                "sha256": sha256_bytes(readable),
                "model_sha256": digest,
            },
            {
                "format": "structured",
                "route": "case.json",
                "download_filename": f"{slug}-design-reference.json",
                "media_type": "application/json; charset=utf-8",
                "byte_size": len(structured),
                "sha256": sha256_bytes(structured),
                "model_sha256": digest,
            },
        ],
    }
    scan_public_value(manifest)
    files["manifest.json"] = _canonical_json_bytes(manifest, pretty=True)
    scan_generated_bytes(files)
    return files


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _validate_contained_destination(destination: Path, output_root: Path) -> tuple[Path, Path]:
    root = _absolute_path(output_root)
    target = _absolute_path(destination)
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise PublicPackageError(f"package destination escapes the explicit output root: {destination}") from exc
    if root.exists() and root.is_symlink():
        raise PublicPackageError(f"explicit output root cannot be a symlink: {root}")
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise PublicPackageError(f"package destination contains a symlink component: {current}")
    resolved_root = root.resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise PublicPackageError(f"resolved package destination escapes the explicit output root: {destination}") from exc
    return target, root


def create_staging_root(output_root: Path) -> Path:
    root = _absolute_path(output_root)
    if root.exists() and root.is_symlink():
        raise PublicPackageError(f"output root cannot be a symlink: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    if root.parent.is_symlink():
        raise PublicPackageError(f"output root parent cannot be a symlink: {root.parent}")
    return Path(tempfile.mkdtemp(prefix=f".{root.name}.staging-", dir=str(root.parent)))


def replace_output_roots(replacements) -> None:
    prepared = []
    destinations = set()
    for destination, staging in replacements:
        destination = _absolute_path(destination)
        staging = _absolute_path(staging)
        if destination in destinations:
            raise PublicPackageError(f"duplicate output root replacement: {destination}")
        destinations.add(destination)
        if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
            raise PublicPackageError(f"output root must be a real directory: {destination}")
        if staging.is_symlink() or not staging.is_dir() or staging.parent != destination.parent:
            raise PublicPackageError(f"staging root is not a real sibling of its destination: {staging}")
        backup = destination.parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
        prepared.append({
            "destination": destination,
            "staging": staging,
            "backup": backup,
            "had_original": destination.exists(),
            "installed": False,
        })
    try:
        for item in prepared:
            if item["had_original"]:
                os.replace(str(item["destination"]), str(item["backup"]))
        for item in prepared:
            os.replace(str(item["staging"]), str(item["destination"]))
            item["installed"] = True
    except BaseException:
        for item in reversed(prepared):
            destination = item["destination"]
            backup = item["backup"]
            if item["installed"] and destination.exists():
                shutil.rmtree(destination)
            if backup.exists() and not destination.exists():
                os.replace(str(backup), str(destination))
        raise
    finally:
        for item in prepared:
            if item["staging"].exists():
                shutil.rmtree(item["staging"])
            if item["backup"].exists():
                if not item["destination"].exists():
                    os.replace(str(item["backup"]), str(item["destination"]))
                else:
                    shutil.rmtree(item["backup"])


def _replace_package_tree(destination: Path, files: dict[str, bytes], *, output_root: Path) -> None:
    destination, output_root = _validate_contained_destination(destination, output_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _validate_contained_destination(destination, output_root)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=str(destination.parent)))
    backup = destination.parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
    try:
        for route, data in files.items():
            target = staging / route
            target.write_bytes(data)
        actual = {path.name for path in staging.iterdir() if path.is_file()}
        if actual != {"case.md", "case.json", "manifest.json"}:
            raise PublicPackageError(f"generated package has unexpected files: {sorted(actual)}")
        scan_generated_bytes({path.name: path.read_bytes() for path in staging.iterdir() if path.is_file()})
        if destination.exists():
            if not destination.is_dir() or destination.is_symlink():
                raise PublicPackageError(f"package destination is not a real directory: {destination}")
            os.replace(str(destination), str(backup))
        try:
            os.replace(str(staging), str(destination))
        except BaseException:
            if backup.exists() and not destination.exists():
                os.replace(str(backup), str(destination))
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists():
            if not destination.exists():
                os.replace(str(backup), str(destination))
            else:
                shutil.rmtree(backup)


def verify_package_tree(destination: Path, model: dict, *, output_root: Path) -> dict:
    destination, _ = _validate_contained_destination(destination, output_root)
    if not destination.is_dir():
        raise PublicPackageError(f"package destination is missing: {destination}")
    paths = sorted(path for path in destination.iterdir())
    if {path.name for path in paths} != {"case.md", "case.json", "manifest.json"}:
        raise PublicPackageError(f"package tree must contain exactly three files: {destination}")
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise PublicPackageError(f"package tree contains a symlink or non-file: {destination}")
    generated = {path.name: path.read_bytes() for path in paths}
    scan_generated_bytes(generated)
    structured = load_json_strict(destination / "case.json")
    manifest = load_json_strict(destination / "manifest.json")
    if structured != model:
        raise PublicPackageError(f"{destination}: structured package differs from the normalized model")
    expected_digest = model_sha256(model)
    if manifest.get("model_sha256") != expected_digest or manifest.get("slug") != model["slug"]:
        raise PublicPackageError(f"{destination}: manifest model binding is invalid")
    expected_files = package_bytes(model)
    if generated != expected_files:
        raise PublicPackageError(f"{destination}: generated bytes or manifest metadata are invalid")
    return manifest


def build_case_package(case_dir: Path, destination: Path, *, output_root: Path) -> dict:
    model = build_public_model(case_dir)
    files = package_bytes(model)
    _replace_package_tree(destination, files, output_root=output_root)
    return verify_package_tree(destination, model, output_root=output_root)


def build_public_packages(cases_root: Path, output_root: Path, slugs=None) -> dict:
    selected = sorted(slugs) if slugs is not None else sorted(path.name for path in cases_root.iterdir() if path.is_dir())
    built = []
    staging_root = create_staging_root(output_root)
    try:
        for slug in selected:
            _validate_slug(slug)
            case_dir = cases_root / slug
            try:
                model = build_public_model(case_dir)
            except NonPublicCaseError:
                continue
            destination = staging_root / "cases" / slug / "downloads"
            _replace_package_tree(destination, package_bytes(model), output_root=staging_root)
            verify_package_tree(destination, model, output_root=staging_root)
            built.append(slug)
        replace_output_roots([(output_root, staging_root)])
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    return {"status": "built", "case_count": len(built), "slugs": built}


__all__ = [
    "FORBIDDEN_KEYS",
    "NonPublicCaseError",
    "PublicPackageError",
    "assert_semantic_parity",
    "build_case_package",
    "build_public_model",
    "build_public_packages",
    "load_json_strict",
    "model_sha256",
    "package_bytes",
    "render_markdown",
    "replace_output_roots",
    "scan_public_value",
    "semantic_leaf_paths",
    "semantic_leaf_bindings",
    "semantic_paths_sha256",
    "verify_package_tree",
]
