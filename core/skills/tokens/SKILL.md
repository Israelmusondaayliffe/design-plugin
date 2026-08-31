---
name: tokens
description: Internal system-definition phase for active Design runs. Define stable DTCG tokens, preserve or map valid existing project tokens, and compile deterministic CSS, Tailwind, Figma, and mobile projections with explicit confidence. Not a standalone user workflow.
user-invocable: false
---

# Design Tokens

Tokens turns approved semantic design roles into a portable source and bounded platform projections. It does not replace a project's existing token system without an explicit preserve-or-map decision.

## Inputs

Read:

- `.design/directions/decision.md`
- `.design/system/reference-lock.json`
- root `DESIGN.md`
- existing token sources, variables, themes, and platform conventions found during Environment

## Source contract

Write `.design/system/tokens.source.json` from `templates/tokens.template.json` using the stable DTCG 2025.10 format.

The source must include `$extensions.com.houseofcuriosity.design` with:

- the approved direction SHA-256
- `existing_token_strategy` set to `new-project`, `preserve`, or `map`
- `existing_token_map`, which is required when the strategy is `map`

Put semantic roles under the top-level `semantic` group. Give every semantic token a `$description` that states its job. Use references such as `{foundation.color.ink}` instead of copying values when a semantic role depends on a foundation token.

## Compile

Run:

```text
python skills/tokens/scripts/design_system.py compile-tokens .design/system/tokens.source.json .design/system/generated-tokens
```

The compiler writes deterministic `tokens.json`, `variables.css`, `tailwind.css`, `figma.json`, `mobile.json`, and `projection-report.json` files. Composite tokens that cannot be represented safely in CSS are listed in the report. Mobile `px` projections are direct; `rem` projections use a 16 px estimate and remain marked `estimated` until verified against the project root size.

Do not copy generated projections into application code before repository-change approval.

## Handoff

After token compilation, activate Plan.
