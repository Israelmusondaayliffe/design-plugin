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
- `source.json`: the exact public owner source, retrieval date, bounded source-identity hash, source scope, permitted-use basis, and limitations. Raw source bytes are not stored.

Generated catalog files are disposable and must be rebuilt from the canonical records.

## Public case packages

Every reviewed case with `publication_status: public` produces one portable package at:

```text
cases/<slug>/downloads/
├── case.md
├── case.json
└── manifest.json
```

`case.md` is the human-readable record. `case.json` is the closed, machine-readable record. Both are rendered from the same normalized public model and preserve the same context, corpus analysis, recommendations, evidence records, provenance, limitations, and unknowns. The manifest binds both files to one model digest and records each stable download filename, media type, byte size, and SHA-256.

The package builder uses explicit fields from `metadata.json`, `evidence.json`, `coverage.json`, and `source.json`. It does not parse or copy canonical `DESIGN.md`, `source-notes.md`, or `review.json`. Reviewer identities, internal paths, archive details, response hashes, redirect history, operational notes, and private case data are not public package fields. Internal evidence locators are omitted; public URL locators are retained. Source limitations keep their meaning, but operational response-hash wording is replaced with a public statement about the recorded retrieval date and claim-level evidence.

Truth labels have specific meanings:

- `observed`: directly supported by a cited public source.
- `inferred`: corpus analysis, not the source owner's stated intent.
- `recommended`: adaptation guidance, not a source claim or outcome guarantee.
- `unknown`: not established by the inspected public material.

`studied_at`, `retrieved_at`, and `captured_at` remain separate because they record different events. Accessibility maturity is guidance from the corpus record, not a test result. Public is the canonical case's publication status. It is not certification of the derived package, adaptation quality, accessibility, or fitness for a particular use. The derived package must pass its own generation checks and independent review before release.

## Qualification commands

```bash
python3 corpus/scripts/validate_corpus.py --allow-pending-review
python3 corpus/scripts/audit_sources.py
python3 corpus/scripts/audit_originality.py
python3 corpus/scripts/validate_corpus.py
python3 corpus/scripts/build_catalog.py --visibility public
python3 -m unittest tests.test_wave11_evidence_exchange
```

The pending-review mode checks a candidate's structure without claiming editorial acceptance. The normal validator accepts only independently reviewed records with matching artifact hashes.

The public catalog command rebuilds both `corpus/generated/` and `site/generated-data/`. A repeated build from unchanged canonical inputs must produce byte-identical package files. Local and pending-review catalog builds may include review-state cases in their existing local routes, but public download packages are generated only for cases whose canonical status is `public`.

## Evidence quality

- `high`: several source-specific observations have precise public locators, followed by separately labeled analysis.
- `medium`: the owner source and scope are directly observed, while the portable design relationships are explicitly marked as analyst inference or recommendation.
- `low`: source access or specificity is insufficient for alpha acceptance.

A successful URL and bounded source-identity hash prove source retrieval, not every design claim. Claim classes, locators, lane-fit rationale, reviewer judgment, and artifact hashes carry the rest of the acceptance burden.

## Publication boundary

Cases in `review` remain local and uncommitted. After independent evidence, rights, asset, and writing review, accepted original cases may be promoted to `public` and committed to the public repository. Site deployment is a separate action and is not implied by corpus promotion.

## Milestones

- Engineering seed: 12 cases.
- Alpha: 60 reviewed cases.
- Team beta: 150 reviewed cases.
- Public v1.0: 300 reviewed cases.
