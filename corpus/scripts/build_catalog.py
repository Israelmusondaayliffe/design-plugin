#!/usr/bin/env python3
"""Generate progressive-disclosure catalog data from canonical corpus records."""
from __future__ import annotations
import json, shutil
from pathlib import Path
import importlib.util

CORPUS_ROOT=Path(__file__).resolve().parents[1]
PLUGIN_ROOT=CORPUS_ROOT.parent
CASES_ROOT=CORPUS_ROOT/"cases"
OUT=CORPUS_ROOT/"generated"
SITE_OUT=PLUGIN_ROOT/"site/generated-data"
VALIDATOR=Path(__file__).with_name("validate_corpus.py")
spec=importlib.util.spec_from_file_location("validate_corpus",VALIDATOR); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def write_json(path,data): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def copy_text(source,dest): dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(source.read_text(encoding="utf-8"),encoding="utf-8")

def build():
    report=mod.validate()
    taxonomy=read_json(CORPUS_ROOT/"taxonomy/taxonomy.json")
    for target in (OUT,SITE_OUT):
        if target.exists(): shutil.rmtree(target)
        target.mkdir(parents=True)
    summaries=[]
    category_map={facet:{} for facet in ("platforms","product_types","industries","archetypes","density","color_modes")}
    for slug in report["slugs"]:
        src=CASES_ROOT/slug; meta=read_json(src/"metadata.json"); preview=read_json(src/"preview-spec.json")
        summary={key:meta[key] for key in ("slug","name","source_name","source_url","platforms","product_types","industries","archetypes","density","color_modes","interaction_complexity","evidence_quality","publication_status","summary","signature_traits","best_for","avoid_for")}
        summary["preview"]=preview; summaries.append(summary)
        for facet in category_map:
            values=meta[facet] if isinstance(meta[facet],list) else [meta[facet]]
            for value in values: category_map[facet].setdefault(value,[]).append(slug)
        for root in (OUT,SITE_OUT):
            base=root/"cases"/slug
            write_json(base/"summary.json",summary)
            for name in ("metadata.json","evidence.json","tokens.json","review.json","preview-spec.json"):
                write_json(base/name,read_json(src/name))
            copy_text(src/"DESIGN.md",base/"DESIGN.md")
    facets={facet:sorted({value for case in summaries for value in (case[facet] if isinstance(case[facet],list) else [case[facet]])}) for facet in category_map}
    index={"schema_version":"1.0","case_count":len(summaries),"facets":facets,"cases":summaries}
    for root in (OUT,SITE_OUT):
        write_json(root/"catalog/index.json",index)
        write_json(root/"taxonomy.json",taxonomy)
        for facet,values in category_map.items():
            for value,slugs in values.items(): write_json(root/"catalog/categories"/facet/f"{value}.json",{"schema_version":"1.0","facet":facet,"value":value,"count":len(slugs),"slugs":sorted(slugs)})
    return {"status":"built","case_count":len(summaries),"generated_root":str(OUT.relative_to(PLUGIN_ROOT)),"site_root":str(SITE_OUT.relative_to(PLUGIN_ROOT))}

if __name__=="__main__": print(json.dumps(build(),indent=2,sort_keys=True))
