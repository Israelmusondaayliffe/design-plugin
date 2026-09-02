#!/usr/bin/env python3
"""Generate local-review or public catalog routes from canonical corpus records."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path


CORPUS_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = CORPUS_ROOT.parent
CASES_ROOT = CORPUS_ROOT / "cases"
DEFAULT_CORPUS_OUT = CORPUS_ROOT / "generated"
DEFAULT_SITE_OUT = PLUGIN_ROOT / "site/generated-data"
VALIDATOR = Path(__file__).with_name("validate_corpus.py")
spec = importlib.util.spec_from_file_location("validate_corpus", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(validator)
PUBLIC_PACKAGES = Path(__file__).with_name("build_public_packages.py")
public_package_spec = importlib.util.spec_from_file_location("build_public_packages", PUBLIC_PACKAGES)
public_packages = importlib.util.module_from_spec(public_package_spec)
assert public_package_spec.loader
public_package_spec.loader.exec_module(public_packages)

CASE_JSON = (
    "metadata.json", "evidence.json", "tokens.json", "review.json", "preview-spec.json",
    "coverage.json", "source.json",
)
CASE_TEXT = ("DESIGN.md", "source-notes.md")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_text(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def validate_output_root(path: Path) -> None:
    resolved = path.resolve()
    forbidden = {Path("/"), PLUGIN_ROOT.resolve(), CORPUS_ROOT.resolve(), (PLUGIN_ROOT / "site").resolve()}
    if resolved in forbidden:
        raise RuntimeError(f"refusing to replace unsafe output root: {resolved}")
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        raise RuntimeError(f"output root must be a real directory: {path}")


def include_case(status: str, visibility: str) -> bool:
    if visibility == "public":
        return status == "public"
    return status in {"review", "public"}


def build(
    *,
    visibility: str = "local",
    allow_pending_review: bool = False,
    corpus_out: Path = DEFAULT_CORPUS_OUT,
    site_out: Path = DEFAULT_SITE_OUT,
) -> dict:
    report = validator.validate(allow_pending_review=allow_pending_review)
    taxonomy = read_json(CORPUS_ROOT / "taxonomy/taxonomy.json")
    roots = (corpus_out, site_out)
    for root in roots:
        validate_output_root(root)
    resolved_roots = tuple(root.resolve(strict=False) for root in roots)
    if resolved_roots[0] == resolved_roots[1] or any(
        left in right.parents for left, right in ((resolved_roots[0], resolved_roots[1]), (resolved_roots[1], resolved_roots[0]))
    ):
        raise RuntimeError("catalog output roots must be distinct and non-nested")
    staged_roots = tuple(public_packages.create_staging_root(root) for root in roots)

    try:
        summaries = []
        category_facets = tuple(facet for facet in taxonomy["facets"] if facet != "publication_status")
        category_map = {facet: {} for facet in category_facets}
        for slug in report["slugs"]:
            source = CASES_ROOT / slug
            metadata = read_json(source / "metadata.json")
            if not include_case(metadata["publication_status"], visibility):
                continue
            preview = read_json(source / "preview-spec.json")
            coverage = read_json(source / "coverage.json")
            summary = {
                key: metadata[key]
                for key in (
                    "slug", "name", "source_name", "source_url", "studied_at", "corpus_lane", "platforms",
                    "product_types", "industries", "archetypes", "typography_character", "media_strategy",
                    "layout_behavior", "journey", "brand_maturity", "accessibility_maturity", "density",
                    "color_modes", "interaction_complexity", "evidence_quality", "publication_status", "summary",
                    "signature_traits", "best_for", "avoid_for",
                )
            }
            summary["confidence"] = coverage["confidence"]
            summary["unknowns"] = coverage["unknowns"]
            summary["preview"] = preview
            summaries.append(summary)
            for facet in category_map:
                value = metadata[facet]
                values = value if isinstance(value, list) else [value]
                for item in values:
                    category_map[facet].setdefault(item, []).append(slug)
            for root in staged_roots:
                destination = root / "cases" / slug
                write_json(destination / "summary.json", summary)
                for name in CASE_JSON:
                    write_json(destination / name, read_json(source / name))
                for name in CASE_TEXT:
                    copy_text(source / name, destination / name)
                if metadata["publication_status"] == "public":
                    public_packages.build_case_package(source, destination / "downloads", output_root=root)

        summaries.sort(key=lambda item: item["name"].casefold())
        facets = {
            facet: sorted({item for case in summaries for item in (case[facet] if isinstance(case[facet], list) else [case[facet]])})
            for facet in category_facets
        }
        index = {
            "schema_version": "1.0",
            "visibility": visibility,
            "case_count": len(summaries),
            "facets": facets,
            "route_contract": {
                "index": "catalog/index.json",
                "category": "catalog/categories/{facet}/{value}.json",
                "case_summary": "cases/{slug}/summary.json",
                "case_analysis": "cases/{slug}/DESIGN.md",
                "case_evidence": "cases/{slug}/evidence.json",
                "case_source": "cases/{slug}/source.json",
                "case_download_manifest": "cases/{slug}/downloads/manifest.json",
                "case_download_readable": "cases/{slug}/downloads/case.md",
                "case_download_structured": "cases/{slug}/downloads/case.json",
            },
            "cases": summaries,
        }
        for root in staged_roots:
            write_json(root / "catalog/index.json", index)
            write_json(root / "taxonomy.json", taxonomy)
            for facet, values in category_map.items():
                for value, slugs in values.items():
                    write_json(
                        root / "catalog/categories" / facet / f"{value}.json",
                        {"schema_version": "1.0", "facet": facet, "value": value, "count": len(slugs), "slugs": sorted(slugs)},
                    )
        public_packages.replace_output_roots(zip(roots, staged_roots))
    finally:
        for root in staged_roots:
            if root.exists():
                shutil.rmtree(root)
    return {
        "status": "built",
        "visibility": visibility,
        "case_count": len(summaries),
        "source_case_count": report["case_count"],
        "review_mode": report["review_mode"],
        "generated_root": str(corpus_out),
        "site_root": str(site_out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visibility", choices=("local", "public"), default="local")
    parser.add_argument("--allow-pending-review", action="store_true")
    parser.add_argument("--corpus-out", type=Path, default=DEFAULT_CORPUS_OUT)
    parser.add_argument("--site-out", type=Path, default=DEFAULT_SITE_OUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                visibility=args.visibility,
                allow_pending_review=args.allow_pending_review,
                corpus_out=args.corpus_out,
                site_out=args.site_out,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
