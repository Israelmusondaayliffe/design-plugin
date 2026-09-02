# Direction 2: Analyst Workbench

## Decision layer

### Thesis

Make search, comparison, evidence inspection, and download one compact working environment for repeated use.

### Why it fits

This direction gives priority to people who return often. The current query, result count, selected cases, evidence state, and available actions stay visible, so the user can move from discovery to comparison to download without losing context.

It is the strongest option when repeated research speed matters more than a long-form opening experience.

### Signature traits

- A persistent query and result workspace.
- Comparison visible beside or directly after results.
- Complete compact control behavior.
- Explicit operational and download states.

### Primary foundation

IBM Carbon owns the workspace grid, productive typography, semantic tokens, surface layers, and component relationships.

### Adaptation axis

Operator-led comparison and retrieval.

### Supporting references

- Elastic EUI contributes behavioral completeness for dense controls only.
- GitHub Primer contributes responsive region parity only.

### Clear risk

The dense workspace can demand too much from a first-time visitor, especially on mobile.

## Expert layer

### Composition and hierarchy

A persistent control rail, result region, and comparison or detail region share one aligned workspace. Current work state outranks introductory prose. Compared cases remain concurrently visible when space allows and become a complete sequential layout when it does not.

Case details and downloads still expose context, intent, value, evidence quality, and limitations. The workspace changes their priority and placement, not their availability.

### Typography and density

Compact productive type dominates controls, rows, counts, provenance, and values. Expressive type appears only at route level. Desktop density supports scanning; mobile density relaxes without removing functions.

### Color and surfaces

Original semantic tokens distinguish action, focus, selection, warning, error, and data quality. Contextual layers and borders define working regions. Color never carries status alone.

### Interaction and motion

Keyboard-ready filters, sort, selection, comparison, evidence inspection, and downloads stay close to the records they affect. Motion explains filtering, sorting, selection, panel changes, and download state rather than decorating the page.

### Feasibility

This fits the current static application and data model. The main work is coordinated state, keyboard behavior, responsive region reflow, and complete download feedback in the existing JavaScript.

### Forbidden drift

- No tabs that hide cases users need to compare.
- No dense rows without keyboard, mobile, empty, loading, and failure behavior.
- No state expressed by color alone.
- No copied Carbon or EUI components, shells, geometry, or palettes.

## Evidence layer

The Carbon basis is supported by `CARBON-E01`, `CARBON-E02`, `CARBON-E03`, `CARBON-E04`, `CARBON-E05`, and `CARBON-E07`. EUI's narrow density role is supported by `EUI-E03`, `EUI-E04`, and `EUI-E05`. Primer's mobile role is supported by `PRIMER-E02` and `PRIMER-E04`.

The research does not prove target keyboard behavior, mobile reflow, or download states. Those are proposed design requirements that must be implemented, rendered, and tested after direction approval.
