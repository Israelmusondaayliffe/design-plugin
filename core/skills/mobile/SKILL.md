---
name: mobile
description: Internal mobile-routing phase for active Design runs. Explain responsive web, cross-platform application, and fully native mobile application paths, test each against project evidence, and recommend the simplest valid option without forcing a framework choice. Not a standalone user workflow.
user-invocable: false
---

# Design Mobile

Do not treat the word mobile as a framework decision. First explain the three possible product paths in plain language:

1. Responsive website.
2. Cross-platform mobile application.
3. Fully native iOS or Android application.

## Evidence

Write `.design/mobile/decision.json` from `templates/mobile-decision.template.json`. Record findings, evidence, and confidence for:

- device features
- app-store requirements
- offline behavior
- performance
- current codebase
- team ability
- budget
- maintenance
- desired experience

Explain the consequence of each factor for all three paths. Mark product requirements as hard or flexible and record whether each path satisfies them.

## Routing rule

Choose the simplest path that satisfies every hard requirement. The order is responsive web, cross-platform, then fully native.

If no path satisfies the current requirements, return to shared understanding with the smallest set of product questions needed to resolve the conflict. Do not hide uncertainty inside a framework recommendation.

A framework may be proposed only after the product path is valid and its consequences are explained. It may remain deferred.

Validate and compile with:

```text
python skills/mobile/scripts/design_adapters.py validate-mobile .design/mobile/decision.json
python skills/mobile/scripts/design_adapters.py compile-mobile .design/mobile/decision.json .design/mobile/decision.md
```

The output is a decision artifact. It does not install a mobile toolchain or change product code.
