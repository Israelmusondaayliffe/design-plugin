---
name: build-wave
description: Internal implementation-wave controller for active Design runs. Load only approved wave context, enforce allowed files and dependency handoffs, verify completion evidence, and advance durable state one wave at a time. Not a standalone user workflow.
user-invocable: false
---

# Design Build Wave

Build Wave turns an approved implementation plan into controlled repository changes. It does not broaden the plan, approve its own work, or replace the state controller.

## Start one wave

Confirm that `.design/state.json` is active in `building`, the repository-change approval is current, and `active_wave` points to the planned wave. Then prepare the canonical manifest:

```text
python skills/build-wave/scripts/design_build.py prepare-wave \
  --project-root . \
  --plan .design/implementation/plan.json \
  --output .design/implementation/waves/<wave-id>/manifest.json \
  --worker-id <worker-identity>
```

Load only:

- approved shared understanding
- approved reference lock
- the relevant `DESIGN.md` sections
- approved implementation plan
- current wave manifest
- current repository evidence
- previous handoff, when one exists

The prepare command binds the new manifest hash into Design state before returning. This keeps preparation and state registration in one controlled operation. Resume from an existing manifest. Never replace it to hide drift.

## Work inside the boundary

Change only the manifest's `allowed_files`. Check scope during the wave:

```text
python skills/build-wave/scripts/design_build.py check-scope \
  --project-root . \
  --manifest .design/implementation/waves/<wave-id>/manifest.json
```

Pause or block when:

- a dependency handoff is missing or incomplete
- an approved artifact changed
- the repository history diverged from the wave baseline
- a changed file falls outside allowed scope
- a design requirement or implementation-plan decision is missing
- a completion criterion fails
- a new dependency, installation, or external action needs approval

Record new risks as they appear. Do not silently add work to make a failing wave look complete.

Use the state controller for a durable stop:

```text
python skills/state-controller/scripts/design_state.py pause \
  --project-root . \
  --reason "Name the evidence, risk, or authority needed before continuing."
```

Use `block` instead when the wave cannot continue without resolving a concrete dependency or contradiction. Record the new risk and failed or blocked checks in `handoff.json` before ending the work session.

## Handoff

Write `handoff.json` from `templates/wave-handoff.template.json`. It must report:

- every changed file, its current SHA-256, or a null hash for a deletion
- completed checks and their evidence
- every planned render target
- every completion criterion
- independent verification results, with reviewer identity distinct from the worker
- known deviations and new risks
- next inputs
- rollback notes

Compile the readable handoff, then verify repository evidence:

```text
python skills/build-wave/scripts/design_build.py compile-handoff \
  --manifest .design/implementation/waves/<wave-id>/manifest.json \
  --handoff .design/implementation/waves/<wave-id>/handoff.json \
  --output .design/implementation/waves/<wave-id>/handoff.md

python skills/build-wave/scripts/design_build.py verify-wave8 \
  --project-root . \
  --manifest .design/implementation/waves/<wave-id>/manifest.json \
  --handoff .design/implementation/waves/<wave-id>/handoff.json
```

Only after verification and independent review pass, use the state controller's `complete-wave` command with the immutable manifest and verified handoff. The controller runs verification again, derives the total wave count from the exact approved structured plan, and advances `active_wave` or moves the workflow to rendering after the final wave. Direct `building` to `rendering` transitions are forbidden.

## Claims

A plan, manifest, or handoff is not an implemented product. Report a wave as complete only when its repository changes, checks, renders, and completion criteria all have matching evidence.
