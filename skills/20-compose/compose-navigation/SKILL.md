---
name: compose-navigation
description: >-
  Choose and implement the navigation model for a Compose app: Navigation 3 state-driven back
  stack, or type-safe Navigation 2 routes with Kotlin serialization. Use when adding screens,
  passing arguments, handling deep links and App Links, scoping a ViewModel to a destination,
  restoring state after process death, or migrating away from string routes and NavController.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - agent-skills-standard (android-navigation-3, android-navigation-type-safe, android-navigation)
    - awesome-android-agent-skills (compose-navigation)
    - android-skill (migrate-nav3)
    - chrisbanes/skills (compose-focus-navigation)
---

# Compose Navigation

Navigation is state, not a controller call. Pick the model the project already uses, then keep
routes typed, back stack owned, and ViewModel scopes aligned with it.

## Use when

- Adding a destination, bottom-bar tab graph, nested graph, or dialog/sheet destination.
- Passing arguments (ids, filters, results back to a previous screen).
- Wiring deep links / App Links to a destination.
- A ViewModel leaks state between destinations, or is recreated on back navigation.
- Migrating string routes → typed routes, or Nav2 → Navigation 3.

## Do not use when

- The question is focus order for TV/keyboard → `tv-and-focus`.
- Sheer routing of skills, not app screens → `router`.

## Rules

1. **Never introduce a second navigation mechanism.** If the project uses Navigation 3, do not
   add `NavHost`; if it uses Nav2, do not add a `SnapshotStateList` back stack. Check the
   existing graph before writing anything.
2. **Arguments are typed values, never serialized strings.** Either a `@Serializable` route
   data class (Nav2 type-safe) or a `NavKey` (Nav3). No `"detail/{id}"` templates, no manual
   `arguments?.getString(...)`.
3. **The back stack is the only source of "where am I".** Do not mirror it into a ViewModel
   boolean or an enum; the two will diverge after process death.
4. **ViewModel scope follows destination identity.** Nav2: `viewModel()` inside the destination
   scope (use `hiltViewModel(navBackStackEntry)` — never the Activity-scoped one). Nav3: scope
   the ViewModel to the `NavEntry`, not to the composition.
5. **Results travel back through the back stack, not through a global singleton.** Nav2:
   `previousBackStackEntry.savedStateHandle`. Nav3: return value on the `NavKey`'s entry, or a
   state holder owned by the graph owner.
6. **A tab is a separate back stack, not a destination.** Switching tabs must restore that tab's
   stack (save/restore per tab). A single shared stack is the classic bottom-nav bug — Back
   walks across tabs.
7. **Deep links must resolve to the same route object the UI uses.** Parse the URI in one place
   (a mapper to `NavKey`/route) and reuse it for `navDeepLink`; do not duplicate the URI pattern.
8. **Every destination declares its animateIn/animateOut policy in one place** (graph-level
   defaults), so transitions do not drift screen by screen.
9. **Nested graphs express feature boundaries, not visual nesting.** A feature's graph should
   not appear in another feature's graph; navigate by route/key across boundaries.
10. **State restoration is part of the destination contract.** Any destination that can be
    restored from process death must rebuild from its arguments only — no reliance on a
    singleton's in-memory cache.

## Procedure

1. Detect the model in use:
   ```bash
   grep -rn "NavHost\|rememberNavController" --include=*.kt app/src | head
   grep -rn "navigation3\|NavDisplay\|NavBackStack" --include=*.kt app/src | head
   ```
   Mixed results = a half-finished migration; finish it before adding screens.
2. For Nav2 type-safe, declare routes:
   ```kotlin
   @Serializable data class Detail(val id: String, val tab: Int = 0)
   composable<Detail> { entry -> val route: Detail = entry.toRoute() }
   ```
3. For Nav3, declare keys:
   ```kotlin
   @Serializable data object Feed : NavKey
   @Serializable data class Detail(val id: String) : NavKey
   NavDisplay(backStack = rememberNavBackStack(Feed)) { entry -> when (val k = entry.key) { … } }
   ```
4. Put per-tab back stacks in the state holder that owns the tab selection.
5. Map deep links once, test with `adb shell am start -a android.intent.action.VIEW -d "<uri>"`.
6. Verify ViewModel scope by navigating A → B → back and asserting no re-fetch on return.

## Checklist

- [ ] Only one navigation API present in the module.
- [ ] All routes/keys are `@Serializable` types; no string templates.
- [ ] ViewModels scoped to the destination entry, not the Activity.
- [ ] Per-tab back stacks implemented and Back returns within the tab.
- [ ] Deep link patterns declared once and mapped to the same route object.
- [ ] Result-passing uses back-stack saved state / entry value, not a singleton.
- [ ] Process death restore verified (`adb shell am kill` then relaunch).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Wrong title after back | store current route in a ViewModel | read the top of the back stack | survives only by accident |
| Back crosses tabs | one shared back stack | per-tab `NavBackStack` | violates Android Back contract |
| Re-created ViewModel on return | `viewModel()` at Activity scope | destination-scoped entry | state lost or leaked |
| Duplicated deep link logic | URI string in manifest + route string in code | single mapper to route object | drift breaks links silently |
| Half migration | `NavHost` + `NavDisplay` in same app | finish migration in one change | two sources of truth for Back |
| Argument crash on restore | `getStringExtra("id")!!` | typed route, non-null by type | null after process death |

## Verify

```bash
./gradlew :app:assembleDebug
adb -s <serial> shell am start -a android.intent.action.VIEW -d "https://example.com/detail/42"
adb -s <serial> shell input keyevent KEYCODE_BACK
```

Expected: deep link lands on the detail screen with `id = 42`, Back returns to the tab stack it
came from, and rotating on the detail screen keeps the same instance.

## References

- `androidx.navigation3:navigation3-runtime` + `navigation3-ui` — `NavDisplay`, `NavKey`
- `androidx.navigation:navigation-compose` — `composable<T>`, `toRoute()`
