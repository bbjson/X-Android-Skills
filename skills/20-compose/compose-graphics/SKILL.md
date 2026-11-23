---
name: compose-graphics
description: >-
  Draw custom graphics in Compose without paying for recomposition or per-frame allocation:
  Canvas, drawBehind/drawWithContent, drawWithCache, Path reuse, graphicsLayer, and text on canvas.
  Use when adding a chart, badge, ring, shimmer, custom shape or drawn decoration, when a drawing
  causes jank, when a modifier looks blurry or mis-aligned, or when drawing needs a semantics node.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - android-developers (Compose graphics + draw modifiers, re-expressed)
    - this-repo (gap analysis: no drawing skill; only recomposition and modifier ordering)
---

# Compose Graphics

One decision: **draw in a `DrawScope` that is invalidated, not in composition that recomposes.**
Everything else is which of the five entry points is the correct one.

## Use when

- Adding a chart, progress ring, sparkline, badge, divider, shadow, blur or custom background.
- Choosing between `Canvas`, `drawBehind`, `drawWithContent`, `drawWithCache` and a `Layout`.
- A drawing causes jank, allocates per frame, or recomposes on every animation frame.
- Text must be drawn inside a canvas, or a drawn area needs a content description.
- A drawn element is blurry, clipped, or offset by a pixel.

## Do not use when

- Modifier order/padding/click-area questions with no drawing → `modifier-and-layout`.
- Recomposition is the problem and nothing is drawn → `recomposition`.
- Animated value plumbing rather than drawing → `compose-animation`.
- Visual regression capture of the drawn output → `screenshot-testing`.

## Rules

1. **Choose the entry point by what invalidates:** `Canvas`/`Modifier.drawBehind` when the drawing
   depends on state read *inside* the lambda; `drawWithContent` when the drawing wraps content;
   `drawWithCache` when geometry-derived objects (brushes, paths, shadows) are expensive.
2. **Never allocate inside `DrawScope` per frame.** `Path()`, `Brush`, `Paint` and text layouts are
   built in `drawWithCache` (or `remember`) and reused; per-frame allocation is GC pressure at
   60/120 Hz, which reads as jank exactly during animation.
3. **`drawWithCache` is the default for anything with a gradient, path or shadow** — its `onBuildDrawCache`
   runs when size or state changes, not per frame.
4. **Prefer `Modifier.graphicsLayer { }` for transforms** (alpha, scale, translation, rotation,
   clip). The lambda form skips recomposition and only invalidates the layer.
5. **A drawn element that conveys information needs semantics.** `Canvas` produces no accessibility
   node: add `Modifier.semantics { contentDescription = ... }` (or a text alternative) or the screen
   is silent (`compose-accessibility`).
6. **`Modifier.alpha` recomposes; `graphicsLayer { alpha = }` does not.** Use `graphicsLayer` for
   animated or gesture-driven opacity, and for anything changing every frame.
7. **Text on canvas goes through `rememberTextMeasurer` + `drawText`**, measured once per style and
   size. Building a `Paragraph` per frame is the most expensive way to draw a label.
8. **Path work is cached by geometry, not by value.** Rebuild the path only when the shape's inputs
   (size, corner radius, data points) change; a path that depends on an animated value belongs in
   `drawWithCache` keyed on that value.
9. **Blur, shadow and `RenderEffect` are the expensive primitives.** Prefer a static asset or a
   solid/gradient approximation; a full-screen blur per frame drops frames on mid-range devices.
10. **Drawn coordinates come from `DrawScope.size`, never from a captured `Dp` constant.** Hardcoded
    pixel dimensions break on density changes and in adaptive windows.
11. **Clip before drawing outside bounds.** Drawing past the composable's bounds on purpose (a glow,
    a badge) becomes a layout surprise: clip explicitly or declare the overflow.
12. **Screenshot the drawing at two densities.** A drawn chart that is correct at one density is a
    hypothesis; `screenshot-testing` at two configurations is the proof.

## Procedure

1. Decide invalidation source (state read in lambda vs outside).
2. Put expensive construction in `drawWithCache`; keep the draw lambda allocation-free.
3. Add semantics for informational drawing.
4. Animate via `graphicsLayer`/`Animatable` state read inside the draw lambda.
5. Capture a screenshot at two densities and check alignment with adjacent text.

## Checklist

- [ ] Entry point matches the invalidation source.
- [ ] No `Path`/`Brush`/`Paint`/`TextLayoutResult` allocation inside the draw lambda.
- [ ] Gradients, paths and shadows built in `drawWithCache`.
- [ ] Transforms and animated alpha via `graphicsLayer`.
- [ ] Informational drawing has `semantics { contentDescription }`.
- [ ] Text drawn via `rememberTextMeasurer`, not per frame.
- [ ] Blur/shadow justified or replaced by a cheaper approximation.
- [ ] Coordinates derived from `DrawScope.size`.
- [ ] Overflow clipped or declared.
- [ ] Screenshot at two densities reviewed.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Jank only while animating | `Path()` in draw lambda | build in `drawWithCache` | allocation per frame |
| Recomposition per frame | `Modifier.alpha(animated)` | `graphicsLayer { alpha = }` | invalidates composition |
| TalkBack silent on a chart | `Canvas` alone | `semantics { contentDescription }` | no semantics node |
| Blurry badge | fixed `dp` converted per draw | derive from `DrawScope.size` + density | rounding at wrong stage |
| Gradient rebuilt constantly | `Brush.linearGradient(...)` in `onDraw` | cached brush | GC + shader recreation |
| Frame drops on scroll | full-screen `RenderEffect` blur | static/gradient approximation | GPU-bound per frame |
| Label misaligned | hardcoded text offset | `TextMeasurer` baseline metrics | font metrics differ per device |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew :app:testDebugUnitTest
adb -s <serial> shell dumpsys gfxinfo <pkg> framestats | head -40   # after an animated draw
adb -s <serial> shell settings put global animator_duration_scale 1
```

Expected: no frames over budget during the drawing's animation on a mid-range device, TalkBack
reads the drawn element's description, and the screenshot test passes at both densities.

## References

- `DrawScope`, `Modifier.drawBehind`, `Modifier.drawWithContent`, `Modifier.drawWithCache`
- `Modifier.graphicsLayer`, `rememberTextMeasurer`, `drawText`
- `Modifier.semantics`, `contentDescription`
