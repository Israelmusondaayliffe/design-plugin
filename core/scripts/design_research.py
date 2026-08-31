#!/usr/bin/env python3
"""Deterministic validation helpers for Design research, forensics, and directions.

This module performs no network access and does not choose aesthetic taste. It validates
structured artifacts, applies the approved candidate score model, preserves evidence
provenance, and catches shallow multi-reference averaging before system definition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_state_validation import load_state as load_design_state

EVIDENCE_CLASSES = {"observed", "measured", "inferred", "estimated", "recommended", "unknown"}
CONFIDENCE = {"high", "medium", "low"}
SCORE_KEYS = ("evidence_quality", "craft_threshold", "project_fit", "feasibility")
SCORE_WEIGHTS = {
    "evidence_quality": 0.20,
    "craft_threshold": 0.25,
    "project_fit": 0.40,
    "feasibility": 0.15,
}
DIRECTION_DIMENSIONS = (
    "composition",
    "typography",
    "color",
    "density",
    "imagery",
    "motion",
    "interaction",
    "hierarchy",
    "surfaces",
)
ROLE_DOMAINS = {"color", "media", "density", "typography", "component", "motion", "interaction", "layout"}
REQUIRED_ROLE_DOMAINS = {"color", "media", "density"}
ROLE_ACTIONS = {"preserve", "adapt", "reject"}
SECONDARY_ROLES = {
    "navigation behavior",
    "form behavior",
    "data visualization",
    "mobile behavior",
    "content hierarchy",
    "typography detail",
    "imagery treatment",
    "motion behavior",
    "component anatomy",
    "accessibility behavior",
    "flow structure",
    "density treatment",
}
SOURCE_LANES = {"project-local", "user-provided", "corpus", "live-public"}
PLAN_MODES = {"substantial", "bounded-repair", "audit"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class ValidationError(ValueError):
    """Raised when a structured research artifact violates the Design contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{label} must be non-empty text")
    return value.strip()


def _number(value: Any, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric")
    number = float(value)
    _require(math.isfinite(number) and 0 <= number <= 100, f"{label} must be between 0 and 100")
    return number


def _string_list(value: Any, label: str, minimum: int = 0) -> list[str]:
    _require(isinstance(value, list) and len(value) >= minimum, f"{label} must be a list with at least {minimum} item(s)")
    cleaned = []
    for index, item in enumerate(value):
        cleaned.append(_text(item, f"{label}[{index}]"))
    return cleaned


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_current_understanding_gate(
    understanding_hash: str,
    project_root: str | Path | None,
    label: str,
) -> None:
    if project_root is None:
        return
    root = Path(project_root).expanduser().resolve()
    state_path = root / ".design/state.json"
    if not state_path.is_file():
        return
    try:
        state = load_design_state(root)
    except RuntimeError as exc:
        raise ValidationError(f"{label} cannot validate Design state authority: {exc}") from exc
    gate = state.get("gates", {}).get("understanding")
    _require(
        isinstance(gate, dict) and gate.get("status") in {"approved", "skipped"},
        f"{label} requires a current understanding gate when Design state exists",
    )
    _require(
        gate.get("artifact_path") == ".design/shared-understanding.md",
        f"{label} understanding gate is not bound to the canonical artifact",
    )
    artifact = root / ".design/shared-understanding.md"
    _require(artifact.is_file(), f"{label} approved understanding artifact is missing")
    current = sha256(artifact)
    _require(gate.get("artifact_sha256") == current, f"{label} understanding gate is stale")
    _require(
        understanding_hash == current,
        f"{label} approved_understanding_sha256 does not match current gate evidence",
    )


def validate_research_plan(
    plan: dict[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(plan, dict), "research plan must be an object")
    _require(plan.get("schema_version") == "1.0", "research plan schema_version must be 1.0")
    understanding_hash = _text(plan.get("approved_understanding_sha256"), "approved_understanding_sha256")
    _require(HEX64.fullmatch(understanding_hash) is not None, "approved_understanding_sha256 must be a 64-character SHA-256 hex digest")
    _validate_current_understanding_gate(understanding_hash.lower(), project_root, "research plan")

    mode = plan.get("mode")
    _require(mode in PLAN_MODES, f"research plan mode must be one of {sorted(PLAN_MODES)}")

    questions = plan.get("research_questions")
    _require(isinstance(questions, list), "research_questions must be a list")
    if mode == "substantial":
        _require(3 <= len(questions) <= 8, "substantial research requires 3-8 research questions")
    else:
        _require(1 <= len(questions) <= 8, "bounded research requires 1-8 research questions")
    for index, question in enumerate(questions):
        _text(question, f"research_questions[{index}]", 4)

    axes = plan.get("search_axes")
    _require(isinstance(axes, list), "search_axes must be a list")
    normalized_axes = [_text(axis, f"search_axes[{index}]").casefold() for index, axis in enumerate(axes)]
    _require(len(set(normalized_axes)) >= (4 if mode == "substantial" else 2), "research plan does not cover enough distinct search axes")

    lanes = plan.get("source_lanes")
    _require(isinstance(lanes, list) and lanes, "source_lanes must be a non-empty list")
    _require(set(lanes) <= SOURCE_LANES, f"unknown source lane; allowed: {sorted(SOURCE_LANES)}")

    targets = plan.get("targets")
    _require(isinstance(targets, dict), "targets must be an object")
    candidates = targets.get("candidates")
    dossiers = targets.get("dossiers")
    directions = targets.get("directions")
    _require(
        all(isinstance(item, int) and not isinstance(item, bool) for item in (candidates, dossiers, directions)),
        "target counts must be integers",
    )
    if mode == "substantial":
        _require(8 <= candidates <= 12, "substantial candidate target must be 8-12")
        _require(5 <= dossiers <= 8, "substantial dossier target must be 5-8")
        _require(3 <= directions <= 5, "substantial direction target must be 3-5")
    elif mode == "bounded-repair":
        _require(1 <= candidates <= 6, "bounded-repair candidate target must be 1-6")
        _require(1 <= dossiers <= 4, "bounded-repair dossier target must be 1-4")
        _require(directions == 1, "bounded-repair direction target must be 1")
    else:
        _require(1 <= candidates <= 12, "audit candidate target must be 1-12")
        _require(1 <= dossiers <= 8, "audit dossier target must be 1-8")
        _require(directions == 0, "audit research does not require design directions")

    thresholds = plan.get("thresholds")
    _require(isinstance(thresholds, dict), "thresholds must be an object")
    evidence_floor = _number(thresholds.get("evidence_quality"), "thresholds.evidence_quality")
    craft_floor = _number(thresholds.get("craft_threshold"), "thresholds.craft_threshold")
    _require(evidence_floor >= 40, "evidence quality floor cannot be below 40")
    _require(craft_floor >= 55, "craft threshold floor cannot be below 55")

    _text(plan.get("decision_to_make"), "decision_to_make", 8)
    _string_list(plan.get("known_evidence_limitations", []), "known_evidence_limitations")
    _string_list(plan.get("stop_conditions", []), "stop_conditions")
    return plan


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(candidate, dict), "candidate must be an object")
    _text(candidate.get("slug"), "candidate.slug")
    _text(candidate.get("source_name"), "candidate.source_name")
    _text(candidate.get("source_url"), "candidate.source_url")
    _require(candidate.get("source_lane") in SOURCE_LANES, f"candidate.source_lane must be one of {sorted(SOURCE_LANES)}")

    scores = candidate.get("scores")
    reasons = candidate.get("score_reasons")
    _require(isinstance(scores, dict), "candidate.scores must be an object")
    _require(isinstance(reasons, dict), "candidate.score_reasons must be an object")
    for key in SCORE_KEYS:
        _number(scores.get(key), f"candidate.scores.{key}")
        _text(reasons.get(key), f"candidate.score_reasons.{key}", 6)

    classes = candidate.get("evidence_classes", [])
    _require(isinstance(classes, list) and classes, "candidate.evidence_classes must be a non-empty list")
    _require(set(classes) <= EVIDENCE_CLASSES, "candidate contains unknown evidence class")
    return candidate


def score_candidate(candidate: dict[str, Any], evidence_floor: float = 50, craft_floor: float = 65) -> dict[str, Any]:
    validate_candidate(candidate)
    evidence_floor = _number(evidence_floor, "evidence_floor")
    craft_floor = _number(craft_floor, "craft_floor")
    scores = candidate["scores"]
    weighted = round(sum(float(scores[key]) * SCORE_WEIGHTS[key] for key in SCORE_KEYS), 2)
    rejection_reasons: list[str] = []
    if float(scores["evidence_quality"]) < evidence_floor:
        rejection_reasons.append(f"evidence_quality below {evidence_floor:g}")
    if float(scores["craft_threshold"]) < craft_floor:
        rejection_reasons.append(f"craft_threshold below {craft_floor:g}")
    result = dict(candidate)
    result["weighted_score"] = weighted
    result["eligible"] = not rejection_reasons
    result["rejection_reasons"] = rejection_reasons
    return result


def rank_candidates(
    candidates: list[dict[str, Any]], evidence_floor: float = 50, craft_floor: float = 65
) -> list[dict[str, Any]]:
    _require(isinstance(candidates, list) and candidates, "candidates must be a non-empty list")
    scored = [score_candidate(candidate, evidence_floor, craft_floor) for candidate in candidates]
    return sorted(scored, key=lambda candidate: (candidate["eligible"], candidate["weighted_score"]), reverse=True)


def validate_role_invariants(items: Any, label: str = "role_invariants") -> list[dict[str, Any]]:
    _require(isinstance(items, list) and items, f"{label} must be a non-empty list")
    seen_domains: set[str] = set()
    for index, item in enumerate(items):
        _require(isinstance(item, dict), f"{label}[{index}] must be an object")
        domain = item.get("domain")
        _require(domain in ROLE_DOMAINS, f"{label}[{index}].domain is invalid")
        _require(domain not in seen_domains, f"{label} repeats domain {domain}")
        seen_domains.add(domain)
        _text(item.get("source_role"), f"{label}[{index}].source_role", 3)
        _text(item.get("target_role"), f"{label}[{index}].target_role", 3)
        _require(item.get("action") in ROLE_ACTIONS, f"{label}[{index}].action must be preserve, adapt, or reject")
        _text(item.get("reason"), f"{label}[{index}].reason", 6)
    missing = REQUIRED_ROLE_DOMAINS - seen_domains
    _require(not missing, f"{label} must explicitly cover {sorted(missing)}")
    return items


def validate_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(dossier, dict), "dossier must be an object")
    _require(dossier.get("schema_version") == "1.0", "dossier schema_version must be 1.0")

    reference = dossier.get("reference")
    _require(isinstance(reference, dict), "dossier.reference must be an object")
    _text(reference.get("slug"), "dossier.reference.slug")
    _text(reference.get("source_url"), "dossier.reference.source_url")
    _require(reference.get("source_lane") in SOURCE_LANES, "dossier.reference.source_lane is invalid")

    facts = dossier.get("facts")
    _require(isinstance(facts, list) and len(facts) >= 3, "dossier requires at least 3 facts")
    evidence_ids: set[str] = set()
    for index, fact in enumerate(facts):
        _require(isinstance(fact, dict), f"facts[{index}] must be an object")
        evidence_id = _text(fact.get("evidence_id"), f"facts[{index}].evidence_id")
        _require(evidence_id not in evidence_ids, f"duplicate evidence_id {evidence_id}")
        evidence_ids.add(evidence_id)
        _require(fact.get("class") in EVIDENCE_CLASSES, f"facts[{index}].class is invalid")
        _text(fact.get("claim"), f"facts[{index}].claim", 8)
        _text(fact.get("source_locator"), f"facts[{index}].source_locator", 2)
        _require(fact.get("confidence") in CONFIDENCE, f"facts[{index}].confidence is invalid")

    dimensions = dossier.get("dimensions")
    _require(isinstance(dimensions, dict), "dossier.dimensions must be an object")
    for dimension in DIRECTION_DIMENSIONS:
        entry = dimensions.get(dimension)
        _require(isinstance(entry, dict), f"dossier.dimensions.{dimension} is required")
        _text(entry.get("finding"), f"dossier.dimensions.{dimension}.finding", 5)
        refs = entry.get("evidence_ids", [])
        _require(isinstance(refs, list), f"dossier.dimensions.{dimension}.evidence_ids must be a list")
        _require(set(refs) <= evidence_ids, f"dossier.dimensions.{dimension} references unknown evidence ids")
        _require(entry.get("confidence") in CONFIDENCE, f"dossier.dimensions.{dimension}.confidence is invalid")
        _require(
            entry.get("trait_status") in {"essential", "adaptable", "incidental", "unknown"},
            f"dossier.dimensions.{dimension}.trait_status is invalid",
        )

    essential = dossier.get("essential_traits")
    incidental = dossier.get("incidental_traits")
    _require(isinstance(essential, list) and 3 <= len(essential) <= 7, "dossier requires 3-7 essential traits")
    _require(isinstance(incidental, list) and incidental, "dossier requires at least one incidental trait")
    for index, item in enumerate(essential):
        _text(item, f"essential_traits[{index}]", 5)
    for index, item in enumerate(incidental):
        _text(item, f"incidental_traits[{index}]", 3)

    validate_role_invariants(dossier.get("role_invariants"), "dossier.role_invariants")
    _require(dossier.get("confidence") in CONFIDENCE, "dossier.confidence is invalid")
    risks = dossier.get("misuse_risks")
    _require(isinstance(risks, list) and risks, "dossier requires misuse_risks")
    limitations = dossier.get("evidence_limitations")
    _require(isinstance(limitations, list), "dossier.evidence_limitations must be a list")
    return dossier


def validate_evidence_refs(items: Any, label: str = "evidence_refs") -> list[dict[str, str]]:
    _require(isinstance(items, list) and items, f"{label} must be a non-empty list")
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        _require(isinstance(item, dict), f"{label}[{index}] must be an object")
        slug = _text(item.get("slug"), f"{label}[{index}].slug")
        evidence_id = _text(item.get("evidence_id"), f"{label}[{index}].evidence_id")
        key = (slug, evidence_id)
        _require(key not in seen, f"{label} contains duplicate {slug}:{evidence_id}")
        seen.add(key)
    return items


def validate_direction(direction: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(direction, dict), "direction must be an object")
    _text(direction.get("id"), "direction.id")
    _text(direction.get("title"), "direction.title")
    _text(direction.get("thesis"), "direction.thesis", 8)

    primary = direction.get("primary_reference")
    _require(isinstance(primary, dict), "direction.primary_reference must be an object")
    primary_slug = _text(primary.get("slug"), "direction.primary_reference.slug")
    _require(
        primary.get("responsibility") == "dominant visual foundation",
        "primary reference must own the dominant visual foundation",
    )

    preserved = direction.get("preserved_primary_traits")
    _require(
        isinstance(preserved, list) and 3 <= len(preserved) <= 5,
        "direction requires 3-5 preserved primary traits",
    )
    for index, trait in enumerate(preserved):
        _text(trait, f"preserved_primary_traits[{index}]", 5)

    secondary = direction.get("secondary_references", [])
    _require(isinstance(secondary, list) and len(secondary) <= 3, "direction supports at most 3 secondary references")
    seen_roles: set[str] = set()
    seen_slugs: set[str] = set()
    for index, item in enumerate(secondary):
        _require(isinstance(item, dict), f"secondary_references[{index}] must be an object")
        slug = _text(item.get("slug"), f"secondary_references[{index}].slug")
        _require(slug != primary_slug, "primary reference cannot also be secondary")
        _require(slug not in seen_slugs, "duplicate secondary reference")
        seen_slugs.add(slug)
        role = item.get("role")
        _require(
            role in SECONDARY_ROLES,
            f"secondary reference role must be narrow; allowed: {sorted(SECONDARY_ROLES)}",
        )
        _require(role not in seen_roles, "secondary reference roles must be distinct")
        seen_roles.add(role)
        _text(item.get("scope"), f"secondary_references[{index}].scope", 6)

    profile = direction.get("dimension_signatures")
    _require(isinstance(profile, dict), "direction.dimension_signatures must be an object")
    for dimension in DIRECTION_DIMENSIONS:
        _text(profile.get(dimension), f"direction.dimension_signatures.{dimension}", 3)

    validate_role_invariants(direction.get("role_invariants"), "direction.role_invariants")
    validate_evidence_refs(direction.get("evidence_refs"), "direction.evidence_refs")

    traits = direction.get("signature_traits")
    _require(isinstance(traits, list) and 3 <= len(traits) <= 5, "direction requires 3-5 signature traits")
    forbidden = direction.get("forbidden_drift")
    _require(isinstance(forbidden, list) and len(forbidden) >= 3, "direction requires at least 3 forbidden drift rules")
    risks = direction.get("risks")
    _require(isinstance(risks, list) and risks, "direction requires risks")
    rejected = direction.get("rejected_alternatives")
    _require(isinstance(rejected, list) and rejected, "direction.rejected_alternatives must be a non-empty list")
    for index, item in enumerate(rejected):
        _require(isinstance(item, dict), f"rejected_alternatives[{index}] must be an object")
        _text(item.get("alternative"), f"rejected_alternatives[{index}].alternative", 3)
        _text(item.get("reason"), f"rejected_alternatives[{index}].reason", 6)
    _text(direction.get("feasibility"), "direction.feasibility", 8)

    presentation = direction.get("presentation")
    _require(isinstance(presentation, dict), "direction.presentation must be an object")
    _text(presentation.get("summary"), "direction.presentation.summary", 8)
    _text(presentation.get("fit"), "direction.presentation.fit", 8)
    _text(presentation.get("risk"), "direction.presentation.risk", 5)
    _text(presentation.get("expert_detail"), "direction.presentation.expert_detail", 8)
    return direction


def direction_difference_count(a: dict[str, Any], b: dict[str, Any]) -> int:
    pa = a["dimension_signatures"]
    pb = b["dimension_signatures"]
    return sum(
        str(pa[key]).strip().casefold() != str(pb[key]).strip().casefold()
        for key in DIRECTION_DIMENSIONS
    )


def validate_direction_set(
    payload: dict[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    _require(isinstance(payload, dict), "direction set must be an object")
    _require(payload.get("schema_version") == "1.0", "direction set schema_version must be 1.0")
    understanding_hash = _text(payload.get("approved_understanding_sha256"), "approved_understanding_sha256")
    _require(HEX64.fullmatch(understanding_hash) is not None, "direction set must bind to a valid approved understanding SHA-256")
    _validate_current_understanding_gate(understanding_hash.lower(), project_root, "direction set")

    mode = payload.get("mode")
    _require(mode in {"substantial", "bounded-repair"}, "direction set mode is invalid")
    directions = payload.get("directions")
    _require(isinstance(directions, list), "directions must be a list")
    if mode == "substantial":
        _require(3 <= len(directions) <= 5, "substantial work requires 3-5 directions")
    else:
        _require(len(directions) == 1, "bounded repair requires exactly one direction")

    ids: set[str] = set()
    primary_slugs: set[str] = set()
    for direction in directions:
        validate_direction(direction)
        _require(direction["id"] not in ids, "direction ids must be unique")
        ids.add(direction["id"])
        slug = direction["primary_reference"]["slug"]
        if mode == "substantial":
            _require(slug not in primary_slugs, "substantial directions must use distinct primary foundations")
        primary_slugs.add(slug)

    if mode == "substantial":
        for left in range(len(directions)):
            for right in range(left + 1, len(directions)):
                difference = direction_difference_count(directions[left], directions[right])
                _require(
                    difference >= 4,
                    f"directions {directions[left]['id']} and {directions[right]['id']} differ across only "
                    f"{difference} signature dimensions; at least 4 required",
                )
    return payload


def _catalog_entries(payload: Any) -> tuple[list[dict[str, Any]], bool]:
    """Return metadata-rich catalog entries and whether detail retrieval is still needed."""
    if isinstance(payload, list):
        entries = [item for item in payload if isinstance(item, dict)]
        return entries, len(entries) != len(payload)
    if not isinstance(payload, dict):
        raise ValidationError("catalog manifest must be an object or list")
    for key in ("entries", "cases"):
        value = payload.get(key)
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return value, False
    seed_cases = payload.get("seed_cases")
    if isinstance(seed_cases, list) and all(isinstance(item, str) for item in seed_cases):
        return [{"slug": slug} for slug in seed_cases], True
    return [], True


def shortlist_manifest(entries: Any, criteria: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Route exact catalog facets without pretending compact seed metadata was inspected."""
    _require(isinstance(criteria, dict), "criteria must be an object")
    _require(isinstance(limit, int) and 1 <= limit <= 12, "limit must be an integer from 1 to 12")
    catalog, needs_detail = _catalog_entries(entries)
    _require(catalog, "catalog does not contain any routable entries")

    if needs_detail:
        return [
            {
                "slug": entry["slug"],
                "routing_score": 0,
                "routing_reasons": [
                    "compact manifest has no facet metadata; retrieve the case summary or use live public research before judging fit"
                ],
                "needs_detail": True,
            }
            for entry in catalog[:limit]
        ]

    wanted_platforms = set(criteria.get("platforms", []))
    wanted_products = set(criteria.get("product_types", []))
    wanted_archetypes = set(criteria.get("archetypes", []))
    wanted_industries = set(criteria.get("industries", []))
    wanted_density = criteria.get("density")
    scored: list[dict[str, Any]] = []
    for entry in catalog:
        score = 0
        reasons: list[str] = []
        for field, wanted, weight in (
            ("platforms", wanted_platforms, 3),
            ("product_types", wanted_products, 3),
            ("archetypes", wanted_archetypes, 2),
            ("industries", wanted_industries, 1),
        ):
            overlap = wanted & set(entry.get(field, []))
            if overlap:
                score += weight * len(overlap)
                reasons.append(f"{field}: {', '.join(sorted(overlap))}")
        if wanted_density and entry.get("density") == wanted_density:
            score += 1
            reasons.append(f"density: {wanted_density}")
        if score:
            scored.append(
                {
                    "slug": entry.get("slug"),
                    "routing_score": score,
                    "routing_reasons": reasons,
                    "needs_detail": False,
                }
            )
    return sorted(scored, key=lambda item: item["routing_score"], reverse=True)[:limit]


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Design research, forensic, and direction artifacts without network access."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("validate-plan")
    command.add_argument("path")
    command.add_argument("--project-root", default=".")

    command = sub.add_parser("rank")
    command.add_argument("path", help="JSON array of candidates")
    command.add_argument("--evidence-floor", type=float, default=50)
    command.add_argument("--craft-floor", type=float, default=65)

    command = sub.add_parser("validate-dossier")
    command.add_argument("path")

    command = sub.add_parser("validate-directions")
    command.add_argument("path")
    command.add_argument("--project-root", default=".")

    command = sub.add_parser("shortlist")
    command.add_argument("manifest")
    command.add_argument("criteria")
    command.add_argument("--limit", type=int, default=8)

    args = parser.parse_args()
    try:
        if args.command == "validate-plan":
            validate_research_plan(load_json(args.path), args.project_root)
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "rank":
            _dump(rank_candidates(load_json(args.path), args.evidence_floor, args.craft_floor))
        elif args.command == "validate-dossier":
            validate_dossier(load_json(args.path))
            _dump({"status": "pass", "artifact": args.path})
        elif args.command == "validate-directions":
            payload = load_json(args.path)
            validate_direction_set(payload, args.project_root)
            differences = []
            directions = payload["directions"]
            for left in range(len(directions)):
                for right in range(left + 1, len(directions)):
                    differences.append(
                        {
                            "a": directions[left]["id"],
                            "b": directions[right]["id"],
                            "different_dimensions": direction_difference_count(
                                directions[left], directions[right]
                            ),
                        }
                    )
            _dump({"status": "pass", "pairwise_distinctness": differences})
        else:
            _dump(shortlist_manifest(load_json(args.manifest), load_json(args.criteria), args.limit))
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Design research validation failed: {exc}") from exc


if __name__ == "__main__":
    main()
