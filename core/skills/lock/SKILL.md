---
name: lock
description: Internal system-definition phase for active Design runs. Freeze the approved direction into one dominant reference foundation, narrowly scoped supporting roles, protected traits, allowed adaptation, and prohibited drift. Not a standalone user workflow.
user-invocable: false
---

# Design Reference Lock

Lock turns an approved direction into a binding implementation reference. It does not reopen direction selection or blend references into a new midpoint.

## Inputs

Read only:

- `.design/shared-understanding.md` and its active approval record
- `.design/directions/direction-set.json`
- `.design/directions/decision.md` and its active approval record
- the approved direction's forensic dossiers and cited evidence

Stop if either approval is missing, stale, or bound to a different SHA-256 digest. The direction approval must also carry the current `.design/directions/direction-set.json` hash in `.design/state.json`.

## Output

Write `.design/system/reference-lock.json` from `templates/reference-lock.template.json`. The artifact must record:

- the approved understanding and direction bindings
- one dominant reference with responsibility `dominant visual foundation`
- zero to three supporting references, each with one narrow responsibility
- at least three frozen visual traits
- allowed variation
- at least three prohibited-drift rules
- claim-level evidence links, assumptions, and confidence

The dominant source must remain visually dominant. A supporting source may solve one bounded problem, but cannot own overall style, brand, composition, or the whole interface.

## Validation

Run:

```text
python skills/lock/scripts/design_system.py validate-lock .design/system/reference-lock.json --decision .design/directions/decision.md --direction-set .design/directions/direction-set.json
```

Validation checks the file hashes, selected direction, dominant source, and every supporting responsibility. If the approved direction changes, rebuild and reapprove the lock instead of editing around the mismatch.

## Handoff

After the lock passes, activate UX. Do not start implementation.
