# Design Plugin Build Plan v1.0

Status: Approved 2026-08-30

Canonical detailed plan and recovery ledger live in Notion under `Design Plugin — Build Hub`. This repository copy is intentionally concise and records the non-negotiable sequence needed to recover after context loss.

## Product

- Two plugins: Codex-first OpenAI edition and Claude Code edition.
- One canonical shared design core.
- No Refero MCP or Refero account dependency.
- Full external Design Knowledge Corpus, with a small bundled manifest only.
- User-visible workflows: Design, Design Audit, Design Resume.
- Automatic activation allowed for unmistakable design work.

## Mandatory project sequence

1. Inspect available request, repository, assets, connections, and tools.
2. Run a full shared-understanding interview.
3. Obtain explicit approval (`Approved` or `This understanding is approved`) or record an explicit skip warning.
4. Research design evidence.
5. Present 3-5 meaningfully distinct directions for substantial work.
6. Obtain direction approval.
7. Produce reference lock, UX definition, root DESIGN.md, and tokens.
8. Produce an implementation plan divided into bounded waves.
9. Obtain repository-change approval.
10. Build one wave at a time with durable handoffs.
11. Render relevant web/mobile states.
12. Run visual, responsive, accessibility, interaction, content, and code QA as applicable.
13. Run no more than three targeted repair passes per affected state.
14. Deliver deviations and final scorecard.
15. Propose broadly reusable learning separately. Never activate learning without audit and approval.

## Grilling protocol

- Fundamental for every Design workflow.
- Up to 6 rounds.
- Normally 3-6 questions per round.
- High-impact questions may be asked one at a time.
- Target 18-30 questions for substantial ambiguous projects; a final round may exceed 30 when needed.
- User may approve or skip early. Warn that unresolved assumptions lower confidence and can cause mismatches, then respect the skip.
- Do not ask for information already visible in the request, repository, assets, or connected tools.

## Research rules

- Truth classes: observed, measured, inferred, estimated, recommended, unknown.
- Screen references answer structure and state questions. Flow references answer user-flow questions. Style references answer visual-language questions.
- Screen references must not silently become the visual authority.
- Rank by evidence quality, craft threshold, project fit, and feasibility.
- One dominant design foundation per direction. Secondary references have bounded jobs.
- Preserve role meanings for color, typography, component, media, and interaction decisions.
- Never average strong references into a safe centroid.

## Progressive disclosure

Use progressive disclosure for interview depth, remote corpus retrieval, reference evidence, directions, technical details, and QA. The plugin should remain understandable to a non-technical user while retaining expert-level evidence on demand.

## Environment and external action boundaries

Always ask before installing software. Explain what the tool is, why it may be needed, what it changes, approximate disk use, whether it runs in the background, whether it is optional, alternatives, removal, and the exact command.

Separate explicit approval is required for deployment, publishing, purchases, paid accounts, image-generation usage when the generation approval rule applies, unspecified destructive repository changes, and external writes not already approved.

## Corpus milestones

- Engineering seed: 12 cases for schema and retrieval testing.
- Personal alpha: 60 deeply reviewed original cases.
- Team beta: 150 cases.
- Public v1.0: 300 cases.

Final 300 distribution:
- 75 brand/editorial/portfolio/marketing
- 75 SaaS/dashboard/admin/productivity
- 50 mobile
- 40 commerce/media/content-heavy
- 35 onboarding/forms/settings/checkout/flows
- 25 design systems/data visualization/experimental

Canonical corpus source: version-controlled Markdown and JSON. ChatGPT Site is the generated searchable interface. If the Site is unavailable, continue with bundled craft guidance, local manifest, user references, and live public research when available, while clearly lowering confidence.

## Core build waves

0. Provenance and requirement baseline.
1. Repository and packaging generator.
2. Orchestrator, state machine, and resume.
3. Grilling and environment inspection.
4. Corpus schema and Site engineering seed.
5. Research, forensics, and directions.
6. Lock, UX, DESIGN.md, tokens, and planning.
7. Imagery, Figma, and mobile adapters.
8. Build-wave engine.
9. Rendering, QA, repair, audit, and learning.
10. Host packaging and internal qualification.
11. Personal alpha at 60 cases plus three benchmarks.
12. Team beta at 150 cases.
13. Public v1.0 at 300 cases.

## Current checkpoint

- Waves 0 through 9: Qualified.
- Wave 9 private-archive source candidate: `a488da4694dedfe536ec1fd66f914a3eaa3c63b7`; no public locator.
- Wave 9 private-archive source CI: Run `33350739053` passed 193 tests on Python 3.11 and Python 3.13, both host builds, 123-file shared-core parity, corpus validation, catalog generation, and the pre-Wave 9 bundled entrypoint set.
- Wave 9 source verification: Runtime attacks passed independent Sol xhigh review. Independent local checks compiled and smoke-tested the Wave 9 runtime and all quality launchers in source and both distributions. A fresh exact-candidate Sol high Unslop review passed.
- Wave 9 integrated ledger: Independent Sol xhigh review passed with no P0, P1, P2, or P3 findings.
- Next: Wave 10 host packaging and internal qualification. Live plugin installation is not approved.
- GitHub workflow hardening: Prepared and ready for the evidence commit. The user approved the required token change, and GitHub confirms the `workflow` scope is active. The existing remote workflow already ran the complete source suite and packaging checks successfully.

## Benchmarks

The persistent benchmark suite lives in Notion under `Design Plugin — Validation Projects`:
1. The House of Curiosity Website.
2. Forensic Reference Extraction to Original Design System.
3. Curiosity Atlas: AI Visual Production OS.

## Acceptance

The plugin is not accepted until every R01-R22 requirement is mapped to implementation, test, evidence, and a passing result. No hard requirement may remain failed, partial, or untested.
