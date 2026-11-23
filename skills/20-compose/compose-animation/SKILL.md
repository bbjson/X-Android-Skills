---
name: compose-animation
description: >-
  Animate Compose UI with the right primitive — animate*AsState, AnimatedVisibility, AnimatedContent,
  Animatable — with motion that respects duration scale, does not leak into tests, and is never the
  only signal of a state change. Use when adding a transition, showing/hiding content, animating a
  value from a gesture, fixing an animation that restarts on recomposition, or making animation
  tests deterministic.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - chrisbanes/skills (compose-animations)
    - agent-skills-standard (android-compose)
    - agent-skills-standard (android-accessibility)
    - kotlin-footguns (compose-visuals-footguns)
---

# Compose Animation

An animation is a **function of state → visual**, never a source of state. If a value only changes
because an animation ran, the animation is hiding a decision.

## Use when

- Adding enter/exit, expand/collapse, cross-fade, or content swap.
- Animating a value driven by a gesture or scroll (offset, scale, alpha).
- An animation restarts, jumps, or ignores the system "remove animations" setting.
- A UI test hangs or flakes because an animation never settles.

## Do not use when

- The change should be instant and the "smoothness" is polish theatre → skip it.
- The cost is recomposition, not animation → `recomposition`.
- The animation is a list item during scroll → `lazy-layouts` (`animateItem`).

## Rules

1. **Pick the primitive by what changes:**
   - a value (`color`, `offset`, `alpha`, `elevation`) → `animate*AsState`
   - a subtree appearing/disappearing → `AnimatedVisibility`
   - swapping between two subtrees → `AnimatedContent`
   - gesture-driven, interruptible, needs velocity → `Animatable` (`snapTo`/`animateDecay`)
   - a looping decoration → `rememberInfiniteTransition` (and see rule 8)
2. **Animation specs come from the theme, not literals at call sites.** Use
   `MaterialTheme.motionScheme` (or a DS motion token) for duration/easing. Ad-hoc `tween(250)` at
   twenty call sites is a design-system bypass.
3. **Never create the transition inside the body without `remember`.** A transition created per
   recomposition restarts from scratch and looks like jank.
4. **`AnimatedVisibility`/`AnimatedContent` take a Boolean/enum, not four booleans.** Same rule as
   `compose-component-api`: variations multiply.
5. **Respect the user's motion setting.** `LocalMotionDurationScale`/animator duration scale 0 means
   "no animation" — do not divide by it, do not compensate. Verify with animations disabled.
6. **The end state must be correct without the animation.** Disable animations and the UI must still
   be right instantly. If a layout depends on the animation completing to look correct, the
   layout is wrong.
7. **Do not animate layout size on a scrolling screen.** `animateContentSize` in a `LazyColumn` item
   invalidates measurement every frame; use it on small static containers only.
8. **Infinite transitions are a cost and a test hazard.** They prevent `waitForIdle` from ever
   idling (hanging instrumented tests) and keep the frame clock busy. Use them only for a genuine
   indeterminate indicator, and stop them when not visible.
9. **One status change = one animated property, not a cascade.** Animating scale + alpha + offset with
   three different specs for one "load" event produces motion that reads as three events.
10. **`AnimatedContent` needs a stable `contentKey`.** Without it, content that changes identity
    (same type, different item) cross-fades from the wrong starting point.

## Procedure

1. Write the state change that should be visible (from `state-holders`), e.g. `Expanded` true/false.
2. Choose the primitive per rule 1.
3. Take duration/easing from the theme (rule 2); `remember` the transition.
4. Add a `@Preview` for start and end states, and one with animations disabled.
5. Verify: state is correct with animations off; then with animations on, nothing restarts on
   unrelated recomposition.
6. If a test touches this UI, disable animations or drive `mainClock` manually.

## Checklist

- [ ] Primitive matches what changes (rule 1).
- [ ] Specs from theme, not literals.
- [ ] Transitions/`Animatable` created once (`remember`) and keyed by identity.
- [ ] `AnimatedVisibility`/`AnimatedContent` driven by Boolean/enum, not boolean clusters.
- [ ] Behaviour correct with animations disabled (rule 6).
- [ ] No `animateContentSize` inside a lazy item.
- [ ] Infinite animation visible only, and stopped when not.
- [ ] `AnimatedContent` has a stable `contentKey`.
- [ ] Tests either disable animations or advance the clock explicitly.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Visual glitch on every recomposition | `val t = updateTransition(...)` in body | `remember { }` | restart from 0 |
| Off-brand motion | `tween(250)` eighteen times | theme motion spec | inconsistent feel |
| Test hangs | infinite shimmer visible | stop when hidden | `waitForIdle` never idles |
| Layout depends on animation | end state only correct after tween | correct layout, then animate | animations-off users see breakage |
| Jank in list | `animateContentSize` per item | pre-sized items | measure every frame |
| Three-in-one motion | scale + alpha + offset, three specs | one coordinated transition | reads as three events |
| Wrong cross-fade | no `contentKey` | key on item identity | fades from stale content |

## Verify

```bash
adb -s <serial> shell settings put global animator_duration_scale 0
adb -s <serial> shell settings put global transition_animation_scale 0
./gradlew :feature:x:testDebugUnitTest
adb -s <serial> shell settings put global animator_duration_scale 1
```

Expected: with scales at 0 every state renders correctly and instantly; tests pass with animations
disabled; with animations restored nothing restarts on unrelated recomposition.

## References

- `androidx.compose.animation.core` — `animateFloatAsState`, `Animatable`, `MotionScheme`
- Accessibility: `LocalMotionDurationScale`, "Remove animations" setting
