---
name: nav2-to-nav3
description: >-
  Migrate a NavHost/NavController graph to Navigation 3's state-driven back stack: NavKey routes,
  NavDisplay, entry decorators for ViewModel and saved state, deep links, and transitions. Use when
  moving to Navigation 3, when a project mixes NavHost and NavDisplay, when ViewModels are recreated
  or leaked after the change, or when Back behaviour differs from the old graph.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - agent-skills-standard (android-navigation-3, android-navigation-type-safe)
    - android-skill (migrate-nav3)
    - awesome-android-agent-skills (compose-navigation)
    - agent-skills-standard (android-legacy-navigation)
---

# Navigation 2 to Navigation 3

The conceptual change: navigation stops being a **controller you call** and becomes **a list you own**.

| Nav2 | Nav3 |
|---|---|
| `NavController.navigate(route)` | `backStack.add(key)` |
| `NavHost(navController, start)` | `NavDisplay(backStack, …)` |
| `popBackStack()` | `backStack.removeLastOrNull()` |
| route `@Serializable` class | `NavKey` |
| `NavBackStackEntry` | `NavEntry` |
| graph DSL | explicit when/entry mapping |

## Use when

- Migrating an app/screen group to Navigation 3.
- A module now has both `NavHost` and `NavDisplay` (half-migrated).
- ViewModels are recreated on every navigation, or outlive their destination after the change.
- Back behaviour or deep-link handling differs from the old graph.

## Do not use when

- The project is staying on Navigation 2 and only needs type-safe routes → `compose-navigation`.
- The problem is deep-link verification → `deep-links`.
- The problem is a Compose state/effect issue → `compose-state-effects`.

## Rules

1. **Keys are `@Serializable` types implementing `NavKey`**, one per destination, not strings and not
   a sealed class hierarchy that depends on a nullable "current route". Arguments are `val` fields.
2. **The back stack is a `SnapshotStateList<NavKey>`** (usually `rememberNavBackStack(start)`), owned
   by the screen that hosts the `NavDisplay` — or by the app-level state holder if tabs need separate
   stacks. It must not live in a ViewModel that outlives it.
3. **Migrate a whole flow at once.** A screen that renders `NavDisplay` inside a `NavHost` destination
   has two navigation models and two Back implementations. Choose the flow boundary (usually a feature
   graph) and convert it completely.
4. **Entry decorators replace what NavHost did implicitly:** ViewModel scoping and saved state come
   from decorators (`rememberViewModelStoreNavEntryDecorator()`, and the saved-state decorator). Without
   them, `viewModel()` inside an entry is Activity-scoped or recreated.
5. **ViewModel scope = the `NavEntry`.** Use `entry`-scoped ViewModel lookups; do not call
   `viewModel()` from a composable that is not inside the entry's decoration, or you get the Activity's
   store.
6. **Back is a list operation, not a controller call.** Handle system Back by popping the list
   (`BackHandler(enabled = backStack.size > 1) { backStack.removeLastOrNull() }`), and let the root
   screen exit.
7. **Transitions are declared on the display**, not per screen: pass a transition spec to `NavDisplay`
   so every destination shares it. Per-screen overrides only for a documented exception.
8. **Deep links map to keys, once.** The URI → `NavKey` mapper is the same function for cold start and
   for an already-running app; buffer a cold-start link until the back stack exists (`deep-links`).
9. **The back stack must be restorable.** Keys are serializable, so save/restore the list (or rely on
   the saved-state decorator) — a back stack lost on process death returns the user to the start screen.
10. **Delete Nav2 once a flow is converted: no `NavHost`, no `navController`, no string routes in the
    same module.** Leaving both is the state that never gets finished.

## Procedure

1. Inventory: `grep -rn "NavHost\|navController\|composable<\|popBackStack" --include=*.kt .`
2. Convert routes: `@Serializable data class Detail(val id: String) : NavKey`; data objects for no-arg.
3. Create the back stack in the host: `val backStack = rememberNavBackStack(Feed)`.
4. Replace `NavHost` with `NavDisplay(backStack, entryDecorators = …, onBack = …) { entry -> when (val key = entry.key) { … } }`.
5. Replace `navigate(x)` with `backStack.add(x)`, `popBackStack()` with `removeLastOrNull()`.
6. Add entry decorators; verify ViewModel scope (leave/return, process death).
7. Map deep links to keys; test cold and warm.
8. Delete Nav2 imports/dependencies from the module.

## Checklist

- [ ] All keys `@Serializable` and implement `NavKey`; no string routes.
- [ ] Back stack is a `SnapshotStateList` owned by the host, not a long-lived ViewModel.
- [ ] The flow is fully converted: no `NavHost` left in the module.
- [ ] ViewModel and saved-state entry decorators applied.
- [ ] ViewModel scope is the entry (verified by navigation + process death).
- [ ] System Back pops the list; root exits.
- [ ] Transitions declared on the display.
- [ ] Deep links map to keys, cold and warm paths identical.
- [ ] Back stack restores after process death.
- [ ] Nav2 dependency removed from the converted module.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Two Back behaviours | `NavDisplay` inside `NavHost` | convert the whole flow | two stacks |
| VM leaks across screens | `viewModel()` outside entry decoration | entry-scoped lookup | Activity store |
| VM recreated on return | no ViewModel decorator | add decorator | new store per entry |
| Back stack lost | list in memory only | save/restore list | returns to start |
| Inconsistent motion | per-screen transitions | display-level spec | drift |
| Dead routes | keep Nav2 imports "for now" | delete after flow | never finished |

## Verify

```bash
./gradlew :app:assembleDebug
grep -rn "NavHost\|navController" --include=*.kt app/src/main   # empty for converted flows
adb -s <serial> shell am force-stop <pkg> && adb -s <serial> shell am start -n <pkg>/.MainActivity
adb -s <serial> shell input keyevent KEYCODE_BACK
```

Expected: navigating into a detail screen and pressing Back returns to the same list position with the
same ViewModel instance; killing the process and relaunching restores the back stack rather than the
start screen; a deep link lands on the intended key.

## References

- `androidx.navigation3:navigation3-runtime` (`NavKey`, `NavBackStack`), `navigation3-ui` (`NavDisplay`)
- Entry decorators for ViewModel store and saved state
