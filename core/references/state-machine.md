# Durable State Machine

`.design/state.json` is the workflow authority for Design. Conversation memory may explain context, but it may not override repository evidence.

A completed workflow is immutable. The `revise` command archives its complete state and artifact hashes under `.design/archive/cycle-N/`, increments `workflow_cycle`, clears active gates, and starts a new intake cycle. Generic transitions cannot leave `complete`.

## Phases

`intake` → `interviewing` → `understanding_awaiting_approval` → `researching`

A standard Design run continues:

`researching` → `directions_awaiting_approval` → `system_definition` → `implementation_plan_awaiting_approval` → `building` → `rendering` → `qa` → `repairing` or `complete`

A Design Audit continues:

`researching` → `qa` → `complete`, or `qa` → `implementation_plan_awaiting_approval` when repair is requested. An audit may enter `repairing` only after the repository-change gate has been approved.

## Gates

- `understanding` protects entry into `researching`.
- `direction` protects entry into `system_definition` for a standard run.
- `repository_changes` protects entry into `building` and any audit repair.

Each gate has one canonical artifact: understanding binds `.design/shared-understanding.md`, direction binds `.design/directions/decision.md`, and repository changes bind `.design/implementation/plan.md`. Direction approval also records the current `.design/directions/direction-set.json` SHA-256. An approval records those exact paths and hashes. If a bound file changes or disappears, verification marks the gate `stale`. Stale gates cannot authorize transitions and never reactivate automatically even if content later returns to an earlier hash.

The understanding gate may be `skipped` only when the risk warning was acknowledged. An understanding approval must say `Approved` or `This understanding is approved`. A direction approval must say `Direction approved` or `This direction is approved`. A repository-change approval must say `Repository changes approved` or `These repository changes are approved`. A direction approval requires an active understanding decision. A standard-run repository approval requires both understanding and direction to remain active.

## State integrity

Validation rejects ambiguous state instead of guessing. It checks:

- phase and status consistency
- project-relative artifact paths
- approval dependency order
- stale metadata consistency
- active-wave timing
- blocker and recovery consistency
- history event timestamps
- creation and update timestamp order

A corrupted state file is a blocker. The controller never overwrites it during validation.

## Pause and block

Pause keeps the current phase and changes status to `paused`. Resume restores the status implied by that phase.

Block records the prior phase, enters `blocked`, and adds exactly one unresolved blocker. Unblock requires a resolution reason and restores the prior phase. A blocked workflow is not a paused workflow. Resume a paused workflow before recording a blocker.

## Repair limit

Use evidence-bound quality commands for `rendering` to `qa`, `qa` to `repairing`, `repairing` to `rendering`, and `qa` to `complete`. The generic transition command rejects these edges.

`begin-repair` binds the current QA report, exact finding IDs, current repository approval, current reference lock, allowed file scope, actions, checks, and rerender targets. Each affected target has its own attempt counter. Attempt four is forbidden before state or product files change. `complete-repair` validates repository scope before returning to rendering. After three unsuccessful attempts for a target, record a blocker and deliver the evidence rather than looping indefinitely.

`accept-renders` validates the declared capture records, current PNG hashes, and planned dimensions before entering QA. It does not prove that a browser performed the capture or that a human inspected it. `complete-quality` validates QA report bindings and completion constraints before completion. It does not independently repeat the underlying inspections.

## Verification and recovery

`verify` refreshes approval staleness and reports both structurally possible transitions and currently legal next actions. A paused workflow reports `resume`; a blocked workflow reports `unblock`; stale gates report the required reapprovals.

## State tool

Use `scripts/design_state.py` for initialization, gates, transitions, pause, resume, block, unblock, and verification. It uses only the Python standard library and does not access the network.

Never edit state by hand unless repairing a documented tool defect. If manual repair is unavoidable, preserve the original file and record the deviation.
