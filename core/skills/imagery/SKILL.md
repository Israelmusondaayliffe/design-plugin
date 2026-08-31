---
name: imagery
description: Internal visual-asset art-direction phase for active Design runs. Prepare direction boards, production assets, edits, and consistent series with explicit lineage, generation boundaries, and LOCK, CHANGE, VERIFY repair instructions. Not a standalone user workflow.
user-invocable: false
---

# Design Imagery

Imagery owns visual-asset art direction while Design is active. Its approved reference lock and asset roles take precedence over generic image prompting.

## Start with the medium decision

Decide whether the slot should use:

- code-native graphics
- an actual product screenshot
- a standard icon
- a chart
- bitmap generation

Do not generate a bitmap when the required result should remain editable, factual, or interface-native.

## Required plan

Write `.design/imagery/plan.json` from `templates/imagery-plan.template.json`. Bind it to the approved direction, reference lock, and root `DESIGN.md`. For every asset define its role, slot, dimensions, source hierarchy, output name, rights and privacy review, prompts when applicable, and an asset lock covering:

- composition
- subject
- materials
- color
- lighting
- visible text
- frozen properties
- allowed variation
- prohibited drift
- verification criteria

Record prompt lineage, reference lineage, parent prompts, and source assets. A series must also define shared visual DNA, a fixed batch size, naming, frozen properties, allowed variation, and acceptance criteria.

## Generation boundary

Prompt writing does not consume image generation and uses `prompt-only` with status `not-required` and output ceiling `0`.

Ask before generating direction boards. A production or edit batch may run only when `generation_boundary.request_sha256` and the exact approval note match the canonical complete request. That request covers asset IDs, prompts, output targets, purpose and ceiling, reference and source lineage, asset locks, upstream bindings, and every other executable batch field. A generic approval sentence or a note for any changed batch field is invalid. Material additional repair batches need renewed approval. See `references/visual-adapters.md` for the exact request and approval renderers.

The validator and compiler do not call an image tool:

```text
python skills/imagery/scripts/design_adapters.py validate-imagery .design/imagery/plan.json
python skills/imagery/scripts/design_adapters.py compile-imagery .design/imagery/plan.json .design/imagery/prompts.md
```

## Targeted edits

Write `.design/imagery/edits/<asset-id>.json` from `templates/image-edit.template.json`. Every edit uses:

```text
LOCK
What must remain unchanged.

CHANGE
The exact intended modification.

VERIFY
What must be inspected after the edit.
```

Run no more than three targeted passes per affected state. Stop after the third failed pass and report the mismatch.

## Handoff

Return the local prompt package, approval status, output ceiling, lineage, acceptance criteria, and unresolved rights or privacy issues. Never claim an asset was generated when only its prompt was prepared.
