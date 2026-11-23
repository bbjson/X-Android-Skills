---
name: xml-to-compose
description: >-
  Migrate XML View screens to Jetpack Compose one screen at a time, using View/Compose
  interop in both directions so the app ships continuously. Use when converting a layout to a
  Composable, embedding Compose inside an existing Fragment/Activity, embedding a View inside
  Compose, translating a RecyclerView adapter, bridging a theme/attribute, or deciding the order
  of a multi-screen migration.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - awesome-android-agent-skills (xml-to-compose-migration)
    - agent-skills-standard (android-compose-migration, android-legacy-navigation, android-legacy-state, android-xml-views)
    - android-skill (migrate-compose)
    - Meet-Miyani-compose-skill (compose-project)
---

# XML to Compose Migration

The migration unit is **one screen**, not one layout file and not the whole app. Ship after each
screen so every regression is attributable to a single change.

## Use when

- Converting an XML layout + Fragment/Activity to a Composable screen.
- Putting Compose into an existing View hierarchy (`ComposeView`) or a View into Compose
  (`AndroidView`).
- Porting a `RecyclerView`/`Adapter`/`ViewHolder` to `LazyColumn`.
- Bridging XML theme attributes, `dimens`, or styles into Compose.
- Ordering a migration across many screens.

## Do not use when

- The target is a new screen and nothing exists yet — just write Compose.
- The problem is navigation graph shape across the app → `compose-navigation`.
- The problem is state ownership in the new screen → `compose-state-effects` / `state-holders`.

## Rules

1. **Migrate leaf-up, screen by screen.** Convert the smallest self-contained screen first (a
   detail/empty state), never the screen with the most custom views. Build confidence with a
   cheap screen before the expensive one.
2. **Two legal interop directions, and only these:**
   - View tree hosts Compose: `ComposeView` in the layout, or `Fragment.setContent { }`.
   - Compose hosts a View: `AndroidView(factory, update)` — including a whole legacy Fragment's view.
   Do not mirror the same UI in both systems.
3. **Do not run two navigation mechanisms.** During migration, the Fragment graph keeps owning
   navigation until *all* screens in a flow are Compose; a Compose screen navigates by calling the
   host (lambda/callback), not by starting its own `NavHost`.
4. **Port state before porting layout.** `LiveData`/`ObservableField` → `StateFlow`/`UiState`
   *first*, verified by the old screen still working. A layout port on top of ad-hoc state is two
   migrations at once.
5. **Interop boundaries must be one-way and documented.** Data crosses as state down, events up
   (lambda). No shared mutable `ViewModel` field read from both a View and a Composable beyond the
   single `collectAsStateWithLifecycle` in the host.
6. **One theme source.** While both systems exist, derive Compose colours/typography from the XML
   theme (or vice versa) in exactly one adapter, so a brand change touches one file. Two palettes
   drift within a sprint.
7. **`RecyclerView` → `LazyColumn` is a data-shape change, not a widget swap.** The adapter's
   `getItemViewType` becomes multiple `item { }` branches; `notifyItemChanged` becomes immutable
   list replacement; item state must be keyed (`key = { it.id }`) or it is lost on scroll.
8. **View-specific behaviour must be re-specified, not assumed.** `OnTouchListener`, nested
   scrolling, `ViewPager2`, custom `onMeasure`, and infinite `ObjectAnimator` loops have Compose
   equivalents with different semantics — write down the behaviour being preserved.
9. **Every migrated screen must have an equivalent test before the XML is deleted.** At minimum the
   screenshot baseline (see `screenshot-testing`), because pixel-level regressions are the expected
   outcome of this migration.
10. **Delete the XML, the binding class, and the style only after the new screen is verified on a
    device.** Leaving dead layouts behind means two sources of truth and a future developer
    editing the wrong one.
11. **Migrate at a stable Compose version, and do not couple the migration to version bumps.**
    An XML→Compose PR that also bumps Compose/AGP has an ambiguous failure mode.

## Procedure

1. Inventory the screen: layout files, style/theme attrs used, `dimens`, custom views, adapter class.
2. Convert state (rule 4) and keep the XML screen working.
3. Write `Screen(uiState, onEvent)` as a pure composable, preview it with sample state.
4. Host it with `ComposeView`/`setContent` while the Fragment still owns navigation (rule 3).
5. Replace `RecyclerView` with `LazyColumn` + stable keys; port item branching (rule 7).
6. Port interactions: `clickable`, `pointerInput`, `nestedScroll`; animation via
   `animate*AsState`/`AnimatedVisibility` (rule 8).
7. Theme bridge in one file (rule 6).
8. Screenshot-test the screen; compare against the XML version.
9. Delete XML + binding + now-unused styles; run `./gradlew lint` for unused resources.
10. Repeat for the next screen; remove interop once its flow is fully Compose.

## Checklist

- [ ] One screen per change; it builds and installs before the next.
- [ ] Interop in one direction only, documented at the boundary.
- [ ] Navigation owner unchanged during the migration (no second `NavHost`).
- [ ] State converted before layout; old screen verified after the state change.
- [ ] `LazyColumn` has stable keys and no `notify*` calls.
- [ ] Theme attributes come from a single bridge function.
- [ ] Screenshot baseline added for the migrated screen.
- [ ] XML layout, view binding, and orphaned styles deleted.
- [ ] No version bump in the migration commit.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Big-bang rewrite | convert all screens in one PR | one screen per PR | unreviewable, unrevertable |
| Two navigations | `NavHost` inside the Compose screen and Fragment nav | host owns navigation until the flow is Compose | Back stack corruption |
| Lost scroll state | `LazyColumn` without keys | `items(list, key = { it.id })` | item state rebinds |
| Palette drift | Compose hardcoded colours + XML theme | one theme bridge | brand change misses one side |
| Dead layouts | keep XML "for reference" | delete after verification | future edits to the wrong file |
| Adapter ported blindly | `items(list) { ItemView(it) }` with ViewHolder logic lost | port `getItemViewType` branches + item state | behaviour silently dropped |
| Double collection | `observeAsState` + `collectAsState` on the same flow | one collection in the host | duplicate work, racing state |
| Migration + upgrade | bump Compose in the same PR | separate changes | ambiguous failures |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew :feature:x:verifyRoborazziDebug        # if screenshot tests are in place
./gradlew :app:lintDebug                          # UnusedResources after deletion
adb shell am start -n <pkg>/<Activity>            # manual parity check
```

Expected: the migrated screen renders identically (screenshot diff or side-by-side), Back
behaves as before, and `lint` reports no `UnusedResources` for the deleted layout's style entries.

## References

- `ComposeView` / `Fragment.setContent` — View hosts Compose
- `AndroidView(factory, update)` — Compose hosts View
- `LazyColumn` keys and `items(key = …)` — state preservation semantics
