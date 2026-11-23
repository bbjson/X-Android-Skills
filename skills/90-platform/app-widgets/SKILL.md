---
name: app-widgets
description: >-
  Build a home-screen widget that renders from persisted state, updates on real data changes and
  survives being resized, themed and re-added. Use when adding a widget or Glance surface, when a
  widget shows stale data, when taps open the wrong screen, when it looks broken after resize or in
  dark mode, or when deciding between updatePeriodMillis and pushed refresh.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - android-developers (app widgets + Glance, re-expressed)
    - this-repo (gap analysis: widgets absent; Wear tiles only)
---

# App Widgets

One decision: **the widget is a stateless render of persisted state.** It has no live process, no
listeners and no reliable update schedule; every pixel it shows must already exist in storage.

## Use when

- Adding a home-screen widget, a Glance surface, or a quick-action widget.
- A widget shows stale content, or updates only when the app is opened.
- A widget tap opens the wrong screen or a duplicate activity.
- A widget is clipped, ugly or unreadable after resize, rotation, or in dark mode.
- Deciding how often to refresh without waking the device.

## Do not use when

- Wear OS tiles and complications → `wear-os`.
- Notification content and channels → `notifications-fcm`.
- The background job that produces the data → `background-work`.
- Real-time UI while the app is open → `compose-core`.

## Rules

1. **The widget reads persisted state and renders it; it never fetches synchronously.** Rendering
   happens in a broadcast-driven callback with a short budget — a network call there is an ANR.
2. **Refresh is pushed from the data change, not pulled on a timer.** Trigger `updateAll`/`update`
   after the sync or write that changed the data; treat `updatePeriodMillis` as a low-frequency
   safety net with a minimum interval of about half an hour.
3. **`updatePeriodMillis` is not a scheduler.** It cannot be shorter than the platform minimum, it
   does not fire in Doze, and it fires even when nothing changed. Anything time-critical belongs to
   an alarm or a pushed refresh (`background-work`).
4. **Declare the size contract and honour it.** `minWidth`/`minHeight`, `targetCellWidth`/`targetCellHeight`,
   `resizeMode`, and in Glance a `SizeMode` with explicit breakpoints — a widget designed for one
   size is clipped on another launcher.
5. **Every interactive element has its own immutable `PendingIntent` with a unique request code.**
   Reusing one request code makes every button open the same screen; a mutable intent is a
   vulnerability.
6. **Deep-link taps to the right destination with the right back stack**, not to a bare launcher
   activity (`deep-links`, `compose-navigation`).
7. **Handle the three empty states:** no data yet, permission missing, and data stale. A blank
   widget is indistinguishable from a broken one.
8. **Theme by configuration, not by assumption.** Read dark/light from the device configuration and
   use the design-system tokens; hardcoded colours look broken on a themed launcher.
9. **Long work goes to `WorkManager` from the callback, and the widget updates when that work
   finishes.** Refresh actions must tolerate being cancelled.
10. **Widget state is keyed per widget id** when several instances can show different content
    (different account, different filter). One global blob makes two widgets identical.
11. **Test on a real launcher, resized, in both themes, and after a reboot** — the widget host
    restores from its own snapshot, and a widget that only works in the emulator's host is a
    hypothesis.

## Procedure

1. Persist the state the widget renders; define the "no data" representation.
2. Write the receiver/provider and the render code with size breakpoints and theme tokens.
3. Wire refresh to the data-change path; add `updatePeriodMillis` as a safety net.
4. Add one immutable `PendingIntent` per action with unique request codes and deep links.
5. Resize, theme-switch, reboot and re-add the widget on a real launcher.

## Checklist

- [ ] Widget renders only persisted state; no network in the render callback.
- [ ] Refresh pushed from the data change; `updatePeriodMillis` only a fallback.
- [ ] Size contract declared; breakpoints for small/large.
- [ ] One immutable `PendingIntent` per action, unique request code.
- [ ] Taps deep-link to the correct destination with a sane back stack.
- [ ] Empty / permission-missing / stale states rendered differently.
- [ ] Theme read from configuration; tokens not literals.
- [ ] Long work delegated to `WorkManager`; refresh tolerates cancellation.
- [ ] Per-widget state keyed by widget id where instances differ.
- [ ] Verified on a real launcher: resized, dark mode, reboot, re-add.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Widget frozen until app opened | rely on `updatePeriodMillis` | push update after data change | timer is a fallback |
| ANR on refresh | network call in `onUpdate` | `WorkManager` + update on finish | broadcast budget |
| All buttons open one screen | shared request code | unique per action | PendingIntent reuse |
| Clipped on one launcher | one fixed size | size contract + breakpoints | host sizes vary |
| Unreadable in dark mode | hardcoded colours | configuration-aware tokens | themed launchers |
| Blank = broken | no empty state | explicit empty/stale states | user cannot tell |
| Two widgets identical | one global state blob | state keyed by widget id | instances differ |

## Verify

```bash
./gradlew :app:assembleDebug
adb -s <serial> shell dumpsys appwidget | grep -c '<pkg>'   # expected: >= 1 instance
adb -s <serial> shell am broadcast -a android.appwidget.action.APPWIDGET_UPDATE -n <pkg>/.<widget-receiver>
adb -s <serial> shell cmd uimode night yes     # then night no
adb -s <serial> reboot
```

Expected: `dumpsys appwidget` lists the widget instance after reboot, a data change updates the
widget without opening the app, taps land on the intended destination, and the widget is legible in
both themes at two sizes.

## References

- `GlanceAppWidget`, `GlanceAppWidgetReceiver`, `provideGlance`, `updateAll`, `SizeMode`,
  `actionStartActivity`, `ActionCallback`
- `appwidget-provider` attributes: `minWidth`, `minHeight`, `targetCellWidth`, `resizeMode`,
  `updatePeriodMillis`
- `PendingIntent.FLAG_IMMUTABLE`, unique request codes
