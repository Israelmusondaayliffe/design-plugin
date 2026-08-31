---
name: render
description: Internal rendering phase for active Design and Design Audit workflows. Bind exact states and viewports, collect real host-browser PNG captures, record limitations, and submit current evidence to the state controller. Not a standalone user workflow.
user-invocable: false
---

# Design Render

Render implemented states from current project evidence. A render plan is not a capture.

## Prepare

Copy `templates/render-request.template.json` into the project-local `.design/` workspace and replace every placeholder. A run must bind the current reference lock, UX definition, structured implementation plan, and root `DESIGN.md`. Derive targets from those artifacts, the final wave handoff, and known high-risk states. Each run target names an approved UX screen and state.

Compile the current plan:

```text
python skills/render/scripts/design_quality.py prepare-render \
  --project-root . \
  --request .design/renders/request.json \
  --output .design/renders/plan.json
```

The plan must cover each applicable screen, state, viewport, theme, and interaction condition. Include reduced motion. Preserve each reference's bounded screen, flow, style, design-system, or baseline role.

## Capture

Use an already available host browser or capture tool. Observe the current render, act narrowly, then observe again. Save project-local PNG files at the exact planned paths. Do not install browser tooling, start an unapproved external write, generate images, publish, or deploy.

Fill `.design/renders/evidence.json` from `templates/render-evidence.template.json`. Passing captures need current hashes and exact PNG dimensions. Missing tooling, server failure, authentication, or inaccessible states are blockers, not passing evidence.

Submit the captures through the controller:

```text
python skills/state-controller/scripts/design_state.py accept-renders \
  --project-root . \
  --plan .design/renders/plan.json \
  --evidence .design/renders/evidence.json \
  --reason "Name the browser, target coverage, and current evidence."
```

The controller validates the capture records, bindings, hashes, decodable PNG structure, and dimensions before moving a run from rendering to QA. It does not prove browser provenance or visual inspection. A passing record cannot explicitly disclaim that the required capture occurred. Audit captures may be bound while audit state remains in QA.
