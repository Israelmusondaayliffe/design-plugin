#!/usr/bin/env python3
"""Wave 5 regression tests for research, forensics, direction distinctness, and anti-averaging."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core/scripts/design_research.py"
spec = importlib.util.spec_from_file_location("design_research", MODULE_PATH)
research = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(research)

UNDERSTANDING_HASH = "a" * 64
DIMENSIONS = research.DIRECTION_DIMENSIONS


def valid_plan(mode: str = "substantial") -> dict:
    targets = {
        "substantial": {"candidates": 8, "dossiers": 5, "directions": 3},
        "bounded-repair": {"candidates": 3, "dossiers": 2, "directions": 1},
        "audit": {"candidates": 4, "dossiers": 2, "directions": 0},
    }[mode]
    questions = [
        "Which composition model best supports the primary user job?",
        "What density is appropriate for expert versus narrative states?",
        "Which interaction patterns preserve accessibility and speed?",
    ]
    if mode != "substantial":
        questions = questions[:2]
    return {
        "schema_version": "1.0",
        "approved_understanding_sha256": UNDERSTANDING_HASH,
        "mode": mode,
        "decision_to_make": "Choose evidence-backed design logic for the approved product brief.",
        "research_questions": questions,
        "search_axes": ["product type", "platform", "density", "emotional character"] if mode == "substantial" else ["product type", "platform"],
        "source_lanes": ["project-local", "corpus", "live-public"],
        "targets": targets,
        "thresholds": {"evidence_quality": 50, "craft_threshold": 65},
        "known_evidence_limitations": [],
        "stop_conditions": ["Return to shared understanding if research changes the product definition."],
    }


def candidate(slug: str, evidence: int = 80, craft: int = 80, fit: int = 80, feasibility: int = 80) -> dict:
    return {
        "slug": slug,
        "source_name": slug.replace("-", " ").title(),
        "source_url": f"https://example.com/{slug}",
        "source_lane": "live-public",
        "scores": {
            "evidence_quality": evidence,
            "craft_threshold": craft,
            "project_fit": fit,
            "feasibility": feasibility,
        },
        "score_reasons": {
            "evidence_quality": "Relevant states and provenance are directly inspectable.",
            "craft_threshold": "Hierarchy, typography, density, interaction, and responsive behavior are resolved.",
            "project_fit": "The product, audience, workflow, density, and emotional posture match the approved brief.",
            "feasibility": "Important traits can be implemented within the approved stack and scope.",
        },
        "evidence_classes": ["observed", "inferred"],
    }


def role_invariants() -> list[dict]:
    return [
        {
            "domain": "color",
            "source_role": "Accent is reserved for action and focus.",
            "target_role": "Brand accent remains action and focus only.",
            "action": "adapt",
            "reason": "Preserve semantic scarcity while adapting the literal hue.",
        },
        {
            "domain": "media",
            "source_role": "Imagery carries the primary narrative hierarchy.",
            "target_role": "Project imagery remains the narrative carrier.",
            "action": "preserve",
            "reason": "Demoting imagery would collapse the source composition logic.",
        },
        {
            "domain": "density",
            "source_role": "Dense regions support expert scanning and throughput.",
            "target_role": "Operational screens remain compact while narrative screens can open up.",
            "action": "adapt",
            "reason": "Density follows the user task rather than a universal spacious default.",
        },
    ]


def dossier(slug: str) -> dict:
    facts = [
        {"evidence_id": "E1", "class": "observed", "claim": "The primary canvas carries the visual hierarchy.", "source_locator": "desktop primary state", "confidence": "high"},
        {"evidence_id": "E2", "class": "measured", "claim": "Utility controls use a compact repeated rhythm.", "source_locator": "desktop control rail", "confidence": "high"},
        {"evidence_id": "E3", "class": "inferred", "claim": "Sparse chrome protects attention around primary content.", "source_locator": "cross-state synthesis", "confidence": "medium"},
    ]
    dimensions = {
        name: {
            "finding": f"{name.title()} follows a deliberate source-specific relationship.",
            "evidence_ids": ["E1", "E2"],
            "confidence": "high",
            "trait_status": "essential" if name in {"composition", "density", "hierarchy"} else "adaptable",
        }
        for name in DIMENSIONS
    }
    return {
        "schema_version": "1.0",
        "reference": {"slug": slug, "source_url": f"https://example.com/{slug}", "source_lane": "live-public"},
        "facts": facts,
        "dimensions": dimensions,
        "essential_traits": ["Primary content owns attention.", "Utility controls maintain compact rhythm.", "Hierarchy depends on deliberate density contrast."],
        "incidental_traits": ["Exact campaign photography."],
        "role_invariants": role_invariants(),
        "misuse_risks": ["Replacing the source logic with generic rounded cards."],
        "evidence_limitations": ["Authenticated edge states were not publicly inspectable."],
        "confidence": "high",
    }


def direction(identifier: str, primary: str, signature_prefix: str) -> dict:
    return {
        "id": identifier,
        "title": f"Direction {identifier}",
        "thesis": f"A distinct {signature_prefix} design system grounded in the approved brief.",
        "primary_reference": {"slug": primary, "responsibility": "dominant visual foundation"},
        "preserved_primary_traits": ["Primary hierarchy relationship", "Characteristic density behavior", "Source-specific composition logic"],
        "secondary_references": [
            {"slug": "support-mobile", "role": "mobile behavior", "scope": "Navigation compression below tablet width only."}
        ],
        "dimension_signatures": {name: f"{signature_prefix}-{name}" for name in DIMENSIONS},
        "role_invariants": role_invariants(),
        "signature_traits": ["Distinct hierarchy", "Intentional density", "Bounded color roles"],
        "forbidden_drift": ["Do not replace hierarchy with generic cards.", "Do not round every surface by default.", "Do not turn semantic accent into decoration."],
        "risks": ["Requires disciplined content and component prioritization."],
        "rejected_alternatives": [{"alternative": "Safe midpoint", "reason": "It averages away the dominant reference's strongest relationships."}],
        "evidence_refs": [{"slug": primary, "evidence_id": "E1"}],
        "feasibility": "Feasible in the approved implementation environment without new dependencies.",
        "presentation": {
            "summary": f"{signature_prefix} changes the product's dominant composition and interaction character.",
            "fit": "It matches the approved audience, task density, and emotional posture.",
            "risk": "The main risk is losing its sharp primary trait during implementation.",
            "expert_detail": "Full scores, role maps, rejected alternatives, and forensic evidence remain available in the artifact.",
        },
    }


def write_understanding_state(root: Path, content: str = "Approved current scope.\n") -> str:
    understanding = root / ".design/shared-understanding.md"
    understanding.parent.mkdir(parents=True, exist_ok=True)
    understanding.write_text(content, encoding="utf-8")
    digest = research.sha256(understanding)
    state = {
        "schema_version": "1.0",
        "plugin": "design",
        "revision": 0,
        "workflow": "run",
        "route": "standard",
        "phase": "researching",
        "status": "active",
        "phase_before_block": None,
        "gates": {
            "understanding": {
                "gate": "understanding",
                "status": "approved",
                "artifact_path": ".design/shared-understanding.md",
                "artifact_sha256": digest,
                "decided_at": "2026-08-30T00:00:00Z",
                "decision_text": "Approved",
                "warning_acknowledged": False,
                "scope": "Approved current scope.",
                "assumptions_accepted": [],
                "stale_reason": None,
                "stale_at": None,
            },
            "direction": None,
            "repository_changes": None,
        },
        "artifacts": {".design/shared-understanding.md": digest},
        "active_wave": None,
        "repair_cycle": 0,
        "repair_pass": 0,
        "repair_attempts": {},
        "blockers": [],
        "history": [{"event": "test_research_fixture", "at": "2026-08-30T00:00:00Z"}],
        "created_at": "2026-08-30T00:00:00Z",
        "updated_at": "2026-08-30T00:00:00Z",
    }
    (root / ".design/state.json").write_text(json.dumps(state), encoding="utf-8")
    return digest


class Wave5ResearchTests(unittest.TestCase):
    def test_exit_gate_traceable_substantial_project(self) -> None:
        research.validate_research_plan(valid_plan())
        candidates = [candidate(f"candidate-{index}", fit=90 - index) for index in range(8)]
        ranked = research.rank_candidates(candidates)
        self.assertEqual(len(ranked), 8)
        self.assertTrue(all(item["eligible"] for item in ranked))
        self.assertEqual(ranked[0]["slug"], "candidate-0")

        for index in range(5):
            research.validate_dossier(dossier(f"candidate-{index}"))

        payload = {
            "schema_version": "1.0",
            "approved_understanding_sha256": UNDERSTANDING_HASH,
            "mode": "substantial",
            "directions": [
                direction("A", "candidate-0", "editorial"),
                direction("B", "candidate-1", "technical"),
                direction("C", "candidate-2", "spatial"),
            ],
        }
        research.validate_direction_set(payload)
        for left in range(3):
            for right in range(left + 1, 3):
                self.assertGreaterEqual(research.direction_difference_count(payload["directions"][left], payload["directions"][right]), 4)

    def test_plan_is_bound_to_approved_understanding_hash(self) -> None:
        plan = valid_plan()
        plan["approved_understanding_sha256"] = "not-a-hash"
        with self.assertRaises(research.ValidationError):
            research.validate_research_plan(plan)

    def test_research_and_direction_validation_use_current_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current_hash = write_understanding_state(root)
            plan = valid_plan()
            with self.assertRaisesRegex(research.ValidationError, "current gate evidence"):
                research.validate_research_plan(plan, root)
            plan["approved_understanding_sha256"] = current_hash
            research.validate_research_plan(plan, root)

            payload = {
                "schema_version": "1.0",
                "approved_understanding_sha256": UNDERSTANDING_HASH,
                "mode": "bounded-repair",
                "directions": [direction("A", "primary-a", "editorial")],
            }
            with self.assertRaisesRegex(research.ValidationError, "current gate evidence"):
                research.validate_direction_set(payload, root)
            payload["approved_understanding_sha256"] = current_hash
            research.validate_direction_set(payload, root)

    def test_substantial_plan_rejects_shallow_search(self) -> None:
        plan = valid_plan()
        plan["research_questions"] = ["What looks good?"]
        plan["search_axes"] = ["style", "style"]
        with self.assertRaises(research.ValidationError):
            research.validate_research_plan(plan)

    def test_audit_mode_requires_zero_directions(self) -> None:
        plan = valid_plan("audit")
        research.validate_research_plan(plan)
        plan["targets"]["directions"] = 1
        with self.assertRaises(research.ValidationError):
            research.validate_research_plan(plan)

    def test_hard_quality_floors_override_high_weighted_score(self) -> None:
        weak = candidate("weak-craft", evidence=100, craft=40, fit=100, feasibility=100)
        result = research.score_candidate(weak)
        self.assertFalse(result["eligible"])
        self.assertIn("craft_threshold below 65", result["rejection_reasons"])
        self.assertGreater(result["weighted_score"], 80)

    def test_project_fit_has_largest_ranking_weight(self) -> None:
        fit_first = candidate("fit-first", evidence=80, craft=80, fit=95, feasibility=80)
        fit_second = candidate("fit-second", evidence=90, craft=90, fit=70, feasibility=90)
        ranked = research.rank_candidates([fit_second, fit_first])
        self.assertEqual(ranked[0]["slug"], "fit-first")

    def test_unknown_evidence_class_is_rejected(self) -> None:
        item = candidate("bad-class")
        item["evidence_classes"] = ["observed", "vibes"]
        with self.assertRaises(research.ValidationError):
            research.validate_candidate(item)

    def test_dossier_requires_color_media_and_density_roles(self) -> None:
        item = dossier("missing-media")
        item["role_invariants"] = [entry for entry in item["role_invariants"] if entry["domain"] != "media"]
        with self.assertRaises(research.ValidationError):
            research.validate_dossier(item)

    def test_dossier_requires_all_nine_dimensions(self) -> None:
        item = dossier("missing-motion")
        del item["dimensions"]["motion"]
        with self.assertRaises(research.ValidationError):
            research.validate_dossier(item)

    def test_secondary_reference_cannot_own_broad_style_role(self) -> None:
        item = direction("A", "primary-a", "editorial")
        item["secondary_references"][0]["role"] = "overall style"
        with self.assertRaises(research.ValidationError):
            research.validate_direction(item)

    def test_substantial_directions_require_distinct_primary_foundations(self) -> None:
        payload = {
            "schema_version": "1.0",
            "approved_understanding_sha256": UNDERSTANDING_HASH,
            "mode": "substantial",
            "directions": [
                direction("A", "same-primary", "editorial"),
                direction("B", "same-primary", "technical"),
                direction("C", "other-primary", "spatial"),
            ],
        }
        with self.assertRaises(research.ValidationError):
            research.validate_direction_set(payload)

    def test_cosmetic_direction_variants_fail_four_dimension_floor(self) -> None:
        first = direction("A", "primary-a", "base")
        second = copy.deepcopy(first)
        second["id"] = "B"
        second["title"] = "Direction B"
        second["primary_reference"]["slug"] = "primary-b"
        second["evidence_refs"] = [{"slug": "primary-b", "evidence_id": "E1"}]
        for name in ("color", "surfaces", "motion"):
            second["dimension_signatures"][name] = f"variant-{name}"
        third = direction("C", "primary-c", "third")
        payload = {
            "schema_version": "1.0",
            "approved_understanding_sha256": UNDERSTANDING_HASH,
            "mode": "substantial",
            "directions": [first, second, third],
        }
        with self.assertRaises(research.ValidationError):
            research.validate_direction_set(payload)

    def test_direction_requires_traceable_evidence_and_rejected_alternative(self) -> None:
        item = direction("A", "primary-a", "editorial")
        item["evidence_refs"] = []
        with self.assertRaises(research.ValidationError):
            research.validate_direction(item)
        item = direction("A", "primary-a", "editorial")
        item["rejected_alternatives"] = []
        with self.assertRaises(research.ValidationError):
            research.validate_direction(item)

    def test_compact_manifest_discloses_missing_routing_detail(self) -> None:
        result = research.shortlist_manifest({"seed_cases": ["apple-hig", "material-3"]}, {"platforms": ["web"]}, limit=2)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["needs_detail"] for item in result))
        self.assertTrue(all(item["routing_score"] == 0 for item in result))
        self.assertIn("no facet metadata", result[0]["routing_reasons"][0])

    def test_metadata_rich_catalog_routes_exact_facets(self) -> None:
        catalog = {
            "cases": [
                {"slug": "web-dense", "platforms": ["web"], "product_types": ["productivity"], "archetypes": ["developer-dense"], "industries": ["technology"], "density": "dense"},
                {"slug": "mobile-open", "platforms": ["mobile"], "product_types": ["commerce"], "archetypes": ["consumer"], "industries": ["retail"], "density": "open"},
            ]
        }
        result = research.shortlist_manifest(catalog, {"platforms": ["web"], "product_types": ["productivity"], "density": "dense"})
        self.assertEqual(result[0]["slug"], "web-dense")
        self.assertFalse(result[0]["needs_detail"])

    def test_cli_validates_plan_and_reports_direction_distinctness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(valid_plan()), encoding="utf-8")
            plan_run = subprocess.run([sys.executable, str(MODULE_PATH), "validate-plan", str(plan_path)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(plan_run.returncode, 0, plan_run.stderr)

            directions_path = root / "directions.json"
            payload = {
                "schema_version": "1.0",
                "approved_understanding_sha256": UNDERSTANDING_HASH,
                "mode": "substantial",
                "directions": [
                    direction("A", "primary-a", "editorial"),
                    direction("B", "primary-b", "technical"),
                    direction("C", "primary-c", "spatial"),
                ],
            }
            directions_path.write_text(json.dumps(payload), encoding="utf-8")
            direction_run = subprocess.run([sys.executable, str(MODULE_PATH), "validate-directions", str(directions_path)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(direction_run.returncode, 0, direction_run.stderr)
            report = json.loads(direction_run.stdout)
            self.assertEqual(len(report["pairwise_distinctness"]), 3)
            self.assertTrue(all(item["different_dimensions"] >= 4 for item in report["pairwise_distinctness"]))


if __name__ == "__main__":
    unittest.main()
