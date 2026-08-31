---
name: plan
description: Internal pre-implementation phase for active Design runs. Produce bounded implementation waves with exact file scope, render targets, tests, completion criteria, rollback, risk, and a repository-change approval gate. Not a standalone user workflow.
user-invocable: false
---

# Design Implementation Plan

Plan translates the approved design system into an executable sequence. It must stop before product implementation and wait for approval against the exact plan hash.

## Inputs

Read only the material needed to plan the target:

- approved direction and reference lock
- root `DESIGN.md`
- `.design/system/ux-definition.json`
- token source and projection report
- current repository structure, tests, build commands, and constraints

## Structured plan

Write `.design/implementation/plan.json` from `templates/implementation-plan.template.json`. Bind `quality_targets` to the approved UX definition with exact target ID, screen, state, route, viewport, theme, reduced-motion setting, and required status. Define one to seven bounded waves. Every wave must include:

- dependencies that point only to earlier waves
- one clear goal
- exact approved inputs for the wave
- approved design requirements implemented by the wave
- the exact relevant `DESIGN.md` sections
- exact relative files or directories allowed to change
- work items and render targets
- tests and completion criteria
- rollback steps and risks
- initial status `planned`

For a substantial product, normally use this sequence:

1. foundation
2. core structure
3. product behavior
4. responsive and mobile behavior
5. imagery and motion
6. integration and polish
7. QA and repair

Smaller work may use fewer waves when the approved scope does not need every category. Do not add empty waves to imitate the default pattern.

Keep publication, deployment, purchase, account changes, uploads, software installation, and other external actions under `separate-required` approval.

## Compile and verify

Run:

```text
python skills/plan/scripts/design_system.py validate-plan .design/implementation/plan.json
python skills/plan/scripts/design_system.py compile-plan .design/implementation/plan.json .design/implementation/plan.md
```

The structured plan must retain `repository_change_gate: awaiting_approval`. The compiler will not accept `approved`, and it does not modify product files.

After all five system-definition artifacts exist, run the aggregate `verify-wave6` command described in `references/system-definition.md`.

## Approval

Present the human-readable plan. Ask the user to supply `Repository changes approved` or `These repository changes are approved`. Pass the user's accepted phrase unchanged to the state controller as `--decision-text`, bound to the exact `.design/implementation/plan.md` SHA-256. If the plan changes, approval becomes stale.

Only then may Run enter implementation and build one wave at a time.
