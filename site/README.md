# Design Reference Site Foundation

Wave 4 provides a dependency-free static reference interface over generated corpus JSON.

The Site is not deployed in Wave 4. Deployment and public publishing remain separately gated.

`build_catalog.py` generates `site/generated-data/` from canonical case records. The browser application reads only those generated files and supports search, filtering, case inspection, and comparison.

If ChatGPT Sites later proves unsuitable for stable machine-readable routes, the same generated records can be hosted from the public GitHub repository or another approved static host without changing the corpus schema.
