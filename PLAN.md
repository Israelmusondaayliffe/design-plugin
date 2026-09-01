# Design Plugin Build Plan v1.0

Status: Approved 2026-08-30

The canonical detailed plan and recovery ledger live in the Design Plugin Build Hub in Notion. This repository copy is intentionally concise and records the non-negotiable sequence needed to recover after context loss.

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
- Wave 10 host packaging and public repository publication: Passed.
- Public repository: `https://github.com/Israelmusondaayliffe/design-plugin`.
- Installed host baseline: Public commit `41d849aeef0b0104cf0fe6ff1e0420843dbf172f`, version `0.1.0-dev.10`, is installed in Codex and Claude Code. Installation does not count as harness-independent selection proof.
- Wave 11: Active by explicit user authorization. The personal-alpha corpus milestone now contains 60 independently accepted original cases in the exact 15/15/10/8/7/5 lane allocation.
- Corpus evidence: 80 of 80 owner URLs pass, locator mismatches and redirect collisions are zero, the originality audit passes, and no source binary assets are stored.
- Local Site: Qualified against the accepted-only 60-case public catalog at desktop and mobile widths. Search, all six lanes, deeper filters, progressive analysis and evidence, source retrieval dates, URL state, and comparison of up to five cases pass. The Site remains undeployed.
- Published Wave 11 candidate: Public commit `93908428c8949cf57f77f374fab13659e803bd80` and private counterpart `457c825f6498887b0e5bf43eaa964f2499e79de8` contain byte-identical shared project files.
- Regression evidence: 242 tests pass locally under Python 3.9.6 and in both repositories under Python 3.11 and Python 3.13. Public CI run `33548219494` and private CI run `33548217993` pass.
- Activation boundary: R04 remains partial and is explicitly deferred as a nonblocking evidence gap for this work. The probe restrictions are not plugin runtime restrictions and cannot reject an ordinary installation.
- Acceptance boundary: Wave 11 remains partial until all three benchmarks pass. R22 remains partial until those benchmarks and later acceptance gates pass.
- Next: Run the three approved benchmarks and repair any critical workflow failure within the authorized scope. Public Site deployment still requires separate authorization.

## Benchmarks

The persistent benchmark suite lives in the Design Plugin Validation Projects section in Notion:
1. The House of Curiosity Website.
2. Forensic Reference Extraction to Original Design System.
3. Curiosity Atlas: AI Visual Production OS.

## Acceptance

The plugin is not accepted until every R01-R22 requirement is mapped to implementation, test, evidence, and a passing result. No hard requirement may remain failed, partial, or untested.
