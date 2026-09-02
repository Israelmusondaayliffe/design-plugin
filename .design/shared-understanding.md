# Shared Understanding

## What We Are Building

Expand the existing Design Reference Library into a responsive, download-first design-intelligence Site. The Site will keep its current 60-case public catalog, search, lane and facet filtering, evidence inspection, and comparison. Its main new action will be downloading each case as:

- a clear, self-contained brief for people and language-model workflows; and
- structured data for deterministic software processing.

Both forms must express the same reviewed, evidence-bounded meaning. Factual claims must be verified, while inferences, estimates, recommendations, limitations, and unknowns remain labeled. The outputs support original adaptation and must not provide copied source assets or imitate an owner brand.

## Why It Needs to Exist

The current Site helps a reader find, inspect, and compare design references, but it does not yet provide portable case data. The expanded Site will turn reviewed evidence into material a designer can understand, download, and use when creating an original interface.

The downloaded material must explain:

- Context: the owner source, product setting, audience, platform, study date, and known limitations.
- Intent: the problem a design relationship appears to solve and the purpose of adapting it.
- Value: what is reusable, when it helps, when to avoid it, and how it can support an original result.
- Quality: the evidence level, confidence, provenance, review state, and unresolved unknowns. Quality is not a blanket certification.

## Primary Users

- Designers and builders studying references for an original project.
- Language-model design and coding workflows consuming the same human-readable briefs.
- Deterministic software workflows that need structured case data.

## Primary Jobs

1. Find a relevant case by problem, lane, platform, product type, evidence quality, or another supported facet.
2. Understand what was observed, what was inferred, why the design relationships matter, and where they should not be applied.
3. Compare cases without blending them into an untraceable average.
4. Download a case in readable and structured forms.
5. Use the reviewed, evidence-bounded relationships and limits as input to an original adaptation.

## Required Screens and Flows

- Catalog landing view with the current search, six lanes, facets, sorting, and public case count.
- Case detail view with overview, analysis, evidence, owner source, retrieval date, context, intent, value, quality, limitations, and unknowns.
- Comparison view for up to five cases, preserving each source's distinct role.
- A clear download action on every public case.
- Human-readable and structured outputs derived from equivalent approved public data.
- Method section explaining evidence classes, originality boundaries, review status, and how to use downloaded material.
- Loading, unavailable, invalid, empty, and download-failure states.

## Content and Assets

- Canonical input: the accepted public cases under `corpus/cases/`.
- Current verified catalog count: 60 cases, all marked `public` in `site/generated-data/catalog/index.json`.
- Dominant forensic reference: IBM Carbon Design System, using the current public corpus record and refreshed live research after approval.
- The refreshed IBM Carbon record must identify the exact owner source, retrieval date, available interaction states, device coverage, and evidence limitations before the reference lock.
- Public owner links, retrieval dates, evidence IDs, locators, evidence classes, confidence, suitable uses, unsuitable uses, limitations, and unresolved unknowns.
- Original case analysis and original abstract previews only.
- No owner screenshots, logos, fonts, copyrighted copy, proprietary images, source notes, reviewer identities, internal archive URLs, redirect history, or operational review details in public downloads.
- Downloads must expose only approved public information rather than copying raw case folders. The exact projection mechanism belongs in the implementation plan.

## Brand and Desired Character

The Library keeps its own identity and content. IBM Carbon is the single dominant forensic reference for the benchmark. The transferable relationships to test include productive versus expressive hierarchy, precision under density, contextual tokens, exact component states, and restrained action color.

IBM branding, IBM Plex, Carbon component geometry, and IBM blue are not identity assets for this product. They must not be copied by default.

Other references may contribute only narrow, named responsibilities that solve an approved need. They may not become co-equal foundations, dilute Carbon's essential relationships, or produce a generic blended style.

## Benchmark workflow requirements

- After the shared understanding is approved, inspect IBM Carbon at forensic depth across typography, hierarchy, spacing rhythm, grids, alignment, surfaces, color roles, component anatomy, interaction states, imagery, motion, responsive changes, density, and signature design moves.
- Separate observed facts, strong inferences, weak inferences, and unresolved unknowns.
- Identify which Carbon relationships are essential to preserve and which details are incidental or unsafe to transfer.
- Research other designs only for narrow, named supporting roles when the approved product need requires them.
- Produce at least three meaningfully different adaptations. Obtain explicit approval for one before implementation.
- Create an approved reference lock and a new project-specific `DESIGN.md`.
- Define tokens, component specifications, state matrices, responsive rules, image direction, and implementation guidance for the approved adaptation.
- Implement the approved responsive web result, compare it visually with the approved reference lock, repair material drift, and document intentional departures and unresolved limitations.

## Platforms

- Responsive web Site for desktop, tablet, and mobile.
- Local-only implementation and preview during Benchmark 2.
- Direct Figma access is unavailable in the current host. Whether a Figma-ready handoff adds benchmark value remains deferred until system definition; no Figma write is authorized.

## Technical Environment

- Existing implementation: dependency-free static HTML, CSS, and JavaScript in `site/`.
- Existing declared progressive route contract: catalog index, category, case summary, case analysis, case evidence, and case source routes beneath `site/generated-data/`.
- ChatGPT Sites is available as bounded implementation support. It may not flatten or break the progressive case routes.
- Browser rendering is available for desktop, tablet, mobile, interaction, accessibility, and visual-comparison evidence.
- No software installation is authorized by the interview.
- No accounts, backend, automatic sync, server recovery, or long-term project storage in version one.
- Hosting and deployment remain unauthorized.

## Accessibility Requirements

- Keyboard access for search, filters, case details, comparison, and downloads.
- Visible focus states, semantic headings, landmarks, labels, and status announcements.
- Touch targets and layouts appropriate for mobile use.
- Reduced-motion support and no dependence on motion for meaning.
- No page-level horizontal overflow. Dense comparison may scroll inside a clearly bounded region.
- Download controls must identify the case and output purpose clearly.

## Explicit Exclusions

- Deployment, hosting, or a public Site URL without separate approval.
- Accounts, authentication, a production backend, cross-device sync, or server recovery.
- Copied third-party assets, owner branding, or proprietary source material.
- Downloads from `review`, `private`, `blocked`, or otherwise unaccepted cases.
- Claims that flatten inference, estimates, or recommendations into observed fact.
- Unverified measurements or behavior.
- Co-equal multi-reference styling or generic averaging.
- Changes to the distributed Design plugin runtime unless the benchmark exposes a critical workflow defect and the approved repair process authorizes it.

## Success Criteria

- Every accepted public case has a readable download and structured download derived from approved public case data.
- Every factual claim is traceable to a canonical corpus field or evidence item with source and retrieval information.
- Observations, inferences, estimates, recommendations, limitations, and unknowns remain distinguishable.
- Readable and structured outputs have semantic parity and deterministic generation.
- Download data contains no private fields, reviewer identities, internal paths, operational notes, or third-party binary assets.
- The Site makes context, intent, value, and quality understandable before download.
- A designer can move from finding a case to downloading useful, evidence-backed adaptation material without needing an account.
- Every major design decision is traceable to evidence or a documented product requirement.
- The final system has a coherent internal logic of its own.
- At least three adaptations are documented and one is explicitly approved before implementation.
- The approved result has a reference lock, project-specific `DESIGN.md`, tokens, component specifications, state matrices, responsive rules, image direction, and implementation guidance.
- The final visual system preserves IBM Carbon's approved design relationships without looking like IBM or Carbon.
- Desktop, tablet, and mobile renders pass accessibility, interaction, content, and bounded visual-comparison review.
- Tests cover all 60 cases, public-only filtering, schema validation, semantic parity, deterministic output, hostile text and filenames, privacy exclusions, and download failure behavior.
- The final deviations report names every intentional departure and unresolved limitation.

## Confirmed Decisions

- Benchmark 2 will expand the existing Design Reference Library.
- IBM Carbon Design System is the single dominant forensic reference.
- Other designs may supply narrowly assigned ideas when needed.
- The main new product action is downloading explained design-reference data.
- Each public case supports both a readable brief and structured data.
- Human-readable material must stand on its own for people and language-model workflows.
- Context, intent, value, and quality are required content principles.
- Every factual statement must be verified and carry its evidence boundary.
- Version one has no accounts, backend, sync, recovery, or saved project workspace.
- ChatGPT Sites may support implementation, but the work remains local-only and undeployed.

## Assumptions

- The existing 60 accepted public cases are the version-one download set.
- A readable text format and a structured JSON format are the likely projections, subject to the approved implementation plan.
- The safest download mechanic may be separate files rather than an archive if avoiding a new dependency reduces risk.
- Existing search, filtering, comparison, and progressive loading remain valuable unless research disproves a specific interaction.

## Unresolved Risks

- Sites compatibility with the existing static project and progressive route contract has not been proved.
- Live owner sources may change after recorded retrieval dates. Downloads must preserve the date and limitation rather than imply timeless accuracy.
- Existing corpus review binds canonical artifacts, not the new derived downloads. The download generator and its output require separate bindings and review.
- The exact secondary references and their narrow responsibilities are not selected until research.
- The final visual direction, component system, public-data projection mechanism, download mechanics, and any Figma-ready handoff are not approved yet.

## Approval

Status: Awaiting approval

Approval must use `Approved` or `This understanding is approved` and will bind to the exact SHA-256 of this document.

## Evidence Basis

- Benchmark contract: [Benchmark 2 - Forensic Reference Extraction to Original Design System](https://app.notion.com/p/3cc8f54141668176b6e8e00af4be299f)
- Current Site contract: `site/README.md`, `site/index.html`, `site/app.js`, and `site/styles.css`
- Current public catalog: `site/generated-data/catalog/index.json`
- Canonical IBM Carbon case: `corpus/cases/ibm-carbon/`
- Interview evidence: `.design/interview/questions.md`, `.design/interview/answers.md`, `.design/interview/assumption-ledger.md`, and `.design/interview/session.json`
