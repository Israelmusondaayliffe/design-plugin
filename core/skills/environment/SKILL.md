---
name: environment
description: Internal pre-interview project and capability inspection for active Design workflows. Inspect existing files, design artifacts, local development prerequisites, and host-visible connections before asking the user avoidable questions. Explain missing prerequisites in plain language and never install anything without separate explicit permission. Not a standalone user workflow.
user-invocable: false
---

# Design Environment Inspection

Inspect before questioning. The purpose is to learn what the project and current host can already answer so the Grilling skill does not waste the user's time or invent technical constraints.

## Local inspection

Use the skill-local helper:

```bash
python3 scripts/design_intake.py inspect --project "$PROJECT_ROOT"
```

For a new workflow, scaffold the project-local intake artifacts:

```bash
python3 scripts/design_intake.py scaffold --project "$PROJECT_ROOT"
```

The helper is standard-library-only. It accesses no network, installs nothing, and writes only `.design/` artifacts. It detects common project files, existing Design artifacts, project directories, package-manager hints, Git presence, and common local executables.

Inspect relevant existing files rather than merely listing them. Prioritize, when present:

- root `DESIGN.md` and `.design/`
- README, AGENTS.md, CLAUDE.md, product or brand documentation
- package and framework configuration
- app/page/component structure
- user-provided screenshots, images, and assets
- existing tokens, CSS, themes, design-system packages, or Figma handoff files
- current site or preview information available through the host

Do not rewrite or restructure existing Design artifacts during inspection.

## Host capability inspection

The local helper cannot see host-managed tools. The agent must separately inspect what the current host exposes, including when relevant:

- browser or preview capability
- image generation/editing capability
- Figma connection or plugin
- filesystem/repository write authority
- mobile build or simulator capability
- connected design or documentation sources

Record capability availability and limitations in `.design/environment.json`. Do not claim a connector is available merely because its software may exist on the machine.

## Question suppression

Pass confirmed environment facts to Grilling. Do not ask the user:

- which framework the project uses when repository files establish it
- whether a design system exists when its files are present
- whether an image tool or Figma connection is available when the host can directly inspect that fact
- for content or assets already supplied

Ask only when evidence is missing, contradictory, stale, or would require a user preference rather than a technical observation.

## Installation boundary

Inspection does not authorize installation. Never install Node.js, package managers, Playwright, Chromium, browsers, fonts, CLIs, SDKs, mobile toolchains, Figma helpers, or dependencies without a separate explicit approval.

Before asking to install anything, explain:

- Tool
- What it is
- Why this project might need it
- What it changes on the computer
- Approximate disk use, clearly labeled as an estimate when exact size is unknown
- Whether it runs in the background
- Whether it is required or optional
- A viable alternative without installing, when one exists
- How to remove it
- The exact command that would be run

Then ask for explicit approval for that named installation. Approval of the Design plan, a repository-change plan, or another tool does not authorize an unspecified installation.

## Environment artifact

`.design/environment.json` must distinguish:

- observed project facts
- detected local executables
- host-reported capabilities
- unavailable or unverified capabilities
- proposed prerequisites
- installation approval status

The initial local probe must record `software_installed: false` and `network_accessed: false`.

## Completion

Environment inspection is complete when the plugin has enough evidence to avoid redundant technical questions and can identify which remaining decisions truly require the user. No software installation is part of this skill's completion criteria.
