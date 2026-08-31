---
name: learn
description: Internal proposal-only learning phase for completed Design work. Separate project facts from reusable candidates, require multi-project evidence and privacy review, and validate a local proposal without activating or writing it anywhere else. Not a standalone user workflow.
user-invocable: false
---

# Design Learn

Learning is optional and proposal-only. A successful project does not create a universal rule.

Use `templates/learning-proposal.template.json` only when the same narrow observation has evidence from at least two projects. Keep source project identifiers opaque. Bind each observation and evidence artifact to one opaque project identifier, and use a distinct evidence artifact for each project. Redact private details, client names, proprietary code or copy, personal information, secrets, absolute paths, and benchmark data.

Every proposal includes project-bound observations, distinct hashed evidence artifacts, candidate rule, exceptions, risks, conflicts, destination candidate, evaluation on a separate project, a hashed privacy-review record, and pending approval. Build the review record from `templates/learning-privacy-review.template.json`. It must declare a human reviewer and cover the proposal, every evidence artifact, private details, absolute paths, secrets, and benchmark data. An explicit synthetic or non-human review record is invalid.

Write only under `.design/learning/proposals/`, then validate:

```text
python skills/learn/scripts/design_quality.py validate-learning \
  --project-root . \
  --proposal .design/learning/proposals/<proposal-id>.json
```

The `validate-learning` subcommand is read-only and has no activation command. Its checks cannot prove that a source really came from the named project or that a human privacy review was competent. Separate review and approval are required before any later destination write.
