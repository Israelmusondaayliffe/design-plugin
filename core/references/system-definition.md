# System definition contract

Wave 6 converts an approved direction into complete, bound design artifacts. It does not change product implementation files. When `.design/state.json` is available, the validators check understanding, decision, and direction-set hashes against current gate evidence instead of accepting free-standing digests.

## Artifact layout

```text
.design/
├── directions/
│   ├── decision.md
│   └── direction-set.json
├── implementation/
│   ├── plan.json
│   └── plan.md
└── system/
    ├── reference-lock.json
    ├── ux-definition.json
    ├── design-system.json
    ├── tokens.source.json
    └── generated-tokens/
        ├── tokens.json
        ├── variables.css
        ├── tailwind.css
        ├── figma.json
        ├── mobile.json
        └── projection-report.json
DESIGN.md
```

## Binding chain

Each stage binds to exact SHA-256 digests:

```text
approved understanding
  -> approved direction and direction set
  -> reference lock
  -> UX definition
  -> structured design system
  -> root DESIGN.md
  -> implementation plan
```

The token source binds directly to the approved direction. A changed upstream artifact makes downstream material stale. Recompile and reapprove it through the normal workflow.

## Reference ownership

One reference owns the dominant visual foundation. Up to three supporting references may each solve one narrow responsibility. The lock must preserve the approved direction's source roles. It cannot introduce a broad supporting role or synthesize a safe midpoint.

## Token source

The canonical token source uses the stable DTCG 2025.10 schema:

```text
https://www.designtokens.org/schemas/2025.10/format.json
```

The compiler supports aliases, detects cycles and unknown references, and rejects type-changing aliases. It projects supported primitive types to CSS and records unsupported composite projections instead of silently dropping them. Figma and mobile outputs are specifications, not external writes.

## Aggregate verification

Run after all system-definition artifacts have been compiled:

```text
python scripts/design_system.py verify-wave6 \
  --lock .design/system/reference-lock.json \
  --decision .design/directions/decision.md \
  --direction-set .design/directions/direction-set.json \
  --ux .design/system/ux-definition.json \
  --system .design/system/design-system.json \
  --design-md DESIGN.md \
  --tokens .design/system/tokens.source.json \
  --token-output-dir .design/system/generated-tokens \
  --plan .design/implementation/plan.json \
  --plan-md .design/implementation/plan.md
```

The pass result proves artifact structure, hashes, deterministic `DESIGN.md`, token compilation, and the closed implementation gate. It does not prove rendered quality or authorize implementation.

## Repository-change gate

New plans must contain `repository_change_gate: awaiting_approval`. Plan validation rejects any other value. Record user approval against the exact compiled `plan.md` hash through the state controller before product implementation begins.
