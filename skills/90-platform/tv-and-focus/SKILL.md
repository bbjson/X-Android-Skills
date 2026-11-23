---
name: tv-and-focus
description: >-
  Make a Compose UI usable without a touchscreen: D-pad and keyboard focus order, initial focus,
  focus restoration across navigation, Back semantics, and 10-foot layout for TV and desktop. Use when
  building for Android TV, adding keyboard/D-pad support, when focus jumps unpredictably or is lost on
  return, or when a control is reachable by touch but not by remote.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - chrisbanes/skills (compose-focus-navigation)
    - agent-skills-standard (android-compose)
    - awesome-android-agent-skills (android-accessibility)
    - kotlin-footguns (compose-screens-footguns)
---

# TV and Focus Navigation

On TV, desktop and with a keyboard, **focus is the cursor**. A control that cannot receive focus does
not exist, no matter how visible it is.

## Use when

- Building for Android TV or a 10-foot UI.
- Adding D-pad/keyboard support to an existing Compose screen.
- Focus jumps to an unexpected element, or disappears after navigation/back.
- A `clickable`/`pointerInput` control is unreachable by remote.
- Handling Back on TV (where it means "exit", not "up").

## Do not use when

- The concern is TalkBack semantics/roles → `compose-accessibility` (focus order appears there too, but
  this skill owns D-pad behaviour).
- The concern is responsive layout for big screens → `compose-core`.
- The app has no focus-relevant surface (single touch-only screen).

## Rules

1. **Every interactive element must be focusable.** `Modifier.clickable` provides focus; raw
   `pointerInput` does not. If you must keep the gesture, add `focusable()` + `onKeyEvent`.
2. **Author the initial focus.** `FocusRequester` + `LaunchedEffect(Unit) { requestFocus() }` on the
   element that makes sense (first item, or the previously focused one). Relying on the default
   initial focus is how a TV app opens with focus on the wrong control.
3. **Author the graph where visual order ≠ traversal order.** Use `Modifier.focusProperties { next/down/up = … }`
   for grids and carousels; automatic D-pad order follows layout, which is often wrong for 2D grids.
4. **Restore focus on return.** Remember the id of the last focused item and re-request it when the
   screen recomposes after back navigation. `FocusRequester` + a saved index in the state holder.
5. **`key()`/stable item keys plus `focusRestorer` for lists**: without stable keys, focus lands on a
   different item after data updates.
6. **Back on TV exits the app from the root screen.** Use `BackHandler` per screen for "up", and let the
   root screen allow the system Back to finish the activity. On phones, Back at root exits; on TV,
   users expect the same from a top-level screen, not an infinite "up" loop.
7. **Focus indication must be visible from 3 metres.** A 1dp outline is invisible: use a scale/colour/
   border change with the focus state, and never remove the default indication without a replacement.
8. **Disable touch-only gestures on TV builds** (swipe, long-press menus) or provide a D-pad path.
9. **Handle `KeyEvent` for media keys and menu** where the platform delivers them; do not intercept keys
   the system owns (Home/Back) without a reason.
10. **Layout for overscan safety:** keep interactive content within ~5% margins, and never place focusable
    items at the extreme edge (they get clipped or lose the focus halo).

## Procedure

1. Mark audit: list every interactive element and whether it has `clickable`/`focusable`.
2. Provide a `FocusRequester` for the intended initial element; request focus on first composition.
3. For each dimension where layout order differs from intended order, add `focusProperties`.
4. Add focus restoration: store last focused id/index in the state holder, re-request on return.
5. Add `BackHandler` per screen; leave the root screen's Back to the system.
6. Verify with a D-pad: traverse the whole screen, enter/exit every control, and return from a detail
   screen.
7. Verify the focus indication from a distance (screen recording at TV scale).

## Checklist

- [ ] Every interactive element is focusable (`clickable`/`focusable`).
- [ ] Initial focus explicitly requested.
- [ ] `focusProperties` authored where layout order ≠ intended order.
- [ ] Focus restored after back navigation and after data updates.
- [ ] Back on a root screen exits; per-screen `BackHandler` only for "up".
- [ ] Focus indication visible at TV viewing distance.
- [ ] No touch-only interaction without a D-pad equivalent.
- [ ] Content inside overscan-safe margins.
- [ ] Verified with a real D-pad traversal, not just visually.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Unreachable control | `pointerInput { detectTapGestures }` | `clickable` / `focusable` + `onKeyEvent` | no focus node |
| Focus on wrong item | rely on default | `FocusRequester` + request | unpredictable |
| Grid traversal sideways | automatic order | `focusProperties { down = … }` | layout ≠ intent |
| Focus lost on return | no restoration | save last id + re-request | users re-navigate |
| Back loops forever | `BackHandler` on root | root allows system Back | trapped user |
| Invisible focus | 1dp border | scale/colour + halo | 3 m distance |
| Edge clipping | items at 0dp margin | overscan margin | clipped focus halo |

## Verify

```bash
adb shell input keyevent KEYCODE_DPAD_DOWN
adb shell input keyevent KEYCODE_DPAD_RIGHT
adb shell input keyevent KEYCODE_ENTER
adb shell input keyevent KEYCODE_BACK
adb shell dumpsys window | grep -m1 mCurrentFocus    # focus target changes as expected
```

Expected: D-pad traversal visits every control in the intended order, Enter activates it, Back returns
to the previous screen with focus on the item you left, and Back on the root screen exits.

## References

- `FocusRequester`, `Modifier.focusProperties`, `Modifier.focusRestorer`, `BackHandler`
- Android TV overscan guidance; `androidx.tv` material for leanback replacements
