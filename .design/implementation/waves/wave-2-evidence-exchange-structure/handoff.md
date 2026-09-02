# wave-2-evidence-exchange-structure handoff

Status: complete
Wave number: 2

## Changed files

- `site/README.md`: changed; SHA-256 `0b81e1552696a0130fba10d4ca693b3f9f34f413ecaa633e48da17d6ef008242`. Documents the Evidence Exchange information model, local build command, public package decision order, query-state contract, privacy boundary, and separate publication gate.
- `site/app.js`: changed; SHA-256 `d748a16025131a06e7508b0e500f99af8c0eae2bf7e85d9505222c39bd8234b8`. Implements the 60-case public catalog, six lanes, six facets, sorting, reload-safe URL state, progressive validated case and package loading, evidence presentation, safe download routes, and comparison of two to five public cases.
- `site/index.html`: changed; SHA-256 `d45620f3d395a53754ba62032cafa95e89e79fe7a18339670a012416a5302e78`. Defines the catalog, case, package, comparison, and method screens with semantic landmarks and places package context, contents, evidence boundary, provenance, limitations, unknowns, and file details before download actions.
- `site/styles.css`: changed; SHA-256 `06baf90f66bf8f4db123661b50527fcad971d84b98d2e8c90802c0684c5ea668`. Applies the approved original warm-neutral identity to Carbon-derived grid, density, semantic-role, contextual-layer, and relationship patterns across four-, six-, and twelve-column responsive layouts.
- `tests/test_wave11_site.py`: changed; SHA-256 `3726fb723045082bbdd27a9e172438eed29aa29af4c339d373d9c6b0138c2176`. Adds 13 focused Site contract tests for the five screens, ordered package contract, catalog controls, query state, comparison bounds, semantic structure, responsive roles, original tokens, local-only documentation, and absence of remote visual dependencies.

## Completed checks

- Extend tests/test_wave11_site.py to verify the five screen regions, ordered package contract, preserved catalog controls, comparison limit, public count, local-only boundary, and absence of remote visual dependencies.: pass. All 13 Site tests and all 21 public-package tests passed. The relevant Wave 4 compatibility tests passed 2 of 2, and the full isolated suite passed 277 of 277 tests on Python 3.9.6 and Python 3.12.13.
- Use DOM and computed-style inspection to verify semantic landmarks, ordered headings, original token roles, bounded reading measure, and no repeated-card layout substitution.: pass. The live Site exposed all five task regions and semantic landmarks, preserved ordered headings and a 68-character reading measure, used original semantic tokens and list rows, and produced no page-level horizontal overflow at any tested viewport.
- Render every named target and compare it with the approved Evidence Exchange direction and reference lock, not with source-brand pixels.: pass. All 14 named wide, tablet, and mobile targets were freshly rendered. They retained the approved grid, productive and expressive density, semantic roles, contextual layers, and relationship hierarchy while excluding IBM Plex, IBM blue, source geometry, source assets, remote fonts, and a copied Carbon shell.

## Render targets

- catalog-default-wide: pass. At 1440 by 1000, the original Evidence Exchange hero, public count, six lanes, six facets, sorting, and list-row catalog rendered with 60 of 60 public cases and no page overflow.
- catalog-default-mobile: pass. At 390 by 844, the four-column composition retained the complete hero and contract, used bounded horizontal lane scrolling, kept all facets available, and matched the viewport width.
- catalog-default-tablet: pass. At 1024 by 900, the six-column catalog retained 60 public cases, seven lane buttons including All, all six facets, readable hierarchy, and no page overflow.
- case-default-wide: pass. IBM Carbon opened in the wide case screen with case context, analysis, claim-level evidence, limitations, unknowns, a generated recognition cue, and no dialog overflow.
- case-default-tablet: pass. At 1024 by 900, IBM Carbon retained its full title, source line, preview, comparison action, three local navigation items, and three case regions without horizontal overflow.
- package-default-wide: pass. The wide package screen validated IBM Carbon, kept the back action compact, and placed seven ordered contract regions before two enabled safe download routes.
- package-default-mobile: pass. At 390 by 844, the package screen preserved the full decision order, 44-pixel back and close targets, one-column evidence boundaries, bounded file-table scrolling, and no page or dialog overflow.
- package-default-tablet: pass. At 1024 by 900, the package title, validation status, seven ordered regions, and two enabled formats remained readable and horizontally contained.
- comparison-default-wide: pass. The wide comparison rendered two public cases across ten distinct attributes with row and column headers, two case-open actions, and no page overflow.
- comparison-default-mobile: pass. At 390 by 844, the comparison remained inside one labeled 356-pixel region whose 760-pixel table scrolled internally while the document stayed within the viewport.
- comparison-default-tablet: pass. At 1024 by 900, the two-case, ten-row comparison fit its dialog without page or table-region overflow.
- method-default-wide: pass. The wide method screen presented truth classes, originality, package use, and privacy as four relationship-based sections with no sticky comparison obstruction.
- method-default-mobile: pass. At 390 by 844, the method became one column without removing any section, retained 44-pixel site-link targets, and produced no page overflow.
- method-default-tablet: pass. At 1024 by 900, the method used a two-column composition and preserved all four sections, all four truth definitions, and the explanatory copy.

## Completion criteria

- All five screens exist in one coherent local static Site and preserve the approved decision order.: pass. Catalog, case, package, comparison, and method regions exist in one static Site. Live DOM inspection and all 14 renders confirmed their coherent hierarchy and the ordered package path.
- The catalog still exposes all 60 public cases, six lanes, six advanced facets, sorting, progressive detail, evidence, and two-to-five comparison.: pass. Runtime verification found 60 public rows, lane counts of 5, 15, 15, 10, 8, and 7, six facet controls, working search, filtering, sorting, URL restoration, progressive case loading, and comparison disabled at one, enabled at two, and capped at five.
- The package contract is visible before any enabled download action at wide and mobile targets.: pass. The seven ordered contract regions precede the final action region in DOM and visual order. Download links remained disabled until the public case model and manifest validated, then exposed two safe relative routes with stable filenames.
- Fresh renders show Carbon-derived relationships with original project identity and no copied reference shell.: pass. Fresh wide, tablet, and mobile renders used the approved original warm-neutral palette, human serif, interface sans, technical mono, rust action color, teal focus color, low-radius geometry, and generated abstract previews. No IBM Plex, IBM blue, remote visual asset, source screenshot, CDN dependency, or copied Carbon shell was present.

## Review results

- independent-verifier by wave11_gate_verifier: pass. Verified all 12 frozen hashes, exact manifest scope, focused and full tests, all 14 named targets, the five-screen hierarchy, the package decision order, catalog preservation, responsive containment, and original identity with no plan-fidelity blocker.
- specialist by codex_install_verifier: pass. Independently passed syntax, scope, 34 focused tests, two compatibility tests, and 277-test full suites on both Python versions; verified progressive network loading, safe packages, two-to-five comparison, responsive containment, and zero console or external-resource errors.
- unslop-reviewer by claude_install_verifier: pass. Confirmed supported public claims, useful context, evidence and privacy boundaries, zero true em dashes, no clichés or filler, no copied Carbon identity, coherent wide and mobile renders, and unchanged frozen hashes.

## Known deviations

- None.

## New risks

- None.

## Next inputs

- Prepare the approved Wave 3 manifest for download behavior and recovery from this verified Wave 2 handoff before changing any Wave 3 file.

## Rollback notes

- Revert only the five Wave 2 product changes through a scoped patch while keeping the validated Wave 1 public package generator and generated public routes.
- Rebuild the unchanged public catalog data and rerun the prior Site and package tests after the scoped rollback.

Ended at: 2026-09-02T01:35:21Z
