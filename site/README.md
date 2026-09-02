# Design Reference Library Site

This dependency-free static Site teaches design through 60 reviewed public cases. It is written for curious makers, founders, developers, product owners, designers, and tools. A reader can begin with an everyday problem, inspect an original visual study, see what relationship is worth noticing, check the evidence, and download the same case as readable Markdown or structured JSON.

The Site uses a plain definition: design arranges attention, choices, and consequences. It shapes what people notice, understand, feel, and do. Beauty matters because people must want to approach and return to what we make. The opening uses familiar forms, rooms, services, tools, and screens before introducing design-system language.

The five task regions are:

1. Catalog: four problem-led starting paths, search, six lanes, six optional facets, sorting, and a bounded visual atlas. The first 12 matches render as one connected list of case studies by default; every one of the 60 cases remains searchable, filterable, and available through progressive loading.
2. Case: the problem, what to notice, where the relationship helps, where it can fail, the full technical analysis, evidence, limitations, and unknowns.
3. Download package: the human-versus-tool file choice first, followed by contents, evidence boundary, provenance, limitations, unknowns, and exact verification details.
4. Comparison: two to five public cases kept distinct in one bounded table.
5. Method: truth classes, originality limits, privacy exclusions, and responsible package use.

Each case receives an original explanatory UI or composition study. The deterministic renderer uses only approved public fields, including lane, platform, archetype, use stage, density, pattern, layout, motion, and documented relationships. Six visual families share one graphite, white, cobalt, lime, hot-pink, and tomato evidence frame while changing their composition for systems, dashboards, editorial work, mobile, commerce, and flows. These visuals explain the library's reading. They are not the source product, evidence, or a copy of the source identity. The Site does not load or store source screenshots, logos, fonts, branded colors, or other owner assets.

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

## Publication status

The accepted Wave 5 Site is published at `https://israelmusondaayliffe.github.io/design-plugin/`. A local repair is not production proof. Any later repair must pass the full local and browser checks, deploy through the repository's GitHub Pages workflow, and receive a fresh anonymous production check before it is described as live. The Site requires no analytics or account system.

The public GitHub repository contains the Site source and its build instructions. Generated public data is rebuilt from the canonical corpus and remains outside the distributed plugin package.
