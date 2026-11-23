---
name: targetsdk-bump
description: >-
  Raise targetSdk by one platform level without discovering the behaviour changes in production:
  read every skipped level's changes, fix insets, back handling, permissions and service types,
  then verify on the new level and one older device. Use when the yearly platform release arrives,
  when Play requires a target date, when edge-to-edge or predictive back breaks the UI, or when an
  upload is rejected for targetSdk.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - android-developers (behaviour changes per release, re-expressed)
    - this-repo (gap analysis: no yearly platform-adaptation skill)
---

# targetSdk Bump

One decision: **targetSdk is a contract you renew yearly, one level at a time, with a device matrix
on both sides.** Skipping levels turns three small migrations into one unattributable breakage.

## Use when

- The yearly platform release arrives, or Play's target API requirement has a deadline.
- An upload is rejected for `targetSdkVersion`.
- Raising targetSdk broke edge-to-edge layout, back navigation, notifications or a service.
- A project is several levels behind and needs a plan.

## Do not use when

- AGP/Gradle/Kotlin version upgrades → `agp9-migration`, `kotlin-toolchain`.
- Insets and adaptive layout design in general → `adaptive-layout`.
- Permission UX design beyond the platform change → `permissions-and-pickers`.
- Background execution mechanism choice → `background-work`.

## Rules

1. **One level per cycle, never several at once.** Each level owns a set of behaviour changes; a
   multi-level jump makes a regression unattributable and the fix becomes guesswork.
2. **Read the behaviour-changes list for *every* level between the current and the target**, not
   only the newest — behaviour changes apply to apps targeting that level and above, so skipped
   levels still bite.
3. **`compileSdk` goes to the target first and builds green before any behaviour work starts.**
   Compiling against the new SDK surfaces removed APIs at the cheapest possible moment.
4. **Edge-to-edge is a layout migration, not an attribute.** Do not rely on the opt-out: make the
   app draw behind system bars deliberately, consume insets at the scaffold, and verify with gesture
   navigation *and* three-button navigation.
5. **Back is state, not an activity finish.** Migrate `onBackPressed` overrides to
   `OnBackPressedCallback`/`BackHandler`, make predictive back not skip animations, and ensure the
   back stack is owned by navigation, so the new gesture does not close the app from a sub-screen.
6. **Every new runtime permission is requested at the point of use**, with a denial path; a target
   bump that adds a permission without UX is a silently dead feature (`permissions-and-pickers`).
7. **Foreground services declare a type and its permission, and the type matches the work.**
   Types have different time budgets; a long-running job that no longer fits must move to
   `WorkManager` or be reclassified.
8. **Exact alarms become a user-granted capability.** Provide an inexact fallback and a settings
   path instead of assuming the grant.
9. **`registerReceiver` calls declare the exported flag.** A non-system broadcast without it throws
   at runtime, usually on a background code path nothing tests.
10. **Native libraries must be rebuilt for the current page-size requirement**, and any prebuilt
    `.so` that cannot be rebuilt is a blocker to shipping, not a warning (`ndk-jni`).
11. **Restricted settings on sideloaded installs** mean accessibility and notification-listener
    access require an extra user step; deep-link to the right settings screen and explain it.
12. **Verify on both sides of the change:** a device on the new level and one on the previous level.
    Toggling individual behaviour changes with `am compat` is faster than a full device matrix, but
    it is not a substitute for one real run on each.
13. **Keep a written record of each level's changes and the commit that addressed it**, so the next
    bump starts from evidence instead of archaeology.

## Procedure

```bash
# 1. reveal the work before changing anything
./gradlew :app:lintDebug                  # NewApi / Deprecated / ExpiredTargetSdkVersion
grep -rn 'targetSdk\|compileSdk' --include=*.kts --include=*.toml . | head
```

2. Raise `compileSdk` to the new level; fix removed APIs until the build is green.
3. Read the behaviour-changes list for each skipped level; turn it into a checklist on the PR.
4. Fix insets/edge-to-edge, then back handling, then permissions, then service types/alarms.
5. Run the smoke matrix: new-level device, previous-level device, and a minSdk device.
6. Raise `targetSdk`; keep the commit separate from step 2 so a bisect can tell them apart.

## Checklist

- [ ] `compileSdk` raised and building green before behaviour fixes.
- [ ] Behaviour changes read for every skipped level, listed on the PR.
- [ ] Edge-to-edge drawn deliberately; insets consumed at the scaffold.
- [ ] Gesture nav and three-button nav both verified.
- [ ] Back handled by callbacks/navigation, predictive back does not exit unexpectedly.
- [ ] New runtime permissions requested at point of use with denial paths.
- [ ] Foreground services declare matching types and permissions.
- [ ] Exact alarms degrade to inexact when not granted.
- [ ] `registerReceiver` declares the exported flag everywhere.
- [ ] Native libraries rebuilt for the required page alignment.
- [ ] Restricted-settings flows explained and deep-linked.
- [ ] Verified on new level, previous level, and minSdk device.
- [ ] Per-level record written (change → commit).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Regressions after a 3-level jump | one commit, no attribution | one level per cycle | changes overlap |
| Layout under the status bar | opt-out attribute | draw edge-to-edge + insets | opt-out is temporary |
| Back closes the app | `finish()` in `onBackPressed` | callback/`BackHandler` + nav stack | gesture changes routing |
| Feature silently dead | permission added, never asked | request at point of use | denial is invisible |
| Crash on broadcast | flag omitted | exported flag explicit | runtime exception |
| Rejected Play upload | targetSdk lowered to dodge | fix changes, then raise | requirement is a deadline |
| Native lib fails to load | keep old prebuilt `.so` | rebuild for page size | loader rejects mapping |

## Verify

```bash
./gradlew :app:lintVitalRelease
adb -s <serial> shell getprop ro.build.version.sdk
adb -s <serial> shell dumpsys package <pkg> | grep -E 'targetSdk|versionName'
# toggle one behaviour change to confirm the app copes both ways
adb -s <serial> shell am compat enable <change-id> <pkg>
adb -s <serial> shell monkey -p <pkg> -c android.intent.category.LAUNCHER 200
```

Expected: lintVital reports no `NewApi`/`Deprecated`/target-SDK findings for the release build, the
installed package reports the new `targetSdk`, and a monkey run on a new-level device produces no
crash, ANR, or layout that overlaps a system bar.

## References

- Android behaviour-changes documentation per API level
- `am compat enable/disable` for individual behaviour changes
- `enableEdgeToEdge`, `WindowInsets`, `OnBackPressedCallback`, `BackHandler`
- Foreground service types, exact-alarm capability, receiver export flags
