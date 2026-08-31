---
name: design-md
description: Internal system-definition phase for active Design runs. Compile the approved understanding, direction, reference lock, and UX definition into the canonical root DESIGN.md contract. Not a standalone user workflow.
user-invocable: false
---

# Design MD

Design MD creates the project design contract. The structured source is authoritative. Root `DESIGN.md` is its deterministic human-readable projection.

## Inputs

Read:

- `.design/shared-understanding.md`
- `.design/directions/decision.md`
- `.design/system/reference-lock.json`
- `.design/system/ux-definition.json`
- existing root `DESIGN.md`, when present, so valid project decisions can be mapped instead of discarded

Every input must match its active SHA-256 binding.

## Structured source

Write `.design/system/design-system.json` from `templates/design-system.template.json`. Complete every canonical section with either:

- one or more direct, testable rules, or
- one explicit `not_applicable_reason`

Do not use the not-applicable field to avoid a decision that the approved product needs. Evidence references should point to project artifacts or cited research evidence.

## Compile and validate

Run:

```text
python skills/design-md/scripts/design_system.py compile-design .design/system/design-system.json DESIGN.md
python skills/design-md/scripts/design_system.py validate-design DESIGN.md
```

Do not hand-edit the generated file. Change the structured source and recompile so the artifact bindings and section order remain exact.

## Handoff

After compilation, activate Tokens. Implementation remains blocked.
