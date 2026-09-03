"""Command-line interface for the Design workflow controller."""

from __future__ import annotations

import argparse
import json
import sys

from design_state_commands import *

def add_common(parser: argparse.ArgumentParser, *, reason: bool = False) -> None:
    parser.add_argument("--project-root", default=".", help="Project root containing .design/")
    parser.add_argument("--at", default=None, help="Explicit ISO-8601 event time for deterministic runs")
    if reason:
        parser.add_argument("--reason", required=True, help="Evidence-based reason for the state change")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new Design state file")
    add_common(init)
    init.add_argument("--workflow", choices=["run", "audit"], required=True)
    init.add_argument("--route", choices=["standard", "lightweight_repair"], default="standard")

    transition = sub.add_parser("transition", help="Apply one legal phase transition")
    add_common(transition, reason=True)
    transition.add_argument("--to", choices=sorted(PHASES - {"blocked"}), required=True)

    gate = sub.add_parser("record-gate", help="Record approval or acknowledged understanding skip")
    add_common(gate)
    gate.add_argument("--gate", choices=GATE_NAMES, required=True)
    gate.add_argument("--status", choices=["approved", "skipped"], required=True)
    gate.add_argument("--artifact", required=True)
    gate.add_argument("--decision-text", required=True)
    gate.add_argument("--warning-acknowledged", action="store_true")
    gate.add_argument("--scope", default="")
    gate.add_argument("--assumption", action="append", default=[])

    pause = sub.add_parser("pause", help="Pause without changing the current phase")
    add_common(pause, reason=True)

    resume = sub.add_parser("resume", help="Resume a paused workflow")
    add_common(resume, reason=True)

    revise = sub.add_parser("revise", help="Archive a completed cycle and begin a revision")
    add_common(revise, reason=True)

    block = sub.add_parser("block", help="Enter blocked state")
    add_common(block, reason=True)

    unblock = sub.add_parser("unblock", help="Resolve the latest blocker and restore its phase")
    add_common(unblock, reason=True)

    complete_wave = sub.add_parser("complete-wave", help="Validate a wave handoff and advance")
    add_common(complete_wave, reason=True)
    complete_wave.add_argument("--manifest", required=True, help="State-bound wave manifest")
    complete_wave.add_argument("--handoff", required=True, help="Verified complete wave handoff JSON")

    accept_renders = sub.add_parser("accept-renders", help="Validate capture records and enter QA")
    add_common(accept_renders, reason=True)
    accept_renders.add_argument("--plan", default=".design/renders/plan.json")
    accept_renders.add_argument("--evidence", default=".design/renders/evidence.json")

    begin_repair = sub.add_parser("begin-repair", help="Start one finding-bound repair cycle")
    add_common(begin_repair, reason=True)
    begin_repair.add_argument("--qa-report", required=True)
    begin_repair.add_argument("--finding", action="append", required=True)
    begin_repair.add_argument("--worker-id", required=True)
    begin_repair.add_argument("--allowed-file", action="append", required=True)
    begin_repair.add_argument("--action", action="append", required=True)
    begin_repair.add_argument("--check", action="append", required=True)

    complete_repair = sub.add_parser("complete-repair", help="Validate repair scope and enter rerendering")
    add_common(complete_repair, reason=True)
    complete_repair.add_argument("--plan", required=True)
    complete_repair.add_argument("--handoff", required=True)

    complete_quality = sub.add_parser("complete-quality", help="Validate quality bindings and completion constraints")
    add_common(complete_quality, reason=True)
    complete_quality.add_argument("--qa-report", required=True)
    complete_quality.add_argument("--deviations", default=".design/qa/deviations.json")
    complete_quality.add_argument("--scorecard", default=".design/qa/scorecard.json")

    verify = sub.add_parser("verify", help="Validate state and refresh approval staleness")
    add_common(verify)

    show = sub.add_parser("show", help="Print validated state")
    show.add_argument("--project-root", default=".")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            result = command_init(args)
            code = 0
        elif args.command == "transition":
            result = command_transition(args)
            code = 0
        elif args.command == "record-gate":
            result = command_record_gate(args)
            code = 0
        elif args.command == "pause":
            result = command_pause(args)
            code = 0
        elif args.command == "resume":
            result = command_resume(args)
            code = 0
        elif args.command == "revise":
            result = command_revise(args)
            code = 0
        elif args.command == "block":
            result = command_block(args)
            code = 0
        elif args.command == "unblock":
            result = command_unblock(args)
            code = 0
        elif args.command == "complete-wave":
            result = command_complete_wave(args)
            code = 0
        elif args.command == "accept-renders":
            result = command_accept_renders(args)
            code = 0
        elif args.command == "begin-repair":
            result = command_begin_repair(args)
            code = 0
        elif args.command == "complete-repair":
            result = command_complete_repair(args)
            code = 0
        elif args.command == "complete-quality":
            result = command_complete_quality(args)
            code = 0
        elif args.command == "verify":
            result, code = command_verify(args)
        elif args.command == "show":
            result = command_show(args)
            code = 0
        else:
            raise StateError(f"Unknown command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return code
    except StateError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
