# Design

Design is a research-grounded design operating system for Codex and Claude Code. It reaches a shared understanding before research, presents distinct evidence-backed directions, compiles an approved design system, implements in bounded waves, renders the result, and repairs measurable drift.

This directory is the canonical source package. Do not edit generated files under `dist/` by hand.

## Install

Clone the repository and build the two generated local marketplaces:

```bash
git clone https://github.com/Israelmusondaayliffe/design-plugin.git
cd design-plugin
python3 scripts/build_distributions.py
python3 scripts/build_installable_packages.py
```

Install in Codex:

```bash
codex plugin marketplace add "$PWD/dist/installable/openai"
codex plugin add design@design-local-openai --json
```

Install in Claude Code:

```bash
claude plugin marketplace add "$PWD/dist/installable/claude" --scope user
claude plugin install design@design-local-claude --scope user
```

Start a fresh task after installation. Invoke `$design:run`, `$design:audit`, or `$design:resume` in Codex. Invoke `/design:run`, `/design:audit`, or `/design:resume` in Claude Code.

See [INSTALL.md](INSTALL.md) for verification, update, restart, and removal commands.

## Build and verify distributions

```bash
python3 scripts/build_distributions.py
python3 scripts/build_installable_packages.py
python3 scripts/verify_distributions.py
python3 scripts/verify_installable_packages.py
```

All four scripts use only the Python standard library. They install nothing and make no network calls.

## Canonical structure

- `core/`: shared skills, references, schemas, templates, and compact catalog manifest.
- `hosts/openai/`: OpenAI/Codex-only manifest, skill metadata, and documentation.
- `hosts/claude/`: Claude Code-only manifest and documentation.
- `dist/`: deterministic generated distributions.
- `requirements/`: plan requirements and traceability.
- `review/`: plan-compliance evidence.

The full Design Knowledge Corpus and its generated reference Site are not bundled in either plugin distribution.
