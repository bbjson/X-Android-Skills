---
name: compose-ui-testing
description: >-
  Test Compose UI through semantics the user can perceive — text, content description, role —
  not through internal state, tags on every node, or sleeps. Use when adding interaction tests
  for a screen or component, when a Compose test is flaky or passes with broken UI, when
  deciding testTag strategy, verifying `rememberSaveable` restoration, or testing a list, dialog,
  snackbar, or async-loaded content.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - chrisbanes/skills (compose-ui-testing-patterns)
    - agent-skills-standard (android-testing)
    - android-skill (write-tests)
    - awesome-android-agent-skills (android-testing)
---

# Compose UI Testing

A Compose test drives the same semantics tree accessibility services use. If a test cannot find
your content, a screen reader cannot either — that is the useful side effect of doing this right.

## Use when

- Testing click/input/navigation feedback on a screen or component.
- A Compose test is flaky, hangs on `waitForIdle`, or passes while the UI is visibly broken.
- Choosing between `onNodeWithText`, `onNodeWithContentDescription`, and `onNodeWithTag`.
- Verifying state survives rotation (`StateRestorationTester`).
- Testing lists, dialogs, snackbars, or content loaded asynchronously.

## Do not use when

- The claim is about pixels/appearance → `screenshot-testing`.
- The logic under test is a ViewModel/flow → `unit-testing`.
- The claim requires a real device, real network, camera, or cross-app flow → `e2e-device-testing`.

## Rules

1. **Find by what the user perceives, in this order:** `onNodeWithText` →
   `onNodeWithContentDescription` → `onNodeWithRoleAnd…` → `onNodeWithTag`. A tag is a fallback
   for nodes with no accessible meaning (custom canvas, chart), not the default.
2. **`testTag` is a public API of the screen.** Name it `<screen>.<element>` (`feed.list`,
   `feed.retry`) and keep it stable — tests and (potentially) other teams depend on it. Do not
   generate tags in loops with indices when the semantic identity is data.
3. **Assert visible state, not internal state.** `onNodeWithText("Retry").assertIsDisplayed()`
   beats reaching into a ViewModel. If the assertion needs a ViewModel, the claim belongs in
   `unit-testing`.
4. **`useUnmergedTree = true` only when necessary**, and justify it: it bypasses the merged
   semantics the user actually gets. Usually the fix is to give the parent a `contentDescription`.
5. **Never `Thread.sleep`.** Use `waitUntil { }` on a condition or rely on `waitForIdle` after an
   action; compose test rules synchronise with the composition clock. For a suspend load, drive
   the fake to completion, don't wait on wall time.
6. **Disable animations in the test rule** (`mainClock.autoAdvance` policy or animation scale off)
   so transitions do not race assertions.
7. **Provide the state explicitly.** Render `Screen(uiState = Loading)`, `Error(msg)`,
   `Content(sample)`; never let the test depend on a production default, network, or clock.
8. **`StateRestorationTester` for `rememberSaveable` claims.** `emulateSavedInstanceStateRestore()`
   then assert the restored value — this is the only way to catch the classic "lost on rotation".
9. **Scroll/act by semantic action, not coordinates.** `performScrollToIndex`, `performClick`,
   `performTextInput`. Coordinates encode device geometry and break on other densities.
10. **One test per behaviour + state pair.** Testing every state of every element produces a slow
    suite nobody reads; test the transition the feature owns.
11. **Assert absence explicitly.** `assertDoesNotExist()` on the error banner after retry is a
    real claim; most "it works" tests only assert presence and miss stale UI.

## Procedure

1. Give the screen a `@Composable` that takes its `UiState` — this is what you test (rule 7).
2. Write the interaction:
   ```kotlin
   composeRule.onNodeWithText("Retry").performClick()
   composeRule.onNodeWithText("Loaded 3 items").assertIsDisplayed()
   ```
3. For lists: `onNodeWithTag("feed.list").performScrollToIndex(19)` then assert the item.
4. For async: inject a fake that emits synchronously; assert the resulting node.
5. For restoration: wrap in `StateRestorationTester(composeRule)`, set state, restore, assert.
6. Run, then break the behaviour and confirm red.

## Checklist

- [ ] Every finder uses text/contentDescription unless a documented tag exception applies.
- [ ] Tags follow `<screen>.<element>` and are stable.
- [ ] No `Thread.sleep`; no wall-clock waits.
- [ ] Animations disabled; mainClock handled.
- [ ] Each test renders an explicit `UiState`.
- [ ] Absence asserted where stale UI is the risk.
- [ ] `StateRestorationTester` used for any `rememberSaveable` claim.
- [ ] `useUnmergedTree` absent or justified inline.
- [ ] Test proven to fail on broken behaviour.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Green with broken UI | assert on ViewModel state | assert node displayed/absent | bypasses rendering |
| Flaky | `Thread.sleep(1000)` | `waitUntil { nodeExists() }` | races the clock |
| Tag soup | `testTag = "item$i"` everywhere | text/role first | tags hide a11y gaps |
| Rotation bug ships | never test saveable | `StateRestorationTester` | only way to catch it |
| Passes on one device | `click(Offset(x, y))` | `performClick()` on the node | density-dependent |
| Hangs | `waitForIdle` with infinite animation | disable animations | never idles |

## Verify

```bash
./gradlew :feature:feed:testDebugUnitTest --tests '*FeedScreenTest*'
./gradlew :feature:feed:connectedDebugAndroidTest     # instrumented variant
```

Then comment out the onClick handler and confirm the assertion of the resulting UI fails.

## References

- `androidx.compose.ui.test` — `onNodeWith*`, `performScrollToIndex`, `StateRestorationTester`
- Semantics merging: `Modifier.semantics(mergeDescendants = true)`
