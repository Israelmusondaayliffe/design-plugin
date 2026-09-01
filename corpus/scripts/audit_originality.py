#!/usr/bin/env python3
"""Audit alpha-corpus prose for literal repetition and slot-filled templates."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "corpus/cases"
ALLOCATION = ROOT / "review/wave-11-alpha-allocation.json"
DEFAULT_REPORT = ROOT / "review/wave-11-originality-audit.json"
BOUND_FILES = ("DESIGN.md", "metadata.json", "evidence.json", "coverage.json", "preview-spec.json")
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
BANNED = (
    "delve", "leverage", "unlock", "journey", "game-changer", "paradigm shift", "deep dive",
    "synergy", "robust", "disruptive", "revolutionary", "groundbreaking", "navigate the landscape",
    "in today's fast-paced world", "it is not just", "at the end of the day", "the bottom line is",
    "moving forward",
)
REQUIRED_HEADINGS = {
    "# title", "## visual thesis", "## signature relationships", "## adaptation rules",
    "## failure modes", "## evidence boundary", "## evidence confidence and gaps",
}
COMPLIANCE_SECTIONS = {
    "confidence and unknowns", "evidence confidence and gaps", "scope limits", "known and unknown",
    "evidence boundary",
}
JOURNEY_LABELS = {
    "browse-discover": "browsing and discovery",
    "evaluate-convert": "evaluation and conversion",
    "create-manage": "creation and management",
    "monitor-operate": "monitoring and operations",
    "learn-progress": "learning and progress",
    "transact-checkout": "transactions and checkout",
    "onboard-configure": "onboarding and configuration",
    "complete-service": "service completion",
    "visualize-explore": "visual exploration",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def collect_strings(value) -> list[str]:
    if isinstance(value, str):
        if value.startswith("https://") or value in {"1.0", "low", "medium", "high", "review", "public", "private", "blocked"}:
            return []
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in collect_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in collect_strings(item)]
    return []


def design_analysis(text: str) -> str:
    """Remove fixed disclosure sections from duplication analysis, not banned-language review."""
    kept = []
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            if section not in COMPLIANCE_SECTIONS:
                kept.append(line)
            continue
        if section not in COMPLIANCE_SECTIONS:
            kept.append(line)
    return "\n".join(kept)


def narrative_segments(case_dir: Path, *, include_compliance: bool = False) -> list[str]:
    design = (case_dir / "DESIGN.md").read_text(encoding="utf-8")
    parts = [design if include_compliance else design_analysis(design)]
    metadata = read_json(case_dir / "metadata.json")
    for key in ("summary", "signature_traits", "best_for", "avoid_for"):
        parts.extend(collect_strings(metadata[key]))
    evidence = read_json(case_dir / "evidence.json")
    parts.extend(
        item["claim"] for item in evidence["items"]
        if "establishes source identity and public availability only" not in item["notes"].lower()
    )
    coverage = read_json(case_dir / "coverage.json")
    for key in ("visual_thesis", "signature_moves", "failure_modes", "suitable_uses", "unsuitable_uses"):
        parts.extend(collect_strings(coverage[key]))
    preview = read_json(case_dir / "preview-spec.json")
    parts.extend([preview["pattern"], preview["layout"], preview["motion"]])
    segments = []
    for part in parts:
        segments.extend(
            item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", part)
            if item.strip() and not item.lstrip().startswith("#")
        )
    return segments


def design_sentences(text: str) -> set[str]:
    sentences = set()
    for line in design_analysis(text).splitlines():
        stripped = re.sub(r"^[-*]\s+", "", line.strip())
        stripped = re.sub(r"^[0-9]+\.\s+", "", stripped)
        stripped = re.sub(r"^#+\s+", "", stripped)
        if len(normalize_words(stripped)) >= 8:
            sentences.add(" ".join(normalize_words(stripped)))
    return sentences


def complete_case_prose(case_dir: Path) -> str:
    """Return every human-authored string for banned-language and mechanical scans."""
    parts = [(case_dir / "DESIGN.md").read_text(encoding="utf-8")]
    metadata = read_json(case_dir / "metadata.json")
    for key in ("name", "source_name", "summary", "signature_traits", "best_for", "avoid_for"):
        parts.extend(collect_strings(metadata[key]))
    evidence = read_json(case_dir / "evidence.json")
    for item in evidence["items"]:
        parts.extend((item["claim"], item["notes"]))
    tokens = read_json(case_dir / "tokens.json")
    for item in tokens["tokens"]:
        parts.extend((item["role"], item["notes"]))
    coverage = read_json(case_dir / "coverage.json")
    for key, value in coverage.items():
        if key not in {"schema_version", "source", "study_date", "platform", "category", "industry", "archetype", "confidence"}:
            parts.extend(collect_strings(value))
    preview = read_json(case_dir / "preview-spec.json")
    parts.extend(preview[key] for key in ("pattern", "layout", "motion"))
    source = read_json(case_dir / "source.json")
    parts.extend(source["limitations"])
    return "\n".join(parts)


def case_terms(case_dir: Path) -> list[str]:
    """Return identifiers only; never erase complete narrative fields as slots."""
    metadata = read_json(case_dir / "metadata.json")
    evidence = read_json(case_dir / "evidence.json")
    values = [metadata["name"], metadata["source_name"], metadata["slug"], urlparse(metadata["source_url"]).hostname or ""]
    values.extend(item["locator"] for item in evidence["items"])
    cleaned = {" ".join(str(value).split()).lower() for value in values if isinstance(value, str) and len(value.strip()) >= 3}
    return sorted(cleaned, key=len, reverse=True)


def entity_normalize(text: str, terms: list[str]) -> str:
    normalized = " ".join(text.lower().split())
    for term in terms:
        normalized = re.sub(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", " <slot> ", normalized)
    normalized = re.sub(r"https://[^\s)]+", " <url> ", normalized)
    return " ".join(normalize_words(normalized))


def structure_profile(design: str) -> str:
    sections = []
    heading = "preamble"
    counts = Counter()
    for raw in design.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            sections.append((heading, tuple(sorted(counts.items()))))
            heading = line[3:].strip().lower()
            counts = Counter()
        elif re.match(r"^[-*]\s+", line):
            counts["bullet"] += 1
        elif re.match(r"^[0-9]+\.\s+", line):
            counts["numbered"] += 1
        elif line.startswith("|"):
            counts["table"] += 1
        elif line:
            counts["prose"] += 1
    sections.append((heading, tuple(sorted(counts.items()))))
    return json.dumps(sections, separators=(",", ":"))


def corpus_binding(cases: list[Path]) -> tuple[str, dict[str, dict[str, str]]]:
    digest = hashlib.sha256()
    bindings = {}
    for case_dir in cases:
        files = {}
        for name in BOUND_FILES:
            value = hashlib.sha256((case_dir / name).read_bytes()).hexdigest()
            files[name] = value
            digest.update(f"{case_dir.name}/{name}\0{value}\n".encode("utf-8"))
        bindings[case_dir.name] = files
    return digest.hexdigest(), bindings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-findings", type=int, default=300)
    args = parser.parse_args()

    cases = sorted(path for path in CASES.iterdir() if path.is_dir())
    allocation = read_json(ALLOCATION)
    new_cases = {slug for values in allocation["new_cases"].values() for slug in values}
    literal_repeat_threshold = max(3, math.ceil(len(new_cases) * 0.12))
    normalized_template_threshold = 3

    ngram_cases: dict[tuple[str, ...], set[str]] = defaultdict(set)
    sentence_cases: dict[str, set[str]] = defaultdict(set)
    normalized_sentence_cases: dict[str, set[str]] = defaultdict(set)
    heading_cases: dict[str, set[str]] = defaultdict(set)
    profile_cases: dict[str, set[str]] = defaultdict(set)
    banned_findings = []
    mechanical_findings = []
    degenerate_normalizations = []
    summary_leads = Counter()

    for case_dir in cases:
        slug = case_dir.name
        design = (case_dir / "DESIGN.md").read_text(encoding="utf-8")
        segments = narrative_segments(case_dir)
        full_text = complete_case_prose(case_dir)
        lowered = full_text.lower()
        for pattern, label in (
            (r"\.\.", "double period"),
            (r"\bintakeand\b", "joined words"),
            (r"\bintergalacticdesign\b", "joined words"),
            (r"\bIOS\b", "incorrect iOS capitalization"),
            (r"\bios\b", "incorrect iOS capitalization"),
            (r"\biphone\b", "incorrect iPhone capitalization"),
            (r"\bandroid\b", "incorrect Android capitalization"),
            (r"\bsupplies the destination test\b", "subject-verb agreement in flows"),
            (r"\bis the decisive fit\b", "fragile lane-fit agreement"),
        ):
            haystack = full_text if pattern in {r"\bIOS\b", r"\bios\b", r"\biphone\b", r"\bandroid\b"} else lowered
            if re.search(pattern, haystack):
                mechanical_findings.append({"slug": slug, "issue": label})
        for heading in re.findall(r"^## (.+ in practice)$", design, re.MULTILINE):
            words = [word for word in normalize_words(heading) if word not in {"in", "practice"}]
            source_words = heading.rsplit(" in practice", 1)[0].split()
            if len(words) > 1 and all(word[:1].isupper() for word in source_words):
                mechanical_findings.append({"slug": slug, "issue": "title-case generated heading"})
        for phrase in BANNED:
            if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", lowered):
                banned_findings.append({"slug": slug, "phrase": phrase})
        for segment in segments:
            words = normalize_words(segment)
            for index in range(len(words) - 7):
                ngram_cases[tuple(words[index:index + 8])].add(slug)
        for sentence in design_sentences(design):
            sentence_cases[sentence].add(slug)
        if slug in new_cases:
            terms = case_terms(case_dir)
            for segment in segments:
                normalized = entity_normalize(segment, terms)
                if normalized in {"slot", "url"}:
                    degenerate_normalizations.append({"slug": slug, "segment": segment[:160]})
                if len(normalize_words(normalized)) >= 6:
                    normalized_sentence_cases[normalized].add(slug)
            profile_cases[structure_profile(design)].add(slug)
        for line in design.splitlines():
            if line.startswith("# "):
                heading_cases["# title"].add(slug)
            elif line.startswith("## "):
                heading_cases[line.lower()].add(slug)
        lead = normalize_words(read_json(case_dir / "metadata.json")["summary"])
        if lead:
            summary_leads[lead[0]] += 1

    repeated_ngrams = [
        {"phrase": " ".join(words), "case_count": len(slugs), "slugs": sorted(slugs)}
        for words, slugs in ngram_cases.items() if len(slugs) >= literal_repeat_threshold
    ]
    repeated_ngrams.sort(key=lambda item: (-item["case_count"], item["phrase"]))
    repeated_sentences = [
        {"sentence": sentence, "case_count": len(slugs), "slugs": sorted(slugs)}
        for sentence, slugs in sentence_cases.items() if len(slugs) >= literal_repeat_threshold
    ]
    repeated_sentences.sort(key=lambda item: (-item["case_count"], item["sentence"]))
    normalized_templates = [
        {"template": sentence, "case_count": len(slugs), "slugs": sorted(slugs)}
        for sentence, slugs in normalized_sentence_cases.items() if len(slugs) >= normalized_template_threshold
    ]
    normalized_templates.sort(key=lambda item: (-item["case_count"], item["template"]))
    dominant_profiles = [
        {"profile": profile, "case_count": len(slugs), "slugs": sorted(slugs)}
        for profile, slugs in profile_cases.items() if len(slugs) > len(new_cases) * 0.80
    ]
    uniform_optional_headings = [
        {"heading": heading, "case_count": len(slugs), "slugs": sorted(slugs)}
        for heading, slugs in heading_cases.items()
        if heading not in REQUIRED_HEADINGS and len(slugs) > len(cases) / 2
    ]
    dominant_summary_lead = summary_leads.most_common(1)[0] if summary_leads else (None, 0)
    summary_lead_issue = dominant_summary_lead[1] > len(cases) / 2
    failures = (
        banned_findings or mechanical_findings or degenerate_normalizations or repeated_ngrams or repeated_sentences
        or normalized_templates or dominant_profiles or uniform_optional_headings or summary_lead_issue
    )
    tree_sha256, bindings = corpus_binding(cases)
    status = "fail" if failures else "pass"
    report = {
        "schema_version": "1.0",
        "case_count": len(cases),
        "new_case_count": len(new_cases),
        "status": status,
        "method": "Literal repetition plus strict normalization of case identity, source identity, URLs, and locators only. Complete traits, uses, failures, visual thesis, and preview copy remain visible to repetition scoring. Every human-authored string in the case, including lane_fit and flows, is scanned for banned language and mechanical defects. Fixed confidence and rights disclosures are excluded only from repetition scoring.",
        "corpus_binding_sha256": tree_sha256,
        "bound_files": list(BOUND_FILES),
        "case_bindings": bindings,
        "rules": {
            "literal_repeat_case_threshold": literal_repeat_threshold,
            "normalized_template_case_threshold": normalized_template_threshold,
            "banned_phrase_count": len(banned_findings),
            "mechanical_prose_finding_count": len(mechanical_findings),
            "degenerate_normalization_count": len(degenerate_normalizations),
            "repeated_eight_word_phrase_count": len(repeated_ngrams),
            "repeated_narrative_sentence_count": len(repeated_sentences),
            "entity_normalized_template_count": len(normalized_templates),
            "dominant_structure_profile_count": len(dominant_profiles),
            "uniform_optional_heading_count": len(uniform_optional_headings),
            "dominant_summary_lead": {"word": dominant_summary_lead[0], "count": dominant_summary_lead[1], "fails": summary_lead_issue},
        },
        "banned_phrases": banned_findings[:args.max_findings],
        "mechanical_prose_findings": mechanical_findings[:args.max_findings],
        "degenerate_normalizations": degenerate_normalizations[:args.max_findings],
        "repeated_eight_word_phrases": repeated_ngrams[:args.max_findings],
        "repeated_narrative_sentences": repeated_sentences[:args.max_findings],
        "entity_normalized_templates": normalized_templates[:args.max_findings],
        "dominant_structure_profiles": dominant_profiles[:args.max_findings],
        "uniform_optional_headings": uniform_optional_headings,
    }
    write_json(args.report, report)
    print(json.dumps({"status": status, **report["rules"]}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
