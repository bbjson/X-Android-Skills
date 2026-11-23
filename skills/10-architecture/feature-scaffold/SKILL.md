---
name: feature-scaffold
description: >-
  Create a new feature end to end — packages or modules, contract types, DI binding, navigation
  registration, screen skeleton and test stubs — so that the first commit is reviewable and the
  feature is wired the way the project already works. Use when starting a new feature, splitting a
  screen into its own module, adding a destination, or when a half-scaffolded feature has files in
  the wrong layers.
license: Apache-2.0
metadata:
  domain: architecture
  level: core
  sources:
    - android-skill (new-feature, compose-screen)
    - mobile-agent-skillpack (android-compose-feature-delivery, mobile-modern-clean-architecture)
    - agent-skills-standard (android-architecture)
    - android-agent-engineering (workflows/implement)
---

# Feature Scaffold

Scaffolding is **copying the project's existing shape**, not applying a template from a blog post.
The deliverable is a compiling feature with one visible screen, one real state and one real test.

## Use when

- Starting a new feature or a new screen that will grow.
- Moving an existing screen into its own module.
- Adding a navigation destination.
- A feature's files are scattered across layers with no ownership.

## Do not use when

- The feature is a one-file change → just do it.
- The layer ownership question is unresolved → `layering` first.
- The module count question is unresolved → `modularization` first.

## Rules

1. **Find the closest existing feature and copy its shape.** Same package layout, same naming, same
   test locations, same convention plugins. Introducing a second pattern doubles maintenance for
   zero benefit.
2. **Decide module vs package by the project's existing threshold, not by ambition.** If the project
   has 4 features and none is a module, a new module is a decision to raise the threshold for
   everything — do that intentionally or not at all.
3. **Scaffold in this order:** contract types → repository/DI → state holder → screen →
   navigation registration → tests. Each step compiles.
4. **Ship one real slice, not five empty ones.** A feature with three empty screens and no data path
   cannot be reviewed or tested. One screen that loads real (or faked) data end to end is a feature;
   the rest are placeholders that will be rewritten.
5. **Every feature owns its navigation entry point and its state type.** The app module wires the
   destination; the feature exposes `fun Destination(nav: …)` or a `NavKey`, not a `NavHost`.
6. **Register DI in the feature's own module, not in the app's.** A feature that adds its bindings to
   a shared module creates a merge conflict for every parallel feature.
7. **Test stubs are created now, not later.** One ViewModel test (state transitions), one screen test
   (renders a state), one mapper/repository test if there is data. Empty `@Test` bodies are
   acceptable in the first commit only if they are listed as remaining work.
8. **No feature-specific string/dimension/colour literals.** Resources and tokens from the start;
   retrofitting them is the most-mechanical, least-enjoyable work and gets skipped.
9. **The scaffold must build and run on a device before any further feature code.** `assembleDebug`
   green + screen reachable by navigation is the definition of a done scaffold.
10. **Delete the template artefacts you did not use.** Leftover sample code from a copied feature is
    how projects accumulate dead classes nobody dares delete.

## Procedure

1. Identify the reference feature (`git log --diff-filter=A -- '*Feature*'` or the newest one).
2. Copy its directory layout; rename; delete sample-specific code (rule 10).
3. Write contract types: route/args, `UiState`, events.
4. Add repository function + DI binding in the feature's own module.
5. Write the state holder with a single `stateIn` (see `state-holders`).
6. Write the screen as `Screen(uiState, onEvent)` (see `compose-core`).
7. Register the destination in the app's nav graph (see `compose-navigation`).
8. Add test stubs at the paths the reference feature uses.
9. Build, install, navigate to the screen.

## Checklist

- [ ] Shape copied from the closest existing feature; no new pattern introduced.
- [ ] Module-vs-package decision matches the project's current threshold.
- [ ] Contract types written before implementation.
- [ ] DI binding lives in the feature's own module.
- [ ] Screen is `Screen(uiState, onEvent)`, previewable without DI.
- [ ] Destination registered in the app graph; feature does not own a `NavHost`.
- [ ] Test stubs exist at the project-standard paths.
- [ ] Strings/dimensions from resources and tokens.
- [ ] `assembleDebug` green and screen reachable on a device.
- [ ] Copied sample code removed.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Two conventions | new feature uses a different layout | copy the existing shape | maintenance doubles |
| Merge conflicts | DI in `app/AppModule.kt` | feature's own module | every feature edits one file |
| 5 empty screens | scaffold all destinations | one real slice | unreviewable, untestable |
| Unreachable screen | destination registered later | register in the scaffold commit | no end-to-end proof |
| Literal retro | hardcoded strings "temporarily" | resources now | cleanup never happens |
| Dead sample code | leftover `TodoList` classes | delete immediately | permanent dead weight |
| Untestable feature | ViewModel inside the screen | `Screen(uiState, onEvent)` | no preview, no test |

## Verify

```bash
./gradlew :feature:x:assembleDebug
./gradlew :feature:x:testDebugUnitTest
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -W -n <pkg>/.MainActivity   # navigate to the new destination
```

Expected: the feature compiles independently, its test task runs, and the screen is reachable through
normal navigation without touching a debug entry point.

## References

- `layering` — which package each new type belongs to
- `state-holders` — the state holder this scaffold creates
- `compose-navigation` — destination registration
