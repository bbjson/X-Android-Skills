---
name: screenshot-testing
description: >-
  Add JVM-side screenshot regression tests for Compose screens so UI changes fail in CI instead
  of in review, and keep them deterministic. Use when adding Roborazzi/Roborazzi-style snapshot
  tests, a UI change needs visual proof, a screenshot test is flaky or all-green when it should
  not be, or a font/theme/locale change must be verified across configurations.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - android-skill (snapshot-tests)
    - chrisbanes/skills (compose-ui-testing-patterns)
    - compose-ai-tools (render-evidence)
    - awesome-android-agent-skills (android-testing)
---

# Screenshot Testing

A screenshot test is a claim about pixels. It is only worth having if it fails when the pixels
change and passes when they do not. Most snapshot suites fail the second half: they are
all-green because the state is empty or the render is unstable.

## Use when

- A screen, component, or design-system piece changes and review cannot prove it looks right.
- Setting up Roborazzi (JVM, no device) or an equivalent snapshot runner.
- A snapshot test is flaky, or it passes after an obvious visual regression.
- Verifying light/dark, RTL, font scale, or locale rendering.

## Do not use when

- The claim is about behaviour/interaction, not pixels → `compose-ui-testing`.
- The claim needs a real device compositor, camera, or gesture → `e2e-device-testing`.
- The screen is not stable enough to render deterministically yet → fix state first
  (`compose-state-effects`), then snapshot it.

## Rules

1. **Snapshot the state, explicitly.** Each test renders a *named* state: `Loading`, `Empty`,
   `Error(message)`, `Content(sampleData)`, plus the edge case that broke. A test that only
   renders `Content(emptyList())` cannot catch the bug.
2. **Deterministic inputs only.** Fixed `Locale`, `FontScale`, `density`, and a stub
   `Clock`/time source. No `System.currentTimeMillis()`, no `Random`, no real network, no
   animations left running.
3. **Disable animation before rendering.** `@Test` must set the animation scale off (or use a
   test rule / `ComposeUiTest` with animations disabled). A mid-animation capture is a flake.
4. **Load images synchronously or stub them.** Coil/Glide must be configured with a test
   `ImageLoader` that resolves deterministically; a real network image is a flake and a
   non-hermetic test.
5. **Record baselines deliberately, review them as pixels.** `record` mode output must be
   inspected in the PR diff. Never re-record to make a red test green without saying which
   pixels changed and why.
6. **One test per (state × configuration) that matters**, not a combinatorial explosion.
   Minimum set: dark/light, RTL if the app ships an RTL locale, largest font scale for text-heavy
   screens.
7. **Snapshot the smallest composable that owns the claim.** A whole-screen shot re-renders
   unrelated components and couples unrelated PRs.
8. **Keep the baseline in VCS, keep the runner JVM-only.** Device-rendered PNGs drift across
   GPU/API levels; JVM rendering (Roborazzi/`ComposeUiTest` with Robolectric) is stable enough to
   diff in CI.
9. **Fail on missing baseline, not silently skip.** A new test with no recorded image must be an
   error in CI, otherwise the suite decays into all-green nothing.

## Procedure

1. Add the runner and plugin versions via the catalog (`libs.plugins.roborazzi`, `libs.robolectric`).
2. Write the state matrix first:
   ```kotlin
   @Test fun feed_content_light() = capture("feed-content-light") { FeedScreen(FeedUiState.Content(sample)) }
   @Test fun feed_error_dark()  = capture("feed-error-dark")  { … }
   ```
3. `capture` sets qualifiers (`RobolectricDeviceQualifiers`), disables animations, stubs images.
4. Record once: `./gradlew :feature:feed:recordRoborazziDebug`.
5. Verify: `./gradlew :feature:feed:verifyRoborazziDebug`.
6. Sanity-check the test actually fails: change one padding value, run verify, expect red, revert.

## Checklist

- [ ] Each test names a UI state; loading/empty/error/content covered where applicable.
- [ ] Locale, font scale and density fixed per test; clock/time stubbed.
- [ ] Animations disabled; image loading stubbed.
- [ ] Baselines committed and reviewed as images in the PR.
- [ ] Missing baseline fails CI.
- [ ] `verify`, not `record`, runs in CI.
- [ ] Test proven to fail on a deliberate visual change.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| All-green forever | only `Content(emptyList())` snapshot | state matrix incl. error/edge | nothing to regress |
| Flaky by morning | animations + real clock | disable + stub | time and frames vary |
| Green after regression | re-record and move on | inspect diff, state the change | baseline drifts silently |
| Blame unrelated PRs | whole-screen snapshots | smallest owning composable | couples teams |
| Cross-host diffs | record on device, verify on CI | JVM rendering both sides | GPU/API differ |
| Missing baseline skipped | treat absent file as pass | fail | suite becomes vacuous |

## Verify

```bash
./gradlew :feature:feed:verifyRoborazziDebug
# deliberate regression check
sed -i 's/16.dp/24.dp/' src/main/kotlin/.../FeedScreen.kt
./gradlew :feature:feed:verifyRoborazziDebug   # must FAIL
git checkout src/main/kotlin/.../FeedScreen.kt
```

Expected: passes on unchanged code, fails on the one-value change, and the failure image shows
exactly that change.

## References

- Roborazzi — `captureRoboImage`, `recordRoborazziDebug` / `verifyRoborazziDebug`
- `ComposeUiTest` + Robolectric device qualifiers
