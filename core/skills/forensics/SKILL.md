---
name: forensics
description: Internal reference-analysis phase for active Design workflows. Break finalist references into evidence-backed design relationships, distinguish essential traits from incidental details, record color/media/density role invariants, and state confidence and misuse risks before references can influence a direction or audit judgment. Not a standalone user workflow.
user-invocable: false
---

# Design Forensics

Forensics turns an attractive reference into usable design intelligence. Do not summarize a reference as adjectives such as modern, premium, minimal, playful, or clean.

## Inputs

Use only ranked finalists from the active research plan. Read full case records or public-source evidence only for those finalists. Preserve the candidate source lane and source URL.

## Required artifact

Write one structured dossier per finalist under:

```text
.design/research/dossiers/<slug>.json
```

A substantial dossier must cover these dimensions when applicable:

- composition
- typography
- color
- density
- imagery
- motion
- interaction
- hierarchy
- surface treatment

For each dimension, record the finding, supporting evidence IDs, confidence, and whether the trait is essential, adaptable, incidental, or unknown. A dimension may be unknown, but it may not simply disappear from the dossier.

## Claim-level traceability

Every dossier contains at least three facts. Each fact records:

- a unique evidence ID
- claim
- truth class: observed, measured, inferred, estimated, recommended, or unknown
- source locator or inspected state
- confidence

Dimension findings may reference only evidence IDs that exist in that dossier. Record evidence limitations separately rather than manufacturing precision.

## Essential versus incidental

Identify 3–7 essential traits that create the reference's design logic. Separately identify incidental details that may be visually noticeable but are not necessary to preserve the system.

Examples of essential relationships:

- an editorial serif only at narrative scale while utility UI remains sans
- dense table rhythm paired with compact action controls
- image sequencing that carries the hierarchy instead of cards
- a semantic action color that never becomes a decorative surface
- full-bleed composition whose impact depends on sparse adjacent controls

Examples of incidental details:

- the exact hero photograph
- a launch-campaign illustration
- a temporary promotional badge
- copy specific to the source company

## Role invariants

Every dossier must explicitly consider:

- **color roles**: what each meaningful color is allowed to do
- **media roles**: what photography, illustration, video, texture, or absence of media is doing in the hierarchy
- **density roles**: where the system is intentionally dense, open, compact, or expansive

Use `preserve`, `adapt`, or `reject` for each transferable role and explain why. A literal source value is not required to preserve its role.

## Misuse analysis

State how an agent is likely to produce a shallow imitation. Examples:

- copying radius and palette while losing density
- preserving typeface but destroying hierarchy
- using the source accent everywhere
- replacing an image-led system with generic cards
- adding motion that fights a deliberately static system

## Handoff

A reference may influence a Design direction only after its dossier validates. Pass validated dossiers to Directions. During Design Audit, pass them directly into evidence-based judgment instead of generating cosmetic alternatives.

A dossier does not authorize copying proprietary copy, logos, brand assets, source identity, or unlicensed media.
