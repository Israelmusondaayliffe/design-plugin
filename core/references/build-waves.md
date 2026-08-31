# Build-wave contract

Wave 8 controls implementation after the exact compiled plan has repository-change approval. It does not approve product scope or perform external actions.

## Artifact chain

Each wave lives under `.design/implementation/waves/<wave-id>/` and has:

1. `manifest.json`, created before changes.
2. Product changes restricted to `allowed_files`.
3. `handoff.json`, written after checks and renders.
4. `handoff.md`, compiled for human review.

The manifest binds the approved understanding, reference lock, root `DESIGN.md`, structured plan, compiled approved plan, current Git baseline, worker identity, and previous handoff. The state controller records the manifest hash before product work. Changed inputs or a changed manifest stop verification.

## Repository comparison

The baseline records the starting commit and pre-existing dirty files with their hashes. Scope verification reports product files changed after that point. Exact engine-owned manifest, handoff, readable handoff, and verification receipt paths are control artifacts rather than product scope. An unchanged pre-existing user edit is not claimed as wave work. A modified pre-existing edit is treated as wave work and must be inside the approved scope.

Repository history must keep the baseline commit as an ancestor. A rebase, reset, or branch replacement during a wave blocks verification because the comparison is no longer reliable.

## Completion

A complete handoff must match repository evidence exactly. Each changed product file records its current SHA-256, and dependent waves recheck those bytes before starting. Every planned test and completion criterion must pass. Every render target must pass or be explicitly not applicable with evidence. A distinct independent verifier and a distinct Unslop reviewer must pass the result. Neither may be the implementation worker. A failed or blocked item keeps the wave incomplete.

After verification, the state controller records the handoff hash. It advances to the next plan wave or moves from building to rendering after the final wave.

## Pause conditions

Stop the wave when:

- plan or approval hashes are stale
- a dependency handoff is missing or changed
- repository history diverges
- file scope is exceeded
- required design guidance is absent
- tests, renders, or criteria fail
- a new dependency or external action needs authority

Use the existing state controller to pause or block. Resume from the manifest, repository evidence, and latest verified handoff, not from conversation recall.
