---
name: directions
description: Internal decision phase for active Design runs. Build 3 to 5 genuinely distinct evidence-backed directions from forensic dossiers, keep one dominant primary foundation per direction, assign secondary references narrow responsibilities, enforce anti-averaging and color/media/density role preservation, and present the decision through progressive disclosure. Not a standalone user workflow.
user-invocable: false
---

# Design Directions

Directions converts research into a decision the user can approve. The goal is not to show everything found. The goal is to show the strongest meaningfully different futures for the approved brief.

## Approval binding

The direction set must carry the same `approved_understanding_sha256` used by the validated research plan. If that artifact changed, stop. Do not construct directions from stale research.

## Count

For substantial work, present 3 directions by default and 4 to 5 only when ambiguity, experimentation, or reinvention genuinely warrants it.

For a bounded repair inside an approved system, one direction is allowed.

Do not create cosmetic variants to inflate the count. Substantial directions use distinct dominant primary foundations by default as an additional guard against cosmetic variation.

When the approved brief explicitly requires several adaptations of one dominant foundation, use the `single-foundation-adaptations` direction strategy. Give every direction a unique, specific `adaptation_axis`, keep the same primary slug across the set, and preserve the four-of-nine dimension difference floor. Do not use this strategy for bounded repairs.

## Direction anatomy

Each direction must contain:

- a concise title and one-line thesis
- one dominant primary reference foundation
- one adaptation axis when the set uses `single-foundation-adaptations`
- 3 to 5 primary traits that must survive adaptation
- zero to three secondary references
- one narrow responsibility for each secondary reference
- a nine-dimension signature profile covering composition, typography, color, density, imagery, motion, interaction, hierarchy, and surfaces
- explicit color, media, and density role invariants
- project-fit explanation
- technical feasibility
- risks and likely failure modes
- at least three forbidden-drift rules
- rejected nearby alternatives and why they lost
- claim-level evidence references into the forensic dossiers
- a concise decision-layer presentation plus expert detail

## Primary dominance

One reference owns the overall visual foundation of a direction. Secondary references may contribute only bounded jobs such as:

- navigation behavior
- form behavior
- data visualization
- mobile behavior
- content hierarchy
- typography detail
- imagery treatment
- motion behavior
- component anatomy
- accessibility behavior
- flow structure
- density treatment

Do not assign a secondary source roles such as overall style, visual direction, entire design, brand system, or everything.

A secondary reference cannot silently reverse the primary reference's defining density, color-role logic, media hierarchy, typographic character, or composition.

## Anti-averaging

Do not find the polite midpoint between strong references.

If the primary is image-led, preserve image leadership unless the project requirement contradicts it.
If it is intentionally dense, do not automatically open it into oversized cards.
If it is sharp and technical, do not soften it into generic rounded SaaS styling.
If it is editorial, do not remove the contrast between narrative and utility typography.
If it is deliberately restrained, do not add decoration merely to make the direction look different.

The `design_research.py validate-directions` check requires substantial direction pairs to differ across at least four of nine signature dimensions. That mechanical check is a floor, not proof of conceptual distinctness. The agent must still be able to explain the different design logic in plain language.

## Role preservation

For color, media, and density, explicitly map the source role into the proposed system. Preserve the job even when literal values change.

Examples:

- source blue is a primary action role, so the adapted brand color may replace the hue while retaining the action-only job
- source photography is the primary narrative carrier, so adaptation cannot demote it to decorative thumbnails without an approved reason
- source compact density is essential in expert workspaces, so mobile adaptation changes structure rather than simply adding whitespace everywhere

## Progressive disclosure

Default user presentation for each direction:

1. title and one-line thesis
2. why it fits
3. 3 to 5 signature traits
4. one clear risk
5. primary source and narrowly named supporting sources

Keep full scores, evidence IDs, forensic details, rejected candidates, role maps, and feasibility notes in the structured artifact and expose them when the user asks or when a consequential choice needs proof.

Do not dump 8 to 12 research candidates on the user.

## Approval

Write the full set to `.design/directions/direction-set.json` and human-readable direction files. Validate the structured set before presentation. After discussion, write the selected result to `.design/directions/decision.md`.

The user must approve the direction before the workflow may enter system definition. Ask the user to supply `Direction approved` or `This direction is approved`, then pass those exact words unchanged to the state controller as `--decision-text`. Bind approval to the exact `.design/directions/decision.md` hash and the current `.design/directions/direction-set.json` hash.

If the user rejects all directions, return to research or forensics. Do not quietly synthesize another option and proceed without approval.
