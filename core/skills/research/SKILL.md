---
name: research
description: Internal evidence-research phase for active Design workflows. Convert the approved shared understanding into a bounded research plan, retrieve only relevant corpus records progressively, use public research when the corpus is insufficient, rank candidates by evidence quality, craft quality, project fit, and feasibility, and preserve claim-level provenance. Not a standalone user workflow.
user-invocable: false
---

# Design Research

Research has two bounded modes. `pre-grill` informs the interview before approval. `deep`, `audit`, and `bounded-repair` answer the approved brief after the shared-understanding gate is active. Neither mode browses without a decision to support.

## Pre-grill scan

Before interviewing, inspect current practice only when it can improve the questions or expose a material unknown. Use at most three focused queries and retain at most five useful sources. Stop after two consecutive sources add no decision-relevant evidence. Record the question each source informed and its date. Do not score candidates, choose a direction, or treat this scan as approved project research.

Skip the scan when project-local evidence already answers the relevant questions, the task is a small edit, the user supplied the needed current evidence, or current external practice cannot change the plan.

## Inputs

Read only what is needed for this phase:

- `.design/shared-understanding.md`
- the active understanding approval record or acknowledged skip record
- `.design/environment.json`
- existing root `DESIGN.md`, brand rules, screenshots, and user-provided references when present
- `catalog-manifest/catalog.json`
- `references/research-method.md` when detailed scoring or fallback rules are needed

For post-approval modes, do not silently reinterpret an approved requirement. If research reveals a contradiction that changes the problem, stop and return to shared understanding.

## Required artifacts

Create or update:

```text
.design/research/
├── plan.md
├── plan.json
├── sources.json
├── candidates.json
└── dossiers/
```

Use the bundled `scripts/design_research.py` helper to validate structured research artifacts and rank candidate scores. The helper performs no network access and does not choose taste for the agent.

## Approval binding

`plan.json` must record `approved_understanding_sha256`, the SHA-256 of the exact `.design/shared-understanding.md` artifact covered by the active approval or acknowledged skip. When `.design/state.json` exists, pass the project root to validation so it checks the digest against current gate evidence. Validate it before research. If the understanding changes, stop and return through the normal approval gate instead of continuing on stale research.

## Research plan

Translate the approved understanding into a bounded plan before searching.

For a substantial Design run:

- write 3–8 research questions
- search across at least four meaningful axes such as product type, platform, audience, primary job, density, emotional character, required components, flow complexity, accessibility, or technical feasibility
- target 8–12 candidate references
- target 5–8 forensic dossiers
- target 3–5 directions

For a bounded repair or audit, reduce the counts to what the decision actually needs. An audit sets the direction target to zero. Never create three directions merely to satisfy a ritual when the task is a narrow repair.

## Source lanes

Use the strongest applicable lanes, in this order of authority for factual claims:

1. user-owned or project-local source of truth
2. user-provided references with clear provenance
3. original Design Knowledge Corpus records
4. official public product, design-system, or brand sources
5. credible public secondary sources only when primary evidence is unavailable

Every candidate records its source lane. The corpus is a routing and reasoning source, not an authority that overrides the current project.

## Progressive corpus retrieval

Do not load the full corpus.

1. Read the compact manifest.
2. Retrieve only relevant category indexes or use exact manifest routing.
3. Read compact summaries for plausible candidates.
4. Open complete `DESIGN.md` records only for finalists.
5. Open `evidence.json` and `tokens.json` only when validating a consequential decision.

The bundled engineering-seed manifest is intentionally compact. If it contains only seed slugs rather than facet metadata, do not pretend it proves category fit. The helper marks those entries `needs_detail: true`; retrieve a summary, use the canonical generated catalog when available, or move to live public research.

When the remote Site or repository is unavailable, continue with the local manifest, bundled craft guidance, user references, project evidence, and available public research. State the missing remote evidence and lower confidence. Never imply inaccessible cases were reviewed.

## Live public research fallback

Use host-available browser or public-web research when:

- the corpus has weak or no matches
- the task depends on current product behavior
- a required flow, component, or platform pattern is missing
- the user names a specific public reference
- the corpus case is stale or insufficiently evidenced

Prefer primary official sources. Capture source URL, date, relevant state or viewport, claim, evidence class, and confidence. Do not copy a third-party page into the corpus during a project run.

## Candidate scoring

Every finalist candidate receives four 0–100 scores with written reasons:

- **Evidence quality, 20%**: can the relevant behavior and visual system actually be inspected?
- **Craft threshold, 25%**: does the reference demonstrate coherent hierarchy, typography, spacing, color roles, composition, interaction, responsive integrity, accessibility maturity, and context-specific character?
- **Project fit, 40%**: does it fit this product type, audience, platform, job, density, brand posture, required components, flow, and emotional character?
- **Feasibility, 15%**: can its important traits be implemented within the approved technology, content, asset, accessibility, and scope constraints?

Project fit is intentionally the largest weight. A beautiful but irrelevant reference is not a good reference.

Default hard floors:

- evidence quality: 50
- craft threshold: 65

A candidate below either floor is rejected regardless of weighted score. A user-mandated or analytically useful weak reference may remain in `candidates.json` as explicit negative evidence, but it does not become an eligible primary foundation merely because its weighted score is high.

Scores are a screening and ranking aid, not aesthetic truth. Judgment still has to explain why the reference actually fits the approved problem.

## Truth classifications

Every consequential research claim must be classified:

- observed
- measured
- inferred
- estimated
- recommended
- unknown

Do not convert inference into measurement. Do not fill an unknown with a fashionable default.

## Handoff

Research ends with ranked candidates and source evidence. Activate Forensics on the best 5–8 substantial-project finalists, or the smallest sufficient set for an audit or repair.

Do not present all research to the user. Directions owns the user-facing decision set for Design runs. Audit uses the evidence to judge the existing interface and does not invent a direction set unless a redesign path is separately authorized.
