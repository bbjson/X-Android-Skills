---
name: compose-core
description: >-
  Write a Composable that is stateless, previewable and cheap: correct parameter order, one
  modifier applied once, work kept out of composition, and the right layout primitive. Use when
  creating or refactoring any Composable function, when a screen nests five layouts to align two
  labels, when a Preview cannot be rendered without dependencies, or when text overflows, a list
  janks, or a function returns something other than Unit.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - agent-skills-standard (android-compose)
    - agent-skills-standard (android-resources)
    - awesome-android-agent-skills (compose-ui)
    - kotlin-footguns (compose-screens-footguns)
    - mobile-agent-skillpack (jetpack-compose)
---

# Compose Core

A Composable is a function from inputs to a piece of layout. Three properties follow from that:
it takes values, it returns `Unit`, and it does no work that is not about layout.

## Use when

- Writing a new Composable or extracting one from a larger screen.
- A Composable is hard to Preview, or needs a ViewModel to render at all.
- Deciding `Column` vs `LazyColumn`, or fixing deep nesting to align elements.
- Text truncation, `stringResource`/plural handling, or hardcoded dimensions.
- A Composable recomputes work (sort/filter/format) in its body.

## Do not use when

- The question is who owns state or which effect to use → `compose-state-effects`.
- The question is the public API shape of a reusable component → `compose-component-api`.
- The question is theme tokens and colours → `design-system`.
- The measured problem is recomposition cost → `recomposition`.
- Sizing a screen for tablet/foldable/split-window targets → `adaptive-layout`.

## Rules

1. **Parameter order is fixed:** required values → optional values → `modifier: Modifier = Modifier`
   as the first optional parameter → trailing `content`/slot lambdas → other lambdas after slots.
   This is the order every Compose API uses; deviating makes the call site unreadable.
2. **One `modifier` parameter, applied exactly once, to the outermost layout** of the function:
   `Box(modifier = modifier.padding(...))`. Never apply the incoming `modifier` to a child, never
   apply it twice, never default it to anything but `Modifier`.
3. **A Composable returns `Unit` and takes values.** If you are returning a data structure or
   building a tree of custom objects, you are writing a DSL, not UI.
4. **Stateless by default.** State is either hoisted to the caller (value + `onValueChange`) or
   internal to a genuinely self-contained component. A screen-level Composable that fetches,
   formats and lays out is three responsibilities.
5. **No work in the composition body.** No sorting/filtering large collections, no formatting
   loops, no `SimpleDateFormat` construction, no disk/network. Do it upstream (ViewModel) or
   `remember(key) { }`.
6. **Use `remember(key)` with the *minimum* identity that must invalidate it.** `remember(items) { … }`
   where `items` is a new list instance every emission invalidates every time — use a stable
   identity (id, count) or move the derivation upstream.
7. **Lazy when it can exceed one screen.** `Column` + `forEach` renders every child; `LazyColumn`
   composes only the visible ones. Rule of thumb: unknown or >~20 items → lazy. Also lazy when the
   item is expensive even if few (images, video).
8. **Never nest scrollables in the same direction.** `LazyColumn` inside a `Column` with
   `verticalScroll` crashes with an infinite-height constraint. Use one scrollable and put the rest
   inside it as items.
9. **Text must declare its overflow behaviour.** `maxLines` + `overflow = TextOverflow.Ellipsis` for
   any user- or server-provided string. Unbounded text is how a translation breaks a fixed-height row.
10. **All user-visible strings come from resources.** `stringResource(id = R.string.x)`, plural via
    `pluralStringResource`. A literal in a Composable cannot be translated and will be missed by lint
    only sometimes.
11. **Dimensions come from the theme, not literals.** `MaterialTheme.spacing.md`, not `16.dp`.
    Ad-hoc `dp` literals are how a design-system change misses 200 call sites.
12. **A Preview must render without infrastructure.** Provide sample data; never a ViewModel, never a
    network call. If you cannot, the Composable is not stateless enough (rule 4).
13. **Prefer `Row`/`Column`/`Box` with explicit sizing over nested wrapping to align content.**
    Alignment is an `Arrangement`/`Alignment` parameter, not a wrapper hierarchy. Three levels of
    nesting for one `Alignment.CenterVertically` is a review finding.

## Procedure

1. Write the signature with rule 1's order.
2. Decide state ownership (hoist or internal) and write it once.
3. Pick the layout primitive: 1 axis → `Row`/`Column`; overlap → `Box`; unknown count → lazy.
4. Move any computation out of the body into the caller or `remember`.
5. Add overflow behaviour to every text.
6. Add a `@Preview` with realistic and edge-case data (long string, empty, large font scale).
7. Check the modifier is applied once, at the root.

## Checklist

- [ ] Parameter order follows rule 1; `modifier` is the first optional parameter.
- [ ] Incoming `modifier` applied once, at the root element.
- [ ] Function returns `Unit`.
- [ ] No collection processing / formatting / I/O in the body.
- [ ] `remember` keys use stable identity.
- [ ] Lazy list where item count is unbounded; no nested same-axis scrolling.
- [ ] Every `Text` has `maxLines` + `overflow` where content is dynamic.
- [ ] Strings from resources; dimensions from theme tokens.
- [ ] `@Preview` renders with sample data only.
- [ ] No more than one wrapper level purely for alignment.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Unusable API | `fun Card(text: String, onClick: () -> Unit, modifier: Modifier)` | `fun Card(modifier: Modifier = Modifier, text: String, onClick: () -> Unit)` | call sites and tooling expect the standard order |
| Padding missing / doubled | `modifier` applied to inner `Text` | apply to outer layout | caller's layout intent ignored |
| Preview crashes | construct a ViewModel in Preview | pass sample `UiState` | Preview has no DI/graph |
| Scroll crash | `LazyColumn` inside `verticalScroll` | one scrollable, lazy items | infinite height constraint |
| Broken translation | `Text("Save")` | `stringResource(R.string.save)` | untranslatable, lint-only |
| Jank on scroll | `items.forEach { Row(it) }` in `Column` | `LazyColumn { items(...) }` | all children composed |
| Recompute every frame | `remember { sortAll() }` without key | compute upstream | stale or wasted work |
| Text breaks layout | no `maxLines` | `maxLines = 2, overflow = Ellipsis` | unbounded growth |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew :app:lintDebug     # UnusedResources, HardcodedText
```

Then in Android Studio: render the `@Preview` with font scale 2.0 and a 200-character string —
the row must not jump or clip content.

## References

- Compose API guidelines (parameter order, `modifier`, slots) — android.googlesource.com compose docs
- `LazyColumn` scrollable constraints — nested-scrollable error message
