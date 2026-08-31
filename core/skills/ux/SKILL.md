---
name: ux
description: Internal system-definition phase for active Design runs. Define information architecture, screens, flows, states, responsive behavior, mobile task priorities, accessibility, and a bounded Figma handoff from the approved reference lock. Not a standalone user workflow.
user-invocable: false
---

# Design UX Definition

UX converts the approved product understanding and reference lock into complete behavior before visual implementation begins.

## Inputs

Read:

- `.design/shared-understanding.md`
- `.design/system/reference-lock.json`
- existing routes, screens, product rules, and platform constraints found during Environment
- only the research evidence needed to resolve the approved flows

Do not invent product scope, permissions, or business rules. Record unresolved product decisions as unknowns and stop when they affect architecture or a primary flow.

## Output

Write `.design/system/ux-definition.json` from `templates/ux-definition.template.json`. It must define:

- a complete information-architecture tree
- every intended screen and its primary tasks, permissions, and responsive behavior
- primary flows, success outcomes, and error paths
- default, loading, empty, error, and permission-denied states for every screen
- responsive mode, ordered breakpoints, content priority, and adaptation rules
- mobile primary tasks, deferred tasks, device capabilities, offline behavior, and navigation model
- an accessibility target with concrete requirements
- a Figma handoff mode with either a reason or an explicit frame, component, variable, and interaction list

## Validation

Run:

```text
python skills/ux/scripts/design_system.py validate-ux .design/system/ux-definition.json
```

The validator rejects missing screen states, unknown flow screens, duplicate IDs, unordered breakpoints, weak accessibility definitions, and incomplete Figma handoffs.

## Handoff

After validation, activate Design MD. Do not change implementation files.
