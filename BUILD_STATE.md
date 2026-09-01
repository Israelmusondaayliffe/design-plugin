# Design Plugin Build State

Last updated: 2026-09-01
Approved plan: Design Plugin Build Plan v1.0
Canonical development repository: `Israelmusondaayliffe/design-plugin`
Canonical development path: repository root
Branch: `main`
Historical pre-migration source: Retained in a private archive outside the public project.

Historical commit IDs and CI run IDs in this ledger are private-archive evidence with no public locator. Fresh public qualification begins with Wave 10.

## Current phase

Wave 11 is active by explicit user authorization. The 60-case personal-alpha corpus and the local undeployed reference Site have passed their scoped qualification. The three approved benchmarks have not started, so Wave 11 is partial. R04 remains partial and is explicitly deferred as a nonblocking evidence gap for this work. R22 remains partial until the benchmarks and later acceptance gates pass.

## Current Wave 11 candidate

- Canonical cases: 60, all independently accepted and marked public.
- Lane allocation: 15 brand/editorial, 15 product UI, 10 mobile, 8 commerce, 7 flows/forms, and 5 design systems/data/experimental.
- Owner-source audit: 80 of 80 URLs pass; zero locator mismatches; zero effective-URL collisions.
- Originality audit: Pass across all 60 canonical records.
- Source binary assets stored: None.
- Accepted-only public catalog: 60 cases.
- Local Site: Search, six lane filters, advanced facets, progressive case analysis and evidence, source retrieval dates, URL state, and up-to-five comparison pass.
- Browser evidence: Desktop 1280 by 720 and mobile 390 by 844 pass with no page-level horizontal overflow and no console warnings or errors.
- Local regression suite: 242 tests pass under the locally available Python 3.9.6.
- Public Site deployment: Not authorized and not performed.
- Benchmarks complete: 0 of 3.
- R04: Partial, deferred and nonblocking for this work by explicit user direction.
- R22: Partial.

## Latest qualified installed runtime baseline

- Public candidate commit: `41d849aeef0b0104cf0fe6ff1e0420843dbf172f`.
- Public candidate tree: `58a6ce33015c852c443fe9ea1f411e88213c7458`.
- Installed version: `0.1.0-dev.10` in Codex and Claude Code.
- CI workflow: `Design Plugin CI`
- Public CI run: `33353752204`.
- Python 3.11 job: Pass.
- Python 3.13 job: Pass.
- Regression tests: 204 passed on each Python version.
- Bundled-manifest corpus validation: Pass, 12 compact routing entries. The external Wave 11 corpus now contains 60 cases.
- Catalog generation: Pass.
- OpenAI distribution: 627,146 bytes, 130 files.
- Claude distribution: 626,168 bytes, 129 files.
- Shared files: 125, byte-identical.
- OpenAI deterministic archive: 204,202 bytes.
- Claude deterministic archive: 203,612 bytes.
- Generated Python bytecode bundled: No.
- MCP bundled: No.
- Full corpus bundled: No.
- Site bundled: No.
- User-machine installations: 2 current hosts, Codex and Claude Code, at the frozen runtime baseline above. The earlier Wave 10 qualification itself used only isolated temporary homes.
- Publication: Public GitHub repository.
- Deployment, release, or tag: None.

The public candidate adds finalized host manifests, deterministic installable packages, exact Codex and Claude Code install guidance, activation fixtures, package bloat checks, and isolated temporary-host lifecycle qualification. Codex prompt input exposed installed routing descriptions and Claude reported the installed component inventory, but those checks do not prove model selection. The R04 follow-up adds a fail-closed 20-case-per-host runner without adding qualification restrictions to either distributed plugin.

The public workflow ran the complete 204-test suite, corpus checks, host builds, parity checks, deterministic package checks, filesystem lifecycle simulation, and bundled entrypoint checks. The separate isolated host check used temporary configuration roots, copied no credentials, left active registries unchanged, and deleted its temporary roots. Neither check proves active-user installation, identical host routing, browser rendering, visual quality, accessibility behavior, or benchmark success.

## Repository migration result

PASS. The complete Design project lives in its own GitHub repository.

- Destination: `Israelmusondaayliffe/design-plugin`.
- Visibility: Public.
- Canonical branch: `main`.
- Initial public snapshot commit: `5b5dccdd2e2405a46e60643914d2ccce46368b0f`.
- Initial public snapshot tree: `9f91c8747b5f59fc69763c61509ca3d95ae0fa9d`.
- Historical source locators: Retained only in the private archive.
- Public snapshot tree parity: Pass.
- Anonymous clone: Pass.
- Public root-path CI: Pass, run `33353752204`.
- Full project moved: `core/`, `corpus/`, `hosts/`, `requirements/`, `review/`, `scripts/`, `site/`, tests, licenses, notices, plan, and state.
- Opaque historical staging payload: Retained only in the private archive and excluded from the public project.
- Temporary source repository changed: No.
- Evidence: `review/repository-migration-evidence.json`.

## Wave 0 result

PASS. Provenance and requirement baseline is complete.

- Approved plan persisted in Notion.
- R01-R22 encoded.
- Refero upstream pinned to `1d324d5be0492352e2c8702f70a4f9c386c2345f`.
- Refero MIT attribution recorded.
- Refero MCP, account dependency, branding dependency, and bulk catalog copying excluded.

## Wave 1 result

PASS. Repository and packaging generator is complete.

- One canonical shared core with host-only overlays.
- Deterministic standard-library package builder and verifier.
- Host manifests isolated.
- Shared files byte-identical across hosts.
- 1 MiB package ceiling enforced.
- MCP and full corpus excluded from distributions.

Current packaging after Wave 8:
- OpenAI: 445,826 bytes.
- Claude: 445,387 bytes.
- Shared files: 94.
- Python bytecode and cache directories: Excluded.

## Wave 2 result

PASS. Orchestrator state foundation and resume system are complete.

- Design, Design Audit, and Design Resume routes.
- Durable `.design/state.json`.
- Canonical artifact-bound understanding, direction, and repository approvals with user-supplied accepted phrases.
- Direction approval also binds the exact direction-set SHA-256.
- Approval staleness and downstream invalidation.
- Pause, block, unblock, resume, and corruption rejection.
- Audit repair approval boundary.
- Maximum three repair passes.

## Wave 3 result

PASS. Grilling and environment inspection are complete.

- Environment inspection before avoidable interview questions.
- Local read-only probe with no network or software installation.
- Six interview rounds maximum.
- 3-6 questions per ordinary round.
- High-impact questions one at a time.
- Bounded assumption ledger.
- Explicit `Approved` / `This understanding is approved` handling.
- Acknowledged-risk skip path.
- Plain-language prerequisite proposal and separate installation permission.

## Wave 4 result

PASS. Corpus schema and Site engineering seed are complete.

Implemented:
- `corpus/source-policy/SOURCE_POLICY.md`.
- Canonical metadata, evidence, token, and review schemas.
- Design taxonomy.
- Standard-library corpus validator.
- Standard-library progressive catalog generator.
- Twelve original seed case studies:
  - Adobe Spectrum 2
  - Apple HIG
  - Atlassian Design System
  - GitHub Primer
  - GOV.UK Design System
  - IBM Carbon
  - Material 3
  - Microsoft Fluent 2
  - Porsche Design System
  - Salesforce SLDS 2
  - Shopify Polaris
  - USWDS
- Each case contains original `DESIGN.md`, metadata, claim-level evidence, normalized roles, source notes, editorial review state, and original preview specification.
- Refero domains are rejected as case sources by the validator.
- Source screenshots, fonts, images, PDFs, and other binary source assets are not stored in canonical seed records.
- Compact local manifest with 12 routing entries and 12/60/150/300 milestones.
- Progressive retrieval sequence: manifest -> category index -> ranked summaries -> finalist `DESIGN.md` -> validation evidence/tokens.
- Offline fallback that continues with bundled craft guidance, user references, and available public research while explicitly lowering confidence.
- Dependency-free static reference Site foundation with search, archetype/platform filters, and comparison of up to five cases.
- Site remains undeployed and unpublished.

Wave 4 qualification:
- Safety-branch candidate `84a242f674811969f3b1a45d9669dca4ae183ac5` passed first.
- Qualified work was merged into canonical without force-updating.
- A separate additive staging stream was retained in the private archive and excluded from the public project.
- Canonical candidate `7666c1dc1b35f4090ee91984110dd0297a51839a` then passed CI run `33336630872`.
- Corpus validator: 12 cases, pass.
- Catalog generator: pass.
- Full suite: 60 tests on Python 3.11 and 60 on Python 3.13, pass.
- Both host builds and shared-core parity: pass.
- MCP bundled: No.
- Full corpus bundled: No.
- Site bundled: No.

Wave 4 exit gate:
- Canonical case schemas: Pass.
- Source and publication policy: Pass.
- Design taxonomy: Pass.
- 12 engineering seed cases: Pass.
- Catalog generation and validation: Pass.
- Progressive remote retrieval structure: Pass.
- Small local catalog manifest: Pass.
- Reference Site search and comparison foundation: Pass.
- Offline fallback: Pass.

## Wave 5 result

PASS. Research, forensics, and directions are complete.

- Research plans bind to the approved shared-understanding SHA-256.
- Substantial, repair, and audit research modes have bounded targets.
- Evidence uses the approved truth classes: observed, measured, inferred, estimated, recommended, and unknown.
- Candidate scoring weights project fit highest and keeps hard evidence and craft floors.
- Forensic dossiers cover the nine required design dimensions.
- Color, media, and density roles record preserve, adapt, or reject decisions.
- Substantial projects require 3 to 5 directions with one dominant primary reference per direction.
- Secondary references have narrow named jobs.
- Direction pairs must differ across at least four of nine dimensions.
- Directions include traceable evidence, forbidden drift, and rejected nearby alternatives.
- Progressive disclosure separates decision, expert, and evidence layers.
- Audit mode produces no directions unless redesign is separately authorized.

Historical Wave 5 qualification:
- Source runtime commit: `d9ef0863955d4d79055428ef1764d969c61e9b54`.
- Source evidence commit: `fac32c86c69d5b31e5c4e53280b5e7ce97241253`.
- Source CI run: `33339143756`.
- Tests: 76 on Python 3.11 and 76 on Python 3.13, pass.
- Evidence: `review/wave-5-research-evidence.json`.

Post-migration qualification:
- Candidate commit: `12b7107580810f5bcd414d89ac18bd981aa409fe`.
- CI run: `33341295869`.
- Tests: 77 on Python 3.11 and 77 on Python 3.13, pass.
- Both host builds, shared-core parity, corpus validation, catalog generation, and bundled runtime entrypoints: Pass.
- MCP, full corpus, Site, screenshots, fonts, renders, and generated Python bytecode in packages: None.

## Wave 6 result

PASS. Reference lock, UX definition, canonical `DESIGN.md`, semantic tokens, and implementation planning are complete.

- Five internal skills: Lock, UX, Design MD, Tokens, and Plan.
- Standard-library `design_system.py` runtime and five portable skill launchers.
- Reference lock binds the approved understanding, decision, direction set, dominant source, and bounded supporting roles by SHA-256.
- UX definition requires complete information architecture, screens, flows, states, responsive behavior, mobile task priorities, accessibility, and explicit Figma handoff scope.
- Structured design-system source compiles deterministic root `DESIGN.md` with 30 canonical sections and exact artifact bindings.
- Stable DTCG 2025.10 token source validates semantic descriptions, aliases, cycles, types, and existing-token preserve or map strategy.
- Token projections include canonical JSON, CSS variables, Tailwind theme values, Figma variable specification, mobile values, and a projection report.
- Display P3 and other DTCG color spaces retain their color-space meaning instead of being flattened to sRGB.
- Structured implementation plans define bounded waves, exact relative file scope, render targets, tests, completion criteria, rollback, risk, and separately approved external actions.
- Plan validation accepts only `repository_change_gate: awaiting_approval` and verifies current compiled `plan.md`.
- Research and system verification use current state-gate evidence instead of accepting free-standing digests when Design state exists.
- The post-audit candidate passed CI run `33346612875` with 162 tests on Python 3.11 and Python 3.13.
- Original Wave 6 host builds, 68-file shared-core parity, corpus validation, catalog generation, and bundled runtime entrypoints: Pass.
- Evidence: `review/wave-6-system-definition-evidence.json`.

## Wave 7 result

PASS. Imagery, Figma, and mobile adapters are complete.

- Three internal skills: Imagery, Figma, and Mobile.
- Standard-library `design_adapters.py` runtime and three portable skill launchers.
- Imagery planning binds the approved direction, reference lock, and `DESIGN.md` by SHA-256.
- Medium selection distinguishes code-native graphics, screenshots, standard icons, charts, and bitmap generation.
- Prompt-only work has an output ceiling of zero and cannot claim that assets were generated.
- Direction, production, and repair batches require a purpose-specific approval state, exact output ceiling, complete canonical request hash, and byte-exact approval note.
- Any prompt, output target, source, reference, asset lock, scope, purpose, or ceiling change makes imagery approval stale.
- Asset locks cover composition, subject, materials, color, lighting, visible text, frozen properties, allowed variation, prohibited drift, and acceptance criteria.
- Series work requires fixed shared visual DNA, batch size, naming, variation, and acceptance rules.
- Targeted edits compile `LOCK`, `CHANGE`, and `VERIFY` and stop after three passes.
- Figma capability is detected rather than assumed, and the plugin bundles no Figma MCP.
- The Figma fallback is a structurally validated handoff scaffold. It is not claimed complete or rebuild-ready without separate project-specific coverage proof.
- Direct Figma actions require an authorized connection, exact target file, structured action list, per-action destructive flags, aggregate destructive classification, and a byte-exact approval bound to the complete canonical request.
- Mobile routing explains responsive web, cross-platform, and native options against nine required project factors.
- Mobile routing chooses the simplest option satisfying every hard requirement and returns to grilling when none is viable.
- Wave 7 aggregate verification first validates the complete current Wave 6 chain.
- Post-audit CI run `33346612875` passed 162 tests on Python 3.11 and Python 3.13.
- Both host builds, 94-file shared-core parity, corpus validation, catalog generation, and all bundled runtime entrypoints: Pass.
- Evidence: `review/wave-7-visual-adapters-evidence.json`.

## Wave 8 result

PASS. The controlled build-wave engine is complete.

- Internal Build Wave skill, standard-library runtime, schemas, templates, and reference contract.
- One to seven waves are derived from the exact approved structured implementation plan.
- Each prepared manifest is immutable, state-bound, plan-bound, scope-bounded, and dependency-checked.
- The engine distinguishes product scope from its own control artifacts.
- Changed product files require current SHA-256 evidence; deleted files use an explicit deleted state.
- Every planned test, completion criterion, and render target must reach an allowed terminal result.
- Readable `handoff.md`, structured handoff, verification receipt, and state all bind each other by hash.
- Completed dependency product files and readable handoffs are rechecked before a dependent wave starts.
- Implementation worker, independent verifier, and Unslop reviewer must be three distinct identities, and every review must pass.
- The state controller re-runs verification before closing a wave and alone advances to the next wave or rendering.
- Direct `building` to `rendering` transitions are forbidden.
- CI run `33346612875` passed 162 tests on Python 3.11 and Python 3.13.
- Both host builds, 94-file shared-core parity, corpus validation, catalog generation, and all bundled runtime entrypoints: Pass.
- Evidence: `review/wave-8-build-waves-evidence.json`.

## Wave 9 result

PASS. Source, CI, Unslop, and independent integrated-ledger verification are complete.

- Render plans bind the approved implementation plan, UX definition, exact quality targets, routes, states, viewports, themes, reduced-motion settings, and required status.
- Render evidence validates local relative paths, SHA-256 hashes, standard non-interlaced PNG structure, CRCs, decodable image payloads, and exact dimensions.
- Passing records cannot disclaim the required observation. Validation does not substitute for actual browser capture or inspection.
- QA covers typography, spacing, color, media, hierarchy, responsive behavior, accessibility, states, overflow, touch, motion, interaction, content, and applicable code quality.
- Accessibility evidence requires eight inner checks, aggregate consistency, measured evidence, and reasons for every not-applicable result.
- Findings preserve audit category, truth class, confidence, target, evidence, expected result, and P0 to P3 severity.
- Repairs bind exact finding IDs, approved repository scope, current authority, and exact rerender target IDs.
- The fourth repair attempt is rejected before state or file mutation. Repair cannot delete files or widen scope.
- Generic phase transitions cannot bypass render, QA, repair, deviation, or scorecard evidence.
- Audit remains read-only until a bounded repair plan receives current repository-change approval.
- Learning is proposal-only, requires distinct evidence from at least two projects plus a strict privacy review, and has no activation command.
- CI run `33350739053` passed 193 tests on Python 3.11 and Python 3.13.
- Both host builds, 123-file shared-core parity, corpus validation, catalog generation, and the pre-Wave 9 bundled entrypoint set in CI: Pass.
- Wave 9 runtime and all quality launchers in source and both distributions: Independent local compile and smoke test pass.
- Source verifier runtime attacks: Pass. Integrated ledger verdict: Pass.
- Fresh exact-candidate Unslop review: Pass.
- Evidence: `review/wave-9-quality-loop-evidence.json`.

## Wave 10 result

PARTIAL. Host packaging and public repository publication passed. Automatic activation qualification remains partial.

- OpenAI and Claude host manifests: Pass.
- Deterministic distributions and installable archives: Pass.
- Exact Codex and Claude Code install, update, removal, and verification guidance: Pass.
- Only Design, Design Audit, and Design Resume are user-visible: Pass.
- Nineteen internal skills are installed in both host packages: Pass.
- Activation fixtures: 9 positive and 6 negative, with precedence Resume, Audit, Run.
- Isolated temporary Codex and Claude lifecycle checks: Pass.
- Prior test version to dev.10 update, cache parity, fresh-process discovery, and scoped removal: Pass.
- Active user registries unchanged: Yes.
- Credentials copied: No.
- Shared files: 125, byte-identical.
- OpenAI distribution: 627,146 bytes. Claude distribution: 626,168 bytes.
- MCP, full corpus, Site, browser binaries, fonts, screenshots, renders, and bytecode bundled: No.
- Public repository, anonymous clone, and first public CI on the exact root snapshot: Pass.
- Public CI run `33353752204` passed 204 tests on Python 3.11 and Python 3.13.
- Codex prompt-input routing exposure: Pass, but model selection is not proved.
- Claude installed component discovery: Pass, but model selection is not proved.
- Harness-independent runtime selection: Blocked. No separate preauthenticated Codex home or bare-compatible Claude API-key path was supplied. Codex CLI 0.151 JSONL has no accepted resolved-model field in the current evidence set.
- Nonqualifying Claude method canaries: One positive native Skill selection and one negative boundary ran through the existing subscription login. They received no acceptance credit.
- Clean qualification model inference: Not called.
- At Wave 10 qualification time, user-machine active installation, deployment, release, or tag: None. The current dual-host installation happened afterward at the frozen baseline above.
- Evidence: `review/wave-10-host-qualification-evidence.json` and `review/r04-runtime-selection-preflight.json`.

## Wave 11 checkpoint

PARTIAL. The personal-alpha corpus and local reference Site are qualified. The three benchmarks remain.

- Authorization and lane contract: `review/wave-11-alpha-allocation.json`.
- Canonical case count: 60.
- Publication state: 60 public, zero review or draft cases.
- Exact lane counts: 15/15/10/8/7/5, matching the approved alpha allocation.
- Required files: Nine per case, present and schema-valid.
- Owner-source audit: Pass, 80 of 80 URLs, zero locator mismatches, zero stored identity-hash mismatches, and zero effective-URL collisions.
- Source-audit binding: `8d10eb6cdd7fdf65f50fde4f1f0c47105a180d6f81baefb710298fbc34ab96a2`.
- Originality and writing audit: Pass across all 60 cases.
- Originality binding: `d1b3144802fbc81ccee56688e75091fbe180797c456746367206e78472336e20`.
- Source assets, screenshots, logos, fonts, and other owner binaries stored: None.
- Public catalog generation: Pass, accepted-only, 60 cases.
- Site features: Search, six lane filters, six advanced facets, sort, progressive case analysis and evidence, canonical source retrieval date, owner-source link, URL filter state, and comparison of two to five cases.
- Site visual treatment: Original CSS-only abstract previews generated from canonical preview specifications. No remote visual dependency or source asset is loaded.
- Desktop browser: 60 cards, seven lane controls including All, detail routes, evidence routes, and five-case comparison pass at 1280 by 720. Page-level horizontal overflow: None. Console warnings or errors: None.
- Mobile browser: Single-column cards and dialogs fit a 390 by 844 viewport. Page-level horizontal overflow: None. The wide comparison table scrolls inside its own container.
- Site deployment: Not authorized and not performed.
- Local tests: 242 passed under Python 3.9.6. Fresh public CI on Python 3.11 and Python 3.13 remains pending for this candidate.
- Independent technical Site review: Pass.
- Independent Site writing and Unslop review: Pass after six exact wording repairs.
- Independent plan review: Pass after source-date and durable-state repairs.
- Benchmarks: 0 of 3 complete.
- Wave 11: Partial.
- R04: Partial, explicitly deferred as a nonblocking evidence gap for this work.
- R22: Partial.

The evidence-only commit is accepted only when the public Design Plugin CI check attached to the current HEAD succeeds. That post-commit result is owned by GitHub Actions and is intentionally not embedded in the commit it verifies.

## Next required work

Mirror the accepted corpus and Site source into the private repository, push the independently reviewed candidate to both repositories, and pass public CI. Then run the three approved Wave 11 benchmarks and repair any critical workflow failure within scope.

R04 cannot pass until both hosts produce native selection evidence for all explicit, automatic, negative, and precedence cases. The runner refuses the active harness and contains no credential-copy operation. Codex credential provenance still requires external attestation. These qualification restrictions are absent from the distributed runtime, so they cannot reject an ordinary installation. Normal multi-plugin compatibility is not proved by R04. The user explicitly accepted this as a noncritical, nonblocking evidence gap for Wave 11 work. It remains partial and is not silently converted to a pass.

## Recovery instruction

After any context loss, read in this order:
1. Notion `Design Plugin: Build Hub` and `Current Build State & Recovery Ledger`.
2. Repository `BUILD_STATE.md`.
3. `PLAN.md`.
4. `requirements/traceability.yaml`.
5. `review/wave-11-alpha-allocation.json` and the current Wave 11 evidence receipts.
6. `review/wave-10-host-qualification-evidence.json`.
7. `review/repository-migration-evidence.json`.
8. `review/wave-9-quality-loop-evidence.json`.
9. `review/wave-8-build-waves-evidence.json`.
10. `review/wave-7-visual-adapters-evidence.json`.
11. `review/wave-6-system-definition-evidence.json`.
12. `review/wave-5-research-evidence.json`.
13. Current `main` branch state and latest CI result.
14. The active wave plan and completion criteria.

Do not infer progress from memory. Verify repository evidence and update this file before continuing.
