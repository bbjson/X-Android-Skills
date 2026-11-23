---
name: modifier-and-layout
description: >-
  Get Modifier chains and custom layout right: order semantics (padding vs clickable vs background),
  Modifier.Node instead of Modifier.composed, IntrinsicSize cost, and when a custom Layout beats
  nested Row/Column. Use when a click area is wrong, a background covers the wrong bounds, a
  modifier is silently ignored, a custom modifier misbehaves on recomposition, or a layout reports
  jank from over-measuring.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - skydoves/compose-performance-skills (modifiers/migrating-to-modifier-node, modifiers/ordering-modifier-chains)
    - agent-skills-standard (android-compose)
    - kotlin-footguns (compose-visuals-footguns)
---

# Modifier and Layout

A Modifier chain is **a series of wrappers applied left to right**. Reading the chain backwards
tells you which wrapper is outermost — and therefore what the user actually touches and sees.

## Use when

- Click area, ripple bounds, background, or border is wrong.
- A modifier "does nothing" (applied after something that swallowed the constraint).
- Writing a custom `Modifier` (draw, pointer, layout).
- Deciding between nested `Row`/`Column`, `ConstraintLayout`, and a custom `Layout`.
- A custom modifier resets state on recomposition or leaks.
- Measuring shows excessive measure passes.

## Do not use when

- The cost is recomposition (`@Composable` re-execution) → `recomposition`.
- The cost is lazy list item management → `lazy-layouts`.
- The question is a component's API → `compose-component-api`.

## Rules

1. **Order is semantics.** `Modifier.padding(16.dp).clickable {}` → the padding area is clickable.
   `Modifier.clickable {}.padding(16.dp)` → only the content is clickable. Decide which is intended,
   then order accordingly. Same for `background`: `background().padding()` paints the padded area,
   `padding().background()` paints only the inner content.
2. **`clip()` must precede what should be clipped.** `background(color, shape)` already clips to the
   shape; a separate `clip` after `background` clips the wrong layer. Put `clip` before `background`
   and `border` when you need both.
3. **`Modifier.offset` does not remeasure; `padding` does.** For a visual shift that should not affect
   layout, use `offset`. For a shift that should, use `padding`.
4. **Animation of position/scale/alpha goes through `graphicsLayer`, not layout modifiers.**
   `graphicsLayer { translationX = …; scaleX = …; alpha = … }` runs on the draw layer without
   remeasuring or recomposing siblings.
5. **Write custom modifiers as `Modifier.Node`, not `Modifier.composed`.** `composed` allocates on
   every recomposition and cannot participate in the modifier-node lifecycle; it is legacy.
   Migrate existing `composed` usages when touching them (the two have equivalent behaviour, but
   `Node` is faster and cancel-correct).
6. **A layout modifier must honour the incoming constraints.** A custom `Modifier.layout` that
   ignores `constraints` produces overflow that looks like a rendering bug. Use
   `measurable.measure(constraints)` and `layout(w, h) { place(...) }` with values derived from the
   measured placeable.
7. **Integers in a custom modifier must be `toInt()`-safe.** `Modifier.offset(x.roundToInt())` on a
   float from a gesture, and never `Int` overflow from a huge scroll offset.
8. **`IntrinsicSize` costs an extra measure pass; use it sparingly.** `Modifier.height(IntrinsicSize.Max)`
   measures children twice. Acceptable for small static rows; unacceptable in lists or deep trees.
9. **Prefer one custom `Layout` over four nested `Box`+`offset` wrappers when alignment is
   non-linear.** Nested wrappers are measured once each; a single `Layout` measures children once and
   places them explicitly — cheaper and far clearer than a wrapper pyramid.
10. **`Modifier.weight` only exists in `RowScope`/`ColumnScope`, and only for direct children.** A
    weight inside a nested wrapper applies to the wrong parent — a classic "weight does nothing" bug.
11. **Modifier parameters must be `Modifier`, defaulted, and applied once at the root** — see
    `compose-core` rule 2; a custom modifier is still a modifier and follows the same contract.

## Procedure

1. Read the chain right to left and write down the wrapper order.
2. Identify the intended touch/paint bounds; reorder per rules 1–2.
3. Replace layout-affecting animation with `graphicsLayer` (rule 4).
4. For custom behaviour: write a `Modifier.Node` with a `NodeElement`, implement
   `onAttach`/`onDetach`, and only the lifecycle you need (`DrawModifierNode`, `PointerInputModifierNode`,
   `LayoutModifierNode`).
5. If alignment needs >2 nested wrappers, write a `Layout` (rule 9).
6. Measure: check for double-measure with Layout Inspector "measure" counts, not by guessing.

## Checklist

- [ ] Click/paint bounds match the intended design (order verified).
- [ ] `clip` precedes `background`/`border` where both are used.
- [ ] No layout modifier used for pure visual offsets.
- [ ] Animated transforms use `graphicsLayer`.
- [ ] Custom modifiers are `Modifier.Node`; no new `Modifier.composed`.
- [ ] Custom layout honours incoming constraints.
- [ ] Float→Int conversions rounded where needed.
- [ ] `IntrinsicSize` not used in lists or deep trees.
- [ ] No `weight()` outside its direct `Row`/`Column` scope.
- [ ] Modifier parameter applied exactly once at the root.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Padding not clickable | `clickable {}.padding(16.dp)` | `padding(16.dp).clickable {}` | wrapper order |
| Background too big | `background().padding()` when inner paint wanted | `padding().background()` | paints padded area |
| Square corners | `background(shape).clip(shape)` order flipped | `clip(shape).background()` | clip applies to the wrong layer |
| Jank on drag | `offset(animatedValue.dp)` | `graphicsLayer { translationX = value }` | remeasure per frame |
| Custom modifier resets | `Modifier.composed { … }` | `Modifier.Node` | allocation + lifecycle |
| Overflow from custom layout | ignores `constraints` | measure with constraints | size mismatch |
| Double measure | `IntrinsicSize.Max` in a list item | fixed/`heightIn` | 2x measure |
| "weight does nothing" | `weight` inside nested `Box` | weight on the direct `Row`/`Column` child | wrong scope |
| Wrapper pyramid | 4 nested `Box`+`offset` | single `Layout` | measure cost + readability |

## Verify

```bash
./gradlew :app:assembleDebug
# Layout Inspector: enable "Count measure/layout" on the suspect composable
```

Expected: tapping the visual bounds triggers the action (not a smaller inner area), and the measure
counter for the modified node stays at 1 per frame during a drag/animation.

## References

- `Modifier.Node` / `ModifierNodeElement` migration guide (androidx.compose.ui.node)
- `Layout` (`MeasurePolicy`) for custom placement
