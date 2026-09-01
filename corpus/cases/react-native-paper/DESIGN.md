# React Native Paper

## Visual thesis

React Native components carry Material roles into mobile implementation. Color, typography, shape, and elevation can adapt while semantic jobs remain stable.

## Signature relationships

| Relationship | Consequence |
| --- | --- |
| Material-native grammar | React Native components carry Material roles into mobile implementation. |
| theme continuity | Color, typography, shape, and elevation can adapt while semantic jobs remain stable. |
| stateful touch controls | Press, focus, disabled, loading, and selection behavior are explicit. |
| cross-platform pragmatism | Shared code supports both platforms while leaving room for platform-specific decisions. |

## Material-native grammar in practice

Material mobile stack with adaptive component grouping. React Native components carry Material roles into mobile implementation.

Color, typography, shape, and elevation can adapt while semantic jobs remain stable.

Press, focus, disabled, loading, and selection behavior are explicit. Shared code supports both platforms while leaving room for platform-specific decisions.

Touch feedback and state continuity.

## Adaptation rules

Suitable contexts: React Native products using a Material foundation, and mobile teams needing themeable accessible components.

Preserve: Material-native grammar and theme continuity.

Poor fit: strongly iOS-native products that should not inherit Material interaction character.

## Failure modes

**Stop 1.** Applying theme colors outside their semantic roles.

**Stop 2.** Treating Android and iOS behavior as automatically identical.

**Stop 3.** Ignoring loading and disabled states in touch controls.

## Evidence confidence and gaps

Only source identity is classified as directly observed. The design relationships are source-bounded analyst interpretations, and the adaptation rules are recommendations. Internal metrics, unpublished decisions, and closed-source implementation details were not inspected.

## Evidence boundary

This case is original analysis of owner-published material for React Native Paper. The corpus stores no owner screenshots, logos, fonts, illustrations, product copy, or proprietary binaries. Preview colors and composition are original study values. Observations establish the source; inferences and recommendations belong to the corpus author.
