---
name: recomposition
description: >-
  Find and fix unnecessary Jetpack Compose recomposition by classifying when a Composable is
  skipped, why it is not, and which of the four causes applies. Use when reviewing Compose
  performance, reading stability reports, seeing jank on state change, investigating why a
  Composable recomposes on every frame, or deciding whether strong skipping, derivedStateOf,
  or lambda deferral is the right fix.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - skydoves/compose-performance-skills (recomposition/*, stability/*)
    - chrisbanes/skills (compose-performance)
    - awesome-android-agent-skills (compose-performance-audit)
---

# Recomposition

Compose recomposition is a *symptom*. Every fix reduces to one of four causes, and each cause
has exactly one correct remedy. Diagnose the cause before touching code.

## Use when

- A screen or component recomposes when unrelated state changes.
- Scrolling, typing, or animation causes visible jank.
- A stability report lists composables as `unstable` / `not skippable` and you must decide
  whether it matters.
- Choosing between `derivedStateOf`, lambda parameters, `key()`, or `@Stable` annotations.

## Do not use when

- The cost is in layout/measure (`LazyLayout` prefetch, `SubcomposeLayout` budget) → `lazy-layouts`.
- The cost is Modifier chain structure → `modifier-and-layout`.
- You have no measurement at all yet → run `startup-and-perfetto` first; never optimise blind.

## Rules

1. **Never optimise without a count.** Enable recomposition counts (Layout Inspector or
   `@TraceRecomposition`), record the number before, change one thing, record after. A change
   without a before/after pair is not a fix.
2. **Classify first — there are only four causes:**
   - (a) **State read too high**: a value read at the root that only a leaf needs.
   - (b) **Parameter is not equal**: a new object/lambda/data-class instance every call.
   - (c) **Type is unstable**: the compiler cannot prove `equals`, so it never skips.
   - (d) **Scope invalidation broadcast**: an effect or state written during composition
     invalidates the whole subtree.
3. **Cause (a) fix is deferral, not memoisation.** Pass `() -> T` lambdas or read state at the
   leaf. `remember` the value does not stop the parent from recomposing.
4. **Cause (b) fix is stability of the *instance*, not of the class.** Hoist lambda creation out
   of the composable (`remember { { onClick(it) } }` only when it captures changing values —
   prefer passing the Event/VM function reference), and do not construct data objects inline in
   arguments.
5. **Cause (c) is fixed by making the class provably stable, not by slapping `@Stable` on it.**
   Order of preference: `val` properties of stable types → immutable collections → `@Immutable`
   for pure data holders → `@Stable` only when state is genuinely observable and `equals` is
   intentionally identity-based. `@Stable` on a class with a mutable `var` of a mutable type is
   a lie that produces stale UI.
6. **`List<T>` is unstable by default.** Replace API-facing `List` with `kotlinx.collections.immutable`
   (`ImmutableList`) at the composable boundary, or pass a stable wrapper. Do not copy to
   `persistentListOf()` inside the composable on every recomposition.
7. **Strong skipping is the default — do not configure around it.** With strong skipping on,
   unstable parameters no longer block skipping; the remaining cost is re-executing the body.
   Any advice to enable `feature(StrongSkippingMode)` explicitly is obsolete. Do not add it.
8. **`derivedStateOf` is for two cases only**: expensive derivation from fast-changing inputs,
   or distinct-until-changed. `remember(key) { compute }` is the tool for "recompute when key
   changes"; `derivedStateOf` is not a substitute.
9. **Never write state during composition.** No `state.value = x` in a body (causes (d));
   use `SideEffect` / `LaunchedEffect`, or derive instead of storing.
10. **A skipped Composable is not automatically cheap.** Skipping saves the body, not the layout.
    For lists and animation, measure frames, not counts.

## Procedure

1. Record baseline: Layout Inspector recomposition counts, or a Perfetto trace with
   `@TraceRecomposition` annotations for the suspect composable.
2. Read the compiler's stability output. Since the Compose compiler moved to a Gradle plugin
   (Kotlin 2.0+), the `-Pandroidx.compose.compiler.reports` property no longer produces
   anything — configure the destination in the module instead:
   ```kotlin
   // app/build.gradle.kts
   composeCompiler { reportsDestination = layout.buildDirectory.dir("compose_compiler") }
   ```
   ```bash
   ./gradlew :app:compileDebugKotlin --rerun-tasks
   ls app/build/compose_compiler     # <module>-composables.csv, <module>-classes.txt
   ```
3. For each composable with a high count, assign cause (a)-(d) from the report + code:
   - appears `restartable skippable` but still recomposes → (a) or (b)
   - appears `restartable` only → (c)
   - count grows without state change → (d)
4. Apply the single matching remedy from rules 3–6, 9.
5. Re-measure. Keep the change only if the count or frame time improved; otherwise revert —
   the added indirection is now pure cost.

## Checklist

- [ ] Before/after numbers recorded (counts or frame time), not adjectives.
- [ ] Each changed composable has a named cause from the four.
- [ ] No `@Stable` added to a class containing mutable unstable properties.
- [ ] No new `derivedStateOf` unless one of the two legal cases applies.
- [ ] No `List` passed into a hot composable without a stability argument.
- [ ] No state writes in composition bodies in the diff.
- [ ] `StrongSkippingMode` feature flag not toggled anywhere.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Parent recomposes on scroll | `val offset = scrollState.value` at root | `scrollState.value` read inside the leaf | (a) deferral |
| Lambdas cause recomposition | new `{ }` in argument position | pass VM function reference or `remember`ed lambda | (b) instance changes |
| `data class ScreenState(val items: List<X>)` not skipping | `@Stable` on it | `ImmutableList<X>` or make items' type stable | (c) `List` is unstable |
| `@Immutable` on a holder with `var` | annotate anyway | make fields `val`, or drop the annotation | stale UI, silent |
| `derivedStateOf` everywhere | on `state.count` | plain read | allocation, zero benefit |
| "Optimised" with no measurement | trust the pattern | measure, then decide | most patterns are inert here |
| Whole tree recomposes after `LaunchedEffect` writes state | write during composition | `SideEffect` / derive | (d) broadcast |

## Verify

```bash
./gradlew :app:compileDebugKotlin --rerun-tasks
ls app/build/compose_compiler                       # <module>-composables.csv, <module>-classes.txt
grep -A3 "restartable" app/build/compose_compiler/*-composables.csv | head -40
```

Expected: the composables you changed now appear as `restartable skippable`, or the measured
recomposition count dropped for the specific interaction you targeted, with no increase in
frame time elsewhere.

## References

- `skydoves/compose-stability-analyzer` (IDE plugin + CI gate) — for rule 2/5 diagnostics
- Compose compiler reports: `androidx.compose.compiler.reports` property
