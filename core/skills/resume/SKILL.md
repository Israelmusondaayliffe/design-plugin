---
name: resume
description: Resume an interrupted Design or Design Audit project from durable repository evidence. Use when the user invokes Design Resume, says to continue a prior Design workflow, or when `.design/state.json` indicates unfinished work. Do not reconstruct progress from chat memory when state and artifacts can be inspected.
---

# Design Resume

Resume from evidence, not memory.

## Recovery order

1. Locate the project root and `.design/state.json`.
2. Activate the internal `state-controller` skill and run its bundled verification command.
3. If state is invalid, corrupted, ambiguous, or references missing artifacts, stop with a blocker. Do not overwrite it.
4. Refresh gate staleness. A changed approved artifact must be reapproved before its protected transition.
5. Read only:
   - current state
   - approved shared understanding
   - active reference lock
   - relevant `DESIGN.md` sections
   - active implementation wave or audit target
   - previous handoff
   - current repository diff and environment
6. Compare recorded state with actual files. Report contradictions.
7. State the last verified phase, active gate, unfinished target, changed assumptions, and next legal action.
8. Use the controller’s `resume` command only when state is paused. Resolve blocked state explicitly rather than treating it as paused.
9. Continue through the owning Design skill.

If the state is already `complete` and the user asks to revise the accepted work, do not overwrite or reopen the completed cycle. Use the controller's `revise` command. It archives the prior state and its artifact hashes, increments `workflow_cycle`, and returns to intake for a new evidence-bound cycle.

## Rules

- Never repeat completed interview rounds merely because conversation history is absent.
- Ask again only when a previous answer is missing, contradicted, stale, or materially affected by changed project evidence.
- Never skip a stale approval.
- Never assume a prior plan authorizes newly discovered dependencies, destructive changes, installations, image batches, external writes, deployment, or publishing.
- Preserve the existing workflow type. `run` resumes through Design. `audit` resumes through Design Audit.

## Output

Present a short recovery receipt:

```text
Workflow: [run/audit]
Phase: [phase]
State status: [active/awaiting approval/paused/blocked/complete]
Last verified artifact: [path + hash]
Stale approvals: [none/list]
Repository changes since checkpoint: [summary]
Next legal action: [action]
Blocked by: [none/list]
```
