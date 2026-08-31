# Upstream Map

Pinned source: `referodesign/refero_skill@1d324d5be0492352e2c8702f70a4f9c386c2345f`

This file records what is intentionally carried forward from the MIT-licensed Refero Design plugin. The finished Design plugin is independent at runtime and does not require Refero, its MCP, or a Refero account.

| Upstream path | Treatment | Destination / effect |
|---|---|---|
| `skills/refero-design/SKILL.md` | Rewrite from licensed methodology | Split across Design orchestration, research, direction, lock, compiler, build, QA, and repair skills. Preserve research-before-design, reference locks, decision traceability, bounded secondary references, role preservation, and render validation. Remove Refero-specific routing and MCP calls. |
| `references/visual-workflow.md` | Adapt | Design imagery, visual-direction, render, QA, and repair skills. Preserve target locks, intentional asset generation, severity-based QA, and post-build comparison. |
| `references/anti-ai-slop.md` | Rewrite from principle | Contextual anti-generic-design checks. Replace universal aesthetic bans with evidence tests and project-specific justification. Preserve anti-averaging, token-role drift, media-role preservation, identity tests, and intentional-design principle. |
| `references/typography.md` | Adapt selectively | Typography craft reference. Preserve hierarchy, scale discipline, tracking, line length, responsive type, wrapping, accessibility, and performance. Remove claims that one preset is universally correct. |
| `references/color.md` | Adapt selectively | Color craft reference. Preserve semantic tokens, contrast, purposeful roles, dark-theme mechanics, and role-based naming. Replace categorical palette bans with evidence-based checks. |
| `references/motion.md` | Adapt selectively | Motion craft reference. Preserve feedback/continuity/hierarchy purposes, timing discipline, reduced motion, explicit transitions, and interruptibility. |
| `references/icons.md` | Adapt selectively | Icon craft reference. Preserve consistency, optical correction, sizing, currentColor, accessibility, and touch targets. |
| `references/copywriting.md` | Adapt selectively | Interface and marketing copy craft reference. Preserve clarity, concrete proof, action labels, errors, empty states, and operational copy principles. |
| `references/craft-details.md` | Adapt selectively | Accessibility, forms, image loading, mobile/touch, navigation, performance, and implementation QA. |
| `references/example-workflow.md` | Study only | Used to validate phase separation and evidence-led synthesis. No sample product or example copy is shipped as canonical guidance. |
| `references/mcp-tools.md` | Discard | No Refero MCP, Refero account, or Refero tool names in the finished plugin. |
| `.mcp.json`, `mcp.json`, `server.json`, MCP publishing workflow | Discard | Runtime independence from Refero is a locked requirement. |
| Refero manifests and branding | Study only | New Design manifests and branding are authored independently for Codex and Claude Code. |

## Corpus boundary

The external Design Knowledge Corpus will contain original evidence-based analyses. It will not bulk-copy Refero `DESIGN.md` records, screenshots, or catalog data.

## Attribution rule

The Refero copyright and MIT permission notice remain in `NOTICE` and `THIRD_PARTY_NOTICES.md` in distributions that contain substantial adapted portions.
