---
name: lazy-layouts
description: >-
  Make LazyColumn/LazyRow/LazyGrid correct and smooth: stable keys, content types, item animation,
  paging triggers, prefetch, sticky headers, and item state that survives recycling. Use when scroll
  jank appears only in lists, items lose state or jump, animateItem misbehaves, an infinite list
  re-fetches the wrong page, or a list feels slow with heterogeneous content.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - skydoves/compose-performance-skills (lists/optimizing-lazy-layouts, lists/configuring-lazy-prefetch)
    - agent-skills-standard (android-compose)
    - awesome-android-agent-skills (compose-performance-audit)
    - kotlin-footguns (compose-screens-footguns)
---

# Lazy Layouts

A lazy list is a **recycling viewport with identity**. Two things make it misbehave: unstable
identity (wrong keys) and work per item (formatting, allocation, unbounded measure).

## Use when

- Scroll jank, dropped frames, or slow first scroll in a list.
- Item state (expanded, playing, text selection) is wrong after scrolling away and back.
- `animateItem` glitches, or items animate from the wrong position.
- Infinite/paged list fetches repeatedly, or stops one page early.
- Heterogeneous list (headers, ads, items) re-composes everything on a small change.
- Sticky headers, or a grid with variable item sizes.

## Do not use when

- The jank is also present on non-list screens → `recomposition`.
- The list source/pagination is a data-layer concern → `data-layer`.
- The first-frame (pre-list) cost dominates → `startup-and-perfetto`.

## Rules

1. **`key` must be the stable domain id, never the index and never a data-class instance.**
   `items(list, key = { it.id })`. Index keys break item state, animation and scroll position on any
   insertion or reorder. An object key whose `hashCode` changes recomposes the whole list.
2. **`key` must be unique across the whole list, including headers/ads.** Two sections both keyed by
   `"header"` crash at runtime ("key was already used").
3. **Use `contentType` for heterogeneous lists.** Returning a distinct type per item shape lets the
   composer reuse slots and avoids recomposing every item when one type's data changes.
   `items(list, key = { it.id }, contentType = { it::class })`.
4. **`animateItem()` needs stable keys and a `LazyItemScope`; it does not work with `contentType`
   switching identity mid-animation.** If it glitches, keys are the first suspect, not the animation.
5. **Item-level state must be keyed, or hoisted out of the item.** `rememberSaveable` inside an item
   is recreated on recycle. Hoist per-item state into the ViewModel keyed by id, or use
   `rememberSaveable(key = item.id)`.
6. **Trigger paging from list state, not from item composition.** Use
   `derivedStateOf { listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index }` +
   `snapshotFlow`, or a `PagingSource`. Triggering a fetch from a composable's `LaunchedEffect(item)`
   fires per recycled item and duplicates requests.
7. **Never nest same-axis scrollables.** A `LazyColumn` inside a `verticalScroll` `Column` throws; a
   `LazyColumn` inside another `LazyColumn` requires a fixed height and defeats recycling. Use one
   lazy list with header/footer items.
8. **Sticky headers use `stickyHeader(key = …)`, not an overlay computed from scroll offset.** The
   overlay approach breaks with RTL, insets, and item height changes.
9. **Avoid `IntrinsicSize` and `wrapContentHeight` cascades inside items.** Each forces an extra
   measure pass per visible item. Give items a `heightIn(min = …)` and let content grow within it.
10. **Prepare item view-models upstream, not in the item lambda.** Sorting, filtering, date
    formatting, and string building per item run on every recomposition of that item. Do it once in
    the ViewModel (see `recomposition` cause (a)).
11. **Prefetch defaults are usually right; tune only with measurement.** `LazyListPrefetchStrategy`
    and `LazyLayoutCacheWindow` help when items are expensive and stable; increasing the cache window
    increases memory and can make jank worse by displacing the prefetch budget. Measure before and
    after (rule of `recomposition`: no change without a before/after number).

## Procedure

1. Audit keys: `grep -n "items(\|itemsIndexed(\|key =" <file>`.
2. Replace index/instance keys with domain ids; ensure global uniqueness.
3. Add `contentType` where item shapes differ.
4. Hoist or key item state (rule 5).
5. Rewrite paging triggers to `snapshotFlow`/Paging (rule 6).
6. Remove nested scrollables (rule 7); use header items.
7. Move per-item formatting upstream.
8. Measure: frame timing in a Perfetto trace or `dumpsys gfxinfo`, before/after.

## Checklist

- [ ] All `items` have stable, globally unique domain-id keys.
- [ ] No index-based keys anywhere in the diff.
- [ ] `contentType` set for heterogeneous lists.
- [ ] `animateItem` only with stable keys.
- [ ] Item state hoisted or `rememberSaveable(key = id)`.
- [ ] Paging triggered by list state, not by item composition.
- [ ] No nested same-axis scrolling.
- [ ] Sticky headers via `stickyHeader`.
- [ ] No per-item formatting/sorting in the item lambda.
- [ ] Frame timing measured before/after any prefetch tuning.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| State on wrong item | `items(list) { index -> }` without key | `key = { it.id }` | recycling rebinds state |
| Crash on insert | duplicate `"header"` keys | unique keys incl. headers | Lazy key uniqueness |
| Everything recomposes | no `contentType` | `contentType = { it.type }` | no slot reuse |
| Duplicate fetches | `LaunchedEffect` inside item | `snapshotFlow` on listState | one per recycled item |
| Scroll crash | `LazyColumn` in `verticalScroll` | single lazy list | infinite constraint |
| Broken sticky header | overlay + offset math | `stickyHeader` | RTL/insets/measure |
| Jank per item | `SimpleDateFormat` in item | format upstream | repeated work |
| Worse after "tuning" | bigger cache window blindly | measure first | memory/jank trade-off |

## Verify

```bash
./gradlew :app:assembleDebug
adb shell dumpsys gfxinfo <pkg> framestats | head -40    # janky frames while scrolling
# Perfetto: record scroll, check for frames > 16.6ms and for repeated measure passes
```

Expected: scroll shows no repeated measure passes, item state survives scrolling 50 items down and
back, and inserting one item at the top does not reset scroll position or animation.

## References

- `LazyListState` / `LazyGridState` — `layoutInfo`, `snapshotFlow`
- `LazyItemScope.animateItem`, `LazyListScope.stickyHeader`, `contentType`
