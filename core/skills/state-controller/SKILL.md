---
name: state-controller
description: Internal durable workflow controller for Design, Design Audit, and Design Resume. Use when a Design workflow must initialize, validate, transition, pause, resume, block, unblock, or verify `.design/state.json` and approval artifact hashes. Not a standalone user workflow.
user-invocable: false
---

# Design State Controller

This internal skill owns durable workflow state. Use it only while Design, Design Audit, or Design Resume is active, or when a project already contains `.design/state.json`.

## Bundled executable

Run `scripts/design_state.py` relative to this skill directory. Agent Skills resolve bundled script paths from the skill root. Do not resolve the command relative to the user's project directory.

The controller uses only the Python standard library. It installs nothing and accesses no network. It writes durable state and validation receipts only under `.design/` inside the selected project root.

## Commands

Initialize a standard Design run:

```bash
python3 scripts/design_state.py init --project-root "$PROJECT_ROOT" --workflow run
```

Initialize an audit:

```bash
python3 scripts/design_state.py init --project-root "$PROJECT_ROOT" --workflow audit
```

Validate state and refresh approval staleness:

```bash
python3 scripts/design_state.py verify --project-root "$PROJECT_ROOT"
```

Apply one legal phase transition:

```bash
python3 scripts/design_state.py transition --project-root "$PROJECT_ROOT" --to PHASE --reason "EVIDENCE-BASED REASON"
```

Quality edges are evidence-bound and cannot use the generic transition command:

```text
accept-renders: rendering to qa
begin-repair: qa to repairing
complete-repair: repairing to rendering
complete-quality: qa to complete
```

Use the internal Render, QA, and Repair skills for their exact commands and artifacts.

Record an approval gate against an exact project artifact:

```bash
python3 scripts/design_state.py record-gate \
  --project-root "$PROJECT_ROOT" \
  --gate understanding \
  --status approved \
  --artifact .design/shared-understanding.md \
  --decision-text "Approved"
```

Every gate is bound to its canonical artifact. The user must supply an accepted approval phrase, and the agent must pass the user's exact words unchanged as `--decision-text`. Direction approval uses `.design/directions/decision.md` with `Direction approved` or `This direction is approved`. Repository-change approval uses `.design/implementation/plan.md` with `Repository changes approved` or `These repository changes are approved`.

Pause and resume:

```bash
python3 scripts/design_state.py pause --project-root "$PROJECT_ROOT" --reason "REASON"
python3 scripts/design_state.py resume --project-root "$PROJECT_ROOT" --reason "REASON"
```

Block and resolve a blocker:

```bash
python3 scripts/design_state.py block --project-root "$PROJECT_ROOT" --reason "BLOCKER"
python3 scripts/design_state.py unblock --project-root "$PROJECT_ROOT" --reason "RESOLUTION"
```

Read validated state:

```bash
python3 scripts/design_state.py show --project-root "$PROJECT_ROOT"
```

Begin a revision after a completed run or audit:

```bash
python3 scripts/design_state.py revise --project-root "$PROJECT_ROOT" --reason "USER-REQUESTED REVISION"
```

`revise` is legal only from `complete`. It writes an archive under `.design/archive/cycle-N/`, preserves the completed state and artifact hashes, increments `workflow_cycle`, clears active gates, and begins a new intake cycle. It never edits the archived evidence.

## Rules

- Never initialize over an existing state file.
- Never hand-edit state when the controller can express the change.
- Never continue after `verify` reports stale gates.
- Reapproval must bind to the current artifact hash.
- Corrupt or ambiguous state is a blocker. Preserve it for diagnosis.
- A pause is not a blocker. A blocker is not a pause.
- Each affected target may receive no more than three repair attempts. Attempt four is rejected before state or product files change.
- Never bypass render, QA, repair, deviation, or scorecard evidence with the generic transition command.
- The controller authorizes phase movement only. It does not authorize installations, image-generation usage, external writes, deployment, publishing, purchases, or paid accounts.
