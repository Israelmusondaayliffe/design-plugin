# Corpus Retrieval and Offline Fallback

The full Design Knowledge Corpus is external to the plugin package. Use progressive disclosure so research depth grows only when evidence warrants it.

## Retrieval levels

1. **Bundled manifest.** Read `catalog-manifest/catalog.json` for milestones, taxonomy hints, seed identifiers, and remote route contracts.
2. **Category index.** Retrieve only the relevant platform, product type, industry, archetype, density, or flow category.
3. **Ranked summaries.** Inspect compact summaries for candidate cases. Do not load every full case.
4. **Finalist cases.** Retrieve full `DESIGN.md` and metadata only for strong candidates.
5. **Validation evidence.** Retrieve `evidence.json` and `tokens.json` only when a major decision needs proof or exact role verification.

## Remote route contract

The generated corpus publishes machine-readable paths shaped like:

- `/catalog/index.json`
- `/catalog/categories/<facet>/<value>.json`
- `/cases/<slug>/summary.json`
- `/cases/<slug>/DESIGN.md`
- `/cases/<slug>/metadata.json`
- `/cases/<slug>/evidence.json`
- `/cases/<slug>/tokens.json`

The human reference Site is a presentation layer over the same canonical Markdown and JSON records. The repository remains the source of truth.

## Offline or unavailable remote source

If neither the reference Site nor repository case files can be reached:

1. Continue with bundled craft guidance and the compact manifest.
2. Use user-provided references and current project evidence.
3. Use live public research when a browser or web research capability exists.
4. State that remote corpus cases were unavailable.
5. Lower confidence instead of pretending that unavailable cases were reviewed.
6. Do not stop a well-specified project solely because the remote corpus is unavailable.

The local manifest is a routing aid, not a replacement for the full corpus.
