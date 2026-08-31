# Material 3

## Visual thesis

Material 3 is a themable component language, not a purple palette. Its useful structure is the relationship between semantic color roles, a named typography hierarchy, shape, elevation, and component behavior. Expression can change substantially while the system remains coherent.

## Signature relationships

- **Tonal roles instead of isolated swatches.** Accent families provide compatible roles for containers, foregrounds, emphasis, and states.
- **Named type jobs.** Display, headline, title, body, and label tiers separate content purpose from arbitrary font-size choices.
- **Shape as system personality.** Component geometry is repeated deliberately instead of using unrelated radii.
- **Theme inheritance.** Components should consume semantic theme values rather than local styling exceptions.
- **Adaptability.** Personalization and platform adaptation are expected rather than treated as drift.

## Layout and density

Material can support both roomy consumer surfaces and denser application patterns. The mistake is to apply large expressive containers to every task. Match component scale to frequency and information density.

## Typography

Use the named hierarchy to keep display expression separate from operational labels and body text. A large display style should be rare inside dense product workflows.

## Color and surfaces

Start from semantic relationships, not the baseline sample hues. If a product brand is orange, green, monochrome, or another direction, rebuild the tonal roles around that identity while preserving readable on-colors and surface hierarchy.

## Components and interaction

Components should inherit theme color, typography, and shape. Interaction states need to remain systematic across buttons, navigation, selection controls, dialogs, and surfaces.

## Adaptation rules

- Preserve semantic role structure, named type jobs, consistent shape logic, and component inheritance.
- Change palette, font family, and expressive geometry when brand evidence supports it.
- For a dense desktop tool, use the system's structural rigor without forcing oversized consumer-style surfaces.

## Failure modes

- Copying baseline purple and large rounded cards as the definition of Material.
- Using different radii and colors per component because theming was bypassed.
- Mixing expressive display typography into operational UI labels.
- Applying elevation and container color decoratively instead of to hierarchy or state.

## Evidence boundary

This is original analysis from public Material 3 and Android documentation. Exact type values included here are limited to values explicitly documented in the cited source.
