---
name: adb-automation
description: >-
  Drive a real device or emulator deterministically over ADB — tap, type, scroll, inspect the UI
  tree, capture screenshots, read logs — with waits and assertions instead of sleeps. Use when
  scripting a device flow, verifying a build on hardware, writing an automated smoke test,
  reproducing a field bug, or debugging a stuck UI test, and when multiple devices are attached.
license: Apache-2.0
metadata:
  domain: device
  level: core
  sources:
    - android-adb-skill
    - android-qa-kit
    - android-skill (artemis)
    - android-agent-engineering (android-testing)
---

# ADB Automation

ADB is a collection of one-shot commands with no session. Every reliable automation is a loop:
**observe → decide → act → observe**, with a timeout. Anything that assumes a fixed delay will
fail on a slower device.

## Use when

- Scripting an install-launch-assert flow on a device/emulator.
- Driving UI without writing an instrumented test.
- Verifying a release build or an AAB-derived APK on hardware.
- Reproducing a reported bug from steps described by a user.
- Debugging a hung instrumented test or a flaky automation.

## Do not use when

- The flow belongs in CI as a repeatable test → `compose-ui-testing` / `e2e-device-testing`.
- The goal is measuring performance → `startup-and-perfetto` / `baseline-profiles`.
- The goal is reading a crash cause → `bug-fix`.

## Rules

1. **Always target a device explicitly.** With more than one attached, `adb` fails or picks the
   wrong one. Resolve once and use `-s`:
   ```bash
   ADB="adb -s $(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
   ```
2. **Never `sleep` as synchronization.** Poll the observable condition:
   ```bash
   wait_for() { for i in $(seq 1 50); do eval "$1" && return 0; sleep 0.2; done; return 1; }
   ```
   A sleep that is long enough today is a flake tomorrow and wasted time always.
3. **Wait for the *screen*, not the launch command.** `am start -W` waits for the activity, not
   for data to render. Confirm with the focused window or a UI node:
   `adb shell dumpsys window | grep -m1 mCurrentFocus`.
4. **Locate elements by text/bounds from the UI tree, not by remembered coordinates.**
   `adb shell uiautomator dump` → parse `bounds="[x1,y1][x2,y2]"` → tap the centre. Coordinates
   hardcoded from one device break on another density/resolution.
5. **`input text` has no escaping.** Spaces must be `%s`; shell metacharacters must be quoted for
   both adb and the device shell. Prefer `input keyevent` for special keys, and verify the text
   landed by reading the UI tree.
6. **Clear the app state between runs, or use distinct accounts.** `pm clear <pkg>` for a clean
   first-run; otherwise your automation tests the second-run path and misses onboarding bugs.
7. **Capture evidence on failure, not only on success.** Screenshot + `logcat -d` on any timeout;
   a failed automation without evidence is a re-run, not a diagnosis.
8. **Use `exec-out screencap -p` for a clean PNG.** `screencap -p > file` through `shell` can
   corrupt line endings on some shells.
9. **Read logs by tag range, and clear first.** `logcat -c`, reproduce, then `logcat -d -v threadtime`
   and slice by pid: `--pid=$(pidof <pkg>)`. Unbounded logcat is mostly other apps' noise.
10. **Uninstall/`pm clear` the test artefacts.** A leftover `pm grant`ed permission changes the
    behaviour of the next run and hides permission-request bugs.

## Procedure

1. Select the device (rule 1); assert exactly one is chosen.
2. Reset state: `$ADB shell pm clear <pkg>` when the flow starts from first run.
3. Install and launch with wait:
   ```bash
   $ADB install -r app/build/outputs/apk/debug/app-debug.apk
   $ADB shell am start -W -n <pkg>/<launchActivity>
   ```
4. Observe: `$ADB shell uiautomator dump /sdcard/ui.xml && $ADB pull /sdcard/ui.xml /tmp/`
5. Parse for the target text; tap its bounds centre.
6. Assert the next screen's text; on failure capture screenshot + logcat (rule 7).
7. Repeat with the polling helper; total timeout per step.

## Checklist

- [ ] Device selected explicitly; script fails fast with ≠1 device.
- [ ] No bare `sleep`; every wait is a polled condition with a timeout.
- [ ] Element positions derived from the UI dump, not literals.
- [ ] Text input verified by re-reading the tree.
- [ ] State reset (`pm clear` / fresh install) at flow start.
- [ ] Screenshot + logcat dumped on failure.
- [ ] Logs sliced by pid, buffer cleared before reproduction.
- [ ] Permissions granted/revoked explicitly if the flow depends on them.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Flaky script | `sleep 3` between steps | poll UI tree until node appears | device speed varies |
| Wrong device tapped | bare `adb shell input tap` | `-s <serial>` | multi-device ambiguity |
| Works on my phone | coordinates from own device | bounds from `uiautomator dump` | density/resolution |
| Text missing spaces | `input text Hello World` | `input text 'Hello%sWorld'` | device shell splits args |
| Second-run only | never clear state | `pm clear` at start | onboarding path untested |
| No idea why it failed | assert + exit | screenshot + `logcat -d` | unreproducible failure |
| Logcat soup | `logcat` unfiltered | `--pid=$(pidof pkg)` | other apps' noise |

## Verify

```bash
adb devices -l
adb -s <serial> shell pm clear <pkg>
adb -s <serial> shell am start -W -n <pkg>/.MainActivity
adb -s <serial> shell dumpsys window | grep -m1 mCurrentFocus
adb -s <serial> exec-out screencap -p > /tmp/shot.png
```

Expected: `mCurrentFocus` names your activity (not the launcher, not a system dialog), and the
screenshot shows rendered content rather than a white frame.

## References

- `adb shell input` (tap/swipe/text/keyevent), `am start -W`, `pm clear`
- `uiautomator dump` output format — `node` attributes `text`, `resource-id`, `bounds`
