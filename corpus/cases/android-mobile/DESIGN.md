# Android Mobile UI Guidance

## Visual thesis

A small viewport exposes the next useful action without removing context or recovery. Window size, posture, orientation, and device variation change arrangement before they change meaning.

## Signature relationships

| Relationship | Consequence |
| --- | --- |
| handheld task priority | A small viewport exposes the next useful action without removing context or recovery. |
| adaptive mobile structure | Window size, posture, orientation, and device variation change arrangement before they change meaning. |
| system-aware surfaces | Navigation, system bars, sheets, and edge treatment remain coherent with Android behavior. |
| input and state reachability | Touch targets, focus, gestures, keyboard paths, and visible state survive one-handed and assistive use. |

## Handheld task priority in practice

Compact mobile pane that reorders by window size and task. A small viewport exposes the next useful action without removing context or recovery.

Window size, posture, orientation, and device variation change arrangement before they change meaning.

Navigation, system bars, sheets, and edge treatment remain coherent with Android behavior. Touch targets, focus, gestures, keyboard paths, and visible state survive one-handed and assistive use.

Predictable state changes that remain interruptible.

## Adaptation rules

- Suitable contexts: Android phone applications that must adapt across handheld window sizes, and mobile workflows with recurring navigation, input, and system-state pressure.
- Preserve: handheld task priority and adaptive mobile structure.
- Poor fit: fixed kiosk layouts that do not participate in Android navigation or window behavior.

## Failure modes

- Assuming one phone size is the Android layout.
- Using gesture-only actions without visible alternatives.
- Letting edge-to-edge decoration obscure system state or controls.

## Evidence confidence and gaps

Only source identity is classified as directly observed. The design relationships are source-bounded analyst interpretations, and the adaptation rules are recommendations. Internal metrics, unpublished decisions, and closed-source implementation details were not inspected.

## Evidence boundary

This case is original analysis of owner-published material for Android Mobile UI Guidance. The corpus stores no owner screenshots, logos, fonts, illustrations, product copy, or proprietary binaries. Preview colors and composition are original study values. Observations establish the source; inferences and recommendations belong to the corpus author.
