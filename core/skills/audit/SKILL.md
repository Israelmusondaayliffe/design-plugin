---
name: audit
description: Audit an existing website, application, mobile interface, design system, or implemented visual surface through shared understanding, evidence research, repository and render inspection, severity-ranked findings, and an optional approved repair plan. Use when the user invokes Design Audit or asks Design to inspect, critique, diagnose, compare, or repair an existing interface.
---

# Design Audit

Audit existing work against its intended job, approved design truth, user needs, evidence, and rendered behavior. Separate defects from preferences.

## State

Use `.design/state.json` with `workflow: audit`.

- Activate the internal `state-controller` skill. Use its bundled `scripts/design_state.py` command.
- Initialize an `audit` workflow when no state exists. Never initialize over existing state.
- Validate existing state before continuing.
- Never silently convert a run workflow into an audit workflow or vice versa.

## Sequence

1. Activate the internal Environment skill. Inspect the repository, current product, available routes, renders, design files, content, local prerequisites, and host-visible connections before asking avoidable questions.
2. Activate internal Research in `pre-grill` mode. Run only the bounded current-practice scan needed to ask informed questions. Use at most three focused queries and five useful sources, and stop after two low-yield sources.
3. Transition to `interviewing` and activate the internal Grilling skill. Run the same full shared-understanding protocol used by Design, focused on intended outcome, users, important states, known design truth, constraints, and audit success criteria.
4. Validate `.design/shared-understanding.md` and obtain approval or an explicitly acknowledged skip.
5. Transition to `researching` and activate internal Research in `audit` mode. Bind the plan to the exact shared-understanding SHA-256, research only the evidence needed to judge the interface, and set the direction target to zero.
6. Activate internal Forensics for any external or corpus references that materially influence the judgment. Use claim-level evidence, all applicable design dimensions, confidence, and role invariants instead of aesthetic adjectives.
7. Activate internal Render and inspect real rendered states when available. Bind current viewport captures and limitations. Do not audit code alone when the user-facing result can be rendered.
8. Classify findings:
   - implementation defect
   - usability defect
   - accessibility defect
   - responsive defect
   - design-system drift
   - content or copy defect
   - evidence limitation
   - subjective opportunity
9. Activate internal QA. Rank actionable findings P0 through P3 and cite the target, evidence, truth class, confidence, and expected result.
10. Deliver the audit without modifying files unless repair is separately approved.
11. For repair, write `.design/implementation/plan.md`, record repository-change approval, then use bounded implementation waves and internal Repair with exact finding IDs and file scope. Rerender and rerun QA after every attempt.

## Research discipline

Audit does not create design directions by default. Its evidence exists to judge the implemented surface, not to smuggle in a redesign.

- Classify consequential claims as observed, measured, inferred, estimated, recommended, or unknown.
- Prefer project truth and user-authorized material over external references.
- Use corpus and live-public sources progressively and state when remote evidence is unavailable.
- Reject weak evidence and weak craft as reference authority even when the source is visually fashionable.
- Treat candidate scores as a screening aid, never as a substitute for judgment.
- Keep evidence limitations explicit.

A redesign or new direction set is a separate design decision. If the audit establishes that a redesign is needed, return through the appropriate Design direction and repository-change approval gates rather than quietly changing the system.

## Audit discipline

- Do not invent a missing brand rule and then penalize the interface for violating it.
- Do not treat taste preference as a defect.
- Do not recommend a redesign when a smaller repair solves the measured problem.
- Do not call an interface accessible without checking applicable semantics, focus, contrast, zoom, keyboard, touch, and reduced-motion behavior.
- State what could not be inspected.
- Environment inspection never authorizes software installation. A repair plan never authorizes unspecified prerequisites.

## Completion

An audit is complete when the intended target is understood, relevant render evidence is inspected, findings are severity-ranked and reproducible, uncertainties are explicit, and the state controller validates the final QA bindings and completion constraints. Implementation is not authorized by the audit alone.
