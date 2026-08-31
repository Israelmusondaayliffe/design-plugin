# Apple Human Interface Guidelines

## Visual thesis

The useful lesson is not to make every interface look like an Apple settings screen. The system is strongest when an experience feels native to its platform because visual choices, control behavior, hierarchy, accessibility, and system adaptation all agree. Purpose and agency come before decorative signature.

## Signature relationships

- **Semantic role over sampled color.** Dynamic colors represent jobs such as backgrounds, labels, links, and separators. Their meaning survives appearance changes.
- **Platform fit over cross-platform sameness.** A family resemblance can remain while individual platforms use their own conventions.
- **Legibility over delicacy.** Contrast, type weight, size, and appearance settings are not polish added later. They are part of the system.
- **Hierarchy through behavior and grouping.** Separation, navigation, controls, and content priority should explain where the user is and what is possible.
- **Agency over coercion.** Strong design makes important actions understandable without turning every screen into a funnel.

## Layout and density

Use density appropriate to the platform and task. Preserve comfortable touch interaction on mobile, readable content widths, and native navigation expectations. Do not force desktop information density into a touch surface merely to maintain visual sameness.

## Typography

Use a clear hierarchy and allow platform typography to participate in accessibility features. Avoid fragile treatments that collapse when type size grows or when stronger contrast is requested.

## Color and surfaces

Translate colors by semantic purpose. If adapting the system outside Apple platforms, define roles such as primary label, secondary label, canvas, grouped surface, separator, action, destructive, and focus. Do not import literal system-color values and pretend the resulting product is native.

## Components and interaction

Prefer controls that behave exactly as users expect on the target platform. When a custom control is necessary, its states, focus behavior, disabled behavior, and accessibility semantics need the same rigor as its shape.

## Adaptation rules

- Preserve semantic role mapping, platform awareness, accessibility adaptation, and user agency.
- Adapt brand expression through content, imagery, and carefully chosen custom color rather than by breaking core interaction expectations.
- On web, borrow the discipline of semantic tokens and hierarchy rather than simulating iOS chrome.

## Failure modes

- Hard-coding a captured system color and calling it an Apple-like palette.
- Copying rounded native controls into a web product without native behavior.
- Treating minimalism as the system's defining trait while ignoring platform conventions and accessibility.
- Using translucency, blur, or sparse chrome as decoration without a hierarchy reason.

## Evidence boundary

This case is an original analysis of public Apple design guidance. It does not reproduce Apple assets, screenshots, or proprietary interface files. Exact values are intentionally omitted where the source advises using semantic APIs rather than fixed values.
