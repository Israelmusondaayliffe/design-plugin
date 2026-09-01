# Design Knowledge Corpus

This directory is the canonical source for the independent Design Knowledge Corpus.

The corpus contains original design analyses. It does not mirror Refero or any other proprietary catalog. Each case is based on public, open-source, user-owned, client-authorized, or otherwise permitted source material and is written in original language.

## Canonical case record

Each case under `cases/<slug>/` contains:

- `DESIGN.md`: original design analysis and adaptation guidance.
- `metadata.json`: identity, taxonomy, provenance, rights basis, and publication status.
- `evidence.json`: evidence records labeled observed, inferred, or recommended, each with confidence and a locator.
- `tokens.json`: normalized design roles and any source-supported values.
- `source-notes.md`: what was inspected, what was not, and source limitations.
- `review.json`: editorial and publication review state.
- `preview-spec.json`: original abstract preview instructions. The reference Site renders this spec rather than redistributing source screenshots by default.
- `coverage.json`: machine-checkable alpha coverage for every design field required by the approved plan, including lane fit, explicit confidence, and unknowns.
- `source.json`: the exact public owner source, retrieval date, canonical document-outline hash, source scope, permitted-use basis, and limitations. Raw source bytes are not stored.

Generated catalog files are disposable and must be rebuilt from the canonical records.

## Qualification commands

```bash
python3 corpus/scripts/validate_corpus.py --allow-pending-review
python3 corpus/scripts/audit_sources.py
python3 corpus/scripts/audit_originality.py
python3 corpus/scripts/validate_corpus.py
python3 corpus/scripts/build_catalog.py
```

The pending-review mode checks a candidate's structure without claiming editorial acceptance. The normal validator accepts only independently reviewed records with matching artifact hashes.

## Evidence quality

- `high`: several source-specific observations have precise public locators, followed by separately labeled analysis.
- `medium`: the owner source and scope are directly observed, while the portable design relationships are explicitly marked as analyst inference or recommendation.
- `low`: source access or specificity is insufficient for alpha acceptance.

A successful URL and canonical outline hash prove source retrieval, not every design claim. Claim classes, locators, lane-fit rationale, reviewer judgment, and artifact hashes carry the rest of the acceptance burden.

## Publication boundary

Cases in `review` remain local and uncommitted. After independent evidence, rights, asset, and writing review, accepted original cases may be promoted to `public` and committed to the public repository. Site deployment is a separate action and is not implied by corpus promotion.

## Milestones

- Engineering seed: 12 cases.
- Alpha: 60 reviewed cases.
- Team beta: 150 reviewed cases.
- Public v1.0: 300 reviewed cases.
