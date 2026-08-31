---
name: repair
description: Internal targeted-repair phase for active Design workflows. Bind open finding IDs, enforce current authority and file scope, apply no more than three attempts per affected target, validate the repair handoff, and require rerendered QA. Not a standalone user workflow.
user-invocable: false
---

# Design Repair

Repair only current, evidence-backed findings. Do not widen the approved direction, reference lock, implementation plan, or repository scope.

## Begin

Use the state controller, not a generic phase transition:

```text
python skills/state-controller/scripts/design_state.py begin-repair \
  --project-root . \
  --qa-report .design/qa/reports/cycle-<current-cycle>.json \
  --finding <finding-id> \
  --worker-id <worker-identity> \
  --allowed-file <exact-file-or-directory> \
  --action "State the exact bounded change." \
  --check "State the exact local check." \
  --reason "Name the current finding evidence."
```

The controller rejects attempt four for any affected target before state or product files change. It creates `.design/qa/repairs/cycle-<n>.json` with repository baseline, current approval, reference lock, allowed files, actions, checks, and rerender targets.

## Apply and hand off

Change only allowed files. Repair handoffs cannot delete files. Return to a separately approved implementation plan when deletion is required. Do not install tools or take external actions without their separate approval.

Fill `.design/qa/repairs/cycle-<n>-handoff.json` from `templates/repair-handoff.template.json`. Claim every changed file with its current hash. Copy each planned action and check exactly. Mark targeted findings only as `implemented-awaiting-rerender`.

Verify and enter rendering:

```text
python skills/state-controller/scripts/design_state.py complete-repair \
  --project-root . \
  --plan .design/qa/repairs/cycle-<n>.json \
  --handoff .design/qa/repairs/cycle-<n>-handoff.json \
  --reason "Name the scope checks and rerender targets."
```

Only fresh captures and QA may mark a finding resolved. After three failed attempts for a target, record a blocker and deliver the evidence.
