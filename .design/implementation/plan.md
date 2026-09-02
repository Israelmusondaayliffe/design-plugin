# Design implementation plan

Goal: Turn the 60 reviewed public cases into a local Evidence Exchange Site where people can understand, compare, and download a readable brief or equivalent structured JSON without exposing private project material.

Repository-change gate: awaiting approval. Do not start implementation until this exact plan is approved.

## Artifact bindings

- Approved direction SHA-256: `ea3096da2603b09bd3af29cdefda553eebe723a8ee5c1e5ec132421cb70d0fa5`
- Reference lock SHA-256: `1ab7408df01119bb7e6194db84cf9008e62e79f0a8727f95e0cf64d2e163f449`
- UX definition SHA-256: `cfa1c4ff0e7dec586d23ea98680a440071aaf2e1f59f657d00c63a8c2bf20502`
- DESIGN.md SHA-256: `8af31f454c86342b788674c842fed9c8ddefae02d8ef6824387a15e3f4a47d8a`

## Approved quality targets

- `catalog-default-wide`: screen `catalog`, state `default`, route `/`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `catalog-default-mobile`: screen `catalog`, state `default`, route `/`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `catalog-default-tablet`: screen `catalog`, state `default`, route `/`, viewport `tablet` 834x1112 at 1x, theme `light`, reduced motion `false`, required `true`
- `catalog-empty-mobile`: screen `catalog`, state `empty`, route `/?q=no-such-reviewed-case`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `catalog-loading-mobile`: screen `catalog`, state `loading`, route `/?test-state=catalog-loading`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `catalog-error-wide`: screen `catalog`, state `error`, route `/?test-state=catalog-error`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `case-default-wide`: screen `case-detail`, state `default`, route `/?case=ibm-carbon`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `case-loading-mobile`: screen `case-detail`, state `loading`, route `/?case=ibm-carbon&test-state=case-loading`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `case-default-tablet`: screen `case-detail`, state `default`, route `/?case=ibm-carbon`, viewport `tablet` 834x1112 at 1x, theme `light`, reduced motion `false`, required `true`
- `case-error-mobile`: screen `case-detail`, state `error`, route `/?case=missing-case`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `package-default-wide`: screen `download-package`, state `default`, route `/?case=ibm-carbon#download-package`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `package-default-mobile`: screen `download-package`, state `default`, route `/?case=ibm-carbon#download-package`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `package-default-tablet`: screen `download-package`, state `default`, route `/?case=ibm-carbon#download-package`, viewport `tablet` 834x1112 at 1x, theme `light`, reduced motion `false`, required `true`
- `package-error-mobile`: screen `download-package`, state `error`, route `/?case=ibm-carbon&test-state=download-error#download-package`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `package-denied-wide`: screen `download-package`, state `permission_denied`, route `/?case=private-test-case#download-package`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `comparison-default-wide`: screen `comparison`, state `default`, route `/?compare=ibm-carbon,vercel-geist`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `comparison-default-mobile`: screen `comparison`, state `default`, route `/?compare=ibm-carbon,vercel-geist`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `comparison-default-tablet`: screen `comparison`, state `default`, route `/?compare=ibm-carbon,vercel-geist`, viewport `tablet` 834x1112 at 1x, theme `light`, reduced motion `false`, required `true`
- `method-default-wide`: screen `method`, state `default`, route `/#method`, viewport `wide` 1440x1000 at 1x, theme `light`, reduced motion `false`, required `true`
- `method-default-mobile`: screen `method`, state `default`, route `/#method`, viewport `mobile` 390x844 at 1x, theme `light`, reduced motion `true`, required `true`
- `method-default-tablet`: screen `method`, state `default`, route `/#method`, viewport `tablet` 834x1112 at 1x, theme `light`, reduced motion `false`, required `true`

## Prohibited scope

- Do not deploy the Site, create a public URL, add analytics, or configure hosting.
- Do not add a backend, database, account system, authentication, sync service, or offline guarantee.
- Do not copy source screenshots, logos, fonts, branded illustrations, videos, or other third-party binaries.
- Do not expose source notes, reviewer identity, internal paths, archive URLs, redirect history, operational notes, or non-public cases.
- Do not change canonical case claims as a shortcut around projection or presentation failures. A claim correction requires source evidence and independent review.
- Do not update the private repository or install the dev.11 plugin on active Codex or Claude hosts during this benchmark.
- Do not copy a reference brand identity, product shell, palette, typography, component geometry, or icon set.

## wave-1-public-package-contract: Create one deterministic, privacy-filtered public case model that generates equivalent readable and structured packages for all 60 reviewed public cases.

### Dependencies

- None.

### Inputs

- .design/shared-understanding.md
- .design/system/reference-lock.json
- .design/system/ux-definition.json
- DESIGN.md
- corpus/source-policy/SOURCE_POLICY.md
- corpus/cases/*/{metadata.json,evidence.json,coverage.json,source.json,DESIGN.md}
- corpus/scripts/build_catalog.py

### Approved design requirements

- Each public package explains context, intent, value, quality, evidence, provenance, limitations, and unknowns before the file action.
- Readable Markdown and structured JSON come from one normalized public semantic model and carry the same supported claims.
- Every public claim preserves its evidence ID, source URL, retrieval date, truth class, and limitation when present in canonical evidence.
- The allowlist excludes private, review, blocked, missing, or invalid cases and every prohibited operational field.
- Repeated builds from unchanged source produce byte-identical package files, manifests, stable filenames, and hashes.

### Relevant DESIGN.md sections

- Provenance and Confidence
- Approved Shared Understanding
- Implementation Rules
- Explicit Do Rules
- Explicit Do-Not Rules

### Files allowed to change

- corpus/scripts/build_catalog.py
- corpus/scripts/build_public_packages.py
- corpus/schemas/public-case-package.schema.json
- corpus/README.md
- site/generated-data
- tests/test_wave11_evidence_exchange.py

### Work items

- Define a versioned public package schema and normalized model with explicit truth-class, evidence, provenance, limitation, unknown, and file-detail fields.
- Implement an allowlist projector that reads only approved canonical inputs and rejects unexpected private or operational fields.
- Generate a readable Markdown brief and structured JSON from the same model, plus a manifest containing filename, media type, byte size, and SHA-256.
- Integrate public package routes into the catalog build without changing the existing progressive catalog, category, summary, analysis, evidence, or source routes.
- Normalize Unicode, line endings, key ordering, list ordering where semantics permit, escaping, and filenames so hostile but valid content cannot alter paths or markup structure.
- Add a semantic parity comparator that fails when the readable and structured outputs support different public claims.

### Render targets

- No visual render is required in this data-contract wave. Inspect generated Markdown and JSON for IBM Carbon and at least one case from each of the other five corpus lanes.

### Tests

- Run python3 corpus/scripts/validate_corpus.py in accepted-only mode and require 60 valid cases.
- Build with python3 corpus/scripts/build_catalog.py --visibility public and require exactly 60 public package manifests.
- Run tests/test_wave11_evidence_exchange.py for schema conformance, public-only filtering, prohibited-field absence, semantic parity, stable filenames, Unicode, hostile content, invalid slugs, and deterministic repeated builds.
- Compare complete generated trees from two clean temporary output roots and require identical relative paths and SHA-256 values.

### Completion criteria

- Exactly 60 reviewed public cases produce readable Markdown, structured JSON, and a manifest from one normalized public model.
- Every package passes the schema, public-only allowlist, prohibited-field scan, claim-level evidence binding, semantic parity, path-safety, and deterministic-build checks.
- No raw canonical case folder or prohibited field is copied into a public package route.
- The original catalog route contract and full existing test suite remain passing.

### Rollback

- Remove the new projector, schema, package routes, and tests through a scoped patch while leaving canonical corpus cases and the prior catalog routes unchanged.
- Regenerate public data with the prior catalog build after the scoped rollback.

### Risks

- Pause if canonical records cannot support context, intent, value, quality, evidence, limitations, and unknowns without invented text.
- Pause if semantic parity requires parsing presentation text instead of comparing the shared normalized model.
- Pause if any private or operational field reaches the generated public tree.


## wave-2-evidence-exchange-structure: Recompose the existing static Site into the approved Evidence Exchange hierarchy while preserving catalog discovery and comparison.

### Dependencies

- wave-1-public-package-contract

### Inputs

- .design/system/design-system.json
- .design/system/tokens.source.json
- .design/system/generated-tokens/variables.css
- .design/implementation/plan.md
- site/index.html
- site/styles.css
- site/app.js
- site/generated-data/catalog/index.json

### Approved design requirements

- IBM Carbon owns the visual foundation through grid alignment, productive and expressive density, semantic roles, contextual layers, and relationship-based components.
- The Site uses original fonts, colors, geometry, icons, and previews rather than a reference brand identity.
- Catalog, case, package, comparison, and method screens keep the approved information and task hierarchy.
- Context, contents, evidence boundary, provenance, limitations, unknowns, and file details appear before download actions.
- Search, six lanes, six advanced facets, sorting, public count, progressive loading, case evidence, and comparison of two to five cases remain available.

### Relevant DESIGN.md sections

- Design North Star
- Reference Foundation
- Information Architecture
- Layout and Grid
- Typography
- Color and Semantic Roles
- Surfaces, Borders, Radius, and Elevation
- Navigation

### Files allowed to change

- .design/system/tokens.source.json
- site/index.html
- site/styles.css
- site/app.js
- site/README.md
- tests/test_wave11_site.py
- tests/test_wave11_evidence_exchange.py

### Work items

- Map existing CSS variables with valid semantic projections to approved roles. Preserve --shadow as an explicitly unmapped legacy value until this wave removes it or replaces it with a tested dialog-only CSS shadow.
- Add stable catalog, case-detail, download-package, comparison, and method regions with semantic landmarks and ordered headings.
- Give human explanation the primary reading register and separate labels, provenance, tabular values, filenames, evidence IDs, and machine values into compact technical registers.
- Present original public-data previews as optional recognition cues, never as evidence or provenance.
- Preserve the existing query-string contract for search, facets, sort, selected comparison cases, and current case.

### Render targets

- catalog-default-wide
- catalog-default-mobile
- catalog-default-tablet
- case-default-wide
- case-default-tablet
- package-default-wide
- package-default-mobile
- package-default-tablet
- comparison-default-wide
- comparison-default-mobile
- comparison-default-tablet
- method-default-wide
- method-default-mobile
- method-default-tablet

### Tests

- Extend tests/test_wave11_site.py to verify the five screen regions, ordered package contract, preserved catalog controls, comparison limit, public count, local-only boundary, and absence of remote visual dependencies.
- Use DOM and computed-style inspection to verify semantic landmarks, ordered headings, original token roles, bounded reading measure, and no repeated-card layout substitution.
- Render every named target and compare it with the approved Evidence Exchange direction and reference lock, not with source-brand pixels.

### Completion criteria

- All five screens exist in one coherent local static Site and preserve the approved decision order.
- The catalog still exposes all 60 public cases, six lanes, six advanced facets, sorting, progressive detail, evidence, and two-to-five comparison.
- The package contract is visible before any enabled download action at wide and mobile targets.
- Fresh renders show Carbon-derived relationships with original project identity and no copied reference shell.

### Rollback

- Revert only the Site and Site-test changes in this wave through a scoped patch while keeping the validated public package generator from wave 1.
- Rebuild the unchanged public data routes and rerun the prior Site tests.

### Risks

- Pause if the visual system copies reference colors, fonts, geometry, or branded shell patterns.
- Pause if the package hierarchy pushes discovery, comparison, evidence, or limitations out of the main task path.
- Pause if the static architecture cannot preserve the existing query-state contract without a wider architecture decision.


## wave-3-download-behavior-and-recovery: Make readable and structured package selection, validation, download, and failure recovery complete without losing case context.

### Dependencies

- wave-2-evidence-exchange-structure

### Inputs

- .design/system/ux-definition.json
- DESIGN.md
- site/generated-data/cases/*/downloads/manifest.json
- site/generated-data/cases/*/downloads/case.md
- site/generated-data/cases/*/downloads/case.json

### Approved design requirements

- A download is enabled only for a validated public package and a named available format.
- Readable and structured formats show equivalent public meaning with different presentation suited to people and tools.
- Loading, empty, validation error, unavailable, permission-denied, success, and browser failure states preserve package context.
- Every failure names the case, format, problem, and exact retry or return action.
- A downloaded file's bytes and filename match the validated generated package route.

### Relevant DESIGN.md sections

- Screens and User Flows
- Components and States
- Forms and Validation
- Motion and Feedback
- Content and Interface Copy

### Files allowed to change

- site/index.html
- site/styles.css
- site/app.js
- site/README.md
- corpus/scripts/build_public_packages.py
- tests/test_wave11_site.py
- tests/test_wave11_evidence_exchange.py

### Work items

- Load and validate the package manifest before presenting enabled readable and structured download actions.
- Show format contents, media type, filename, byte size, SHA-256, evidence boundary, provenance, limitations, and unknowns before each action.
- Implement standard browser download behavior that preserves exact generated bytes and stable filenames.
- Implement specific loading, empty, invalid projection, unavailable case, non-public case, missing file, and browser failure states with retry or return actions.
- Add deterministic test-state hooks that are inert unless a local test query explicitly requests them, so required error and loading renders can be inspected.

### Render targets

- case-loading-mobile
- case-error-mobile
- package-default-wide
- package-default-mobile
- package-error-mobile
- package-denied-wide

### Tests

- Test valid readable and structured downloads for a representative case and verify filename, media type, byte count, and SHA-256 against the manifest.
- Test missing files, invalid manifests, failed validation, unavailable cases, non-public cases, network failure, and browser download failure without clearing context.
- Test that readable and structured package views expose the same normalized claims, evidence IDs, provenance, limitations, and unknowns.
- Inspect every named failure target for exact case, format, problem, and recovery copy.

### Completion criteria

- Both formats download successfully for all 60 validated public cases and match their manifests.
- No action can generate or expose a file for a non-public, invalid, missing, or failed package.
- Every required loading and failure target retains case context and exposes a specific next action.
- Tests prove semantic parity from the shared normalized model rather than from matching file counts.

### Rollback

- Remove download controls and behavior through a scoped patch while keeping the wave 1 package generator and wave 2 information structure intact.
- Restore the package screen to a read-only explanation state until the behavior is repaired.

### Risks

- Pause if browser-generated bytes differ from the validated static package bytes.
- Pause if test-state hooks affect ordinary routes or can expose non-public fixtures.
- Pause if error handling clears search, comparison, case, or package context.


## wave-4-responsive-accessibility-and-copy: Make every approved screen and state usable by keyboard, assistive technology, text resizing, reduced motion, and narrow viewports without removing information.

### Dependencies

- wave-3-download-behavior-and-recovery

### Inputs

- .design/system/ux-definition.json
- .design/system/tokens.source.json
- DESIGN.md
- site/index.html
- site/styles.css
- site/app.js

### Approved design requirements

- Target WCAG 2.2 AA with fresh manual and automated evidence.
- DOM order, reading order, focus order, and visual decision order remain aligned at every target.
- Primary mobile controls are at least 44 by 44 CSS pixels, and page-level horizontal overflow is absent.
- Only the labeled comparison table may scroll horizontally, and it remains keyboard reachable.
- Reduced motion removes nonessential transitions without removing state meaning.
- Interface copy uses observable claims and keeps facts, project analysis, recommendations, limitations, and unknowns distinct.

### Relevant DESIGN.md sections

- Responsive Strategy
- Mobile-Specific Rules
- Accessibility
- Typography
- Content and Interface Copy
- Motion and Feedback

### Files allowed to change

- site/index.html
- site/styles.css
- site/app.js
- site/README.md
- tests/test_wave11_site.py
- tests/test_wave11_evidence_exchange.py
- .design/quality

### Work items

- Complete names, roles, values, labels, landmarks, ordered headings, table headers, busy states, live status, errors, and focus restoration.
- Recompose every screen at base, compact, medium, and wide widths without removing filters, evidence, limitations, file details, format choice, comparison, or recovery actions.
- Constrain comparison overflow to one labeled region and verify the document root never exceeds the viewport width.
- Verify text contrast, meaningful non-text boundaries, focus contrast, 200 percent zoom, text spacing overrides, touch targets, and reduced motion.
- Run an Unslop pass on interface and recovery copy without changing evidence, identifiers, commands, citations, or factual scope.

### Render targets

- catalog-default-wide
- catalog-default-mobile
- catalog-default-tablet
- catalog-empty-mobile
- catalog-loading-mobile
- catalog-error-wide
- case-default-wide
- case-default-tablet
- case-loading-mobile
- case-error-mobile
- package-default-wide
- package-default-mobile
- package-default-tablet
- package-error-mobile
- package-denied-wide
- comparison-default-wide
- comparison-default-mobile
- comparison-default-tablet
- method-default-wide
- method-default-mobile
- method-default-tablet

### Tests

- Run automated accessibility checks against every required target and record findings without treating the scanner as full acceptance.
- Complete keyboard-only search, filtering, case detail, evidence tabs or sections, comparison, package selection, download, retry, return, and dialog close flows.
- Measure root overflow, bounded comparison overflow, primary touch targets, focus visibility, and content retention at 390, 600, 834, 960, 1280, and 1440 CSS pixels.
- Inspect 200 percent zoom, text-spacing overrides, reduced-motion mode, loading announcements, error announcements, and focus restoration.

### Completion criteria

- Every required quality target renders with all approved information and actions present.
- Keyboard, focus, semantic, contrast, resize, reduced-motion, touch-target, and overflow checks have no unresolved blocking findings.
- Comparison is concurrently inspectable at wide widths and uses one labeled bounded scroll region at narrow widths.
- Copy identifies exact states and recovery actions without unsupported quality or completion claims.

### Rollback

- Revert only the accessibility, responsive, and copy changes that caused the regression through a scoped patch, then retain the last passing structure and behavior.
- Keep failed target evidence and reopen the affected wave instead of lowering the acceptance requirement.

### Risks

- Pause if a visual treatment cannot meet contrast without changing the approved semantic role or hierarchy.
- Pause if mobile fit is achieved by hiding evidence, limitations, controls, or recovery actions.
- Pause if automated results conflict with keyboard or rendered evidence and resolve the conflict before acceptance.


## wave-5-integration-render-and-independent-review: Prove the complete Benchmark 2 corpus and Site outcome against the approved direction, privacy boundary, runtime behavior, and all required quality targets.

### Dependencies

- wave-4-responsive-accessibility-and-copy

### Inputs

- .design/directions/decision.md
- .design/system/reference-lock.json
- .design/system/ux-definition.json
- DESIGN.md
- .design/implementation/plan.md
- corpus/scripts/build_catalog.py
- site/index.html
- site/styles.css
- site/app.js

### Approved design requirements

- Completion requires evidence for all 60 public cases, both formats, semantic parity, deterministic builds, privacy exclusions, required states, responsive behavior, accessibility behavior, and rendered direction fidelity.
- The worker cannot serve as the independent verifier.
- One reviewer verifies the approved plan and direction, one verifies technical and evidence behavior, and one performs an independent Unslop and copy-boundary review.
- A validator pass, test count, or filesystem presence cannot replace fresh rendered and runtime proof.
- Any unresolved blocker reopens the owning implementation wave before acceptance is recorded.

### Relevant DESIGN.md sections

- Provenance and Confidence
- Reference Lock
- Accessibility
- Implementation Rules
- Decision Ledger
- Known Deviations
- Unknowns and Future Decisions

### Files allowed to change

- .design/system/tokens.source.json
- site/index.html
- site/styles.css
- site/app.js
- site/README.md
- corpus/scripts/build_catalog.py
- corpus/scripts/build_public_packages.py
- corpus/schemas/public-case-package.schema.json
- corpus/README.md
- tests/test_wave11_site.py
- tests/test_wave11_evidence_exchange.py
- .design/quality
- review/wave-11-source-health.json
- review/wave-11-benchmark-2-acceptance-evidence.json
- BUILD_STATE.md

### Work items

- Rebuild the public corpus and package trees twice from clean temporary roots and record deterministic path and hash evidence.
- Run the entire Python test suite on both supported Python versions when both are available, plus corpus validation, public-only scans, schema checks, parity checks, and manifest-byte checks.
- Serve the Site locally and capture fresh wide, tablet, and mobile evidence for every required quality target, including loading, empty, error, permission-denied, comparison, method, and reduced-motion states.
- Compare renders with the approved Evidence Exchange direction and reference lock, checking relationship fidelity and copied-identity exclusions.
- Send the complete result to three independent reviewers with separate plan, technical, and Unslop mandates. Repair exact blockers and rerun the affected checks.
- Write one acceptance receipt with commands, test counts, target evidence, hashes, reviewer decisions, remaining limits, and external actions still awaiting approval. Update BUILD_STATE.md only after every required item has a terminal result.

### Render targets

- catalog-default-wide
- catalog-default-mobile
- catalog-default-tablet
- catalog-empty-mobile
- catalog-loading-mobile
- catalog-error-wide
- case-default-wide
- case-default-tablet
- case-loading-mobile
- case-error-mobile
- package-default-wide
- package-default-mobile
- package-default-tablet
- package-error-mobile
- package-denied-wide
- comparison-default-wide
- comparison-default-mobile
- comparison-default-tablet
- method-default-wide
- method-default-mobile
- method-default-tablet

### Tests

- Run python3 -m unittest discover -s tests -p 'test_*.py' and repeat under the second supported Python version when available.
- Run accepted-only corpus validation, public catalog build, public package schema validation, prohibited-field scan, semantic parity checks, and two-clean-build hash comparison.
- Use a fresh local server and browser session for all 21 required quality targets, keyboard flows, downloaded-byte checks, page-overflow checks, and reduced-motion checks.
- Run the repository harness quality gate on changed human-facing text and use the independent Unslop reviewer for interface copy.
- Require written pass or exact blocker findings from the plan verifier, technical verifier, and Unslop reviewer after the final repair.

### Completion criteria

- All automated tests pass with exact counts recorded, and no required test is skipped without an approved reason.
- All 60 public cases produce validated readable and structured downloads with semantic parity, deterministic bytes, public-only fields, and matching manifests.
- All 21 required targets and complete keyboard flows pass fresh rendered review with no unresolved accessibility, responsive, recovery, privacy, or direction-fidelity blockers.
- All three independent reviewers pass the final same-hash result, and the worker repairs every blocker before recording acceptance.
- The receipt states that deployment, push, release, active-host installation, and Figma writes were not performed.

### Rollback

- Use the last passing wave boundary and scoped patches to remove only the failed integration changes while preserving canonical corpus evidence and approved system-definition artifacts.
- Do not publish or install a partially accepted result. Reopen the exact owning wave and keep the acceptance receipt incomplete until repaired.

### Risks

- Pause if different Python versions, clean builds, or browser sessions produce different public package bytes or visible claims.
- Pause if a reviewer evaluates a different artifact hash than the final candidate.
- Pause if any required target, case, format, state, privacy scan, or independent review lacks terminal evidence.

## External actions

- Push or publish Benchmark 2 repository changes to any GitHub remote: separate approval required.
- Deploy the Site, configure hosting, or create a public URL: separate approval required.
- Install the dev.11 Design plugin on the active Codex or Claude host: separate approval required.
- Write this system to Figma or another external design tool: separate approval required.

Approval artifact: `.design/implementation/plan.md`
