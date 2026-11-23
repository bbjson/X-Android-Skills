---
name: view-ui-testing
description: >-
  Test View-based screens with Espresso and UI Automator: real user-facing selectors, explicit
  synchronisation instead of sleeps, adapter scrolling, idling resources, and system dialogs.
  Use when a screen is still XML/Fragment based, when an instrumented test is flaky or passes on a
  broken UI, when a test must dismiss a system permission dialog, or when migrating test coverage
  from a View screen to Compose.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - android-developers (Espresso + UI Automator guides, re-expressed)
    - this-repo (gap analysis: quality domain covered only Compose UI tests)
---

# View UI Testing

One decision: **the test asserts what a user can perceive, and it waits on a signal — never on a
duration.** A View test that needs `Thread.sleep` is a test that has not found its idle signal yet.

## Use when

- Adding instrumented tests to a Fragment/Activity screen or a custom `View`.
- A test passes while the UI is visibly broken, or fails only on CI/slow devices.
- A flow must dismiss a system dialog (permission, chooser) or navigate outside the app.
- Writing a migration test as a regression net before converting XML to Compose.
- A `RecyclerView` list must be scrolled to reach an item.

## Do not use when

- The UI is Compose-native → `compose-ui-testing`.
- The test spans app → system → notification → deep link → app → `e2e-device-testing`.
- Pure JVM logic (ViewModel, mapper, repository) → `unit-testing`.
- Pixel comparison of a rendered screen → `screenshot-testing`.
- Driving the device from a shell script rather than a test → `adb-automation`.

## Rules

1. **Select by what the user sees** — `withText`, `withContentDescription`, `withHint` — and use
   `withId` only for containers that have no text. An id-only suite survives a redesign of the UI
   it was supposed to protect.
2. **Every wait is an idle signal.** Compose/Espresso wait for the main looper; anything asynchronous
   (network fake, image loader, timer, `WorkManager`) needs an `IdlingResource` or a synchronous
   fake. `Thread.sleep` and retry loops hide the race they should expose.
3. **Disable animations on the device, not in the test.** Set the three animation scales to zero via
   `adb shell settings put global ...`; a test that fights animations is a test with a timeout bug.
4. **`ActivityScenario`/`FragmentScenario` own the lifecycle.** Use them to drive `onResume`/recreate
   rather than launching activities directly; a scenario that is not closed leaks state into the
   next test.
5. **RecyclerView assertions scroll explicitly** (`RecyclerViewActions.scrollToPosition` /
   `scrollToHolder`), then assert. Asserting on an off-screen item works only by accident.
6. **System UI is UI Automator's job.** A permission or chooser dialog belongs to the system process;
   `UiDevice`/`UiObject2` clicks it with a timeout, then the test returns to Espresso.
7. **Assert state, not just presence.** "The button exists" passes on a button that does nothing;
   assert the resulting text, the enabled state, or the persisted value.
8. **One scenario per test, and each test starts from a known data state** (fresh database or
   `clearPackageData`, fake clock, fixed locale and font scale).
9. **Custom matchers over `allOf(withId, withText)` repetition** for recurring structures (list item
   by title, error banner). A matcher that appears five times is a missing matcher.
10. **`IdlingResource` is registered in `@Before` and unregistered in `@After`**, and production code
    exposes the counting hook through an injectable seam — not a static flag the release build also
    carries.
11. **Mixed hierarchies are asserted with the tool that owns each node**: Compose nodes via
    `onNodeWithTag`, `View` nodes via `onView`. An Espresso query cannot see a Compose node and vice
    versa; a failing "not found" is usually this, not a missing element.
12. **A test that cannot fail is deleted.** Break the UI deliberately once (remove the text, disable
    the button) and confirm the test goes red before trusting it.

## Procedure

1. Add the fake seams (fake repository, counting idling resource, fixed clock) before writing assertions.
2. Write the happy path with text/description selectors.
3. Add one failure path per screen (empty, error, offline).
4. Register/unregister idling resources; disable animations in the CI script.
5. Run each test against a deliberately broken build once.

## Checklist

- [ ] Selectors are user-visible text/descriptions; ids used only where necessary.
- [ ] No `Thread.sleep`, no retry loops, no `SystemClock` polling in the test.
- [ ] Idling resources registered and unregistered around each test.
- [ ] Animations disabled at the device level in the run script.
- [ ] Scenarios closed; no activity launched outside a scenario.
- [ ] List assertions scroll first.
- [ ] System dialogs handled by UI Automator with an explicit timeout.
- [ ] Assertions check resulting state, not just element presence.
- [ ] Data state reset per test (database, injector, fake server).
- [ ] Each test observed failing against a deliberately broken UI.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Passes with a broken screen | only `withId` selectors | text/description assertions | ids survive a UI change |
| Flaky on CI only | `Thread.sleep(1000)` | `IdlingResource` | timing assumption |
| Never finds element | Espresso query on a Compose node | `onNodeWithTag` | different node trees |
| Dialog blocks test | clicking by coordinates | UI Automator with timeout | system process owns it |
| Off-screen assertion | `onView(...).check` directly | scroll then check | item not composed/attached |
| State leaks between tests | shared app process | fresh data per test | order-dependent results |

## Verify

```bash
adb -s <serial> shell settings put global window_animation_scale 0
adb -s <serial> shell settings put global transition_animation_scale 0
adb -s <serial> shell settings put global animator_duration_scale 0
./gradlew :app:connectedDebugAndroidTest
```

Expected: instrumented tests pass repeatedly (three consecutive runs, no ordering dependence) with
animations disabled, and each test fails when its assertion target is deliberately broken.

## References

- Espresso `onView`, `onData`, `IdlingResource`, `RecyclerViewActions`
- `ActivityScenario`, `FragmentScenario`, Android Test Orchestrator
- UI Automator `UiDevice`, `UiObject2`, `Until`
