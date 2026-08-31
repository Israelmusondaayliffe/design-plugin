---
name: grill
description: Internal shared-understanding interview for active Design and Design Audit workflows. Use after environment inspection and before any design research. Run up to six rounds, normally three to six questions per round, with high-impact questions asked one at a time. Maintain interview evidence, an assumption ledger, and the approval or acknowledged-skip artifact. Not a standalone user workflow.
user-invocable: false
---

# Design Grilling

The interview is a production phase. Its purpose is not to make conversation. Its purpose is to remove hidden assumptions before research and implementation.

## Preconditions

- Design or Design Audit is active.
- `.design/state.json` exists and validates.
- The Environment skill has inspected the request, project files, existing design artifacts, assets, and host-visible capabilities.
- Do not ask the user for information already established by those sources.
- Transition `intake -> interviewing` only after the initial inspection is recorded.

Use `scripts/design_intake.py scaffold --project "$PROJECT_ROOT"` to create missing interview artifacts without overwriting existing interview files. The helper installs nothing, accesses no network, and writes only inside `.design/`.

## Interview protocol

Run a full interview for every Design workflow unless the user explicitly chooses to skip. Large projects normally need 18–30 questions. Stop earlier only when the shared understanding is genuinely sufficient or the user approves early. Never exceed six rounds.

Ordinary rounds contain 3–6 questions. Ask a high-impact question by itself when its answer changes architecture, product scope, brand direction, rights, platform, business model, or another foundational decision.

Use these rounds as a coverage map, not a rigid questionnaire:

1. Outcome and problem: what is being built, why it should exist, what must change, and the target outcome.
2. Users and context: primary users, technical level, jobs, objections, devices, and usage environment.
3. Scope and content: pages, screens, capabilities, states, assets, version-one essentials, exclusions.
4. Brand and taste: existing identity, desired character, references, dislikes, visual ambition, non-negotiable identity traits.
5. Platform and implementation: web/mobile meaning, existing stack, Figma need, image need, backend or offline requirements, accessibility and technical constraints.
6. Success and contradiction review: acceptance criteria, tradeoffs, conflicts, unresolved assumptions, approval boundaries, delivery expectations.

## Question quality

- Ask questions that can materially change the work.
- Explain technical choices in plain language before expecting a non-technical user to choose.
- Present a recommendation when the user does not know, then ask whether it matches their intent.
- Challenge contradictions directly and neutrally.
- Do not ask the same question in different wording.
- Use progressive disclosure. Give the user the current round and why it matters, not the entire future questionnaire.
- Record actual questions in `.design/interview/questions.md` and confirmed answers in `.design/interview/answers.md`.
- Maintain `.design/interview/session.json`. Validate it with `scripts/design_intake.py validate --project "$PROJECT_ROOT"` before the approval gate.

## Assumption ledger

Every uncertain item must be classified as one of:

- `known`
- `confirmed`
- `assumed`
- `unresolved`
- `deferred`
- `out_of_scope`
- `contradictory`

Record the item, classification, evidence, and resolution in `.design/interview/assumption-ledger.md` and mirror the structured classification in the session JSON.

## Shared understanding

Synthesize `.design/shared-understanding.md` from the interview and inspected evidence. It must cover the product, reason for existence, users, jobs, required screens/flows, content/assets, brand character, platforms, technical environment, accessibility, exclusions, success criteria, confirmed decisions, assumptions, unresolved risks, and approval status.

Transition `interviewing -> understanding_awaiting_approval` only after that artifact is complete.

## Approval

Accept only an explicit `Approved` or `This understanding is approved` as the normal approval phrase. Confirm it with:

```bash
python3 scripts/design_intake.py check-approval --phrase "USER PHRASE"
```

Then mark the session approved and bind the state gate to the exact artifact:

```bash
python3 scripts/design_state.py record-gate \
  --project-root "$PROJECT_ROOT" \
  --gate understanding \
  --status approved \
  --artifact .design/shared-understanding.md \
  --decision-text "Approved"
```

Do not enter research until this gate is active.

## Early skip

The user may skip at any time. Before accepting the skip, state once that unresolved assumptions remain, confidence is lower, and mismatches caused by those unresolved decisions are more likely. Do not argue after the user acknowledges the risk.

Record the unresolved assumptions, set `warning_acknowledged: true` in the session, mark the shared-understanding artifact as skipped with its known limits, and record the gate as `skipped`. The state machine permits research after an acknowledged skip.

## Completion

This skill is complete only when the environment-derived facts have been incorporated, the interview evidence is durable, assumptions are classified, the shared-understanding artifact exists, and the understanding gate is either approved or explicitly skipped with the warning acknowledged.
