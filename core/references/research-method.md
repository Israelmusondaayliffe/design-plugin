# Design Research Method

This reference defines the evidence, scoring, forensic, and direction-construction rules used by the internal Research, Forensics, and Directions skills.

## Research is a decision system

The purpose of research is to reduce uncertainty about a specific approved design problem. It is not a moodboard collection exercise and it is not a contest for the most fashionable source.

A good research record answers:

1. What decision are we trying to make?
2. What evidence would materially change that decision?
3. Which sources are authoritative for which claims?
4. Which references contain real craft rather than superficial similarity?
5. Which of those references actually fit this product and user?
6. Which traits are feasible in the target environment?
7. What remains unknown?

The research plan and direction set must remain bound to the SHA-256 of the approved shared-understanding artifact. When `.design/state.json` is available, consequential validation checks that value against the current canonical understanding gate instead of accepting a free-standing digest. Material changes return through the approval gate.

## Evidence classes

### Observed
Directly visible or explicitly stated in the source.

### Measured
Captured from a rendered source, design file, specification, or other actual measurement. Include the state and method when useful.

### Inferred
A reasoned conclusion supported by observed evidence. Never relabel as measured.

### Estimated
An approximate value or behavior where exact evidence is unavailable.

### Recommended
A new project-specific design decision created by Design. It is not a fact about the reference.

### Unknown
The evidence is insufficient. Unknown is a valid result.

## Source authority

For project truth, use the current project and user-authorized material first. For public-reference claims, prefer the source company's own live product, design system, official documentation, public brand guidance, or public repository. Use secondary sources only when primary evidence is unavailable or when independent evaluation is specifically relevant.

A source may be authoritative for one claim but weak for another. A marketing page can demonstrate composition and visual identity but may say little about authenticated product flows. A design-system page can prove token roles but may not show real product density.

Every candidate records one source lane: `project-local`, `user-provided`, `corpus`, or `live-public`.

## Candidate quality model

A candidate receives four scored dimensions. The score is a structured aid for ranking, never a substitute for design judgment.

### Evidence quality, weight 0.20

Consider relevant states, multiple viewports or platforms when needed, source recency, inspectable behavior, and clear provenance.

Default hard floor: 50.

### Craft threshold, weight 0.25

Consider hierarchy, typography control, spacing rhythm, color-role discipline, composition, density control, interaction behavior, responsive integrity, accessibility maturity, context-specific character, and meaningful signature decisions.

Default hard floor: 65.

Do not reward novelty alone. Do not punish conventional patterns that are exceptionally resolved.

### Project fit, weight 0.40

Consider product type, audience, primary jobs, platform, business or service goal, content type, information density, required components, flow complexity, emotional character, brand posture, and accessibility expectations.

Project fit is intentionally the strongest weight.

### Feasibility, weight 0.15

Consider current framework and platform, available content, ability to create required media, responsive complexity, performance, accessibility, implementation burden, and approved scope.

A difficult reference is not automatically infeasible. Explain the actual constraint.

## Weighted score

```text
weighted = evidence * 0.20
         + craft * 0.25
         + fit * 0.40
         + feasibility * 0.15
```

Candidates below the evidence or craft floor are rejected from eligibility before weighted ranking. A user-mandated reference can remain as explicit negative or comparison evidence, but its gate failure stays visible.

## Candidate set

For substantial work:

- 8–12 candidates is a useful default range
- 5–8 receive full forensic dossiers
- 3–5 become user-facing directions

More candidates do not automatically create better research. Stop when additional sources are no longer changing the decision space.

## Progressive retrieval

Use the smallest useful evidence layer:

1. bundled manifest
2. relevant category index
3. compact summaries
4. finalist `DESIGN.md`
5. finalist evidence and token records

The engineering-seed manifest may contain only slugs. That is routing identity, not enough metadata to claim project fit. When detailed routing data is unavailable, mark `needs_detail`, retrieve the summary if possible, or use public research. Offline operation must lower confidence rather than fabricate inspection.

## Forensic dimensions

Analyze finalists across:

1. composition
2. typography
3. color
4. density
5. imagery
6. motion
7. interaction
8. hierarchy
9. surfaces

Each finding cites dossier evidence IDs and states confidence and trait status.

## Signature traits

A signature trait is a relationship whose removal materially changes the design's character or usability logic. It is not simply a noticeable detail.

Strong examples:

- small utility typography contrasted against enormous narrative headlines
- dense expert workspace with persistent multi-panel context
- nearly flat surfaces where hierarchy comes from spacing and rules rather than shadows
- full-bleed image sequence that carries narrative hierarchy
- action accent reserved for a narrow semantic role

Weak examples:

- uses blue
- has rounded corners
- looks clean
- has cards
- feels premium

## Primary and secondary references

Every direction has one primary foundation. For substantial work, the direction set uses distinct primary foundations as an additional anti-cosmetic-variation guard. Supporting references need named narrow jobs.

Good:

- Primary: dominant visual foundation
- Secondary A: mobile navigation behavior
- Secondary B: form error treatment

Bad:

- Primary: overall inspiration
- Secondary A: make it modern
- Secondary B: make it premium

A supporting reference cannot own the same broad responsibility as the primary.

## Anti-averaging test

Ask:

- If I removed the primary source name, could I still identify its defining relationships in this direction?
- Did a secondary reference weaken the primary's strongest trait merely because it was easier to implement?
- Did the agent replace a difficult media hierarchy with generic cards?
- Did a compact system become spacious by default?
- Did a sharp system become rounded by default?
- Did an expressive system become neutral by default?
- Did an intentionally restrained system acquire decorative gradients or motion?

If yes, repair the direction before presenting it.

## Role invariants

### Color
Track what meaningful colors do: action, link, focus, status, destructive, surface, label, data series, or brand expression. Preserve or deliberately remap the role.

### Media
Track whether media is narrative, evidentiary, atmospheric, instructional, product-demonstrative, or intentionally absent. Do not treat all imagery as decoration.

### Density
Track where compactness or openness serves scanning, focus, storytelling, touch, or expert throughput. Density may vary by screen and device.

Color, media, and density must all be explicitly represented in every validated dossier and direction.

## Distinct direction test

Substantial directions should differ conceptually and mechanically. The validator compares nine signature dimensions and requires each pair to differ in at least four. A passing validator does not excuse shallow prose tricks. The actual direction must change meaningful design relationships.

## Progressive disclosure

Keep three information layers:

### Decision layer
What the user needs to choose now: thesis, fit, signature traits, risk, primary source.

### Expert layer
Scores, secondary roles, feasibility, role invariants, rejected nearby alternatives.

### Evidence layer
Claims, source URLs, evidence IDs, measurements, confidence, full dossiers.

Expose deeper layers when the user asks, when a conflict needs resolution, or when a consequential decision requires proof.

## Audit mode

Audit uses the same truth classes, candidate screening, and forensic discipline, but its direction target is zero. Evidence judges the existing interface. Do not turn every audit into a redesign. A redesign or repair path still follows the normal repository-change approval boundary.

## Research stop conditions

Stop and ask or return to shared understanding when:

- a source reveals a requirement conflict that changes the product brief
- the project lacks rights to a required asset and that changes the direction
- all strong directions require an unapproved technical dependency
- the user-defined success criteria contradict each other
- research evidence is too weak to make the requested claim confidently

Do not use more browsing to hide a product-definition problem.
