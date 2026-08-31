# Design Knowledge Corpus

This directory is the canonical source for the independent Design Knowledge Corpus.

The corpus contains original design analyses. It does not mirror Refero or any other proprietary catalog. Each case is based on public, open-source, user-owned, client-authorized, or otherwise permitted source material and is written in original language.

## Canonical case record

Each case under `cases/<slug>/` contains:

- `DESIGN.md`: original design analysis and adaptation guidance.
- `metadata.json`: identity, taxonomy, provenance, rights basis, and publication status.
- `evidence.json`: claim-level evidence with truth classification.
- `tokens.json`: normalized design roles and any source-supported values.
- `source-notes.md`: what was inspected, what was not, and source limitations.
- `review.json`: editorial and publication review state.
- `preview-spec.json`: original abstract preview instructions. The reference Site renders this spec rather than redistributing source screenshots by default.

Generated catalog files are disposable and must be rebuilt from the canonical records.

## Milestones

- Engineering seed: 12 cases.
- Alpha: 60 reviewed cases.
- Team beta: 150 reviewed cases.
- Public v1.0: 300 reviewed cases.
