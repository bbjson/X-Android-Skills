---
name: wear-os
description: >-
  Build or migrate a Wear OS app with Wear Compose Material 3: scaling lists, app scaffold, ambient
  mode, battery discipline, and phone–watch data sync. Use when creating a Wear module, porting a phone
  screen to a watch, adding tiles or complications, wiring the Data Layer API, or when a watch app
  drains battery or looks wrong on round screens.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - android-skill (wear-compose)
    - agent-skills-standard (android-compose)
    - android-agent-engineering (android-testing)
    - kotlin-footguns (state-and-background-footguns)
---

# Wear OS

A watch is not a small phone. The two decisions this skill makes: **what fits on one glance, and what
runs while the screen is off.**

## Use when

- Creating a Wear module or migrating from `androidx.wear:wear` (Views) to `wear-compose-material3`.
- Porting a phone screen to a watch face or app.
- Adding a tile, complication, or ongoing activity.
- Syncing data between phone and watch (`MessageClient`/`DataClient`).
- The app drains battery in ambient mode or on standby.

## Do not use when

- The task is a phone UI that happens to be small → `compose-core` + responsive layout.
- The task is notifications on the phone → `notifications-fcm`.
- The task is a watch **face** (a different surface with its own APIs) — out of scope here.

## Rules

1. **Use Wear Compose Material 3, not the phone Material 3 components.** `androidx.wear.compose:compose-material3`
   provides `Scaffold`, `Button`, `Chip`, `TimeText` with watch sizing and semantics.
2. **Always wrap scrolling content in `ScalingLazyColumn`** (not `LazyColumn`) so the first and last
   items scale in/out instead of clipping; add `PositionIndicator` so the user sees where they are.
3. **Design for the round screen first.** Keep the central content inside the inscribed square, handle
   `chipless`/chin devices, and avoid anything anchored to a corner.
4. **Ambient mode is a separate rendering path.** In ambient, use black background (OLED power), no
   animation, minimal updates, and `AmbientLifecycleObserver` to know when to switch. A watch face that
   animates in ambient drains the battery and can be rejected for burn-in.
5. **Assume the screen turns off constantly.** Persist state with `rememberSaveable` + Data Layer / Data
   Store; do not rely on in-memory state surviving a wrist-down.
6. **Battery: no polling.** Use `MessageClient` for fire-and-forget, `DataClient` for synced key-value,
   and `WorkManager`/Ongoing Activity for long tasks. A 1-second timer is a battery bug.
7. **Data Layer sync is asynchronous and eventually consistent.** Handle the case where the phone is
   absent (queued capability message, local-first cache), and never block the UI on a sync result.
8. **One action per screen.** Watch interactions are 1–2 taps; a form with three fields belongs on the
   phone with a "continue on phone" handoff.
9. **Test on the smallest and largest watch sizes, and in ambient mode.** A layout that fits a 41 mm
   round device will clip on a smaller one; ambient mode hides content you thought was visible.
10. **Notification, tile and complication are three different surfaces.** Do not reuse a Compose screen
    for a tile — tiles have a fixed slot layout and no scrolling.

## Procedure

1. Create the module with the Wear target and Wear Compose Material 3 (version from the catalog).
2. Build the screen with `Scaffold` + `TimeText` + `ScalingLazyColumn` + `PositionIndicator`.
3. Add `AmbientLifecycleObserver` and an ambient rendering branch (rule 4).
4. Wire data via Data Layer client; cache locally; handle "phone not reachable".
5. Add a tile/complication only if the information is glanceable in one slot.
6. Verify on a round emulator at 2 sizes, plus ambient.

## Checklist

- [ ] Wear Compose Material 3 components used, not phone Material 3.
- [ ] All scrollable content in `ScalingLazyColumn` with a `PositionIndicator`.
- [ ] Layout survives the smallest round screen and a chin device.
- [ ] Ambient rendering path exists (black, static, minimal updates).
- [ ] State survives screen-off (`rememberSaveable` / persistent store).
- [ ] No polling loops; Data Layer / WorkManager used instead.
- [ ] Phone-absent path handled with a local cache.
- [ ] One primary action per screen.
- [ ] Tiles/complications use their own layout APIs.
- [ ] Verified on two watch sizes + ambient mode.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Content clipped | `LazyColumn` | `ScalingLazyColumn` | no edge scaling |
| Corner content lost | corner-anchored layout | inscribed-square content | round bezel |
| Battery drain | 1s polling timer | Data Layer events / WorkManager | constant wakeups |
| Burn-in / rejected | animation in ambient | static ambient branch | OLED power + policy |
| Lost state | in-memory only | `rememberSaveable` + store | screen off constantly |
| Unusable UI | phone form on watch | one action + handoff | 1–2 taps |
| Blank tile | reuse Compose screen | tile slot API | no scrolling in tiles |

## Verify

```bash
./gradlew :wear:assembleDebug
adb -s <wear-serial> install -r wear/build/outputs/apk/debug/wear-debug.apk
adb -s <wear-serial> shell am start -n <pkg>/.MainActivity
adb -s <wear-serial> shell dumpsys batterystats | head -30
```

Expected: the screen renders fully on a round 41 mm profile, ambient mode shows a static minimal
layout, and a wrist-down/up cycle restores the same screen state.

## References

- `androidx.wear.compose:compose-material3` — `Scaffold`, `ScalingLazyColumn`, `TimeText`
- `AmbientLifecycleObserver`, Wear Data Layer (`MessageClient`, `DataClient`)
