# Render, QA, repair, and learning contract

Wave 9 turns implemented design work into inspectable evidence. It does not treat schemas as proof that a browser rendered a state or that accessibility was checked.

## Artifact chain

1. `.design/renders/plan.json` binds current state, approved design authority, local or audit origin, exact routes, states, viewports, themes, motion mode, capture paths, and bounded reference roles.
2. `.design/renders/evidence.json` records declared PNG captures or an honest blocker. Required captures must exist, match their SHA-256, and match the planned pixel dimensions.
3. The state controller validates the two artifacts, their bindings, hashes, dimensions, and declared statuses before entering QA. The controller does not originate or visually inspect browser captures.
4. `.design/qa/reports/cycle-<n>.json` covers every applicable category for every target. Code checks use the project target.
5. Open findings bind category, truth class, confidence, evidence, expected behavior, repair scope, and P0 to P3 severity.
6. A repair cycle binds exact finding IDs, current repository approval, current reference lock, allowed files, planned actions, checks, and rerender targets.
7. The controller validates repair scope before returning to rendering.
8. Final deviations and scorecard bind the passing QA report before completion.

## Rendering

Use a host-visible browser or capture capability that is already available. The shared runtime does not install Playwright, Chromium, browser drivers, fonts, packages, or CLIs. If the required capability is missing, record the blocker and prepare a prerequisite proposal. Ask before any installation.

For a local origin, use only `localhost`, `127.0.0.1`, or `::1`. Record the exact server method. Managed server commands are argv arrays, not shell strings. The runtime records commands but does not execute them.

Every run capture target binds the current reference lock, UX definition, structured implementation plan, and root `DESIGN.md`. The target set and each target's ID, screen, state, route, viewport, theme, reduced-motion setting, and required status must exactly match the approved implementation plan. Every capture target names:

- approved UX screen, component, or route
- exact state
- viewport and device scale factor
- theme
- reduced-motion setting
- project-local PNG output
- whether the target is required
- one bounded comparison reference and its assigned role

Screen references answer structure and state questions. Flow references answer sequence questions. Style references answer visual-language questions. Do not convert a screen reference into general visual authority or use generic pixel similarity as design judgment.

## QA and severity

Apply only the checks named in the render plan, but cover each applicable target and category exactly once. The supported categories are visual, typography, spacing, color roles, media, hierarchy, responsive behavior, accessibility, states, overflow, touch, motion, interaction, content, code, and reference fidelity.

Use evidence classes honestly:

- `measured` for tool or numeric output
- `observed` for direct rendered inspection
- `inferred` for a conclusion supported by current evidence
- `estimated` for a bounded approximation
- `recommended` for a proposed change
- `unknown` when evidence is missing

Accessibility evidence uses one project-local record per target. It covers semantics, accessible names, focus, contrast, zoom and reflow, keyboard behavior, touch targets, and reduced motion. Each inner result must align with the outer QA accessibility status. A `not-applicable` result requires a specific applicability reason.

Severity:

- P0: safety, destructive behavior, total task failure, or a critical accessibility blocker
- P1: primary job blocked or major accessibility, responsive, or interaction failure
- P2: material usability, fidelity, system-drift, content, or state defect
- P3: minor polish or a bounded subjective opportunity

Each finding also carries an audit type: implementation defect, usability defect, accessibility defect, responsive defect, design-system drift, content defect, evidence limitation, or subjective opportunity.

P0, P1, and P2 cannot be accepted as deviations. A P3 may be accepted only with explicit evidence and rationale. A blocked check or open P0 blocks QA. Any other open finding requires repair.

## Repair ceiling

Use `begin-repair`, never the generic transition command. Each affected target has its own counter. Attempts one through three are allowed. Attempt four fails before state or product files change.

A repair plan cannot widen the approved direction, reference lock, implementation scope, targeted finding scope, or repository approval. It records the exact files that may change. Repair handoffs cannot delete files. A deletion requires a separately approved implementation plan. `complete-repair` checks repository evidence before entering rendering. A claimed fix is only `implemented-awaiting-rerender` until fresh captures and QA evidence support marking the finding resolved for the inspected targets.

After three failed attempts for a target, record a blocker with the current evidence. Do not loop, hide the failure, or lower severity to claim completion.

## Audit

Audit remains read-only unless the user requests repair and the repository-change gate is current. Audit may collect captures during QA. Initial audit repair still requires a bounded implementation plan and approval. Subjective opportunities stay separate from defects.

## Completion

Use `complete-quality`. Generic `qa` to `complete` transitions are forbidden.

Completion requires:

- complete required captures
- every applicable QA category checked
- no open finding
- no blocker
- every accepted P3 represented in deviations
- every applicable category represented in the scorecard
- current hashes for QA, deviations, and scorecard

## Learning

Learning is proposal-only. One project cannot establish a reusable rule. A proposal requires at least two distinct project sources, project-bound redacted observations, distinct evidence content hashes, exceptions, risks, conflicts, a candidate destination, an evaluation plan, a hashed review record that declares a human privacy reviewer, and separate approval.

The `validate-learning` subcommand is read-only and has no activation command. Validation checks bindings, hashes, obvious absolute-path and secret markers, and the presence of a passing human privacy-review record. It does not prove that project provenance is truthful or that a human review was competent. Private details, absolute user paths, secrets, and benchmark data are forbidden in generalized proposals.
