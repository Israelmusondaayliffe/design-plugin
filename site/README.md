# Design Reference Library Site

This dependency-free static Site presents 60 reviewed public design cases as an Evidence Exchange. A visitor can search, filter, compare, inspect claim-level evidence, and review a complete package contract before downloading either a readable Markdown brief or structured JSON.

The five task regions are:

1. Catalog: search, six lanes, six advanced facets, sorting, and public-case results.
2. Case: context, intent, value, quality, analysis, evidence, limitations, and unknowns.
3. Download package: contents, evidence boundary, provenance, limitations, unknowns, file details, then download actions.
4. Comparison: two to five public cases kept distinct in one bounded table.
5. Method: truth classes, originality limits, privacy exclusions, and responsible package use.

Abstract previews are generated from approved public case fields. They are optional recognition cues, not evidence or provenance. The Site does not load or store source screenshots, logos, fonts, or other owner assets.

## Build the public data

From the repository root:

```bash
python3 corpus/scripts/build_catalog.py --visibility public
```

The generator validates the canonical records and writes progressive public routes beneath `site/generated-data/`. The Site initially loads only `catalog/index.json`. It fetches a case's validated `downloads/case.json` and `downloads/manifest.json` when the reader opens that case.

Before enabling either download, the browser fetches both named files and checks each filename, media type, byte count, model binding, and SHA-256 value against the manifest. The enabled links use blobs made from those already-verified bytes. If validation fails, both links remain disabled and the package keeps its case context, exact problem, retry action, and return action.

## Run locally

```bash
python3 -m http.server 4173 --directory site
```

Open `http://127.0.0.1:4173/`.

## Inspect recovery states

Six deterministic query states support local browser review:

- `test-state=case-loading`
- `test-state=case-error`
- `test-state=package-error`
- `test-state=package-denied`
- `test-state=download-error`
- `test-state=download-failure`

Package and download failures accept `test-format=readable` or `test-format=structured`. These hooks run only on `127.0.0.1`, `localhost`, or `::1`, use public cases, and expose no private fixtures. For example:

```text
http://127.0.0.1:4173/?case=ibm-carbon&view=package&test-state=package-error&test-format=readable
```

The exact approved render routes remain supported for plan-level verification:

- `/?case=ibm-carbon#download-package` opens the validated package screen.
- `/?case=ibm-carbon&test-state=download-error#download-package` opens the package validation error for the selected format.
- `/?case=private-test-case#download-package` opens a permission-denied package shell only on a loopback host. It loads no private fixture, source record, or downloadable file.

## Verify the Site contract

```bash
python3 -m unittest tests.test_wave11_site tests.test_wave11_evidence_exchange
```

Fresh browser review is still required for the named wide, tablet, and mobile render targets. Automated checks support that judgment but do not replace it.

## Publication boundary

The Site is a static public-release candidate. Wave 5 acceptance runs locally and does not itself prove deployment. Public publication is authorized only after Wave 5 completes; the public URL must be added after an anonymous production check passes. The Site requires no analytics or account system.

The public GitHub repository contains the Site source and its build instructions. Generated public data is rebuilt from the canonical corpus and remains outside the distributed plugin package.
