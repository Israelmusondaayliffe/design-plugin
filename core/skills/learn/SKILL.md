---
name: learn
description: Internal proposal-only learning phase for completed Design work. Separate project facts from reusable candidates, require multi-project evidence and privacy review, and validate a local proposal without activating or writing it anywhere else. Not a standalone user workflow.
user-invocable: false
---

# Design Learn

Design owns bounded feedback inside an active Design task. Practice Compiler alone owns cross-harness learning. Learning is optional and proposal-only. A successful project does not create a universal rule.

## Private event capture

Use the bundled `scripts/design_learning.py` only when a feedback, friction, repair, missed-tool, cost, or user-method event is worth retaining. The tool writes to `DESIGN_LEARNING_ROOT` when set, otherwise to the operating system's private user-state directory. It rejects symlinks and roots inside Git worktrees, plugin sources, distributions, Sites, review folders, or evidence packages.

Capture redacted paraphrases by default. Retain an exact quote only when the user explicitly says to retain it, for example `file this`, and pass `--retain-exact-quote`. Project identifiers are opaque. V1 never deletes automatically.

```text
python3 scripts/design_learning.py capture --project-key PROJECT --category friction --summary "REDACTED SUMMARY"
python3 scripts/design_learning.py list --project-key PROJECT
python3 scripts/design_learning.py export --project-key PROJECT
python3 scripts/design_learning.py purge-before-date --before 2026-01-01T00:00:00Z
python3 scripts/design_learning.py purge-project --project-key PROJECT
```

The export is neutral and deduplicated by stable fingerprint. It contains no exact quotes or raw event paths. Practice Compiler may ingest that export only through its explicit Design-export adapter. Design never writes to Practice Compiler state or edits another plugin.

Use `templates/learning-proposal.template.json` only when the same narrow observation has evidence from at least two projects. Keep source project identifiers opaque. Bind each observation and evidence artifact to one opaque project identifier, and use a distinct evidence artifact for each project. Redact private details, client names, proprietary code or copy, personal information, secrets, absolute paths, and benchmark data.

Every proposal includes project-bound observations, distinct hashed evidence artifacts, candidate rule, exceptions, risks, conflicts, destination candidate, evaluation on a separate project, a hashed privacy-review record, and pending approval. Build the review record from `templates/learning-privacy-review.template.json`. It must declare a human reviewer and cover the proposal, every evidence artifact, private details, absolute paths, secrets, and benchmark data. An explicit synthetic or non-human review record is invalid.

Multi-project proposals remain project-local review artifacts. Write them only under `.design/learning/proposals/`, then validate:

```text
python skills/learn/scripts/design_quality.py validate-learning \
  --project-root . \
  --proposal .design/learning/proposals/<proposal-id>.json
```

The `validate-learning` subcommand is read-only and has no activation command. Its checks cannot prove that a source really came from the named project or that a human privacy review was competent. Separate review and approval are required before any later destination write.
