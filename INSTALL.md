# Design plugin installation

The repository builds two local marketplace packages from one shared source. Building and verifying them installs nothing and changes no active host configuration.

## Build and verify

From the repository root:

```bash
python3 scripts/build_distributions.py
python3 scripts/build_installable_packages.py
python3 scripts/verify_distributions.py
python3 scripts/verify_installable_packages.py
```

Generated marketplace roots:

- OpenAI and Codex: `dist/installable/openai`
- Claude Code: `dist/installable/claude`

Generated release archives and their SHA-256 values are recorded under `dist/releases/`.

## Permission boundary

The commands below modify a host's plugin configuration and cache. Run them only after the user explicitly approves installation in that host. Building, validation, or approval of the Design project does not authorize installation.

## OpenAI and Codex

Replace `/absolute/path/to/design-plugin` with the repository's absolute path.

Install:

```bash
codex plugin marketplace add "/absolute/path/to/design-plugin/dist/installable/openai"
codex plugin add design@design-local-openai --json
```

Update after rebuilding the package:

```bash
codex plugin add design@design-local-openai --json
```

Remove:

```bash
codex plugin remove design@design-local-openai --json
codex plugin marketplace remove design-local-openai --json
```

Start a new Codex task after installation or update. The visible skills should be `design:run`, `design:audit`, and `design:resume`. Internal workflow skills should not appear as standalone choices.

## Claude Code

Replace `/absolute/path/to/design-plugin` with the repository's absolute path.

Install:

```bash
claude plugin marketplace add "/absolute/path/to/design-plugin/dist/installable/claude" --scope user
claude plugin install design@design-local-claude --scope user
```

Update after rebuilding the package:

```bash
claude plugin marketplace update design-local-claude
claude plugin update design@design-local-claude --scope user
```

Remove:

```bash
claude plugin uninstall design@design-local-claude --scope user --yes
claude plugin marketplace remove design-local-claude --scope user
```

Restart Claude Code after installation or update. The visible slash commands should be `/design:run`, `/design:audit`, and `/design:resume`. Internal workflow skills should not appear as standalone commands.

## Isolated qualification

`scripts/run_isolated_host_checks.py` uses temporary Codex and Claude configuration directories. It installs, updates, inspects, and removes Design only inside those temporary directories, then deletes them. It never changes the active user plugin configuration.

```bash
python3 scripts/run_isolated_host_checks.py
```
