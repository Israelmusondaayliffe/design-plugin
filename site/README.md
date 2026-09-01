# Design Reference Library Site

This dependency-free static interface presents the reviewed public corpus. It supports full-text search, six coverage-lane filters, deeper facet filters, case study dialogs, evidence inspection, and comparison of up to five cases.

The interface renders original abstract previews from each case's `preview-spec.json`. It does not load or store source screenshots, logos, fonts, or other owner assets.

## Build the public data

From the repository root:

```bash
python3 corpus/scripts/build_catalog.py --visibility public
```

The generator validates the canonical records, then writes progressive routes beneath `site/generated-data/`. The Site initially loads only `catalog/index.json`. It fetches full analysis and evidence when a reader opens a case.

## Run locally

```bash
python3 -m http.server 4173 --directory site
```

Open `http://127.0.0.1:4173/`.

## Publication boundary

The Site is local-only during Wave 11. No Site deployment, hosting configuration, or public URL is authorized by this work. Publishing the Site remains a separate approval gate.

The public GitHub repository may contain this source and its build instructions. Generated catalog data is rebuilt from the canonical corpus and remains outside the distributed plugin package.
