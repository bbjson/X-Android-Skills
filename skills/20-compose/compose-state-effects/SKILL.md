---
name: compose-state-effects
description: >-
  Decide who owns each piece of Jetpack Compose state and which effect runs imperative work,
  then keep reads deferred so recomposition stays minimal. Use when writing or reviewing
  remembered state, state hoisting, ViewModel-backed screen state, LaunchedEffect,
  DisposableEffect, SideEffect, Flow collection, snackbar/navigation/analytics triggers, or
  when recomposition is happening more often than state actually changes.
license: Apache-2.0
metadata:
  domain: compose
  level: core
  sources:
    - chrisbanes/skills (compose-state-and-effects)
    - skydoves/compose-performance-skills (using-efficient-effects, choosing-derivedstateof)
    - agent-skills-standard (android-state)
    - awesome-android-agent-skills (android-viewmodel)
---

# Compose State and Effects

Composition renders. State and effects make rendering change safely.

The single decision this skill exists to make: **for every mutable value, name its lowest
responsible owner; for every imperative action, name the effect whose lifecycle follows that
same owner.** If you cannot name both, the design is not finished.

## Use when

- Adding `remember`, `rememberSaveable`, `mutableStateOf`, or hoisting state into a caller.
- Wiring a ViewModel/UiState into a screen (`collectAsStateWithLifecycle`).
- Choosing between `LaunchedEffect`, `DisposableEffect`, `SideEffect`, `rememberCoroutineScope`,
  and `produceState`.
- Firing one-shot work: snackbar, navigation, analytics, permission request, focus request.
- A Composable recomposes on scroll, on unrelated state change, or during rotation.

## Do not use when

- The question is component API shape (modifier parameter, slot API) → `compose-component-api`.
- The problem is measured jank in a list → `lazy-layouts` / `recomposition`.
- State lives in a data layer (Room/DataStore) → `data-layer`.

## Rules

1. **One owner per value, at the lowest node that needs it.** State that only one Composable
   reads must not be hoisted to the screen. If two siblings need it, hoist to their closest
   common parent — never further.
2. **Anything the UI must survive rotation/config change belongs outside composition** —
   ViewModel, `rememberSaveable`, or the data layer. `remember` alone loses it.
3. **The ViewModel exposes exactly one immutable UiState per screen** (data class or sealed
   hierarchy). Multiple independently collected `StateFlow`s in one screen is a defect: it
   permits impossible combinations.
4. **Collect with `collectAsStateWithLifecycle()`**, never bare `collectAsState()`. Bare
   collection keeps the upstream hot after `STOPPED`.
5. **One-shot events are not state.** Use `Channel(Channel.BUFFERED).receiveAsFlow()`, consumed
   in `LaunchedEffect(Unit)` with a `lifecycle.repeatOnLifecycle(STARTED)` collector. `SharedFlow`
   with `replay = 1` will re-fire on rotation; `StateFlow` will silently drop the event.
6. **Never collect a Flow inside composition.** No `flow.collect { }` in the function body —
   every recomposition adds a collector.
7. **Effects key on the minimum identity that matters.** `LaunchedEffect(userId)`, not
   `LaunchedEffect(Unit)` for anything parameterised, and never `LaunchedEffect(state)` where
   `state` is a new data-class instance each emission.
8. **`derivedStateOf` only for (a) expensive computation over fast-changing inputs or (b)
   distinct-until-changed.** It is not a general memoisation primitive; applying it to cheap
   reads adds allocation and confusion.
9. **Defer reads to the leaf that changes.** Pass a lambda (`() -> Float`) or read state inside
   the smallest scope that needs it, so scrolling offsets and progress values skip whole subtrees.
10. **`DisposableEffect` must return a dispose lambda that fully undoes its setup.** Registers
    a listener → must unregister; starts a camera → must unbind.

## Procedure

1. List every mutable value on the screen and write next to it: owner (composition / rememberSaveable
   / ViewModel / data layer) and lifetime (this frame / config change / process death / permanent).
2. Anything with lifetime ≠ "this frame" that you marked composition → move it (rule 2).
3. Merge per-field ViewModel state into one UiState type (rule 3).
4. For each imperative action, pick the effect by trigger semantics:
   - enters composition once, cancel on leave → `LaunchedEffect(key)`
   - acquire/release a resource → `DisposableEffect(key)`
   - fires after every successful composition, no coroutine → `SideEffect`
   - launch from a callback → `rememberCoroutineScope()`
   - derive state from a suspend source → `produceState`
5. Move every state read into the smallest Composable that consumes it (rule 9).
6. Delete any `derivedStateOf` whose inputs change at the same rate as its use.

## Checklist

- [ ] Every mutable value has one named owner; no value is duplicated in two owners.
- [ ] Rotation-sensitive values are outside plain `remember`.
- [ ] One UiState per screen; no screen collects two independent `StateFlow`s.
- [ ] All Flow collection uses `collectAsStateWithLifecycle` or `repeatOnLifecycle`.
- [ ] No `collect` / `runBlocking` / disk or network I/O in a Composable body.
- [ ] One-shot events use Channel-backed flow and are consumed once.
- [ ] Every `DisposableEffect` has a symmetric cleanup.
- [ ] `derivedStateOf` usages each satisfy rule 8.
- [ ] State reads that change per-frame are not at the top of the tree.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Event lost / duplicated on rotation | `MutableSharedFlow(replay = 1)` for snackbar | `Channel(BUFFERED).receiveAsFlow()` | replay re-delivers after config change |
| Impossible UI combinations | `val loading; val error; val data` collected separately | one `sealed interface UiState` | separate flows can be true at once |
| Work runs while backgrounded | `flow.collectAsState()` | `collectAsStateWithLifecycle()` | collection continues below STOPPED |
| Stack of collectors | `LaunchedEffect(Unit) { flow.collect {} }` when key changes | key on the identity, or `produceState` | one collector per key instance |
| Restart on every emission | `LaunchedEffect(uiState)` with data class | `LaunchedEffect(uiState.id)` | new instance ≠ changed meaning |
| Janky scrolling header | `val offset by scrollState.value` at screen root | pass `() -> Int` and read at the leaf | every frame recomposes the whole screen |
| Leaked listener | `DisposableEffect { register() }` without `onDispose` | `onDispose { unregister() }` | listener outlives the UI |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew :app:lintDebug   # catches some effect/collect misuse
```

Observable checks after the change:

- Rotate the device: one-shot events fire exactly once, state survives.
- Background the app (`adb -s <serial> shell input keyevent KEYCODE_HOME`) and watch Logcat: no collection
  or network call from the screen continues.
- Enable Layout Inspector → recomposition counts: scrolling a list must not increment the
  screen-level Composable's count.

## References

- `androidx.lifecycle:lifecycle-runtime-compose` — `collectAsStateWithLifecycle`
- Compose side-effects guide (developer.android.com) — effect naming only, not restated here
