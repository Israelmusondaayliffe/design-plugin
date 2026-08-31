#!/usr/bin/env python3
"""Validate canonical Design Knowledge Corpus records using only the standard library."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from urllib.parse import urlparse

CORPUS_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = CORPUS_ROOT / "cases"
TAXONOMY = CORPUS_ROOT / "taxonomy/taxonomy.json"
REQUIRED_FILES = {"DESIGN.md","metadata.json","evidence.json","tokens.json","source-notes.md","review.json","preview-spec.json"}
TRUTH = {"observed","measured","inferred","estimated","recommended","unknown"}
PUBLICATION = {"private","review","public","blocked"}
BANNED_SOURCE_DOMAINS = {"refero.design","styles.refero.design","api.refero.design"}
BANNED_CASE_EXTENSIONS = {".png",".jpg",".jpeg",".webp",".gif",".pdf",".woff",".woff2",".ttf",".otf"}

class CorpusError(RuntimeError): pass

def read_json(path: Path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise CorpusError(f"missing {path.relative_to(CORPUS_ROOT)}") from exc
    except json.JSONDecodeError as exc: raise CorpusError(f"invalid JSON {path.relative_to(CORPUS_ROOT)}: {exc}") from exc

def require_https(value: str, label: str):
    parsed=urlparse(value)
    if parsed.scheme!="https" or not parsed.netloc: raise CorpusError(f"{label} must be an https URL")
    host=parsed.netloc.lower().split(":")[0]
    if host in BANNED_SOURCE_DOMAINS or any(host.endswith("."+d) for d in BANNED_SOURCE_DOMAINS):
        raise CorpusError(f"{label} uses a prohibited corpus source domain: {host}")

def require_taxonomy(values, facet, taxonomy, slug):
    allowed=set(taxonomy["facets"][facet])
    bad=sorted(set(values)-allowed)
    if bad: raise CorpusError(f"{slug}: invalid {facet}: {bad}")

def validate_case(case_dir: Path, taxonomy: dict):
    slug=case_dir.name
    found={p.name for p in case_dir.iterdir() if p.is_file()}
    missing=sorted(REQUIRED_FILES-found)
    if missing: raise CorpusError(f"{slug}: missing files {missing}")
    for path in case_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in BANNED_CASE_EXTENSIONS:
            raise CorpusError(f"{slug}: source binary asset is not allowed in canonical case records: {path.name}")
    meta=read_json(case_dir/"metadata.json")
    required=["schema_version","slug","name","source_name","source_url","source_kind","studied_at","platforms","product_types","industries","archetypes","density","color_modes","interaction_complexity","evidence_quality","publication_status","rights_basis","summary","signature_traits","best_for","avoid_for"]
    for key in required:
        if key not in meta: raise CorpusError(f"{slug}: metadata missing {key}")
    if meta["schema_version"]!="1.0" or meta["slug"]!=slug: raise CorpusError(f"{slug}: schema/slug mismatch")
    require_https(meta["source_url"], f"{slug} source_url")
    if meta["publication_status"] not in PUBLICATION: raise CorpusError(f"{slug}: invalid publication status")
    for facet in ("platforms","product_types","industries","archetypes","color_modes"):
        require_taxonomy(meta[facet], facet, taxonomy, slug)
    for facet in ("density","interaction_complexity","evidence_quality"):
        require_taxonomy([meta[facet]], facet, taxonomy, slug)
    if len(meta["summary"].strip())<40: raise CorpusError(f"{slug}: summary is too short")
    evidence=read_json(case_dir/"evidence.json")
    items=evidence.get("items",[])
    if evidence.get("schema_version")!="1.0" or len(items)<3: raise CorpusError(f"{slug}: evidence requires schema 1.0 and at least 3 items")
    ids=set()
    for item in items:
        if item.get("id") in ids: raise CorpusError(f"{slug}: duplicate evidence id")
        ids.add(item.get("id"))
        if item.get("class") not in TRUTH: raise CorpusError(f"{slug}: invalid evidence class")
        if item.get("confidence") not in {"low","medium","high"}: raise CorpusError(f"{slug}: invalid evidence confidence")
        require_https(item.get("source_url",""), f"{slug} evidence {item.get('id')}")
    tokens=read_json(case_dir/"tokens.json")
    if tokens.get("schema_version")!="1.0": raise CorpusError(f"{slug}: token schema mismatch")
    for token in tokens.get("tokens",[]):
        if token.get("evidence_class") not in TRUTH: raise CorpusError(f"{slug}: invalid token evidence class")
        unknown=sorted(set(token.get("source_evidence_ids",[]))-ids)
        if unknown: raise CorpusError(f"{slug}: token references unknown evidence {unknown}")
    review=read_json(case_dir/"review.json")
    if review.get("status")!=meta["publication_status"]: raise CorpusError(f"{slug}: review and metadata publication states disagree")
    preview=read_json(case_dir/"preview-spec.json")
    for key in ("primary","secondary","radius","pattern"):
        if key not in preview: raise CorpusError(f"{slug}: preview spec missing {key}")
    design=(case_dir/"DESIGN.md").read_text(encoding="utf-8")
    for heading in ("# ","## Visual thesis","## Signature relationships","## Adaptation rules","## Failure modes"):
        if heading not in design: raise CorpusError(f"{slug}: DESIGN.md missing {heading}")
    return meta

def validate():
    taxonomy=read_json(TAXONOMY)
    if not CASES_ROOT.is_dir(): raise CorpusError("cases directory is missing")
    cases=[]
    for case_dir in sorted((p for p in CASES_ROOT.iterdir() if p.is_dir()), key=lambda p:p.name):
        cases.append(validate_case(case_dir,taxonomy))
    return {"status":"pass","case_count":len(cases),"slugs":[c["slug"] for c in cases]}

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try: print(json.dumps(validate(),indent=2,sort_keys=True)); return 0
    except CorpusError as exc: print(f"CORPUS INVALID: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
