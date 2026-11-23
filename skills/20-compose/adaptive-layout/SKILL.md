---
name: adaptive-layout
description: >-
  Make one screen work from a phone in a small split window to a tablet, foldable or desktop
  window by deciding layout from the window size class instead of from the device or orientation.
  Use when adding a two-pane layout, supporting tablets/foldables/ChromeOS, removing a portrait
  lock, handling a fold or a resized window, or when a layout breaks in split-screen or landscape.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - android-developers (adaptive layouts + window size classes, re-expressed)
    - this-repo (gap analysis: WindowSizeClass absent from all 71 skills)
---

# Adaptive Layout

One decision: **layout is a function of the window it is drawn in.** The device model, the
orientation and the "is tablet" boolean are all proxies that are wrong in multi-window.

## Use when

- Building a list/detail, supporting-pane, or multi-column screen.
- Targeting tablets, foldables, ChromeOS or desktop windowing (Play has large-screen quality tiers).
- A layout breaks in split-screen, free-form windows, or landscape.
- The manifest locks orientation or sets `resizeableActivity="false"`.
- Handling a fold/hinge or a window that can be resized by the user.

## Do not use when

- TV, D-pad focus and 10-foot layout → `tv-and-focus`.
- Watch form factors → `wear-os`.
- Token layer (spacing, colour roles, typography scales) → `design-system`.
- Insets/edge-to-edge and system bar overlap after a targetSdk bump → `targetsdk-bump`.

## Rules

1. **Decide layout from a window size class, not from `orientation`, `smallestScreenWidthDp`, or a
   device-model check.** Use `currentWindowAdaptiveInfo()` (or `calculateWindowSizeClass` where the
   adaptive artifact is unavailable) and branch on compact/medium/expanded width.
2. **The breakpoints are the library's, not yours.** Thresholds around 600dp and 840dp width are
   what Material's scaffolds assume; inventing a 720dp breakpoint produces a layout that fights
   every component you use.
3. **Three layouts, not two.** Compact = single pane; medium = single pane with a navigation rail;
   expanded = list + detail. A boolean `isTablet` collapses medium back into phone behaviour.
4. **Use the pane scaffolds instead of hand-rolling two panes.** `ListDetailPaneScaffold` /
   `SupportingPaneScaffold` already handle the back stack, pane expansion and the fold.
5. **Navigation adapts with the window:** `NavigationSuiteScaffold` picks bottom bar / rail / drawer.
   Choosing the container once at app start and never re-evaluating is the same bug as rule 1.
6. **Detect a fold with `WindowInfoTracker`, and only split when `FoldingFeature.isSeparating`.** A
   non-separating fold (a crease) is not a layout boundary; splitting on it wastes the screen.
7. **Never lock orientation, and keep `resizeableActivity` enabled.** A portrait lock on a foldable
   or in desktop windowing makes the app unusable, and Play's large-screen checks flag it.
8. **Do not add `configChanges` to dodge recreation.** Swallowing `screenSize`/`orientation` stops
   resources and Compose's configuration reads from updating, which is a worse bug than recreation.
9. **State survives the size change**, because a resize *is* a configuration change: screen state in
   the ViewModel, transient UI state in `rememberSaveable` (`compose-state-effects`).
10. **Every screen is previewable at three sizes.** Add `@PreviewScreenSizes` (and a phone preview)
    to the screen composable; a layout that only has a default-size preview is unverified.
11. **Insets are resolved once at the scaffold, not per child.** Nested padding from
    `WindowInsets.safeDrawing` in several places double-pads on gesture navigation.
12. **Test the resize, not just the device:** resize the emulator window (or `adb shell wm size`)
    and verify no clipped content, no lost scroll position, no re-fetch.

## Procedure

1. Replace orientation/device checks with a size-class read at the screen's top level.
2. Choose the pane scaffold; move navigation into the suite scaffold.
3. Hoist list/detail selection into the ViewModel so both panes read one source.
4. Handle the fold only where `isSeparating` is true.
5. Add previews for compact/medium/expanded; verify a real resize.

## Checklist

- [ ] No `orientation`, `smallestScreenWidthDp` or device-model branch in layout code.
- [ ] Size class read from the adaptive API at the top of each screen.
- [ ] Medium has its own treatment (rail), not the phone layout.
- [ ] Pane scaffolds used; selection state hoisted.
- [ ] Fold handling gated on `isSeparating`.
- [ ] No orientation lock; `resizeableActivity` left enabled.
- [ ] No `configChanges` added for `screenSize`/`orientation`.
- [ ] Selection and scroll survive a resize.
- [ ] `@PreviewScreenSizes` plus phone preview present.
- [ ] Verified by resizing a running window, not only by reading code.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Broken in split-screen | `if (isTablet)` | size class of the window | device is not the window |
| Two panes on a phone | `screenWidthDp > 600` hardcoded per screen | one shared size-class read | inconsistent thresholds |
| Wasted foldable screen | split on any `FoldingFeature` | only `isSeparating` | a crease is not a boundary |
| Unusable on tablets | `screenOrientation="portrait"` | adaptive layout | violates large-screen expectations |
| Resources stale after resize | `configChanges="screenSize"` | let the activity recreate | configuration never updates |
| Detail lost on rotate | selection in composable-local state | ViewModel + `rememberSaveable` | state tied to composition |
| Double padding | insets applied per child | insets at the scaffold | nested inset handling |

## Verify

```bash
./gradlew :app:assembleDebug
adb -s <serial> shell wm size 2560x1600    # expanded window
adb -s <serial> shell wm size 1080x2340    # compact window
adb -s <serial> shell wm density 320
./gradlew :app:lintDebug 2>&1 | grep -iE 'LockedOrientation|UnsupportedChromeOsHardware'
```

Expected: the same activity renders single-pane then list+detail without a restart, selection and
scroll position persist across both sizes, and lint reports no locked-orientation or
large-screen-unsupported findings.

## References

- `currentWindowAdaptiveInfo()`, `WindowSizeClass`, `NavigationSuiteScaffold`
- `ListDetailPaneScaffold`, `SupportingPaneScaffold`
- `WindowInfoTracker`, `FoldingFeature.isSeparating`
- `@PreviewScreenSizes`, `@PreviewFontScale`
