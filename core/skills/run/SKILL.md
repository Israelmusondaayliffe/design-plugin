---
name: run
description: Lead substantial website, product-interface, mobile, ChatGPT Site, Claude Artifact-to-site, redesign, and design-system work from a vague request through shared understanding, research, distinct directions, approved system definition, bounded implementation waves, rendering, and repair. Use automatically for unmistakable end-to-end design work or when the user invokes Design. Do not use for backend-only work, deployment-only work, or unrelated standalone image generation.
---

# Design

Design is the primary design authority while this workflow is active. Other coding, browser, image, Figma, and inspection capabilities may execute approved work, but they may not silently replace the approved design direction.

## Activation

When activated automatically, say that Design is taking the lead because the task requires interface, product, or visual-system decisions. State that the first phase is a shared-understanding interview and that the user may opt out by asking for the normal coding workflow.

Do not automatically activate for backend-only work, database maintenance, isolated non-visual bug fixes, deployment-only requests, general design questions, or standalone imagery unrelated to a product or interface.

## Durable state is mandatory

For any non-trivial task, use `.design/state.json` as workflow truth. Do not rely on chat memory to infer the current phase.

- Activate the internal `state-controller` skill. Use its bundled `scripts/design_state.py` command to initialize, validate, and transition state.
- Initialize a `run` workflow when no state exists. Never initialize over existing state.
- Read and validate state before every phase transition.
- Record approvals against the exact artifact hash.
- Treat changed approved artifacts as stale until reapproved.
- Stop on corrupted or ambiguous state. Never guess progress.
- Use the Resume skill for interrupted work.

Use the internal controller instead of manual JSON edits. Read the shared state-machine reference when diagnosing a blocked or invalid state.

## Required sequence

1. Activate the internal Environment skill. Inspect the request, repository, existing design files, assets, screenshots, current site, host-visible connections, and development environment before asking avoidable questions. Discover Browser, Computer Use, image, Figma, connector, and local-tool capabilities. Scaffold the intake artifacts without installing anything.
2. Activate internal Research in `pre-grill` mode. Run at most three focused current-practice queries and keep at most five useful sources. Stop after two consecutive sources add no decision-relevant evidence. Use this scan to sharpen the interview, not to choose a direction.
3. Transition to `interviewing` and activate the internal Grilling skill. Run the full shared-understanding interview using the six-round protocol, assumption ledger, progressive disclosure, and high-impact one-at-a-time handling. Do not ask which tools exist when the host can answer that question.
4. Write and validate `.design/shared-understanding.md` and the interview evidence.
5. Obtain `Approved` or `This understanding is approved`. A user may explicitly skip after the risk warning is acknowledged and recorded.
6. Transition to `researching` and activate internal Research in `deep` mode. Bind the research plan to the exact approved shared-understanding SHA-256, retrieve evidence progressively, classify consequential claims, and rank 8 to 12 candidates for substantial work by evidence quality, craft threshold, project fit, and feasibility.
7. Activate internal Forensics on the strongest 5 to 8 substantial-project finalists. Validate claim-level provenance, all nine design dimensions, essential versus incidental traits, misuse risks, and explicit color/media/density role invariants.
8. Activate internal Directions. Present 3 to 5 genuinely distinct directions for substantial work, normally 3, each with one dominant primary foundation, narrowly bounded secondary roles, traceable evidence, and anti-averaging checks. A bounded repair may use one direction.
9. Ask the user to supply `Direction approved` or `This direction is approved`. Pass the user's accepted phrase unchanged as the direction gate's decision text, bound to `.design/directions/decision.md`.
10. Activate internal Lock, then UX, then Design MD, then Tokens. Validate `.design/system/reference-lock.json`, `.design/system/ux-definition.json`, `.design/system/design-system.json`, root `DESIGN.md`, and the stable DTCG token source and projections. Keep every artifact bound to the approved upstream SHA-256 values.
11. Activate internal Plan. Produce and validate `.design/implementation/plan.json`, then compile `.design/implementation/plan.md` with bounded waves and `repository_change_gate: awaiting_approval`. Run the aggregate system-definition verification from `references/system-definition.md`.
12. Activate internal Mobile and Figma, and activate internal Imagery when the approved system contains visual-asset slots. Validate the responsive, mobile, Figma, and imagery decisions against the approved system. Produce complete local imagery and mobile artifacts plus a structurally validated Figma handoff scaffold when image or Figma tools are unavailable. Run the aggregate Wave 7 verification from `references/visual-adapters.md` only after the complete Wave 6 chain, including both Plan artifacts, passes.
13. Ask the user to supply `Repository changes approved` or `These repository changes are approved`. Pass the user's accepted phrase unchanged as the repository-change gate's decision text, bound to the exact `.design/implementation/plan.md` hash.
14. Activate internal Build Wave. Prepare and state-bind one immutable manifest at a time, change only its approved file scope, and require a durable handoff with separate independent verification and Unslop review before state advances.
15. Activate internal Render. Bind relevant desktop, tablet, mobile, theme, motion, and interaction states, then collect declared host-browser captures without installing tools. The validator checks artifact structure and bindings, not browser provenance.
16. Activate internal QA. Run visual, responsive, accessibility, content, interaction, code, and bounded reference checks as applicable.
17. Activate internal Repair for open findings. Run no more than three targeted attempts per affected state and rerender after every attempt.
18. Deliver deviations, blockers, evidence, and the final scorecard through `complete-quality`.
19. During delivery, capture only useful Design feedback or friction that the user asks to retain, or that materially explains repair, cost, a missed tool, or a reusable method. Use the private `scripts/design_learning.py` store, never the repository. Capture must not interrupt delivery.
20. Activate internal Learn only for a separate, proposal-only, multi-project learning candidate.

## Gates

The following transitions are forbidden without active evidence:

- Enter research only after the shared-understanding gate is approved or explicitly skipped with the warning acknowledged.
- Enter system definition only after direction approval.
- Enter implementation only after repository-change approval.
- Generate image batches only after approval for the exact purpose and output ceiling.
- Write to Figma only after detecting a compatible authorized connection and obtaining approval for the exact external actions.
- Install software, write to other external systems, deploy, publish, purchase, or create paid accounts only after their separate applicable approval.
- Keep Design feedback capture optional, local, redacted, and outside repositories. Any cross-harness proposal must pass through Practice Compiler as a neutral export.

The approved artifact is part of the approval. If its SHA-256 changes, the approval becomes stale. The research plan and direction set must carry that same understanding hash; a mismatch stops the workflow rather than silently reusing stale research.

## Research discipline

Research is a decision system, not a moodboard sweep. Use the compact corpus manifest only as the first routing layer. If its offline data lacks facet detail, state that limitation and retrieve a summary or public source before judging fit. A weak evidence or craft score can reject a candidate regardless of weighted score. Scores support judgment but never replace it.

Do not average strong references into a safe midpoint. Preserve the dominant source's meaningful composition, density, media role, color-role logic, typographic character, and interaction character unless the approved brief requires a deliberate adaptation.

## Work in waves

Large builds must be decomposed. At the beginning of each wave, load only the approved understanding, reference lock, relevant `DESIGN.md` sections, implementation plan, current wave, repository state, and previous handoff. At the end, record changed files, checks, deviations, risks, and the next wave's inputs.

Do not mark progress complete because a plan, report, or mockup exists when the requested target is an implemented product.

## Progressive disclosure

Keep the main path understandable. Show the current phase, decision, and required user action first. Keep full evidence, scores, rejected references, hashes, state history, and technical detail available when needed rather than dumping everything at once.

For direction choices, show the decision layer first: thesis, fit, signature traits, clear risk, primary source, and bounded supporting roles. Keep the expert and evidence layers available behind that decision.

## Completion

Completion requires current state, implemented target, validated render records, applicable QA, no open finding, a deviations report, and a final scorecard. Unresolved P0, P1, or P2 issues block completion. External dependencies remain explicit blockers. Learning remains separate and proposal-only.
