---
name: figma
description: Internal Figma routing phase for active Design runs. Detect host-visible Figma capability, prepare a structurally validated handoff scaffold, and allow direct actions only with a compatible authorized connection and request-bound write approval. Not a standalone user workflow.
user-invocable: false
---

# Design Figma

Figma routing begins with capability inspection. Do not assume a connector exists because Figma is named in the brief.

## Capability report

Record host inspection in `.design/environment-capabilities.json` from `templates/host-capabilities.template.json`. Set `artifact_status` to `ready` only after replacing every scaffold field with direct host evidence. This is separate from the local environment probe because a local script cannot see host-managed connections. Bind its path and SHA-256 in the Figma handoff.

Record whether a compatible connection is:

- unavailable
- available but not authorized
- available and authorized
- unknown

State which host surfaces were checked and the evidence found. The Design package must never require a bundled Figma MCP.

## Structural fallback

Write `.design/handoff/figma.json` from `templates/figma-handoff.template.json`. The specification is required even when direct access exists. It must contain:

- frame names, sizes, and purposes
- grids
- variables, collections, modes, and types
- components, variants, and states
- interaction states
- responsive rules
- content guidance
- measurements
- asset manifest and rights state

Compile the structurally validated handoff scaffold with:

```text
python skills/figma/scripts/design_adapters.py validate-figma .design/handoff/figma.json
python skills/figma/scripts/design_adapters.py compile-figma .design/handoff/figma.json .design/handoff/figma.md
```

## Direct actions

Direct creation or editing requires an available authorized connection, an exact target file, a complete structured action batch, per-action destructive flags, an aggregate destructive-action classification, and separate external-write approval. `external_write_boundary.request_sha256` and the exact approval note must match the canonical request covering those fields, the upstream bindings, and the entire specification section of the handoff scaffold. A generic approval sentence or approval for any changed target, action, destructive classification, or specification is invalid. Repository-change approval alone does not authorize a Figma write. See `references/visual-adapters.md` for the exact request and approval renderers.

If any requirement is missing, keep mode `specification`, set the external-write boundary to `not-required`, and produce the structurally validated fallback scaffold. Never claim it is complete or rebuild-ready without separate project-specific cross-artifact coverage. Never claim a Figma file was changed when only a scaffold was compiled.
