# Visual adapter contract

Wave 7 adds local planning and routing artifacts for imagery, Figma, and mobile work. It does not perform external actions by itself.

## Authority chain

Imagery binds to the approved direction, reference lock, and root `DESIGN.md`. Figma handoff binds to root `DESIGN.md`, the canonical token source, and a host capability attestation when it claims an available or unavailable connection. The attestation must be marked ready and contain a current inspection time, named inspector, exact inspected surfaces, and direct evidence. Mobile routing binds to the approved understanding, UX definition, and root `DESIGN.md`.

A changed upstream artifact makes the related adapter stale. Rebuild it instead of carrying an old prompt, handoff, or platform decision forward.

## External effects

- Prompt writing needs no generation approval.
- Direction-board, production, and repair batches need an exact output ceiling and explicit approval. Before approval, compute `generation_boundary.request_sha256` from `imagery_generation_request_payload(document)`. The canonical payload covers the complete imagery plan or image edit except mutable approval-record fields, including asset IDs, prompts, output targets, purpose and ceiling, reference records, prompt/reference/source lineage, asset locks, upstream hashes, rights review, series scope, and repair scope. An approved note must exactly equal `imagery_generation_approval_text(document)`, whose `design-imagery-generation-approval-v2` payload records the exact canonical request hash. Any request change makes the boundary and note stale.
- Direct Figma actions need a compatible authorized connection and separate external-write approval. Record the exact target file, structured action objects, and destructive-action classification. Before approval, compute `external_write_boundary.request_sha256` from `figma_write_request_payload(handoff)`. The canonical payload covers the target file, complete ordered action batch, per-action destructive flags, aggregate destructive classification, upstream hashes, and the full handoff specification. An approved note must exactly equal `figma_write_approval_text(handoff)`, whose `design-figma-write-approval-v2` payload records that request hash. Any target, action, destructive classification, or specification change makes the boundary and note stale.
- Mobile routing never authorizes software installation.
- Deployment, publication, paid services, and account changes remain separate actions.

The standard-library runtime only reads structured artifacts and writes explicit local output paths supplied by the caller.

## Aggregate verification

```text
python scripts/design_adapters.py verify-wave7 \
  --lock .design/system/reference-lock.json \
  --decision .design/directions/decision.md \
  --direction-set .design/directions/direction-set.json \
  --design-md DESIGN.md \
  --tokens .design/system/tokens.source.json \
  --ux .design/system/ux-definition.json \
  --system .design/system/design-system.json \
  --token-output-dir .design/system/generated-tokens \
  --plan .design/implementation/plan.json \
  --plan-md .design/implementation/plan.md \
  --imagery .design/imagery/plan.json \
  --figma .design/handoff/figma.json \
  --mobile .design/mobile/decision.json
```

Pass approval paths only when an adapter claims approved external use. The aggregate first runs the complete Wave 6 validator, then checks Wave 7 bindings and approval contracts. It does not prove that an image or Figma action happened.

The compiled Figma output is a structurally validated handoff scaffold. Do not call it complete or rebuild-ready unless separate project-specific cross-artifact coverage proves every required screen, state, component, token, asset, interaction, responsive rule, and measurement is present.
