---
name: qa
description: Internal rendered-quality phase for active Design and Design Audit workflows. Inspect every applicable target and category, compare bounded references, classify evidence and severity, and produce a current QA report. Not a standalone user workflow.
user-invocable: false
---

# Design QA

Inspect the current rendered result. Do not infer visual or accessibility quality from code alone.

## Coverage

Read `.design/renders/plan.json`, `.design/renders/evidence.json`, the current reference lock, `DESIGN.md`, UX definition, and applicable implementation handoffs. Load only the evidence needed for the current target.

For each target, run every category named in the render plan. Code is checked once at project scope. Applicable categories may include visual, typography, spacing, color roles, media, hierarchy, responsive behavior, accessibility, states, overflow, touch, motion, interaction, content, code, and reference fidelity.

Record one check per target and category. Each check states method, truth class, confidence, current artifact hashes, and limitations. Accessibility uses `templates/accessibility-evidence.template.json`; the eight inner results must align with the outer accessibility result. Preserve reference roles. Do not turn a screen reference into style authority.

## Findings

Separate defects from subjective opportunities. Every finding names its source check, target, quality category, audit type, observed result, expected result, evidence, confidence, repair scope, and severity. Audit types distinguish implementation, usability, accessibility, responsive, design-system, content, evidence, and subjective findings.

- P0 blocks QA.
- P1 and P2 require repair.
- P3 requires repair or an explicit accepted deviation.
- Only P3 may be accepted as a deviation.

Write the report at `.design/qa/reports/cycle-<repair_cycle>.json`, then validate it:

```text
python skills/qa/scripts/design_quality.py validate-qa \
  --project-root . \
  --report .design/qa/reports/cycle-<repair_cycle>.json
```

After a repair, bind the prior QA report and repair plan, then record the result for every targeted finding. A resolution claim requires rerendered evidence. Blocked checks and unresolved findings remain visible.
