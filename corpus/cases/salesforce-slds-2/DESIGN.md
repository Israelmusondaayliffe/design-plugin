# Salesforce Lightning Design System 2

## Visual thesis

SLDS 2 is useful as a model for evolving a very large enterprise product without losing the semantic stability users rely on. Styling hooks, density options, and repeated workflow patterns provide the control layer. A more expressive visual language can then be added selectively.

## Signature relationships

- **Global hooks before local overrides.** System changes should propagate through named roles.
- **Density is configurable.** Different users and contexts can need different working compactness.
- **Contrast establishes priority.** Color is intentional rather than evenly distributed.
- **Expression remains bounded.** Rounded or circular motifs can add identity without taking over operational components.
- **Enterprise repetition becomes a design asset.** Common data and action patterns should become more familiar over time.

## Layout and density

Support complex records, dashboards, related data, filters, and actions without using a single density everywhere. Compact modes should increase throughput. Comfortable modes should improve readability and touch interaction without changing the underlying hierarchy.

## Typography

Use highly legible product typography with clear roles for record titles, field labels, values, metadata, and actions. Large expressive typography should be limited to surfaces where it helps orientation or narrative.

## Color and surfaces

Build color through semantic hooks and tested themes. Brand expression can become more visible in navigation, highlights, or selected experiences, but status and action roles should remain stable.

## Components and interaction

Complex enterprise components need predictable states and data relationships. Styling hooks should control appearance without requiring each component to fork its own visual system.

## Adaptation rules

- Preserve global semantic hooks, density adaptability, repeated enterprise patterns, and intentional contrast.
- Adapt expressive motifs to the new brand rather than copying Salesforce circles or cloud motifs.
- Treat theme flexibility as infrastructure, not a cosmetic afterthought.

## Failure modes

- Adding a new visual theme by overriding individual components one at a time.
- Increasing whitespace without preserving information hierarchy.
- Using brand color for every selected, status, and action state.
- Copying Salesforce motifs into an unrelated product with no functional reason.

## Evidence boundary

This is original analysis of public Salesforce SLDS 2 guidance and official Salesforce material. No Salesforce screenshots, icons, or brand assets are bundled.
