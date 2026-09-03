#!/usr/bin/env python3
"""Deterministic intake helpers for the Design plugin.

This tool only inspects local state and scaffolds project-local Design artifacts.
It never installs software, accesses the network, or writes outside .design/.
"""
from __future__ import annotations
import argparse, json, platform, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

DESIGN_DIR = ".design"
INTERVIEW_DIR = Path(DESIGN_DIR) / "interview"
ENVIRONMENT_PATH = Path(DESIGN_DIR) / "environment.json"
SESSION_PATH = INTERVIEW_DIR / "session.json"
ASSUMPTION_PATH = INTERVIEW_DIR / "assumption-ledger.md"
QUESTIONS_PATH = INTERVIEW_DIR / "questions.md"
ANSWERS_PATH = INTERVIEW_DIR / "answers.md"
UNDERSTANDING_PATH = Path(DESIGN_DIR) / "shared-understanding.md"
ALLOWED_CLASSIFICATIONS = {"known","confirmed","assumed","unresolved","deferred","out_of_scope","contradictory"}
ALLOWED_SESSION_STATUSES = {"active","awaiting_approval","approved","skipped"}
APPROVAL_PHRASES = {"approved","this understanding is approved"}
COMMON_FILES = ("DESIGN.md","README.md","AGENTS.md","CLAUDE.md","package.json","package-lock.json","pnpm-lock.yaml","yarn.lock","bun.lockb","vite.config.js","vite.config.ts","next.config.js","next.config.mjs","next.config.ts","tailwind.config.js","tailwind.config.ts","tsconfig.json","pyproject.toml","requirements.txt","Cargo.toml","Podfile","Package.swift","app.json","app.config.js","app.config.ts")
DESIGN_ARTIFACTS = ("DESIGN.md",".design/reference-lock.yaml",".design/tokens/tokens.json",".design/shared-understanding.md","figma.json","tokens.json")
BINARY_CANDIDATES = ("git","python3","python","node","npm","npx","pnpm","yarn","bun","deno","playwright","chromium","chromium-browser","google-chrome")
DIRECTORY_HINTS = ("src","app","pages","public","assets","components","ios","android",".git",".design")
CAPABILITY_CLASSES = ("browser","computer_use","image_generation","image_editing","figma","connectors","local_tools")
CAPABILITY_STATUSES = {"unknown","unavailable","available-not-authorized","available-authorized"}

class IntakeError(RuntimeError): pass

def utc_now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def project_root(value):
    root=Path(value).expanduser().resolve()
    if not root.is_dir(): raise IntakeError(f"Project root is not a directory: {root}")
    return root

def safe_target(root, relative):
    target=(root/relative).resolve(); design_root=(root/DESIGN_DIR).resolve()
    try: target.relative_to(design_root)
    except ValueError as exc: raise IntakeError(f"Refusing to write outside {DESIGN_DIR}/: {relative}") from exc
    return target

def command_version(executable):
    path=shutil.which(executable)
    if not path: return None
    for args in ([executable,"--version"],[executable,"-V"]):
        try: result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=2,check=False)
        except (OSError,subprocess.TimeoutExpired): continue
        lines=(result.stdout or "").strip().splitlines()
        if lines: return lines[0][:200]
    return "detected"

def inspect_environment(root):
    files=[x for x in COMMON_FILES if (root/x).is_file()]
    dirs=[x for x in DIRECTORY_HINTS if (root/x).is_dir()]
    artifacts=[x for x in DESIGN_ARTIFACTS if (root/x).is_file()]
    binaries={}
    for name in BINARY_CANDIDATES:
        resolved=shutil.which(name)
        binaries[name]={"path":resolved,"version":command_version(name)} if resolved else None
    package_manager=None
    for lock,manager in (("pnpm-lock.yaml","pnpm"),("yarn.lock","yarn"),("bun.lockb","bun"),("package-lock.json","npm")):
        if (root/lock).exists(): package_manager=manager; break
    capability_classes = {
        name: {"status":"unverified","capability":None,"operations":[],"boundary":"host agent must inspect"}
        for name in CAPABILITY_CLASSES
    }
    return {"schema_version":"1.0","inspected_at":utc_now(),"project_root":str(root),"read_only_probe":True,"network_accessed":False,"software_installed":False,"platform":{"system":platform.system(),"release":platform.release(),"machine":platform.machine(),"python":platform.python_version()},"project":{"files_present":files,"directories_present":dirs,"design_artifacts_present":artifacts,"git_repository":(root/".git").exists(),"package_manager_hint":package_manager},"binaries":binaries,"host_connections":{"status":"host_agent_must_inspect","capability_classes":capability_classes,"note":"The local helper cannot see host-managed connectors or plugins. The Design environment skill must inspect those capabilities before questioning."},"permission_boundary":{"installation_authorized":False,"paid_service_authorized":False,"rule":"Any installation or paid service requires separate explicit user approval."}}

def write_json(path,data): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def write_if_missing(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): return False
    path.write_text(content,encoding="utf-8"); return True

def scaffold(root):
    environment=inspect_environment(root); write_json(safe_target(root,ENVIRONMENT_PATH),environment)
    session={"schema_version":"1.0","status":"active","created_at":utc_now(),"rounds":[],"assumptions":[],"approval":None,"skip":None}
    created={}
    created[str(SESSION_PATH)]=write_if_missing(safe_target(root,SESSION_PATH),json.dumps(session,indent=2)+"\n")
    created[str(QUESTIONS_PATH)]=write_if_missing(safe_target(root,QUESTIONS_PATH),"# Interview Questions\n\nRecord only questions actually asked. Do not duplicate facts already inspected.\n")
    created[str(ANSWERS_PATH)]=write_if_missing(safe_target(root,ANSWERS_PATH),"# Interview Answers\n\nRecord confirmed answers and corrections.\n")
    created[str(ASSUMPTION_PATH)]=write_if_missing(safe_target(root,ASSUMPTION_PATH),"# Assumption Ledger\n\n| Item | Classification | Evidence | Resolution |\n|---|---|---|---|\n")
    created[str(UNDERSTANDING_PATH)]=write_if_missing(safe_target(root,UNDERSTANDING_PATH),"# Shared Understanding\n\n## What We Are Building\n\n## Why It Needs to Exist\n\n## Primary Users\n\n## Primary Jobs\n\n## Required Screens and Flows\n\n## Content and Assets\n\n## Brand and Desired Character\n\n## Platforms\n\n## Technical Environment\n\n## Accessibility Requirements\n\n## Explicit Exclusions\n\n## Success Criteria\n\n## Confirmed Decisions\n\n## Assumptions\n\n## Unresolved Risks\n\n## Approval\nStatus: Awaiting approval\n")
    return {"environment":environment,"created":created}

def load_json(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise IntakeError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc: raise IntakeError(f"Invalid JSON in {path}: {exc}") from exc

def validate_session(data):
    errors=[]
    if data.get("schema_version")!="1.0": errors.append("schema_version must be 1.0")
    if data.get("status") not in ALLOWED_SESSION_STATUSES: errors.append("invalid session status")
    rounds=data.get("rounds")
    if not isinstance(rounds,list): return errors+["rounds must be a list"]
    if len(rounds)>6: errors.append("interview may not exceed six rounds")
    for index,rd in enumerate(rounds,start=1):
        if not isinstance(rd,dict): errors.append(f"round {index} must be an object"); continue
        if rd.get("round")!=index: errors.append(f"round numbers must be sequential; expected {index}")
        qs=rd.get("questions")
        if not isinstance(qs,list): errors.append(f"round {index} questions must be a list"); continue
        high=[q for q in qs if isinstance(q,dict) and q.get("impact")=="high"]
        if high and len(qs)!=1: errors.append(f"round {index} high-impact questions must be asked one at a time")
        if not high and qs and not (3<=len(qs)<=6): errors.append(f"round {index} ordinary rounds must contain 3-6 questions")
        seen=set()
        for q in qs:
            if not isinstance(q,dict): errors.append(f"round {index} contains a non-object question"); continue
            qid=q.get("id")
            if not isinstance(qid,str) or not qid.strip(): errors.append(f"round {index} question is missing id")
            elif qid in seen: errors.append(f"round {index} duplicate question id {qid}")
            else: seen.add(qid)
            if not isinstance(q.get("text"),str) or not q["text"].strip(): errors.append(f"round {index} question {qid or '?'} is missing text")
    assumptions=data.get("assumptions")
    if not isinstance(assumptions,list): errors.append("assumptions must be a list")
    else:
        for index,item in enumerate(assumptions,start=1):
            if not isinstance(item,dict): errors.append(f"assumption {index} must be an object"); continue
            if item.get("classification") not in ALLOWED_CLASSIFICATIONS: errors.append(f"assumption {index} has invalid classification")
    if data.get("status")=="approved":
        approval=data.get("approval"); phrase=approval.get("phrase") if isinstance(approval,dict) else None
        if not isinstance(phrase,str) or phrase.strip().casefold() not in APPROVAL_PHRASES: errors.append("approved session requires phrase Approved or This understanding is approved")
    if data.get("status")=="skipped":
        skip=data.get("skip")
        if not isinstance(skip,dict) or skip.get("warning_acknowledged") is not True: errors.append("skipped session requires acknowledged risk warning")
    return errors

def validate_host_capabilities(data):
    errors=[]
    if not isinstance(data,dict): return ["host capability attestation must be an object"]
    if data.get("schema_version")!="1.0": errors.append("host capability schema_version must be 1.0")
    ready=data.get("artifact_status")=="ready"
    if data.get("artifact_status") not in {"scaffold","ready"}: errors.append("invalid host capability artifact_status")
    if data.get("host") not in {"codex","claude-code","generic"}: errors.append("invalid host capability host")
    for field in ("inspected_at","inspector"):
        if not isinstance(data.get(field),str) or not data[field].strip(): errors.append(f"host capability {field} is required")
    surfaces=data.get("surfaces")
    if not isinstance(surfaces,list) or not surfaces or not all(isinstance(x,str) and x.strip() for x in surfaces): errors.append("host capability surfaces require direct evidence")
    capabilities=data.get("capabilities")
    if not isinstance(capabilities,dict): return errors+["host capability classes are required"]
    if set(capabilities)!=set(CAPABILITY_CLASSES): errors.append("host capability classes must match the required set")
    for name in CAPABILITY_CLASSES:
        item=capabilities.get(name)
        if not isinstance(item,dict): errors.append(f"{name} capability is missing"); continue
        status=item.get("status")
        if status not in CAPABILITY_STATUSES: errors.append(f"{name} capability status is invalid")
        if ready and status=="unknown": errors.append(f"ready attestation cannot leave {name} unknown")
        provider=item.get("provider")
        if status in {"unknown","unavailable"} and provider is not None: errors.append(f"{name} unavailable capability cannot name a provider")
        if status in {"available-not-authorized","available-authorized"} and (not isinstance(provider,str) or not provider.strip()): errors.append(f"{name} available capability requires a provider")
        operations=item.get("operations")
        evidence=item.get("evidence")
        if not isinstance(operations,list) or not all(isinstance(x,str) and x.strip() for x in operations): errors.append(f"{name} operations must be a list of strings")
        if not isinstance(evidence,list) or not evidence or not all(isinstance(x,str) and x.strip() for x in evidence): errors.append(f"{name} evidence is required")
    return errors

def image_tool_route(data):
    errors=validate_host_capabilities(data)
    if errors: raise IntakeError("invalid host capability attestation: "+"; ".join(errors))
    capabilities=data["capabilities"]
    generation=capabilities["image_generation"]["status"]
    editing=capabilities["image_editing"]["status"]
    if generation=="available-authorized": return "generate-and-iterate"
    if editing=="available-authorized": return "edit-approved-inputs-only"
    if generation=="available-not-authorized" or editing=="available-not-authorized": return "ask-before-external-image-use"
    return "local-imagery-scaffold-only"

def validate_understanding(path):
    required=("# Shared Understanding","## What We Are Building","## Why It Needs to Exist","## Primary Users","## Primary Jobs","## Required Screens and Flows","## Brand and Desired Character","## Platforms","## Technical Environment","## Explicit Exclusions","## Success Criteria","## Confirmed Decisions","## Assumptions","## Unresolved Risks","## Approval")
    try: text=path.read_text(encoding="utf-8")
    except FileNotFoundError: return [f"missing shared-understanding artifact: {path}"]
    return [f"missing heading: {h}" for h in required if h not in text]

def validate_project(root):
    session=load_json(safe_target(root,SESSION_PATH)); errors=validate_session(session); errors+=validate_understanding(safe_target(root,UNDERSTANDING_PATH)); env=load_json(safe_target(root,ENVIRONMENT_PATH))
    if env.get("software_installed") is not False: errors.append("environment report must state software_installed=false")
    if env.get("network_accessed") is not False: errors.append("local environment probe must state network_accessed=false")
    return {"valid":not errors,"errors":errors}

def approval_phrase_valid(value): return value.strip().casefold() in APPROVAL_PHRASES

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest="command",required=True)
    for name in ("inspect","scaffold","validate"):
        p=sub.add_parser(name); p.add_argument("--project",required=True)
    p=sub.add_parser("check-approval"); p.add_argument("--phrase",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="check-approval": result={"valid":approval_phrase_valid(args.phrase)}
        else:
            root=project_root(args.project)
            if args.command=="inspect": result=inspect_environment(root)
            elif args.command=="scaffold": result=scaffold(root)
            else: result=validate_project(root)
        print(json.dumps(result,indent=2,sort_keys=True))
        if args.command in {"validate","check-approval"} and not result["valid"]: return 2
        return 0
    except IntakeError as exc: print(f"error: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
