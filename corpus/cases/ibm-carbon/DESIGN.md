# IBM Carbon Design System

## Visual thesis

Carbon's transferable strength is precision under complexity. It can hold dense enterprise information because typography, spacing, component anatomy, state color, and data presentation are systematized. It also explicitly separates productive application moments from more expressive editorial moments.

## Signature relationships

- **Productive versus expressive.** Dense product UI and brand/editorial surfaces are related but not forced into one type scale.
- **Typography is infrastructure.** IBM Plex Sans, Serif, and Mono have distinct jobs rather than acting as arbitrary pairings.
- **Contextual tokens.** A component token can change with its layer while preserving semantic meaning.
- **Specification-level anatomy.** Components document dimensions, spacing, state, and typography rather than only showing appearance.
- **Accent discipline.** Primary blue supports actions and links, not decorative paragraphs.

## Layout and density

Carbon is comfortable with high information density. Use compact spacing where repeated actions and scanning dominate, but restore expressive scale for major narrative or brand moments. Dense does not mean cramped. Alignment and tokenized spacing must remain visible.

## Typography

Use productive styles for tables, controls, labels, structured lists, filters, and working surfaces. Use expressive scale selectively for page-level storytelling. Mono belongs to code or technical values, not as general decoration.

## Color and surfaces

Neutral text and layered surfaces should carry most of the interface. Semantic and interactive colors remain tied to states and actions. Contextual layer tokens are especially useful when the same component appears on different surface depths.

## Components and interaction

Treat each component as a state machine with exact anatomy. Hover, focus, selected, disabled, read-only, error, and loading states need explicit token relationships. Do not reduce Carbon to square gray boxes and blue buttons.

## Adaptation rules

- Preserve productive/expressive separation, token rigor, component-state specificity, and restrained action color.
- Change brand colors and typeface only when the replacement can support the same dense hierarchy.
- Keep data and technical content readable before adding expressive treatments.

## Failure modes

- Using expressive display scale throughout a dense product.
- Applying blue as decoration because Carbon is associated with IBM blue.
- Copying component geometry while ignoring contextual layer tokens and state behavior.
- Treating enterprise density as permission for weak spacing or tiny illegible text.

## Evidence boundary

This case is original analysis of public Carbon documentation. Exact values are included only when directly documented in the cited sources.
